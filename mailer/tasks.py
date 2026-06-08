import ssl
import smtplib
import logging
from django.core.mail import EmailMessage
from django.conf import settings
from orders.models import Order
from reports.models import Report

# Patch SMTP to use unverified SSL context on Windows
_original_starttls = smtplib.SMTP.starttls

def _patched_starttls(self, keyfile=None, certfile=None, context=None):
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    return _original_starttls(self, context=context)

smtplib.SMTP.starttls = _patched_starttls

logger = logging.getLogger(__name__)


def send_report_email(order_id):
    try:
        order = Order.objects.get(id=order_id)
        report = Report.objects.get(order=order)

        logger.info(f'Attempting to send email to {order.email}')

        email = EmailMessage(
            subject=f'Your GDPR Compliance Report — {order.domain}',
            body=f"""Hi,

Thank you for using ClearlyCompliant.

Please find attached your GDPR compliance report for {order.domain}.

The report contains a detailed breakdown of your site's GDPR compliance status, including any areas that need attention.

If you have any questions, please don't hesitate to get in touch.

The ClearlyCompliant Team
""",
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[order.email],
        )

        email.attach(
            filename=f'gdpr-report-{order.domain}.pdf',
            content=bytes(report.pdf),
            mimetype='application/pdf',
        )

        email.send()
        logger.info(f'Email sent successfully to {order.email}')

    except (Order.DoesNotExist, Report.DoesNotExist) as e:
        logger.error(f'Order or Report not found: {e}')
    except Exception as e:
        logger.error(f'Failed to send email for order {order_id}: {type(e).__name__}: {e}')


def send_failure_email(order_id, error_message):
    try:
        order = Order.objects.get(id=order_id)
        logger.info(f'Sending failure email to {order.email}')

        email = EmailMessage(
            subject=f'Issue with your ClearlyCompliant report — {order.domain}',
            body=f"""Hi,

We're sorry, but we encountered an issue while scanning {order.domain}:

{error_message}

Please reply to this email and we'll look into it and either resolve the issue or arrange a full refund.

Apologies for the inconvenience.

The ClearlyCompliant Team
""",
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[order.email],
        )

        email.send()
        logger.info(f'Failure email sent to {order.email}')

    except Exception as e:
        logger.error(f'Failed to send failure email for order {order_id}: {e}')



def send_confirmation_email(order_id):
    try:
        order = Order.objects.get(id=order_id)
        logger.info(f'Sending confirmation email to {order.email}')

        email = EmailMessage(
            subject=f'Your GDPR Report Order Confirmed — {order.domain}',
            body=f"""Hi,

Thank you for your order!

We've received your payment and are now scanning {order.domain} for GDPR compliance issues.

Your full report will be emailed to this address within 3–5 minutes.

If you don't receive it within 10 minutes, please check your spam folder or contact us at admin@clearlycompliant.co.uk.

The ClearlyCompliant Team
""",
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[order.email],
        )
        email.send()
        logger.info(f'Confirmation email sent to {order.email}')

    except Exception as e:
        logger.error(f'Failed to send confirmation email for order {order_id}: {e}')