import logging
from orders.models import Order
from .models import ScanResult
from .scanner import scan_domain

logger = logging.getLogger(__name__)


def run_scan(order_id):
    try:
        order = Order.objects.get(id=order_id)
        order.status = Order.Status.SCANNING
        order.save()
        logger.info(f'Scanning {order.domain} for order {order_id}')

        results = scan_domain(order.domain)
        logger.info(f'Scan complete for {order.domain}')

        ScanResult.objects.create(
            order=order,
            has_privacy_policy=results['has_privacy_policy'],
            has_cookie_banner=results['has_cookie_banner'],
            has_google_analytics=results['has_google_analytics'],
            has_facebook_pixel=results['has_facebook_pixel'],
            has_other_trackers=results['has_other_trackers'],
            other_trackers_found=results['other_trackers_found'],
            is_https=results['is_https'],
            has_contact_info=results['has_contact_info'],
            raw_html=results['raw_html'],
            error=results['error'],
        )

        if not results['error']:
            order.status = Order.Status.COMPLETE
            order.save()
            from reports.tasks import generate_report_task
            generate_report_task(str(order.id))
        else:
            logger.error(f'Scan error for {order.domain}: {results["error"]}')
            order.status = Order.Status.FAILED
            order.save()

    except Order.DoesNotExist:
        logger.error(f'Order {order_id} not found')
    except Exception as e:
        logger.error(f'Unexpected error in run_scan for {order_id}: {e}')