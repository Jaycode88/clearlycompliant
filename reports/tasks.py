from celery import shared_task
from orders.models import Order
from scanner.models import ScanResult
from .models import Report
from .generator import generate_report


@shared_task
def generate_report_task(order_id):
    try:
        order = Order.objects.get(id=order_id)
        scan_result = ScanResult.objects.get(order=order)

        pdf_bytes = generate_report(order, scan_result)

        Report.objects.create(order=order, pdf=pdf_bytes)

    except (Order.DoesNotExist, ScanResult.DoesNotExist):
        pass