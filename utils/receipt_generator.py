from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from datetime import datetime
import os

def generate_receipt(order):
    """Generate a PDF receipt for the order"""
    
    # Create receipts directory if it doesn't exist
    receipts_dir = os.path.join(os.getcwd(), 'receipts')
    if not os.path.exists(receipts_dir):
        os.makedirs(receipts_dir)
    
    # Generate filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"receipt_{order.id}_{timestamp}.pdf"
    filepath = os.path.join(receipts_dir, filename)
    
    # Create the PDF document
    doc = SimpleDocTemplate(filepath, pagesize=A4)
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        alignment=TA_CENTER,
        fontSize=20,
        spaceAfter=30,
        textColor=colors.HexColor('#6c63ff')
    )
    
    header_style = ParagraphStyle(
        'CustomHeader',
        parent=styles['Heading2'],
        alignment=TA_LEFT,
        fontSize=14,
        spaceAfter=12,
        textColor=colors.HexColor('#333333')
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=11,
        spaceAfter=6,
        textColor=colors.HexColor('#666666')
    )
    
    # Build the document content
    story = []
    
    # Header
    story.append(Paragraph("COMPROVANTE DE PAGAMENTO", title_style))
    story.append(Spacer(1, 20))
    
    # Company info
    story.append(Paragraph("Funerária Montserrat", header_style))
    story.append(Paragraph("Atendimento humanizado e respeitoso", normal_style))
    story.append(Paragraph("WhatsApp: (51) 98333-9080", normal_style))
    story.append(Paragraph("www.funerariamontserrat.com.br", normal_style))
    story.append(Spacer(1, 20))
    
    # Order details
    story.append(Paragraph("DETALHES DO PEDIDO", header_style))
    
    order_data = [
        ['Número do Pedido:', f'#{order.id}'],
        ['Data:', order.order_date.strftime('%d/%m/%Y %H:%M')],
        ['Status:', 'Confirmado'],
        ['', ''],
        ['Cliente:', order.customer_name],
        ['E-mail:', order.customer_email],
        ['Telefone:', order.customer_phone],
        ['', ''],
        ['Produto:', order.crown_name],
        ['Preço Base:', f'R$ {order.crown_price:.2f}'],
        ['Forma de Pagamento:', get_payment_method_name(order.payment_method)],
    ]
    
    if order.payment_method == 'credit_installments' and order.installments > 1:
        order_data.append(['Parcelas:', f'{order.installments}x'])
        monthly_payment = order.total_amount / order.installments
        order_data.append(['Valor da Parcela:', f'R$ {monthly_payment:.2f}'])
    
    order_data.append(['', ''])
    order_data.append(['TOTAL:', f'R$ {order.total_amount:.2f}'])
    
    if order.custom_message:
        order_data.append(['', ''])
        order_data.append(['Mensagem Personalizada:', order.custom_message])
    
    # Create table
    table = Table(order_data, colWidths=[2*inch, 3*inch])
    table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, -1), (-1, -1), 12),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#f8f9fa')),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#dee2e6')),
    ]))
    
    story.append(table)
    story.append(Spacer(1, 30))
    
    # Footer
    story.append(Paragraph("INFORMAÇÕES IMPORTANTES", header_style))
    story.append(Paragraph("• Este comprovante serve como confirmação do seu pedido.", normal_style))
    story.append(Paragraph("• Entraremos em contato para coordenar a entrega.", normal_style))
    story.append(Paragraph("• Para dúvidas, entre em contato pelo WhatsApp: (51) 98333-9080", normal_style))
    story.append(Spacer(1, 20))
    
    # Generate timestamp
    generated_at = datetime.now().strftime('%d/%m/%Y às %H:%M:%S')
    story.append(Paragraph(f"Comprovante gerado em {generated_at}", 
                          ParagraphStyle('Footer', parent=styles['Normal'], 
                                       fontSize=8, alignment=TA_CENTER, 
                                       textColor=colors.HexColor('#999999'))))
    
    # Build PDF
    doc.build(story)
    
    return filepath

def get_payment_method_name(payment_method):
    """Convert payment method code to readable name"""
    methods = {
        'pix': 'PIX',
        'debit': 'Cartão de Débito',
        'credit': 'Cartão de Crédito à Vista',
        'credit_installments': 'Cartão de Crédito Parcelado'
    }
    return methods.get(payment_method, payment_method)
