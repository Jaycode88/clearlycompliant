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

        rescan_section = ''
        if order.report_type == 'paid':
            rescan_url = f'https://clearlycompliant.co.uk/orders/rescan/{order.free_result_token}/'
            rescan_section = f'\n\nFREE RE-SCAN AVAILABLE\nYou can re-scan {order.domain} for free within 30 days of this report. Use this link:\n{rescan_url}\n'

        email = EmailMessage(
            subject=f'Your GDPR Compliance Report — {order.domain}',
            body=f"""Hi,

Thank you for using ClearlyCompliant.

Please find attached your full GDPR compliance report for {order.domain}.

The report contains a detailed breakdown of your site's GDPR compliance status, including specific recommendations and AI-powered analysis of your privacy policy and terms & conditions.
{rescan_section}
If you have any questions, please don't hesitate to get in touch at admin@clearlycompliant.co.uk.

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


def send_free_summary_email(order_id):
    try:
        from scanner.models import ScanResult
        order = Order.objects.get(id=order_id)
        scan_result = ScanResult.objects.get(order=order)

        # Calculate score
        checks = [
            scan_result.is_https,
            not scan_result.has_mixed_content,
            scan_result.has_x_frame_options,
            scan_result.has_content_security_policy,
            scan_result.has_x_content_type_options,
            scan_result.has_referrer_policy,
            scan_result.has_privacy_policy,
            scan_result.has_cookie_policy,
            scan_result.has_terms_and_conditions,
            scan_result.has_data_retention_policy,
            scan_result.has_cookie_banner,
            scan_result.has_cookie_preferences_link,
            scan_result.has_form_consent_checkbox,
            not scan_result.has_contact_form or scan_result.has_privacy_policy,
            not scan_result.has_newsletter_signup or scan_result.has_cookie_banner,
            not scan_result.has_login or scan_result.has_privacy_policy,
            not scan_result.has_ecommerce or scan_result.has_privacy_policy,
            not scan_result.has_google_analytics,
            not scan_result.has_facebook_pixel,
            scan_result.has_unsubscribe_mechanism,
            scan_result.has_contact_info,
            scan_result.has_dpo_info,
            scan_result.has_data_subject_rights,
        ]

        passed = sum(1 for c in checks if c)
        total = len(checks)
        score = int((passed / total) * 100)

        if score >= 80:
            rating = 'Good'
        elif score >= 50:
            rating = 'Needs Improvement'
        else:
            rating = 'Poor'

        results_url = f'https://clearlycompliant.co.uk/results/{order.free_result_token}/'

        email = EmailMessage(
            subject=f'Your Free GDPR Scan Results — {order.domain}',
            body=f"""Hi,

Your free GDPR compliance scan for {order.domain} is complete.

OVERALL SCORE: {score}% — {rating}
{passed} of {total} checks passed.

To see the full breakdown of your results including which specific checks failed and why, plus our AI-powered analysis of your privacy policy and terms & conditions, visit:

{results_url}

Upgrade to the full report for just £29.99 to receive a detailed PDF with actionable recommendations.

The ClearlyCompliant Team
""",
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[order.email],
        )
        email.send()
        logger.info(f'Free summary email sent to {order.email}')

    except Exception as e:
        logger.error(f'Failed to send free summary email for order {order_id}: {e}')