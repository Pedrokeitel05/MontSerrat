from flask import render_template, request, redirect, url_for, flash, session, jsonify
from app import app, db
from models import Order, FlowerCrown
from utils.receipt_generator import generate_receipt
import os
import stripe
from datetime import datetime

# Configure Stripe
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')

# Get domain for Stripe redirects
YOUR_DOMAIN = 'localhost:5000'
if os.environ.get('REPLIT_DEV_DOMAIN'):
    YOUR_DOMAIN = os.environ.get('REPLIT_DEV_DOMAIN')
elif os.environ.get('REPLIT_DOMAINS'):
    YOUR_DOMAIN = os.environ.get('REPLIT_DOMAINS').split(',')[0]

# Initialize flower crowns data
def initialize_data():
    if FlowerCrown.query.count() == 0:
        crowns = [
            {
                "name": "Coroa Elegante Branca",
                "description": "Coroa de flores brancas com rosas e lírios, simbolizando pureza e paz.",
                "price": 180.00,
                "image_url": "https://pixabay.com/get/g01c65973cff9a89aecba9673bf60c8dc921fa4f8752e71480d09b1868a06ce4bd6a6f712869d23184ad7f1c9cf23425079a0eb1802f1f4d537018371e0fff24c_1280.jpg"
            },
            {
                "name": "Coroa Tradicional Vermelha",
                "description": "Coroa tradicional com flores vermelhas e folhagem verde, representando amor eterno.",
                "price": 200.00,
                "image_url": "https://pixabay.com/get/g40105fd835c08346206f59c497d834056748330f4aca8bc1a904dc00e371557eb67bd6c68eaa60e06e5f4b31614dd18c86887b1718ae0b4242394ddc8dccea8c_1280.jpg"
            },
            {
                "name": "Coroa Suave Rosa",
                "description": "Delicada coroa com flores rosas e brancas, expressando carinho e ternura.",
                "price": 190.00,
                "image_url": "https://pixabay.com/get/gfd1ec5fa008829e1a5690929435e655bf7f6ebb26104d3a1d34ff1b188fe948fb4ed96a8fc631544651d8adb7b241143939f8b019a7e9cb7d09d3471d053338f_1280.jpg"
            },
            {
                "name": "Coroa Majestosa Roxa",
                "description": "Coroa imponente com flores roxas e lilases, simbolizando dignidade e respeito.",
                "price": 220.00,
                "image_url": "https://pixabay.com/get/g476f2c57ad614a01fb99a317d0553f4e822d1933e3266b661785a9c9943ffb11399e4cd09fa371e600001bc1e17f9afcb7601021b2f79e75701f0a7ff1efc754_1280.jpg"
            },
            {
                "name": "Coroa Clássica Amarela",
                "description": "Coroa clássica com flores amarelas e douradas, transmitindo luz e esperança.",
                "price": 195.00,
                "image_url": "https://pixabay.com/get/g9788778ee508ea0787e289125015c882eaf5a08de09ff23431c23778c781e665e3b765cd72f26ef098583ffb9322fff183aa643e6ee35fc66a9caef4ab83b191_1280.jpg"
            },
            {
                "name": "Coroa Serena Azul",
                "description": "Coroa serena com flores azuis e brancas, evocando tranquilidade e paz celestial.",
                "price": 210.00,
                "image_url": "https://pixabay.com/get/g6e9dab49e087c47431408bb8cc9639837fef48f76c73282c8d708405a488838e967a4308e76c3a637d7aa4d57da9719c8a3d5d366ff478c5a7b9d093fdac06ad_1280.jpg"
            },
            {
                "name": "Coroa Refinada Mista",
                "description": "Coroa refinada com mix de flores coloridas, celebrando uma vida plena.",
                "price": 230.00,
                "image_url": "https://pixabay.com/get/g9c272ff34d5ab0b41297e404adf95edee0379f9970d2ca33590eaf3d0d4511b6a0991a5c0765f15c30eedbcd2ae60d1cdb8247165ece4bc4f67c3d4017f704ec_1280.jpg"
            },
            {
                "name": "Coroa Nobre Branca Premium",
                "description": "Coroa premium com flores brancas nobres, representando pureza e eternidade.",
                "price": 250.00,
                "image_url": "https://pixabay.com/get/g20487e28407f080cde7ad754d2faf2276e517cc7a7a5abf2e8e8ccbf59fbd18fa5005f130d53463a5ca0821d751ae6d4601ea46ef219dbf2ca9924c0ab22eaeb_1280.jpg"
            },
            {
                "name": "Coroa Delicada Pastel",
                "description": "Coroa delicada com tons pastéis suaves, simbolizando gentileza e amor.",
                "price": 175.00,
                "image_url": "https://pixabay.com/get/g05a9b99bc14d8bad2e745060af80e7aa4d32293f051c9be1f1ddffba056076e9ecc1389ce61f2a1f22e2b66f20a486f0dbeac7ae563fb4e398c3d413174f7b42_1280.jpg"
            }
        ]
        
        for crown_data in crowns:
            crown = FlowerCrown(**crown_data)
            db.session.add(crown)
        
        db.session.commit()

