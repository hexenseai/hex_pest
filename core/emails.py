import logging
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from email.mime.image import MIMEImage
from addressbook.models import Contact

logger = logging.getLogger(__name__)

def send_bagimsiz_tespit_email(tespit):
    """
    Independent detection record (BagimsizTespit) creation email sender.
    Sends a styled HTML email with inline images (CID) to all contacts of the customer.
    """
    # 1. Get all customer contacts with non-empty emails
    contacts = Contact.objects.filter(customer=tespit.firma).exclude(email="")
    emails = list(set(contacts.values_list("email", flat=True)))
    
    if not emails:
        logger.warning(f"No contact email found for customer: {tespit.firma}")
        return False
        
    subject = f"Yeni Bağımsız Tespit Kaydı Oluşturuldu - {tespit.tarih:%d.%m.%Y}"
    
    # Context for the template
    context = {
        "tespit": tespit,
        "customer": tespit.firma,
        "facility": tespit.tesis,
        "subject": subject,
    }
    
    html_content = render_to_string("emails/bagimsiz_tespit_email.html", context)
    text_content = strip_tags(html_content)
    
    try:
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "info@kaleilaclama.com"),
            to=emails,
        )
        msg.attach_alternative(html_content, "text/html")
        
        # Attach visuals as inline images using content-id (CID)
        for i, field_name in enumerate(["gorsel1", "gorsel2", "gorsel3"], start=1):
            gorsel = getattr(tespit, field_name)
            if gorsel:
                try:
                    gorsel.open("rb")
                    img_data = gorsel.read()
                    gorsel.close()
                    
                    mime_img = MIMEImage(img_data)
                    mime_img.add_header("Content-ID", f"<gorsel{i}>")
                    mime_img.add_header(
                        "Content-Disposition", 
                        "inline", 
                        filename=gorsel.name.split("/")[-1]
                    )
                    msg.attach(mime_img)
                except Exception as img_err:
                    logger.error(f"Error attaching image {field_name} to email: {img_err}")
                    
        msg.send()
        logger.info(f"Independent detection notification email successfully sent to: {emails}")
        return True
    except Exception as e:
        logger.error(f"Failed to send independent detection email: {e}")
        return False
