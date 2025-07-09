from flask import render_template, request, redirect, url_for, flash, session, jsonify
from app import app, db
from models import Order, FlowerCrown
from utils.receipt_generator import generate_receipt
import os
import stripe
from datetime import datetime
from functools import wraps
import cloudinary.uploader
import time
import hashlib

# Configurações (sem alteração)
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
YOUR_DOMAIN = os.environ.get('REPLIT_DEV_DOMAIN', 'localhost:5000')


# Rotas Públicas (sem alteração)
@app.route('/')
def index():
    crowns = FlowerCrown.query.order_by(FlowerCrown.position).all()
    return render_template('index.html', crowns=crowns)


# ... (outras rotas públicas continuam iguais) ...
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
    if 'cart' not in session: return redirect(url_for('index'))
    return render_template('checkout.html', cart=session['cart'])


@app.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    if 'cart' not in session: return redirect(url_for('index'))
    cart, customer_info = session['cart'], {
        'customer_name': request.form.get('customer_name'),
        'customer_email': request.form.get('customer_email'),
        'customer_phone': request.form.get('customer_phone'),
        'payment_method': request.form.get('payment_method'),
        'installments': int(request.form.get('installments', 1)),
        'total_amount': 0.0
    }
    base_price = cart.get('crown_price', 0.0)
    customer_info['total_amount'] = base_price * (
        1 + 0.015 * (customer_info['installments'] - 1)) if customer_info[
            'payment_method'] == 'credit_installments' and customer_info[
                'installments'] > 1 else base_price
    session['customer_info'] = customer_info
    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'brl',
                    'product_data': {
                        'name': cart.get('crown_name'),
                        'description': f"Coroa - {cart.get('custom_message')}"
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
        flash(f'Erro: {str(e)}', 'error')
        return redirect(url_for('checkout'))


@app.route('/payment-success')
def payment_success():
    if not (session_id := request.args.get('session_id')):
        return redirect(url_for('index'))
    try:
        if stripe.checkout.Session.retrieve(
                session_id).payment_status == 'paid':
            cart, customer_info = session.get('cart', {}), session.get(
                'customer_info', {})
            order = Order(customer_name=customer_info.get('customer_name'),
                          customer_email=customer_info.get('customer_email'),
                          customer_phone=customer_info.get('customer_phone'),
                          crown_id=cart.get('crown_id'),
                          crown_name=cart.get('crown_name'),
                          crown_price=cart.get('crown_price'),
                          custom_message=cart.get('custom_message'),
                          payment_method=customer_info.get('payment_method'),
                          installments=customer_info.get('installments'),
                          total_amount=customer_info.get('total_amount'),
                          status='completed')
            db.session.add(order)
            db.session.commit()
            session.pop('cart', None)
            session.pop('customer_info', None)
            session['last_order'] = {
                'id': order.id,
                'customer_name': customer_info.get('customer_name')
            }
            return redirect(url_for('success'))
    except Exception:
        pass
    return redirect(url_for('checkout'))


@app.route('/success')
def success():
    if 'last_order' not in session: return redirect(url_for('index'))
    return render_template('success.html', order=session['last_order'])


# --- ROTAS DE ADMIN ---
def login_required(f):

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session: return redirect(url_for('login'))
        return f(*args, **kwargs)

    return decorated_function


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST' and request.form.get(
            'username') == os.environ.get(
                'ADMIN_USER',
                'admin') and request.form.get('password') == os.environ.get(
                    'ADMIN_PASSWORD', '1234'):
        session['logged_in'] = True
        return redirect(url_for('admin'))
    elif request.method == 'POST':
        flash('Credenciais inválidas.', 'error')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))


@app.route('/admin')
@login_required
def admin():
    crowns = FlowerCrown.query.order_by(FlowerCrown.position).all()
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
        flash(f'Erro: {str(e)}', 'error')
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
        flash(f'Erro: {str(e)}', 'error')
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
        flash(f'Erro: {str(e)}', 'error')
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


# ===================================================================
# ROTA DE REORDENAÇÃO CORRIGIDA
# ===================================================================
@app.route('/admin/crown/move/<int:crown_id>/<string:direction>',
           methods=['POST'])
@login_required
def move_crown(crown_id, direction):
    crowns = list(FlowerCrown.query.order_by(FlowerCrown.position).all())

    # Encontra o índice do item a ser movido
    idx_to_move = -1
    for i, crown in enumerate(crowns):
        if crown.id == crown_id:
            idx_to_move = i
            break

    if idx_to_move == -1:
        return jsonify({
            'success': False,
            'message': 'Coroa não encontrada.'
        }), 404

    # Calcula o novo índice e faz a troca na lista
    if direction == 'up' and idx_to_move > 0:
        crowns.insert(idx_to_move - 1, crowns.pop(idx_to_move))
    elif direction == 'down' and idx_to_move < len(crowns) - 1:
        crowns.insert(idx_to_move + 1, crowns.pop(idx_to_move))
    else:
        return jsonify({'success': False, 'message': 'Movimento inválido.'})

    # Reatribui todas as posições para garantir a consistência
    for i, crown in enumerate(crowns):
        crown.position = i + 1

    try:
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
