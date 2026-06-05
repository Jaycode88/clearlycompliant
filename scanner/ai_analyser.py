import anthropic
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


def analyse_privacy_policy(policy_text, scan_results):
    """
    Use Claude to analyse the privacy policy against what was detected on the site.
    Returns a dict of findings keyed by section.
    """
    if not policy_text or len(policy_text.strip()) < 100:
        return {
            'available': False,
            'reason': 'Privacy policy text could not be retrieved for analysis.',
        }

    # Build context of what was detected on the site
    detected = []
    if scan_results.get('has_google_analytics'):
        detected.append('Google Analytics')
    if scan_results.get('has_facebook_pixel'):
        detected.append('Facebook Pixel')
    if scan_results.get('other_trackers_found'):
        detected.extend([t.title() for t in scan_results['other_trackers_found']])
    if scan_results.get('live_chat_tools_found'):
        detected.extend([t.title() for t in scan_results['live_chat_tools_found']])
    if scan_results.get('payment_processors_found'):
        detected.extend([t.title() for t in scan_results['payment_processors_found']])
    if scan_results.get('has_contact_form'):
        detected.append('contact form')
    if scan_results.get('has_newsletter_signup'):
        detected.append('newsletter signup')
    if scan_results.get('has_login'):
        detected.append('user login / account system')
    if scan_results.get('has_ecommerce'):
        detected.append('ecommerce / online shop')
    if scan_results.get('social_embeds_found'):
        detected.extend([f'{p.title()} embed' for p in scan_results['social_embeds_found']])

    detected_str = ', '.join(detected) if detected else 'no specific third-party services detected'

    prompt = f"""You are a GDPR compliance expert. I have scanned a website and found the following features and third-party services: {detected_str}.

Below is the website's privacy policy text. Please analyse it and identify any specific gaps or issues from a GDPR compliance perspective.

Focus on:
1. Whether each detected service/feature is mentioned and covered
2. Whether lawful basis for processing is stated
3. Whether data subject rights are adequately covered
4. Whether third-party data sharing is disclosed
5. Whether data retention periods are specified
6. Whether international data transfers are addressed
7. Whether contact details for data queries are provided

For each issue you find, be specific — name the exact gap. For example: "Google Analytics is detected on the site but is not mentioned in the privacy policy."

Keep your response concise and structured. Use short paragraphs. Do not use markdown headers or bullet points — write in plain text only as this will be rendered in a PDF.

If the privacy policy is broadly adequate, say so briefly before listing any remaining gaps.

Privacy policy text:
{policy_text[:8000]}"""

    try:
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        message = client.messages.create(
            model='claude-haiku-4-5-20251001',
            max_tokens=1500,
            messages=[{'role': 'user', 'content': prompt}]
        )
        analysis = message.content[0].text
        return {
            'available': True,
            'analysis': analysis,
        }
    except Exception as e:
        logger.error(f'Privacy policy AI analysis failed: {e}')
        return {
            'available': False,
            'reason': 'AI analysis could not be completed at this time.',
        }


def analyse_terms_and_conditions(terms_text, scan_results):
    """
    Use Claude to analyse the T&C against what was detected on the site.
    Returns a dict of findings.
    """
    if not terms_text or len(terms_text.strip()) < 100:
        return {
            'available': False,
            'reason': 'Terms and conditions text could not be retrieved for analysis.',
        }

    # Build context
    features = []
    if scan_results.get('has_ecommerce'):
        features.append('ecommerce / online shop')
    if scan_results.get('has_login'):
        features.append('user login / account system')
    if scan_results.get('has_newsletter_signup'):
        features.append('newsletter signup')
    if scan_results.get('payment_processors_found'):
        features.extend([t.title() for t in scan_results['payment_processors_found']])
    if scan_results.get('has_contact_form'):
        features.append('contact form')

    features_str = ', '.join(features) if features else 'standard business website'

    prompt = f"""You are a legal compliance expert specialising in UK and EU digital business law. I have scanned a website that has the following features: {features_str}.

Below is the website's terms and conditions text. Please analyse it and identify any specific gaps or issues.

Focus on:
1. Whether there is a clear limitation of liability clause
2. Whether governing law and jurisdiction is stated
3. Whether intellectual property rights are addressed
4. Whether there is a refund or cancellation policy (especially important if ecommerce is present)
5. Whether payment terms are covered (if ecommerce or payment processing is present)
6. Whether account termination terms are included (if login/accounts are present)
7. Whether there is a minimum age requirement stated
8. Whether the business's legal identity and registered address are included
9. Whether there are clear terms around user-generated content (if applicable)
10. Whether the terms cover how disputes are resolved

For each issue you find, be specific. For example: "The site has ecommerce functionality but no refund or returns policy is mentioned in the terms and conditions."

Keep your response concise and structured. Use short paragraphs. Do not use markdown headers or bullet points — write in plain text only as this will be rendered in a PDF.

If the terms are broadly adequate, say so briefly before listing any remaining gaps.

Terms and conditions text:
{terms_text[:8000]}"""

    try:
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        message = client.messages.create(
            model='claude-haiku-4-5-20251001',
            max_tokens=1500,
            messages=[{'role': 'user', 'content': prompt}]
        )
        analysis = message.content[0].text
        return {
            'available': True,
            'analysis': analysis,
        }
    except Exception as e:
        logger.error(f'T&C AI analysis failed: {e}')
        return {
            'available': False,
            'reason': 'AI analysis could not be completed at this time.',
        }