from flask import render_template, request, redirect, url_for, flash, session, jsonify
from app import app, db
from models import Order, FlowerCrown
from utils.receipt_generator import generate_receipt
import os
import stripe
from datetime import datetime
from functools import wraps
import cloudinary.uploader

# Configure Stripe
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')

# Lógica mais segura para definir o domínio da aplicação
YOUR_DOMAIN = 'localhost:5000'
replit_domain = os.environ.get('REPLIT_DEV_DOMAIN')
replit_domains_list = os.environ.get('REPLIT_DOMAINS')

if replit_domain:
    YOUR_DOMAIN = replit_domain
elif replit_domains_list:
    YOUR_DOMAIN = replit_domains_list.split(',')[0]


def upload_image_to_cloudinary(file_to_upload):
    if not file_to_upload:
        return None
    try:
        upload_result = cloudinary.uploader.upload(file_to_upload)
        return upload_result['secure_url']
    except Exception as e:
        print(f"Erro no upload para o Cloudinary: {e}")
        return None

@app.route('/')
def index():
    crowns = FlowerCrown.query.order_by(FlowerCrown.id).all()
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
    cart = session['cart']
    return render_template('checkout.html', cart=cart)

@app.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    if 'cart' not in session:
        flash('Nenhum item no carrinho.', 'error')
        return redirect(url_for('index'))

    cart = session['cart']

    customer_name = request.form.get('customer_name', '')
    customer_email = request.form.get('customer_email', '')
    customer_phone = request.form.get('customer_phone', '')
    payment_method = request.form.get('payment_method', 'pix')
    installments = int(request.form.get('installments', 1))

    base_price = cart.get('crown_price', 0.0)
    if payment_method == 'credit_installments' and installments > 1:
        monthly_rate = 0.015
        total_amount = base_price * (1 + monthly_rate * installments)
    else:
        total_amount = base_price

    session['customer_info'] = {
        'customer_name': customer_name,
        'customer_email': customer_email,
        'customer_phone': customer_phone,
        'payment_method': payment_method,
        'installments': installments,
        'total_amount': total_amount
    }

    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'brl',
                    'product_data': {
                        'name': cart.get('crown_name', 'Produto sem nome'),
                        'description': f"Coroa de flores - {cart.get('custom_message', '')}"
                    },
                    'unit_amount': int(total_amount * 100),
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=f'https://{YOUR_DOMAIN}/payment-success?session_id={{CHECKOUT_SESSION_ID}}',
            cancel_url=f'https://{YOUR_DOMAIN}/checkout',
            customer_email=customer_email,
            metadata={
                'customer_name': customer_name,
                'customer_phone': customer_phone,
                'crown_id': str(cart.get('crown_id', 0)),
                'custom_message': cart.get('custom_message', ''),
                'payment_method': payment_method,
                'installments': str(installments)
            })

        # --- CORREÇÃO DE ERRO ('redirect' com None) ---
        # Verificamos se o URL existe antes de redirecionar
        if checkout_session and checkout_session.url:
            return redirect(checkout_session.url, code=303)
        else:
            flash('Não foi possível gerar o link de pagamento.', 'error')
            return redirect(url_for('checkout'))

    except Exception as e:
        flash(f'Erro ao processar pagamento: {str(e)}', 'error')
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
            cart = session.get('cart', {})
            customer_info = session.get('customer_info', {})
            if not cart or not customer_info:
                flash('Informações do pedido não encontradas.', 'error')
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
                status='completed'
            )
            db.session.add(order)
            db.session.commit()
            receipt_path = generate_receipt(order)
            session.pop('cart', None)
            session.pop('customer_info', None)
            session['last_order'] = {
                'id': order.id,
                'receipt_path': receipt_path,
                'customer_name': customer_info.get('customer_name')
            }
            return redirect(url_for('success'))
        else:
            flash('Pagamento não foi processado com sucesso.', 'error')
            return redirect(url_for('checkout'))
    except Exception as e:
        flash(f'Erro ao verificar pagamento: {str(e)}', 'error')
        return redirect(url_for('checkout'))

@app.route('/success')
def success():
    if 'last_order' not in session:
        return redirect(url_for('index'))
    order_info = session['last_order']
    return render_template('success.html', order=order_info)

#-----------------------------------------
# Admin Routes
#-----------------------------------------

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            flash('É necessário fazer login para aceder a esta página.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        ADMIN_USER = os.environ.get('ADMIN_USER', 'admin')
        ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', '1234')
        if request.form.get('username') == ADMIN_USER and request.form.get('password') == ADMIN_PASSWORD:
            session['logged_in'] = True
            flash('Login realizado com sucesso!', 'success')
            return redirect(url_for('admin'))
        else:
            flash('Nome de utilizador ou palavra-passe inválidos.', 'error')
    if 'logged_in' in session:
        return redirect(url_for('admin'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash('Sessão terminada com sucesso.', 'success')
    return redirect(url_for('login'))

@app.route('/admin')
@login_required
def admin():
    crowns = FlowerCrown.query.order_by(FlowerCrown.id).all()
    return render_template('admin.html', crowns=crowns)

@app.route('/admin/add', methods=['POST'])
@login_required
def add_crown():
    try:
        name = request.form.get('name', 'Coroa sem nome')
        description = request.form.get('description', '')
        price = float(request.form.get('price', 0.0))
        image_file = request.files.get('image_file')

        if not image_file:
            flash('A imagem é obrigatória.', 'error')
            return redirect(url_for('admin'))
        image_url = upload_image_to_cloudinary(image_file)
        if not image_url:
            flash('Erro ao fazer upload da imagem.', 'error')
            return redirect(url_for('admin'))

        new_crown = FlowerCrown(
            name=name,
            description=description,
            price=price,
            image_url=image_url
        )
        db.session.add(new_crown)
        db.session.commit()
        flash(f'Coroa "{name}" adicionada com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao adicionar coroa: {str(e)}', 'error')
    return redirect(url_for('admin'))

@app.route('/admin/edit/<int:crown_id>', methods=['POST'])
@login_required
def edit_crown(crown_id):
    crown = FlowerCrown.query.get_or_404(crown_id)
    try:
        crown.name = request.form.get('name', 'Coroa sem nome')
        crown.description = request.form.get('description', '')
        crown.price = float(request.form.get('price', 0.0))
        image_file = request.files.get('image_file')

        if image_file:
            image_url = upload_image_to_cloudinary(image_file)
            if image_url:
                crown.image_url = image_url
            else:
                flash('Erro ao fazer upload da nova imagem.', 'error')
                return redirect(url_for('admin'))
        db.session.commit()
        flash(f'Coroa "{crown.name}" atualizada com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao editar coroa: {str(e)}', 'error')
    return redirect(url_for('admin'))

@app.route('/admin/delete/<int:crown_id>')
@login_required
def delete_crown(crown_id):
    crown = FlowerCrown.query.get_or_404(crown_id)
    try:
        crown_name = crown.name
        db.session.delete(crown)
        db.session.commit()
        flash(f'Coroa "{crown_name}" removida com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao remover coroa: {str(e)}', 'error')
    return redirect(url_for('admin'))