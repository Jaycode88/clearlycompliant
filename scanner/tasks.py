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
            is_https=results['is_https'],
            has_mixed_content=results['has_mixed_content'],
            has_x_frame_options=results['has_x_frame_options'],
            has_content_security_policy=results['has_content_security_policy'],
            has_x_content_type_options=results['has_x_content_type_options'],
            has_referrer_policy=results['has_referrer_policy'],
            has_privacy_policy=results['has_privacy_policy'],
            has_cookie_policy=results['has_cookie_policy'],
            has_terms_and_conditions=results['has_terms_and_conditions'],
            has_data_retention_policy=results['has_data_retention_policy'],
            privacy_policy_url=results['privacy_policy_url'],
            terms_url=results['terms_url'],
            privacy_policy_text=results['privacy_policy_text'],
            terms_text=results['terms_text'],
            has_cookie_banner=results['has_cookie_banner'],
            has_cookie_preferences_link=results['has_cookie_preferences_link'],
            has_form_consent_checkbox=results['has_form_consent_checkbox'],
            has_contact_form=results['has_contact_form'],
            has_newsletter_signup=results['has_newsletter_signup'],
            has_login=results['has_login'],
            has_google_analytics=results['has_google_analytics'],
            has_facebook_pixel=results['has_facebook_pixel'],
            has_other_trackers=results['has_other_trackers'],
            other_trackers_found=results['other_trackers_found'],
            has_live_chat=results['has_live_chat'],
            live_chat_tools_found=results['live_chat_tools_found'],
            has_payment_processor=results['has_payment_processor'],
            payment_processors_found=results['payment_processors_found'],
            has_cdn=results['has_cdn'],
            cdn_found=results['cdn_found'],
            cms_detected=results['cms_detected'],
            has_unsubscribe_mechanism=results['has_unsubscribe_mechanism'],
            has_contact_info=results['has_contact_info'],
            has_dpo_info=results['has_dpo_info'],
            has_data_subject_rights=results['has_data_subject_rights'],
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
            from mailer.tasks import send_failure_email
            send_failure_email(str(order.id), results['error'])

    except Order.DoesNotExist:
        logger.error(f'Order {order_id} not found')
    except Exception as e:
        logger.error(f'Unexpected error in run_scan for {order_id}: {e}')
        try:
            order.status = Order.Status.FAILED
            order.save()
            from mailer.tasks import send_failure_email
            send_failure_email(str(order.id), str(e))
        except Exception:
            pass