from celery import shared_task
from django.core.mail import EmailMessage
from django.conf import settings
from orders.models import Order
from reports.models import Report


@shared_task
def send_report_email(order_id):
    try:
        order = Order.objects.get(id=order_id)
        report = Report.objects.get(order=order)

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

    except (Order.DoesNotExist, Report.DoesNotExist):
        pass