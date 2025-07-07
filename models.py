from app import db
from datetime import datetime

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(100), nullable=False)
    customer_email = db.Column(db.String(120), nullable=False)
    customer_phone = db.Column(db.String(20), nullable=False)
    crown_id = db.Column(db.Integer, nullable=False)
    crown_name = db.Column(db.String(100), nullable=False)
    crown_price = db.Column(db.Float, nullable=False)
    custom_message = db.Column(db.Text, nullable=True)
    payment_method = db.Column(db.String(20), nullable=False)
    installments = db.Column(db.Integer, default=1)
    total_amount = db.Column(db.Float, nullable=False)
    order_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='pending')
    
    def __repr__(self):
        return f'<Order {self.id}>'

class FlowerCrown(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=False)
    image_url = db.Column(db.String(500), nullable=False)
    
    def __repr__(self):
        return f'<FlowerCrown {self.name}>'
