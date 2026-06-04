from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor, black, white
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.enums import TA_LEFT, TA_CENTER
import io


BRAND_PURPLE = HexColor('#6366f1')
PASS_GREEN = HexColor('#15803d')
PASS_BG = HexColor('#f0fdf4')
PASS_BORDER = HexColor('#bbf7d0')
FAIL_ORANGE = HexColor('#c2410c')
FAIL_BG = HexColor('#fff7ed')
FAIL_BORDER = HexColor('#fed7aa')
GREY = HexColor('#666666')
LIGHT_GREY = HexColor('#e5e7eb')


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

    styles = getSampleStyleSheet()
    elements = []

    # Header
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
    elements.append(HRFlowable(width='100%', thickness=3, color=BRAND_PURPLE, spaceAfter=8*mm))

    # Build checks
    checks = [
        {
            'label': 'HTTPS Enabled',
            'passed': scan_result.is_https,
            'description': 'Your site is served over HTTPS, encrypting data in transit.',
            'recommendation': 'Your site is not using HTTPS. This is a serious GDPR risk — migrate to HTTPS immediately.',
        },
        {
            'label': 'Privacy Policy Present',
            'passed': scan_result.has_privacy_policy,
            'description': 'A privacy policy was detected on your site.',
            'recommendation': 'No privacy policy was detected. GDPR requires you to clearly inform users how their data is used.',
        },
        {
            'label': 'Cookie Consent Banner',
            'passed': scan_result.has_cookie_banner,
            'description': 'A cookie consent mechanism was detected.',
            'recommendation': 'No cookie consent banner was detected. If your site uses cookies, you must obtain prior consent from users.',
        },
        {
            'label': 'Google Analytics',
            'passed': not scan_result.has_google_analytics,
            'description': 'No Google Analytics tracking was detected.',
            'recommendation': 'Google Analytics was detected. Ensure you have a lawful basis for this tracking and that it is covered in your cookie consent.',
        },
        {
            'label': 'Facebook Pixel',
            'passed': not scan_result.has_facebook_pixel,
            'description': 'No Facebook Pixel tracking was detected.',
            'recommendation': 'Facebook Pixel was detected. This transfers user data to Meta — ensure consent is obtained and documented.',
        },
        {
            'label': 'Contact / DPO Information',
            'passed': scan_result.has_contact_info,
            'description': 'Contact information was found on your site.',
            'recommendation': 'No contact or Data Protection Officer information was found. GDPR requires users to be able to contact you regarding their data.',
        },
    ]

    if scan_result.has_other_trackers:
        for tracker in scan_result.other_trackers_found:
            checks.append({
                'label': f'Third-party tracker: {tracker}',
                'passed': False,
                'description': '',
                'recommendation': f'{tracker} tracking was detected. Ensure this is disclosed in your privacy policy and covered by cookie consent.',
            })

    passed = sum(1 for c in checks if c['passed'])
    total = len(checks)
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

    # Score box
    score_data = [[
        Paragraph(f'<font color="{rating_colour.hexval()}"><b>{score}%</b></font>',
                  ParagraphStyle('score', fontSize=36, leading=40)),
        Paragraph(f'<font color="{rating_colour.hexval()}"><b>{rating}</b></font><br/>'
                  f'<font color="#666666">{passed} of {total} checks passed</font>',
                  ParagraphStyle('rating', fontSize=16, leading=24)),
    ]]
    score_table = Table(score_data, colWidths=[40*mm, 120*mm])
    score_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), HexColor('#f8f8ff')),
        ('ROUNDEDCORNERS', [6, 6, 6, 6]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    elements.append(score_table)
    elements.append(Spacer(1, 8*mm))

    # Section heading
    elements.append(Paragraph(
        '<font color="#6366f1"><b>Detailed Findings</b></font>',
        ParagraphStyle('sectionhead', fontSize=14, leading=18)
    ))
    elements.append(HRFlowable(width='100%', thickness=1, color=LIGHT_GREY, spaceAfter=4*mm))

    # Checks
    for check in checks:
        bg = PASS_BG if check['passed'] else FAIL_BG
        icon = '✓' if check['passed'] else '✗'
        label_colour = '#15803d' if check['passed'] else '#c2410c'
        text = check['description'] if check['passed'] else check['recommendation']

        row = [[
            Paragraph(f'<font color="{label_colour}"><b>{icon}</b></font>',
                      ParagraphStyle('icon', fontSize=14, leading=18)),
            Paragraph(f'<font color="{label_colour}"><b>{check["label"]}</b></font><br/>'
                      f'<font color="#555555">{text}</font>',
                      ParagraphStyle('checktext', fontSize=11, leading=16)),
        ]]
        t = Table(row, colWidths=[12*mm, 148*mm])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), bg),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('ROUNDEDCORNERS', [4, 4, 4, 4]),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 3*mm))

    # Footer
    elements.append(Spacer(1, 8*mm))
    elements.append(HRFlowable(width='100%', thickness=1, color=LIGHT_GREY, spaceBefore=4*mm))
    elements.append(Paragraph(
        'This report was generated automatically by ClearlyCompliant. It is intended as a guide only and does not constitute legal advice. '
        'For full GDPR compliance, consult a qualified data protection professional.',
        ParagraphStyle('footer', fontSize=9, textColor=GREY, leading=13)
    ))

    doc.build(elements)
    return buffer.getvalue()