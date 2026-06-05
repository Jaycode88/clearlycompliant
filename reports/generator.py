import io
import logging
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor, white
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable

logger = logging.getLogger(__name__)

BRAND_PURPLE = HexColor('#6366f1')
PASS_GREEN = HexColor('#15803d')
PASS_BG = HexColor('#f0fdf4')
FAIL_ORANGE = HexColor('#c2410c')
FAIL_BG = HexColor('#fff7ed')
INFO_BG = HexColor('#f8f8ff')
GREY = HexColor('#666666')
LIGHT_GREY = HexColor('#e5e7eb')
DARK = HexColor('#1a1a2e')


def make_check_row(label, passed, description, recommendation):
    bg = PASS_BG if passed else FAIL_BG
    icon = '✓' if passed else '✗'
    label_colour = '#15803d' if passed else '#c2410c'
    text = description if passed else recommendation
    row = [[
        Paragraph(f'<font color="{label_colour}"><b>{icon}</b></font>',
                  ParagraphStyle('icon', fontSize=14, leading=18)),
        Paragraph(f'<font color="{label_colour}"><b>{label}</b></font><br/>'
                  f'<font color="#555555">{text}</font>',
                  ParagraphStyle('checktext', fontSize=10, leading=15)),
    ]]
    t = Table(row, colWidths=[12*mm, 158*mm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), bg),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    return t


def make_info_row(label, value):
    row = [[
        Paragraph(f'<font color="#374151"><b>{label}</b></font>',
                  ParagraphStyle('infolabel', fontSize=10, leading=15)),
        Paragraph(f'<font color="#555555">{value}</font>',
                  ParagraphStyle('infovalue', fontSize=10, leading=15)),
    ]]
    t = Table(row, colWidths=[60*mm, 110*mm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), INFO_BG),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    return t


def section_heading(title):
    return Paragraph(
        f'<font color="#6366f1"><b>{title}</b></font>',
        ParagraphStyle('sectionhead', fontSize=13, leading=18, spaceBefore=8)
    )


