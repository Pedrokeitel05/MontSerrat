from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from datetime import datetime
import os


# Função do rodapé atualizada
def create_footer(canvas, doc):
    canvas.saveState()
    styles = getSampleStyleSheet()

    # Estilos para o texto do rodapé
    footer_style_left = ParagraphStyle('FooterLeft',
                                       parent=styles['Normal'],
                                       fontSize=9,
                                       textColor=colors.HexColor('#333333'),
                                       leading=12)
    footer_style_right = ParagraphStyle('FooterRight',
                                        parent=styles['Normal'],
                                        fontSize=8,
                                        textColor=colors.HexColor('#666666'),
                                        leading=11)

    # Coluna da Esquerda: Informações da Empresa (com o novo texto)
    logo_path = os.path.join(os.getcwd(), 'static', 'img', 'logo.png')
    logo = Image(logo_path, width=0.6 * inch, height=0.6 * inch)

    company_details_text = """
    <b>Funerária Mont Serrat</b><br/>
    Telefone: (51) 3012-3044<br/>
    WhatsApp: (51) 99424-9799<br/>
    Instagram: @montserratfuneraria
    """
    company_paragraph = Paragraph(company_details_text, footer_style_left)

    # Tabela simplificada para organizar o logo e o texto
    footer_table = Table([[logo, company_paragraph]],
                         colWidths=[0.8 * inch, 3 * inch])
    footer_table.setStyle(
        TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # Centraliza verticalmente
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ]))

    # Desenha a tabela de informações da empresa no rodapé
    w, h = footer_table.wrap(doc.width, doc.bottomMargin)
    footer_table.drawOn(canvas, doc.leftMargin,
                        0.7 * inch)  # Posição a partir do fundo

    # Data de geração
    generated_at = datetime.now().strftime('%d/%m/%Y às %H:%M:%S')
    canvas.setFont('Helvetica', 7)
    canvas.setFillColor(colors.HexColor('#999999'))
    canvas.drawCentredString(doc.width / 2 + doc.leftMargin, 0.3 * inch,
                             f"Comprovante gerado em {generated_at}")

    canvas.restoreState()


def generate_receipt(order):
    """Gera um recibo em PDF para o pedido"""
    receipts_dir = os.path.join(os.getcwd(), 'receipts')
    if not os.path.exists(receipts_dir):
        os.makedirs(receipts_dir)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"Recibo_Pedido_{order.id}.pdf"  # Nome do ficheiro físico
    filepath = os.path.join(receipts_dir, filename)

    # ADICIONADO O TÍTULO AOS METADADOS DO PDF
    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        bottomMargin=1.5 * inch,
        title=
        f"Recibo Pedido #{order.id} - Funerária Montserrat"  # Título que aparece na aba do navegador
    )
    styles = getSampleStyleSheet()

    # Estilos (sem alterações)
    title_style = ParagraphStyle('CustomTitle',
                                 parent=styles['Heading1'],
                                 alignment=TA_CENTER,
                                 fontSize=20,
                                 spaceAfter=20,
                                 textColor=colors.HexColor('#6c63ff'))
    header_style = ParagraphStyle('CustomHeader',
                                  parent=styles['Heading2'],
                                  alignment=TA_LEFT,
                                  fontSize=14,
                                  spaceAfter=12,
                                  textColor=colors.HexColor('#333333'))
    centered_header_style = ParagraphStyle('CenteredHeader',
                                           parent=header_style,
                                           alignment=TA_CENTER)

    story = []

    # O conteúdo começa diretamente com o título
    story.append(Paragraph("DETALHES DO PEDIDO", centered_header_style))

    # Tabela de Detalhes do Pedido
    order_data = [
        ['Número do Pedido:', f'#{order.id}'],
        ['Data:', order.order_date.strftime('%d/%m/%Y %H:%M')],
        ['Cliente:', order.customer_name],
        ['E-mail:', order.customer_email],
        ['Telefone:', order.customer_phone],
        ['Produto:', order.crown_name],
        ['Preço Base:', f'R$ {order.crown_price:.2f}'],
        ['Forma de Pagamento:',
         get_payment_method_name(order)],
    ]

    if order.payment_method == 'credit' and order.installments > 1:
        order_data.append(['Parcelas:', f'{order.installments}x'])
        monthly_payment = order.total_amount / order.installments
        order_data.append(['Valor da Parcela:', f'R$ {monthly_payment:.2f}'])

    total_row_index = len(order_data)
    order_data.append(['TOTAL:', f'R$ {order.total_amount:.2f}'])

    if order.custom_message:
        order_data.append([
            'Mensagem na Faixa:',
            Paragraph(order.custom_message, styles['Normal'])
        ])

    table = Table(order_data, colWidths=[2 * inch, 4 * inch])

    style_commands = [
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, total_row_index - 1), 1,
         colors.HexColor('#dee2e6')),
        ('FONTNAME', (0, total_row_index), (-1, total_row_index),
         'Helvetica-Bold'),
        ('FONTSIZE', (0, total_row_index), (-1, total_row_index), 12),
        ('BACKGROUND', (0, total_row_index), (-1, total_row_index),
         colors.HexColor('#f0f0f0')),
        ('BOX', (0, total_row_index), (-1, total_row_index), 1,
         colors.HexColor('#333333')),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
    ]

    table.setStyle(TableStyle(style_commands))
    story.append(table)

    doc.build(story, onFirstPage=create_footer, onLaterPages=create_footer)
    return filepath


def get_payment_method_name(order):
    method = order.payment_method
    installments = order.installments
    if method == 'pix': return 'PIX'
    if method == 'debit': return 'Cartão de Débito'
    if method == 'credit':
        return f'Cartão de Crédito ({installments}x)' if installments > 1 else 'Cartão de Crédito à Vista'
    return method.replace('_', ' ').title()
