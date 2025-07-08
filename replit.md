# Funerária Montserrat - Coroas de Flores

## Overview

This is a Flask-based web application for a funeral home's flower crown ordering system. The application allows customers to browse flower crowns, customize messages, and place orders with payment processing capabilities. The system is designed to handle funeral flower arrangements with a respectful and professional interface.

## System Architecture

### Backend Architecture
- **Framework**: Flask (Python web framework)
- **Database**: SQLAlchemy ORM with SQLite (default) or PostgreSQL support
- **Session Management**: Flask sessions with configurable secret key
- **Middleware**: ProxyFix for proper header handling behind proxies
- **File Structure**: Modular design with separate files for models, routes, and utilities

### Frontend Architecture
- **Template Engine**: Jinja2 (Flask's default)
- **CSS Framework**: Bootstrap 5.3.0 for responsive design
- **Icons**: Font Awesome 6.0.0
- **Fonts**: Google Fonts (Inter)
- **JavaScript**: Vanilla JS with Bootstrap components

### Database Schema
- **Orders Table**: Stores customer orders with payment details and status
- **FlowerCrown Table**: Catalog of available flower crowns with descriptions and pricing

## Key Components

### Models (`models.py`)
- **Order Model**: Tracks customer information, selected crown, payment method, installments, and order status
- **FlowerCrown Model**: Manages the product catalog with names, descriptions, prices, and images

### Routes (`routes.py`)
- **Product Display**: Homepage showing available flower crowns
- **Checkout Process**: Multi-step ordering with customer information collection
- **Payment Processing**: Handles different payment methods including installments
- **Order Confirmation**: Success page with order details and WhatsApp integration

### Utilities
- **Receipt Generator**: PDF generation using ReportLab for order receipts
- **Frontend Assets**: Custom CSS and JavaScript for enhanced user experience

## Data Flow

1. **Product Browsing**: Users view available flower crowns on the homepage
2. **Customization**: Users can add custom messages to their orders
3. **Checkout**: Customer information collection and payment method selection
4. **Order Processing**: Order creation and storage in database
5. **Confirmation**: Order confirmation page with receipt generation
6. **Communication**: WhatsApp integration for order tracking

## External Dependencies

### Python Packages
- Flask: Web framework
- Flask-SQLAlchemy: Database ORM
- ReportLab: PDF generation for receipts
- Werkzeug: WSGI utilities and middleware

### Frontend Dependencies
- Bootstrap 5.3.0: UI framework
- Font Awesome 6.0.0: Icon library
- Google Fonts: Typography (Inter font family)

### Third-party Integrations
- **WhatsApp API**: Customer communication and order tracking
- **Pixabay**: Image hosting for flower crown photos
- **Payment Processing**: Framework ready for payment gateway integration

## Deployment Strategy

### Environment Configuration
- **Database**: Configurable via DATABASE_URL environment variable
- **Session Security**: SESSION_SECRET environment variable for production
- **Development**: Built-in Flask development server
- **Production**: WSGI-compatible with ProxyFix middleware

### Database Setup
- **Auto-initialization**: Database tables created automatically on first run
- **Sample Data**: Flower crown catalog populated on startup
- **Connection Pooling**: Configured for reliability with pool recycling

### Hosting Requirements
- Python 3.x environment
- SQLite support (default) or PostgreSQL for production
- Static file serving capability
- Environment variable support

## Changelog
- July 07, 2025. Initial setup
- July 08, 2025. Complete layout redesign - modern dark theme with minimalist approach
  - Implemented dark color scheme with purple accent (#6366f1)
  - Updated all templates with modern card-based layouts
  - Enhanced animations and hover effects
  - Improved mobile responsiveness
  - Updated admin panel with statistics dashboard
  - Redesigned login page with centered modal layout

## User Preferences

Preferred communication style: Simple, everyday language.
Design preference: Modern, minimalist, dark theme instead of white background.