def generate_report(order, scan_result):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20*mm,
        leftMargin=20*mm,
        topMargin=20*mm,
        bottomMargin=20*mm,
    )

    elements = []

    # --- Header ---
    elements.append(Paragraph(
        '<font color="#6366f1"><b>ClearlyCompliant</b></font>',
        ParagraphStyle('brand', fontSize=28, leading=34)
    ))
    elements.append(Spacer(1, 4*mm))
    elements.append(Paragraph(
        f'GDPR Compliance Report — {order.domain}',
        ParagraphStyle('subtitle', fontSize=16, textColor=GREY, leading=20)
    ))
    elements.append(Spacer(1, 3*mm))
    elements.append(Paragraph(
        f'Prepared for: {order.email}<br/>Scan date: {scan_result.scanned_at.strftime("%d %B %Y, %H:%M")} UTC',
        ParagraphStyle('meta', fontSize=11, textColor=GREY, leading=16)
    ))
    elements.append(HRFlowable(width='100%', thickness=3, color=BRAND_PURPLE, spaceAfter=6*mm))

    # --- Site Overview ---
    elements.append(section_heading('Site Overview'))
    elements.append(HRFlowable(width='100%', thickness=1, color=LIGHT_GREY, spaceAfter=3*mm))

    overview_items = []
    if scan_result.cms_detected:
        overview_items.append(make_info_row('CMS / Platform', scan_result.cms_detected))
    if scan_result.payment_processors_found:
        overview_items.append(make_info_row('Payment Processors', ', '.join(scan_result.payment_processors_found).title()))
    if scan_result.cdn_found:
        overview_items.append(make_info_row('CDN', ', '.join(scan_result.cdn_found).title()))
    if scan_result.live_chat_tools_found:
        overview_items.append(make_info_row('Live Chat', ', '.join(scan_result.live_chat_tools_found).title()))

    if overview_items:
        for item in overview_items:
            elements.append(item)
            elements.append(Spacer(1, 2*mm))
    else:
        elements.append(Paragraph(
            '<font color="#666666">No platform or third-party services detected.</font>',
            ParagraphStyle('noitems', fontSize=10, leading=15)
        ))

    elements.append(Spacer(1, 4*mm))

    # Build all checks grouped by section
    sections = [
        {
            'title': '1. Technical Security',
            'checks': [
                (
                    'HTTPS Enabled',
                    scan_result.is_https,
                    'Your site is served over HTTPS, encrypting data in transit.',
                    'Your site is not using HTTPS. This is a serious GDPR risk — migrate immediately.',
                ),
                (
                    'No Mixed Content',
                    not scan_result.has_mixed_content,
                    'No mixed content detected — all resources are loaded securely.',
                    'Mixed content detected — some resources are loaded over HTTP on your HTTPS page. This weakens encryption and may expose user data.',
                ),
                (
                    'X-Frame-Options Header',
                    scan_result.has_x_frame_options,
                    'X-Frame-Options header is set, protecting against clickjacking attacks.',
                    'X-Frame-Options header is missing. Your site may be vulnerable to clickjacking, which could be used to trick users into submitting data.',
                ),
                (
                    'Content Security Policy Header',
                    scan_result.has_content_security_policy,
                    'Content Security Policy header is set, helping prevent cross-site scripting attacks.',
                    'Content Security Policy (CSP) header is missing. This increases the risk of cross-site scripting (XSS) attacks that could compromise user data.',
                ),
                (
                    'X-Content-Type-Options Header',
                    scan_result.has_x_content_type_options,
                    'X-Content-Type-Options header is set.',
                    'X-Content-Type-Options header is missing. This can allow browsers to misinterpret file types, creating security vulnerabilities.',
                ),
                (
                    'Referrer-Policy Header',
                    scan_result.has_referrer_policy,
                    'Referrer-Policy header is set, controlling what data is shared when users navigate away from your site.',
                    'Referrer-Policy header is missing. Without this, full URLs (potentially containing personal data) may be shared with third-party sites when users click links.',
                ),
            ]
        },
        {
            'title': '2. Privacy & Legal Documents',
            'checks': [
                (
                    'Privacy Policy Present',
                    scan_result.has_privacy_policy,
                    'A privacy policy was detected on your site.',
                    'No privacy policy was detected. GDPR requires you to clearly inform users how their data is collected and used.',
                ),
                (
                    'Cookie Policy Present',
                    scan_result.has_cookie_policy,
                    'A cookie policy was detected on your site.',
                    'No separate cookie policy was detected. Under GDPR and PECR, you must clearly explain what cookies you use and why.',
                ),
                (
                    'Terms & Conditions Present',
                    scan_result.has_terms_and_conditions,
                    'Terms and conditions were detected on your site.',
                    'No terms and conditions were detected. While not strictly required by GDPR, T&Cs are important for defining the legal relationship with your users.',
                ),
                (
                    'Data Retention Policy Mentioned',
                    scan_result.has_data_retention_policy,
                    'Your privacy policy references data retention periods.',
                    'No data retention information was found. GDPR requires you to specify how long you retain personal data.',
                ),
            ]
        },
        {
            'title': '3. Consent & Cookie Management',
            'checks': [
                (
                    'Cookie Consent Banner',
                    scan_result.has_cookie_banner,
                    'A cookie consent mechanism was detected on your site.',
                    'No cookie consent banner was detected. GDPR and PECR require prior consent before placing non-essential cookies.',
                ),
                (
                    'Cookie Preferences Link',
                    scan_result.has_cookie_preferences_link,
                    'A cookie settings or preferences link was found, allowing users to manage their consent.',
                    'No cookie preferences or settings link was found. Users should be able to easily manage or withdraw their cookie consent.',
                ),
                (
                    'Form Consent Checkbox',
                    scan_result.has_form_consent_checkbox,
                    'Consent checkboxes were detected on forms.',
                    'No consent checkboxes were found on forms. If your forms collect personal data, explicit consent should be obtained.',
                ),
            ]
        },
        {
            'title': '4. Data Collection',
            'checks': [
                (
                    'Contact Form',
                    not scan_result.has_contact_form,
                    'No contact form detected.',
                    'A contact form was detected. Ensure your privacy policy explains how form submissions are stored and processed.',
                ),
                (
                    'Newsletter Signup',
                    not scan_result.has_newsletter_signup,
                    'No newsletter signup detected.',
                    'A newsletter signup was detected. Ensure you have a lawful basis for email marketing and provide clear unsubscribe options.',
                ),
                (
                    'Login / Account System',
                    not scan_result.has_login,
                    'No login or account system detected.',
                    'A login or account system was detected. Ensure your privacy policy covers account data, and that you have appropriate security measures in place.',
                ),
            ]
        },
        {
            'title': '5. Third-Party & Tracking',
            'checks': [
                (
                    'Google Analytics',
                    not scan_result.has_google_analytics,
                    'No Google Analytics tracking was detected.',
                    'Google Analytics was detected. This transfers user data to Google — ensure you have consent and this is documented in your privacy policy.',
                ),
                (
                    'Facebook Pixel',
                    not scan_result.has_facebook_pixel,
                    'No Facebook Pixel tracking was detected.',
                    'Facebook Pixel was detected. This transfers user data to Meta — ensure consent is obtained and documented in your privacy policy.',
                ),
            ]
        },
        {
            'title': '6. User Rights',
            'checks': [
                (
                    'Unsubscribe Mechanism',
                    scan_result.has_unsubscribe_mechanism,
                    'An unsubscribe or opt-out mechanism was detected.',
                    'No unsubscribe or opt-out mechanism was found. GDPR requires users to be able to withdraw consent and opt out of marketing at any time.',
                ),
                (
                    'Contact Information Present',
                    scan_result.has_contact_info,
                    'Contact information was found on your site.',
                    'No contact information was found. GDPR requires users to be able to contact you regarding their personal data.',
                ),
                (
                    'Data Protection Officer (DPO) Information',
                    scan_result.has_dpo_info,
                    'DPO information was found on your site.',
                    'No Data Protection Officer information was found. Depending on your processing activities, you may be required to appoint and publish DPO contact details.',
                ),
                (
                    'Data Subject Rights Mentioned',
                    scan_result.has_data_subject_rights,
                    'Data subject rights are referenced in your privacy policy.',
                    'No mention of data subject rights was found. GDPR requires you to inform users of their rights, including access, erasure, and portability.',
                ),
            ]
        },
    ]

    # Add other trackers and live chat as dynamic checks
    if scan_result.has_other_trackers:
        for tracker in scan_result.other_trackers_found:
            sections[4]['checks'].append((
                f'Third-party tracker: {tracker.title()}',
                False,
                '',
                f'{tracker.title()} tracking was detected. Ensure this is disclosed in your privacy policy and covered by your cookie consent.',
            ))

    # Calculate score
    all_checks = [c for s in sections for c in s['checks']]
    passed = sum(1 for c in all_checks if c[1])
    total = len(all_checks)
    score = int((passed / total) * 100)

    if score >= 80:
        rating = 'Good'
        rating_colour = HexColor('#22c55e')
    elif score >= 50:
        rating = 'Needs Improvement'
        rating_colour = HexColor('#f59e0b')
    else:
        rating = 'Poor'
        rating_colour = HexColor('#ef4444')

    # --- Score Box ---
    score_data = [[
        Paragraph(f'<font color="{rating_colour.hexval()}"><b>{score}%</b></font>',
                  ParagraphStyle('score', fontSize=36, leading=40)),
        Paragraph(f'<font color="{rating_colour.hexval()}"><b>{rating}</b></font><br/>'
                  f'<font color="#666666">{passed} of {total} checks passed</font>',
                  ParagraphStyle('rating', fontSize=16, leading=24)),
    ]]
    score_table = Table(score_data, colWidths=[40*mm, 130*mm])
    score_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), INFO_BG),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    elements.insert(6, Spacer(1, 4*mm))
    elements.insert(7, score_table)
    elements.insert(8, Spacer(1, 6*mm))

    # --- Sections ---
    for section in sections:
        elements.append(section_heading(section['title']))
        elements.append(HRFlowable(width='100%', thickness=1, color=LIGHT_GREY, spaceAfter=3*mm))
        for label, passed_check, description, recommendation in section['checks']:
            elements.append(make_check_row(label, passed_check, description, recommendation))
            elements.append(Spacer(1, 2*mm))
        elements.append(Spacer(1, 4*mm))

    # --- Footer ---
    elements.append(HRFlowable(width='100%', thickness=1, color=LIGHT_GREY))
    elements.append(Spacer(1, 3*mm))
    elements.append(Paragraph(
        'This report was generated automatically by ClearlyCompliant. It is intended as a guide only and does not constitute legal advice. '
        'For full GDPR compliance, consult a qualified data protection professional.',
        ParagraphStyle('footer', fontSize=9, textColor=GREY, leading=13)
    ))

    doc.build(elements)
    return buffer.getvalue()