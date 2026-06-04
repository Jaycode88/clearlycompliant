from celery import shared_task
from orders.models import Order
from .models import ScanResult
from .scanner import scan_domain


@shared_task
def run_scan(order_id):
    try:
        order = Order.objects.get(id=order_id)
        order.status = Order.Status.SCANNING
        order.save()

        results = scan_domain(order.domain)

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

        order.status = Order.Status.COMPLETE if not results['error'] else Order.Status.FAILED
        order.save()

    except Order.DoesNotExist:
        pass