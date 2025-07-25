from flask import render_template, request, redirect, url_for, flash, session, jsonify
from app import app, db, socketio
from flask_socketio import emit
from models import Order, FlowerCrown
from utils.receipt_generator import generate_receipt
import os
import stripe
from datetime import datetime, date, timedelta
from functools import wraps
import cloudinary.uploader
import time
import hashlib
from flask import send_from_directory
from flask import Response
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment
from io import BytesIO
from utils.email_sender import send_receipt_email


# --- DECORADOR DE LOGIN ---
def login_required(f):

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)

    return decorated_function


# --- FUNÇÃO AUXILIAR PARA ATUALIZAR ESTATÍSTICAS ---
def emit_updated_statistics():
    """Busca os dados mais recentes e emite para os clientes via WebSocket."""
    # O app_context é necessário para aceder à base de dados fora de uma rota normal
    with app.app_context():
        try:
            now_utc = datetime.utcnow()
            now_brt = now_utc - timedelta(hours=3)
            start_of_day_brt = datetime.combine(now_brt.date(),
                                                datetime.min.time())
            start_of_day_utc = start_of_day_brt + timedelta(hours=3)

            # Otimização: Faz as contagens diretamente na base de dados
            total_orders = db.session.query(Order).count()
            today_orders = db.session.query(Order).filter(
                Order.order_date >= start_of_day_utc).count()
            completed_orders = db.session.query(Order).filter_by(
                status='delivered').count()

            statistics = {
                'total_orders': total_orders,
                'today_orders': today_orders,
                'completed_orders': completed_orders,
                'timestamp': now_utc.isoformat() + "Z"
            }
            socketio.emit('statistics_updated', statistics)
            print(f"Estatísticas atualizadas emitidas: {statistics}")
        except Exception as e:
            print(f'Erro ao emitir estatísticas: {e}')


# Configurações
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
YOUR_DOMAIN = os.environ.get('REPLIT_DEV_DOMAIN', 'localhost:5000')


# --- ROTAS PÚBLICAS ---
@app.route('/')
def index():
    crowns = FlowerCrown.query.order_by(FlowerCrown.position).all()
    return render_template('index.html', crowns=crowns)


@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    crown_id = request.form.get('crown_id')
    custom_message = request.form.get('custom_message', '')
    crown = FlowerCrown.query.get_or_404(crown_id)
    session['cart'] = {
        'crown_id': crown.id,
        'crown_name': crown.name,
        'crown_price': crown.price,
        'custom_message': custom_message
    }
    return redirect(url_for('checkout'))


@app.route('/checkout')
def checkout():
    if 'cart' not in session:
        flash('Nenhum item no carrinho.', 'error')
        return redirect(url_for('index'))
    return render_template('checkout.html', cart=session['cart'])