@app.route('/')
def index():
    crowns = FlowerCrown.query.all()
    return render_template('index.html', crowns=crowns)

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    crown_id = request.form.get('crown_id')
    custom_message = request.form.get('custom_message', '')
    
    crown = FlowerCrown.query.get_or_404(crown_id)
    
    # Store in session
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
    
    # Get form data
    customer_name = request.form.get('customer_name')
    customer_email = request.form.get('customer_email')
    customer_phone = request.form.get('customer_phone')
    payment_method = request.form.get('payment_method')
    installments = int(request.form.get('installments', 1))
    
    # Calculate total amount
    base_price = cart['crown_price']
    if payment_method == 'credit_installments' and installments > 1:
        # Apply 1.5% monthly interest
        monthly_rate = 0.015
        total_amount = base_price * (1 + monthly_rate * installments)
    else:
        total_amount = base_price
    
    # Store customer info in session for later use
    session['customer_info'] = {
        'customer_name': customer_name,
        'customer_email': customer_email,
        'customer_phone': customer_phone,
        'payment_method': payment_method,
        'installments': installments,
        'total_amount': total_amount
    }
    
    try:
        # Create Stripe checkout session
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'brl',
                    'product_data': {
                        'name': cart['crown_name'],
                        'description': f"Coroa de flores - {cart['custom_message']}" if cart['custom_message'] else "Coroa de flores"
                    },
                    'unit_amount': int(total_amount * 100),  # Stripe uses cents
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
                'crown_id': str(cart['crown_id']),
                'custom_message': cart['custom_message'] or '',
                'payment_method': payment_method,
                'installments': str(installments)
            }
        )
        
        return redirect(checkout_session.url, code=303)
        
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
        # Retrieve the session from Stripe
        checkout_session = stripe.checkout.Session.retrieve(session_id)
        
        if checkout_session.payment_status == 'paid':
            # Get cart and customer info
            cart = session.get('cart', {})
            customer_info = session.get('customer_info', {})
            
            if not cart or not customer_info:
                flash('Informações do pedido não encontradas.', 'error')
                return redirect(url_for('index'))
            
            # Create order
            order = Order(
                customer_name=customer_info['customer_name'],
                customer_email=customer_info['customer_email'],
                customer_phone=customer_info['customer_phone'],
                crown_id=cart['crown_id'],
                crown_name=cart['crown_name'],
                crown_price=cart['crown_price'],
                custom_message=cart['custom_message'],
                payment_method=customer_info['payment_method'],
                installments=customer_info['installments'],
                total_amount=customer_info['total_amount'],
                status='completed'
            )
            
            db.session.add(order)
            db.session.commit()
            
            # Generate receipt
            receipt_path = generate_receipt(order)
            
            # Clear cart and customer info
            session.pop('cart', None)
            session.pop('customer_info', None)
            
            # Store order info for success page
            session['last_order'] = {
                'id': order.id,
                'receipt_path': receipt_path,
                'customer_name': customer_info['customer_name']
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

@app.route('/calculate_installments')
def calculate_installments():
    price = float(request.args.get('price', 0))
    installments = int(request.args.get('installments', 1))
    
    if installments > 1:
        monthly_rate = 0.015
        total_amount = price * (1 + monthly_rate * installments)
        monthly_payment = total_amount / installments
    else:
        total_amount = price
        monthly_payment = price
    
    return jsonify({
        'total_amount': round(total_amount, 2),
        'monthly_payment': round(monthly_payment, 2)
    })
