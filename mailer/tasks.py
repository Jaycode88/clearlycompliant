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

Please reply to this email and we'll look into it and resolve the issue.

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
        from django.core.mail import EmailMultiAlternatives
        order = Order.objects.get(id=order_id)
        scan_result = ScanResult.objects.get(order=order)

        sections = [
            {
                'title': '1. Technical Security',
                'checks': [
                    scan_result.is_https,
                    not scan_result.has_mixed_content,
                    scan_result.has_x_frame_options,
                    scan_result.has_content_security_policy,
                    scan_result.has_x_content_type_options,
                    scan_result.has_referrer_policy,
                ]
            },
            {
                'title': '2. Privacy & Legal Documents',
                'checks': [
                    scan_result.has_privacy_policy,
                    scan_result.has_cookie_policy,
                    scan_result.has_terms_and_conditions,
                    scan_result.has_data_retention_policy,
                ]
            },
            {
                'title': '3. Consent & Cookie Management',
                'checks': [
                    scan_result.has_cookie_banner,
                    scan_result.has_cookie_preferences_link,
                    scan_result.has_form_consent_checkbox,
                ]
            },
            {
                'title': '4. Data Collection',
                'checks': [
                    not scan_result.has_contact_form or scan_result.has_privacy_policy,
                    not scan_result.has_newsletter_signup or scan_result.has_cookie_banner,
                    not scan_result.has_login or scan_result.has_privacy_policy,
                    not scan_result.has_ecommerce or scan_result.has_privacy_policy,
                ]
            },
            {
                'title': '5. Third-Party & Tracking',
                'checks': [
                    not scan_result.has_google_analytics,
                    not scan_result.has_facebook_pixel,
                ]
            },
            {
                'title': '6. User Rights',
                'checks': [
                    scan_result.has_unsubscribe_mechanism,
                    scan_result.has_contact_info,
                    scan_result.has_dpo_info,
                    scan_result.has_data_subject_rights,
                ]
            },
        ]

        all_checks = [c for s in sections for c in s['checks']]
        total_passed = sum(1 for c in all_checks if c)
        total_checks = len(all_checks)
        score = int((total_passed / total_checks) * 100)

        if score >= 80:
            rating = 'Good'
            score_colour = '#22c55e'
        elif score >= 50:
            rating = 'Needs Improvement'
            score_colour = '#f59e0b'
        else:
            rating = 'Poor'
            score_colour = '#ef4444'

        results_url = f'https://clearlycompliant.co.uk/orders/results/{order.free_result_token}/'

        # Build section rows HTML
        section_rows_html = ''
        for section in sections:
            passed = sum(1 for c in section['checks'] if c)
            total = len(section['checks'])
            failed = total - passed
            s_score = int((passed / total) * 100)

            if s_score >= 80:
                s_colour = '#22c55e'
                s_bg = '#f0fdf4'
                s_border = '#bbf7d0'
            elif s_score >= 50:
                s_colour = '#f59e0b'
                s_bg = '#fffbeb'
                s_border = '#fde68a'
            else:
                s_colour = '#ef4444'
                s_bg = '#fff7ed'
                s_border = '#fed7aa'

            failed_text = f'<span style="color:#c2410c; font-size:12px;">{failed} issue{"s" if failed > 1 else ""} found</span>' if failed > 0 else '<span style="color:#15803d; font-size:12px;">All passed</span>'

            section_rows_html += f"""
            <tr>
                <td style="padding:12px 16px; border-bottom:1px solid #e2e8f0; font-size:14px; color:#0f2044; font-weight:500;">{section['title']}</td>
                <td style="padding:12px 16px; border-bottom:1px solid #e2e8f0; font-size:13px; color:#64748b; text-align:center;">{passed}/{total}</td>
                <td style="padding:12px 16px; border-bottom:1px solid #e2e8f0; text-align:center;">{failed_text}</td>
                <td style="padding:12px 16px; border-bottom:1px solid #e2e8f0; text-align:center;"><span style="color:{s_colour}; font-weight:700; font-size:14px;">{s_score}%</span></td>
            </tr>
            """

        html_body = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin:0; padding:0; background:#f8fafc; font-family:'Helvetica Neue', Helvetica, Arial, sans-serif;">

    <table width="100%" cellpadding="0" cellspacing="0" style="background:#f8fafc; padding:40px 20px;">
        <tr>
            <td align="center">
                <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px; width:100%;">

                    <!-- Header -->
                    <tr>
                        <td style="background:#0f2044; padding:24px 32px; border-radius:12px 12px 0 0;">
                            <span style="color:#ffffff; font-size:20px; font-weight:700;">Clearly<span style="color:#c9a84c;">Compliant</span></span>
                        </td>
                    </tr>

                    <!-- Score Banner -->
                    <tr>
                        <td style="background:linear-gradient(135deg, #0f2044, #1a3a6e); padding:32px; text-align:center;">
                            <p style="color:#94a3b8; font-size:14px; margin:0 0 16px;">GDPR Compliance Scan Results for</p>
                            <p style="color:#ffffff; font-size:20px; font-weight:700; margin:0 0 24px;">{order.domain}</p>
                            <div style="display:inline-block; width:100px; height:100px; border-radius:50%; border:6px solid {score_colour}; text-align:center; line-height:88px; margin:0 auto 16px;">
                                <span style="color:{score_colour}; font-size:28px; font-weight:800;">{score}%</span>
                            </div>
                            <p style="color:{score_colour}; font-size:20px; font-weight:700; margin:0 0 8px;">{rating}</p>
                            <p style="color:#94a3b8; font-size:14px; margin:0;">{total_passed} of {total_checks} checks passed</p>
                        </td>
                    </tr>

                    <!-- Section Breakdown -->
                    <tr>
                        <td style="background:#ffffff; padding:32px;">
                            <h2 style="font-size:18px; font-weight:700; color:#0f2044; margin:0 0 8px;">Section Breakdown</h2>
                            <p style="font-size:14px; color:#64748b; margin:0 0 20px;">Here's how your site performed across each compliance area.</p>

                            <table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #e2e8f0; border-radius:8px; overflow:hidden;">
                                <tr style="background:#0f2044;">
                                    <td style="padding:10px 16px; font-size:12px; font-weight:600; color:#ffffff; text-transform:uppercase; letter-spacing:0.5px;">Section</td>
                                    <td style="padding:10px 16px; font-size:12px; font-weight:600; color:#ffffff; text-align:center; text-transform:uppercase; letter-spacing:0.5px;">Passed</td>
                                    <td style="padding:10px 16px; font-size:12px; font-weight:600; color:#ffffff; text-align:center; text-transform:uppercase; letter-spacing:0.5px;">Status</td>
                                    <td style="padding:10px 16px; font-size:12px; font-weight:600; color:#ffffff; text-align:center; text-transform:uppercase; letter-spacing:0.5px;">Score</td>
                                </tr>
                                {section_rows_html}
                            </table>
                        </td>
                    </tr>

                    <!-- CTA -->
                    <tr>
                        <td style="background:#ffffff; padding:0 32px 32px;">
                            <div style="background:#f8f8ff; border:1px solid #e0e0ff; border-radius:10px; padding:24px; text-align:center;">
                                <p style="font-size:16px; font-weight:700; color:#0f2044; margin:0 0 8px;">See the Full Details</p>
                                <p style="font-size:14px; color:#64748b; margin:0 0 20px; line-height:1.6;">Your full results are waiting — see exactly which checks failed and why, plus get our AI-powered analysis of your privacy policy and terms & conditions.</p>
                                <a href="{results_url}" style="display:inline-block; background:#c9a84c; color:#0f2044; font-size:15px; font-weight:700; padding:14px 32px; border-radius:8px; text-decoration:none;">View My Full Results</a>
                                <p style="font-size:12px; color:#94a3b8; margin:16px 0 0;">Full report £29.99 · Includes free re-scan within 30 days</p>
                            </div>
                        </td>
                    </tr>

                    <!-- What's included -->
                    <tr>
                        <td style="background:#ffffff; padding:0 32px 32px;">
                            <p style="font-size:14px; font-weight:600; color:#0f2044; margin:0 0 12px;">The full report includes:</p>
                            <table cellpadding="0" cellspacing="0">
                                <tr><td style="padding:3px 0; font-size:13px; color:#15803d;">✓ &nbsp;Specific details on every failed check</td></tr>
                                <tr><td style="padding:3px 0; font-size:13px; color:#15803d;">✓ &nbsp;AI-powered analysis of your privacy policy</td></tr>
                                <tr><td style="padding:3px 0; font-size:13px; color:#15803d;">✓ &nbsp;AI-powered analysis of your terms & conditions</td></tr>
                                <tr><td style="padding:3px 0; font-size:13px; color:#15803d;">✓ &nbsp;Professional PDF report by email</td></tr>
                                <tr><td style="padding:3px 0; font-size:13px; color:#15803d;">✓ &nbsp;Free re-scan within 30 days</td></tr>
                            </table>
                        </td>
                    </tr>

                    <!-- Footer -->
                    <tr>
                        <td style="background:#0f2044; padding:20px 32px; border-radius:0 0 12px 12px; text-align:center;">
                            <p style="color:#94a3b8; font-size:12px; margin:0 0 4px;">ClearlyCompliant · admin@clearlycompliant.co.uk</p>
                            <p style="color:#64748b; font-size:11px; margin:0;">This report is automated and does not constitute legal advice.</p>
                        </td>
                    </tr>

                </table>
            </td>
        </tr>
    </table>

</body>
</html>
        """

        # Plain text fallback
        plain_text = f"""Your free GDPR scan for {order.domain} is complete.

Overall Score: {score}% — {rating}
{total_passed} of {total_checks} checks passed.

View your full results at:
{results_url}

The ClearlyCompliant Team
"""

        email = EmailMultiAlternatives(
            subject=f'Your Free GDPR Scan Results — {order.domain} ({score}% — {rating})',
            body=plain_text,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[order.email],
        )
        email.attach_alternative(html_body, 'text/html')
        email.send()
        logger.info(f'Free summary email sent to {order.email}')

    except Exception as e:
        logger.error(f'Failed to send free summary email for order {order_id}: {e}')