@app.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    if 'cart' not in session:
        return redirect(url_for('index'))
    cart = session['cart']

    customer_info = {
        'customer_name': request.form.get('customer_name'),
        'customer_email': request.form.get('customer_email'),
        'customer_phone': request.form.get('customer_phone'),
        'payment_method': request.form.get('payment_method'),
        'installments': int(request.form.get('installments', 1)),
        'deceased_name': request.form.get('deceased_name'),
        'delivery_location': request.form.get('delivery_location'),
        'chapel': request.form.get('chapel'),
        'opening_time': request.form.get('opening_time')
    }

    base_price = cart.get('crown_price', 0.0)

    total_amount = base_price
    if customer_info['payment_method'] == 'credit' and customer_info[
            'installments'] > 1:
        total_amount = base_price * (1 + 0.015 *
                                     (customer_info['installments'] - 1))

    customer_info['total_amount'] = total_amount
    session['customer_info'] = customer_info

    try:
        payment_method_types = []
        if customer_info['payment_method'] == 'pix':
            payment_method_types.append('pix')
        else:  # Para 'debit' e 'credit'
            payment_method_types.append('card')

        checkout_session = stripe.checkout.Session.create(
            payment_method_types=payment_method_types,
            line_items=[{
                'price_data': {
                    'currency': 'brl',
                    'product_data': {
                        'name':
                        cart.get('crown_name'),
                        'description':
                        f"Homenagem para: {customer_info.get('deceased_name', 'Não informado')}"
                    },
                    'unit_amount': int(customer_info['total_amount'] * 100),
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=
            f'https://{YOUR_DOMAIN}/payment-success?session_id={{CHECKOUT_SESSION_ID}}',
            cancel_url=f'https://{YOUR_DOMAIN}/checkout',
            customer_email=customer_info['customer_email'])
        return redirect(checkout_session.url, code=303)

    except Exception as e:
        print(f"Erro ao criar sessão no Stripe: {e}")
        flash(
            f'Ocorreu um erro ao processar seu pagamento. Por favor, verifique se sua chave de API da Stripe está configurada corretamente.',
            'danger')
        return redirect(url_for('checkout'))


@app.route('/payment-success')
def payment_success():
    session_id = request.args.get('session_id')
    if not session_id:
        flash('Sessão de pagamento inválida.', 'error')
        return redirect(url_for('index'))

    try:
        checkout_session = stripe.checkout.Session.retrieve(session_id)
        if checkout_session.payment_status == 'paid':
            cart = session.pop('cart', {})
            customer_info = session.pop('customer_info', {})

            if not customer_info:
                flash('Sua sessão expirou. Por favor, tente novamente.',
                      'error')
                return redirect(url_for('index'))

            order = Order(
                customer_name=customer_info.get('customer_name'),
                customer_email=customer_info.get('customer_email'),
                customer_phone=customer_info.get('customer_phone'),
                crown_id=cart.get('crown_id'),
                crown_name=cart.get('crown_name'),
                crown_price=cart.get('crown_price'),
                custom_message=cart.get('custom_message'),
                payment_method=customer_info.get('payment_method'),
                installments=customer_info.get('installments'),
                total_amount=customer_info.get('total_amount'),
                status='pending',
                deceased_name=customer_info.get('deceased_name'),
                delivery_location=customer_info.get('delivery_location'),
                chapel=customer_info.get('chapel'),
                opening_time=customer_info.get('opening_time'))

            db.session.add(order)
            db.session.commit()

            try:
                filepath = generate_receipt(order)
                send_receipt_email(order, filepath)
            except Exception as e:
                print(
                    f"ERRO CRÍTICO: Não foi possível gerar o recibo ou enviar o e-mail. Erro: {e}"
                )

            # Prepara os dados do novo pedido para enviar em tempo real
            order_data = {
                "id":
                order.id,
                "customer_name":
                order.customer_name,
                "crown_name":
                order.crown_name,
                "order_date_formatted":
                (order.order_date -
                 timedelta(hours=3)).strftime('%d/%m/%Y %H:%M'),
                "order_date_iso":
                order.order_date.isoformat() + "Z"
            }

            # ATUALIZAÇÃO: Emitimos o evento com o nome correto
            socketio.emit('new_order_notification', order_data)

            # ATUALIZAÇÃO: Chamamos a função para atualizar as estatísticas
            emit_updated_statistics()

            session['last_order_id'] = order.id

            return render_template('success.html', order=order)

        else:
            flash(
                'O pagamento não foi confirmado. Por favor, tente novamente.',
                'error')
            return redirect(url_for('checkout'))

    except Exception as e:
        flash(f'Ocorreu um erro ao verificar seu pagamento: {str(e)}', 'error')
        return redirect(url_for('checkout'))


@app.route('/download-receipt/<int:order_id>')
def download_receipt(order_id):
    if 'logged_in' not in session and session.get('last_order_id') != order_id:
        flash('Acesso não autorizado para baixar este recibo.', 'error')
        return redirect(url_for('index'))

    try:
        order = Order.query.get_or_404(order_id)
        filepath = generate_receipt(order)
        directory = os.path.dirname(filepath)
        filename = os.path.basename(filepath)

        return send_from_directory(directory, filename, as_attachment=True)

    except Exception as e:
        flash(f'Ocorreu um erro ao gerar o comprovativo: {str(e)}', 'danger')
        return redirect(url_for('index'))


# --- ROTAS DE ADMIN ---


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Lê o utilizador e a senha dos Secrets
        admin_user = os.environ.get('ADMIN_USER')
        admin_password = os.environ.get('ADMIN_PASSWORD')

        # Compara com os dados enviados pelo formulário
        if request.form.get('username') == admin_user and request.form.get(
                'password') == admin_password:
            session['logged_in'] = True
            flash('Login realizado com sucesso!', 'success')
            return redirect(url_for('admin'))
        else:
            flash('Credenciais inválidas.', 'error')
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    session.pop('logged_in', None)
    flash('Sessão terminada com sucesso.', 'success')
    return redirect(url_for('login'))


@app.route('/admin')
@login_required
def admin():
    crowns = FlowerCrown.query.order_by(FlowerCrown.position).all()
    # ATUALIZAÇÃO: Chamamos a função para garantir que as estatísticas estão atualizadas ao carregar a página
    emit_updated_statistics()
    return render_template('admin.html', crowns=crowns)


@app.route('/admin/add', methods=['POST'])
@login_required
def add_crown():
    try:
        price_str = request.form.get('price',
                                     '0,00').replace('R$', '').strip().replace(
                                         '.', '').replace(',', '.')
        max_pos = db.session.query(db.func.max(
            FlowerCrown.position)).scalar() or 0
        new_crown = FlowerCrown(name=request.form.get('name'),
                                description=request.form.get('description'),
                                price=float(price_str),
                                image_url=request.form.get('image_url'),
                                position=max_pos + 1)
        db.session.add(new_crown)
        db.session.commit()
        flash(f'Coroa "{new_crown.name}" adicionada!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao adicionar coroa: {str(e)}', 'error')
    return redirect(url_for('admin'))


@app.route('/admin/edit/<int:crown_id>', methods=['POST'])
@login_required
def edit_crown(crown_id):
    crown = FlowerCrown.query.get_or_404(crown_id)
    try:
        price_str = request.form.get('price',
                                     '0,00').replace('R$', '').strip().replace(
                                         '.', '').replace(',', '.')
        crown.name, crown.description, crown.price, crown.image_url = request.form.get(
            'name'), request.form.get('description'), float(
                price_str), request.form.get('image_url')
        db.session.commit()
        flash(f'Coroa "{crown.name}" atualizada!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao editar coroa: {str(e)}', 'error')
    return redirect(url_for('admin'))


@app.route('/admin/delete/<int:crown_id>')
@login_required
def delete_crown(crown_id):
    crown = FlowerCrown.query.get_or_404(crown_id)
    try:
        db.session.delete(crown)
        db.session.commit()
        flash(f'Coroa "{crown.name}" removida.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao remover coroa: {str(e)}', 'error')
    return redirect(url_for('admin'))


@app.route('/admin/sign-upload', methods=['POST'])
@login_required
def sign_upload():
    api_key, api_secret, cloud_name = os.environ.get(
        'CLOUDINARY_API_KEY'), os.environ.get(
            'CLOUDINARY_API_SECRET'), os.environ.get('CLOUDINARY_CLOUD_NAME')
    timestamp = str(int(time.time()))
    params_to_sign = {'timestamp': timestamp, 'eager': 'c_fill,h_400,w_600'}
    to_sign = "&".join(f"{k}={v}" for k, v in sorted(params_to_sign.items()))
    signature = hashlib.sha1(
        (to_sign + api_secret).encode('utf-8')).hexdigest()
    return jsonify({
        'signature': signature,
        'timestamp': timestamp,
        'api_key': api_key,
        'cloud_name': cloud_name,
        'eager': params_to_sign['eager']
    })


@app.route('/admin/crown/move/<int:crown_id>/<string:direction>',
           methods=['POST'])
@login_required
def move_crown(crown_id, direction):
    crowns = list(FlowerCrown.query.order_by(FlowerCrown.position).all())
    idx_to_move = next((i for i, c in enumerate(crowns) if c.id == crown_id),
                       -1)
    if idx_to_move == -1:
        return jsonify({
            'success': False,
            'message': 'Coroa não encontrada.'
        }), 404
    if direction == 'up' and idx_to_move > 0:
        crowns.insert(idx_to_move - 1, crowns.pop(idx_to_move))
    elif direction == 'down' and idx_to_move < len(crowns) - 1:
        crowns.insert(idx_to_move + 1, crowns.pop(idx_to_move))
    else:
        return jsonify({'success': False, 'message': 'Movimento inválido.'})
    for i, crown in enumerate(crowns):
        crown.position = i + 1
    try:
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/admin/orders')
@login_required
def order_management():
    now_utc = datetime.utcnow()
    now_brt = now_utc - timedelta(hours=3)
    start_of_day_brt = datetime.combine(now_brt.date(), datetime.min.time())
    end_of_day_brt = datetime.combine(now_brt.date(), datetime.max.time())
    start_of_day_utc = start_of_day_brt + timedelta(hours=3)
    end_of_day_utc = end_of_day_brt + timedelta(hours=3)

    orders_pending = Order.query.filter_by(status='pending').order_by(
        Order.order_date.asc()).all()
    orders_in_progress = Order.query.filter_by(status='in_progress').order_by(
        Order.order_date.asc()).all()
    orders_delivered = Order.query.filter(
        Order.status == 'delivered', Order.order_date >= start_of_day_utc,
        Order.order_date
        <= end_of_day_utc).order_by(Order.order_date.desc()).all()

    return render_template('orders.html',
                           pending=orders_pending,
                           in_progress=orders_in_progress,
                           delivered=orders_delivered)


@app.route('/admin/reports')
@login_required
def reports():
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    query = Order.query

    if start_date_str:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        query = query.filter(Order.order_date >= start_date)

    if end_date_str:
        end_date = datetime.strptime(end_date_str,
                                     '%Y-%m-%d') + timedelta(days=1)
        query = query.filter(Order.order_date < end_date)

    orders = query.order_by(Order.order_date.desc()).all()
    total_revenue = sum(order.total_amount for order in orders)

    return render_template('reports.html',
                           orders=orders,
                           total_revenue=total_revenue,
                           start_date=start_date_str,
                           end_date=end_date_str)


@app.route('/admin/order/details/<int:order_id>')
@login_required
def get_order_details(order_id):
    order = Order.query.get_or_404(order_id)
    order_details = {
        "id":
        f"#{order.id}",
        "status":
        order.status.replace('_', ' ').title(),
        "order_date":
        (order.order_date - timedelta(hours=3)).strftime('%d/%m/%Y às %H:%M'),
        "total_amount":
        f"R$ {order.total_amount:.2f}",
        "customer_name":
        order.customer_name,
        "customer_phone":
        order.customer_phone,
        "customer_email":
        order.customer_email,
        "crown_name":
        order.crown_name,
        "custom_message":
        order.custom_message or "Nenhuma",
        "deceased_name":
        order.deceased_name or "Não informado",
        "delivery_location":
        order.delivery_location or "Não informado",
        "chapel":
        order.chapel or "Não informado",
        "opening_time":
        order.opening_time or "Não informado"
    }
    return jsonify(order_details)


@app.route('/admin/export-report')
@login_required
def export_report():
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    query = Order.query

    if start_date_str:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        query = query.filter(Order.order_date >= start_date)
    if end_date_str:
        end_date = datetime.strptime(end_date_str,
                                     '%Y-%m-%d') + timedelta(days=1)
        query = query.filter(Order.order_date < end_date)

    orders = query.order_by(Order.order_date.desc()).all()
    wb = Workbook()
    ws = wb.active
    ws.title = "Relatorio de Pedidos"
    headers = [
        "ID do Pedido", "Data", "Cliente", "Email", "Telefone", "Produto",
        "Valor", "Status", "Homenageado", "Local Entrega"
    ]
    ws.append(headers)
    bold_font = Font(bold=True)
    for cell in ws[1]:
        cell.font = bold_font
        cell.alignment = Alignment(horizontal="center")
    for order in orders:
        local_date = (order.order_date -
                      timedelta(hours=3)).strftime('%d/%m/%Y %H:%M')
        ws.append([
            order.id, local_date, order.customer_name, order.customer_email,
            order.customer_phone, order.crown_name, order.total_amount,
            order.status, order.deceased_name, order.delivery_location
        ])
    for col in ws.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = (max_length + 2)
        ws.column_dimensions[column].width = adjusted_width
    virtual_workbook = BytesIO()
    wb.save(virtual_workbook)
    virtual_workbook.seek(0)
    filename = "relatorio_pedidos.xlsx"
    if start_date_str and end_date_str:
        filename = f"relatorio_{start_date_str}_a_{end_date_str}.xlsx"
    return Response(
        virtual_workbook,
        mimetype=
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': f'attachment;filename={filename}'})


@app.route('/admin/order/delete', methods=['POST'])
@login_required
def delete_order_from_report():
    """Apaga um pedido da base de dados após confirmação com senha."""
    data = request.get_json()
    order_id = data.get('order_id')
    password = data.get('password')

    # Busca a senha segura guardada nos Secrets
    delete_password = os.environ.get('DELETE_PASSWORD', '1234')

    if not password or password != delete_password:
        return jsonify({'success': False, 'message': 'Senha incorreta.'}), 403

    order = Order.query.get(order_id)
    if order:
        try:
            db.session.delete(order)
            db.session.commit()
            # Opcional: Notificar outros admins em tempo real que o pedido foi apagado
            socketio.emit('order_deleted', {
                'order_id': order_id,
                'customer_name': order.customer_name
            })
            return jsonify({
                'success':
                True,
                'message':
                f'Pedido #{order_id} apagado com sucesso.'
            })
        except Exception as e:
            db.session.rollback()
            return jsonify({
                'success': False,
                'message': f'Erro ao apagar o pedido: {str(e)}'
            }), 500
    else:
        return jsonify({
            'success': False,
            'message': 'Pedido não encontrado.'
        }), 404


# ============ EVENTOS SOCKETIO PARA TEMPO REAL ============
@socketio.on('connect')
def handle_connect():
    print(f'Cliente conectado: {request.sid}')


@socketio.on('disconnect')
def handle_disconnect():
    print(f'Cliente desconectado: {request.sid}')


@socketio.on('join_admin')
def handle_join_admin():
    print(f'Admin conectado: {request.sid}')


@socketio.on('update_order_status')
def handle_update_order_status(data):
    try:
        order_id = data.get('order_id')
        new_status = data.get('new_status')
        if not order_id or not new_status: return

        order = Order.query.get(order_id)
        if not order or new_status not in [
                'pending', 'in_progress', 'delivered'
        ]:
            return

        old_status = order.status
        order.status = new_status
        db.session.commit()

        socketio.emit(
            'order_status_updated', {
                'order_id': order_id,
                'old_status': old_status,
                'new_status': new_status,
                'customer_name': order.customer_name,
                'timestamp': datetime.now().isoformat() + "Z"
            })

        # ATUALIZAÇÃO: Chamamos a função para atualizar as estatísticas
        emit_updated_statistics()
        print(
            f'Status do pedido {order_id} atualizado: {old_status} -> {new_status}'
        )

    except Exception as e:
        db.session.rollback()
        print(f'Erro ao atualizar status do pedido: {e}')


@socketio.on('delete_order')
def handle_delete_order(data):
    try:
        order_id = data.get('order_id')
        if not order_id: return

        order = Order.query.get(order_id)
        if not order: return

        customer_name = order.customer_name
        db.session.delete(order)
        db.session.commit()

        socketio.emit(
            'order_deleted', {
                'order_id': order_id,
                'customer_name': customer_name,
                'timestamp': datetime.now().isoformat() + "Z"
            })

        # ATUALIZAÇÃO: Chamamos a função para atualizar as estatísticas
        emit_updated_statistics()
        print(f'Pedido {order_id} ({customer_name}) foi excluído')

    except Exception as e:
        db.session.rollback()
        print(f'Erro ao excluir pedido: {e}')


# ATUALIZAÇÃO: Função 'handle_new_order' foi REMOVIDA
