import logging
from orders.models import Order
from scanner.models import ScanResult
from .models import Report
from .generator import generate_report

logger = logging.getLogger(__name__)


def generate_report_task(order_id):
    try:
        from mailer.tasks import send_report_email, send_failure_email

        order = Order.objects.get(id=order_id)
        scan_result = ScanResult.objects.get(order=order)

        pdf_bytes = generate_report(order, scan_result)
        Report.objects.create(order=order, pdf=pdf_bytes)

        order.status = Order.Status.EMAILING
        order.save()

        send_report_email(order_id)

        order.status = Order.Status.COMPLETE
        order.save()

    except (Order.DoesNotExist, ScanResult.DoesNotExist) as e:
        logger.error(f'Order or ScanResult not found for {order_id}: {e}')
    except Exception as e:
        logger.error(f'Report generation failed for {order_id}: {e}')
        try:
            from mailer.tasks import send_failure_email
            send_failure_email(order_id, 'We were unable to generate your report.')
        except Exception:
            pass