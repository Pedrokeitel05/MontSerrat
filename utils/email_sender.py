import os
import base64
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import (Mail, Attachment, FileContent, FileName,
                                   FileType, Disposition)


def send_receipt_email(order, pdf_filepath):
    """
    Envia o e-mail de confirmação com o recibo em anexo usando o SendGrid.
    """
    # IMPORTANTE: Cole o URL público do seu logo (do Cloudinary) aqui
    logo_url = 'https://res.cloudinary.com/dajdn7nqw/image/upload/v1753452311/logo_aopjgo.png'

    # Corpo do e-mail em HTML, com o novo texto e assinatura
    html_content = f"""
    <html lang="pt-BR">
    <body style="font-family: Arial, sans-serif; color: #333;">
        <p>Olá, {order.customer_name}.</p>
        <p>Recebemos com respeito e carinho o seu pedido de coroa de flores em homenagem a <strong>{order.deceased_name}</strong>.</p>
        <p>Em anexo, segue o comprovante da solicitação realizada conosco, conforme a escolha feita. Sabemos que este é um momento delicado, e nos colocamos à disposição para garantir que essa homenagem seja entregue com todo o cuidado e consideração que ela merece.</p>
        <p>Caso precise de qualquer informação adicional, estaremos aqui para ajudar.</p>
        <p>Com nossos sinceros sentimentos,</p>
        <hr style="border: none; border-top: 1px solid #ccc; margin: 20px 0;">
        <table style="width: 100%; border-spacing: 0;">
            <tr>
                <td style="width: 70px; vertical-align: top;">
                    <img src="{logo_url}" alt="Logo da Funerária Montserrat" style="width: 60px; height: auto;">
                </td>
                <td style="vertical-align: top; padding-left: 15px; font-size: 12px; color: #555;">
                    <strong style="font-size: 14px; color: #333;">Funerária Mont Serrat</strong><br>
                    Telefone: (51) 3012-3044<br>
                    WhatsApp: 51 99424-9799<br>
                    Instagram: @montserratfuneraria
                </td>
            </tr>
        </table>
    </body>
    </html>
    """

    message = Mail(
        from_email=
        'pedrokeitel23@gmail.com',  # Recomendo usar um e-mail do seu domínio
        to_emails=order.customer_email,
        subject=f'Homenagem para {order.deceased_name} (Pedido #{order.id})',
        html_content=html_content)

    # Anexa o ficheiro PDF
    try:
        with open(pdf_filepath, 'rb') as f:
            pdf_data = f.read()

        encoded_file = base64.b64encode(pdf_data).decode()
        attached_file = Attachment(FileContent(encoded_file),
                                   FileName(os.path.basename(pdf_filepath)),
                                   FileType('application/pdf'),
                                   Disposition('attachment'))
        message.attachment = attached_file
    except Exception as e:
        print(f"Erro ao ler ou anexar o ficheiro PDF: {e}")
        return False

    # Envia o e-mail
    try:
        sendgrid_client = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
        response = sendgrid_client.send(message)
        print(
            f"E-mail enviado para {order.customer_email}, Status: {response.status_code}"
        )
        return response.status_code == 202
    except Exception as e:
        print(f"Erro ao enviar e-mail via SendGrid: {e}")
        return False
