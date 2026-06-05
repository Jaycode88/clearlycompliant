import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin


TRACKER_SIGNATURES = {
    'google_analytics': [
        'google-analytics.com/analytics.js',
        'google-analytics.com/ga.js',
        'googletagmanager.com/gtag',
        'gtag/js',
    ],
    'facebook_pixel': [
        'connect.facebook.net',
        'fbevents.js',
    ],
    'other': [
        'hotjar.com',
        'clarity.ms',
        'mixpanel.com',
        'segment.com',
        'intercom.io',
        'crisp.chat',
        'tiktok.com/i18n/pixel',
        'linkedin.com/insight',
        'twitter.com/i/adsct',
        'snap.licdn.com',
        'ads.pinterest.com',
    ]
}

LIVE_CHAT_SIGNATURES = {
    'intercom': ['intercom.io', 'widget.intercom.io'],
    'crisp': ['crisp.chat', 'client.crisp.chat'],
    'zendesk': ['zendesk.com', 'zopim.com', 'static.zdassets.com'],
    'tawk': ['tawk.to', 'embed.tawk.to'],
    'livechat': ['livechatinc.com', 'cdn.livechatinc.com'],
    'hubspot': ['js.hs-scripts.com', 'js.hubspot.com'],
    'drift': ['drift.com', 'js.driftt.com'],
    'freshchat': ['wchat.freshchat.com'],
}

PAYMENT_SIGNATURES = {
    'stripe': ['stripe.com/v3', 'js.stripe.com'],
    'paypal': ['paypal.com', 'paypalobjects.com'],
    'square': ['squareup.com', 'square.com'],
    'klarna': ['klarna.com'],
    'clearpay': ['clearpay.co.uk', 'afterpay.com'],
}

CDN_SIGNATURES = {
    'cloudflare': ['cloudflare.com', 'cdnjs.cloudflare.com'],
    'aws': ['amazonaws.com', 'cloudfront.net'],
    'fastly': ['fastly.net'],
    'akamai': ['akamaized.net', 'akamaicd.com'],
    'bunnycdn': ['b-cdn.net'],
}

CMS_SIGNATURES = {
    'WordPress': ['wp-content', 'wp-includes', 'wp-json'],
    'Shopify': ['cdn.shopify.com', 'shopify.com/s/'],
    'Wix': ['wix.com', 'wixstatic.com'],
    'Squarespace': ['squarespace.com', 'sqspcdn.com'],
    'Webflow': ['webflow.com', 'webflow.io'],
    'Drupal': ['drupal.js', 'drupal.min.js', 'sites/default/files'],
    'Joomla': ['joomla', '/components/com_'],
    'Magento': ['mage/', 'Mage.Cookies'],
}

COOKIE_BANNER_SIGNATURES = [
    'cookiebot',
    'cookieconsent',
    'cookie-consent',
    'cookie_consent',
    'cookie-banner',
    'cookie-notice',
    'gdpr',
    'onetrust',
    'trustarc',
    'osano',
    'usercentrics',
    'termly',
    'js-cookie-consent',
]

PRIVACY_KEYWORDS = [
    'privacy policy',
    'privacy notice',
    'data protection',
]

COOKIE_POLICY_KEYWORDS = [
    'cookie policy',
    'cookie notice',
    'cookies policy',
]

TERMS_KEYWORDS = [
    'terms and conditions',
    'terms of service',
    'terms of use',
    'legal',
]

DATA_RETENTION_KEYWORDS = [
    'data retention',
    'retain your data',
    'how long we keep',
    'retention period',
    'store your data for',
]

DATA_SUBJECT_RIGHTS_KEYWORDS = [
    'right to access',
    'right to erasure',
    'right to be forgotten',
    'right to rectification',
    'right to portability',
    'data subject rights',
    'your rights',
    'right to object',
]

CONTACT_KEYWORDS = [
    'contact us',
    'get in touch',
]

DPO_KEYWORDS = [
    'data protection officer',
    'dpo@',
    'dpo ',
]

LOGIN_INDICATORS = [
    'login', 'log in', 'sign in', 'signin',
    'my account', 'my-account', 'dashboard',
    'register', 'create account', 'member',
    '/login', '/signin', '/my-account', '/account',
]


def normalise_domain(domain):
    domain = domain.strip()
    if not domain.startswith(('http://', 'https://')):
        domain = 'https://' + domain
    return domain


def fetch_page(url, timeout=15):
    try:
        response = requests.get(
            url,
            timeout=timeout,
            headers={'User-Agent': 'ClearlyCompliant GDPR Scanner/1.0'},
            allow_redirects=True,
        )
        response.raise_for_status()
        return response
    except Exception:
        return None


def find_policy_url(soup, base_url, keywords):
    for a in soup.find_all('a', href=True):
        href = a['href'].lower()
        link_text = a.get_text().lower()
        if any(k in href or k in link_text for k in keywords):
            full_url = urljoin(base_url, a['href'])
            return full_url
    return None


def fetch_policy_text(url):
    if not url:
        return ''
    response = fetch_page(url)
    if not response:
        return ''
    soup = BeautifulSoup(response.text, 'html.parser')
    for tag in soup.find_all(['nav', 'footer', 'header']):
        tag.decompose()
    return soup.get_text(separator=' ', strip=True)[:20000]


def scan_domain(domain):
    domain = normalise_domain(domain)
    results = {
        # Section 1 - Technical Security
        'is_https': False,
        'has_mixed_content': False,
        'has_x_frame_options': False,
        'has_content_security_policy': False,
        'has_x_content_type_options': False,
        'has_referrer_policy': False,

        # Section 2 - Privacy & Legal Documents
        'has_privacy_policy': False,
        'has_cookie_policy': False,
        'has_terms_and_conditions': False,
        'has_data_retention_policy': False,
        'privacy_policy_url': '',
        'terms_url': '',
        'privacy_policy_text': '',
        'terms_text': '',

        # Section 3 - Consent & Cookie Management
        'has_cookie_banner': False,
        'has_cookie_preferences_link': False,
        'has_form_consent_checkbox': False,

        # Section 4 - Data Collection
        'has_contact_form': False,
        'has_newsletter_signup': False,
        'has_login': False,

        # Section 5 - Third Party & Tracking
        'has_google_analytics': False,
        'has_facebook_pixel': False,
        'has_other_trackers': False,
        'other_trackers_found': [],
        'has_live_chat': False,
        'live_chat_tools_found': [],
        'has_payment_processor': False,
        'payment_processors_found': [],
        'has_cdn': False,
        'cdn_found': [],
        'cms_detected': '',

        # Section 6 - User Rights
        'has_unsubscribe_mechanism': False,
        'has_contact_info': False,
        'has_dpo_info': False,
        'has_data_subject_rights': False,

        # Meta
        'raw_html': '',
        'error': '',
        'error_type': '',
    }

    try:
        response = fetch_page(domain)
        if not response:
            raise requests.exceptions.ConnectionError()

        html = response.text
        results['raw_html'] = html[:50000]
        results['is_https'] = response.url.startswith('https://')

        soup = BeautifulSoup(html, 'html.parser')
        text = soup.get_text(separator=' ').lower()
        all_html_lower = html.lower()
        base_url = response.url

        # --- Section 1: Technical Security ---
        headers = {k.lower(): v for k, v in response.headers.items()}
        results['has_x_frame_options'] = 'x-frame-options' in headers
        results['has_content_security_policy'] = 'content-security-policy' in headers
        results['has_x_content_type_options'] = 'x-content-type-options' in headers
        results['has_referrer_policy'] = 'referrer-policy' in headers

        if results['is_https']:
            for tag in soup.find_all(['script', 'img', 'link', 'iframe'], src=True):
                src = tag.get('src', '')
                if src.startswith('http://'):
                    results['has_mixed_content'] = True
                    break

        # --- Section 2: Privacy & Legal Documents ---
        privacy_url = find_policy_url(soup, base_url, ['privacy-policy', 'privacy_policy', 'privacy', 'data-protection'])
        if privacy_url:
            results['has_privacy_policy'] = True
            results['privacy_policy_url'] = privacy_url
            results['privacy_policy_text'] = fetch_policy_text(privacy_url)
        elif any(k in text for k in PRIVACY_KEYWORDS):
            results['has_privacy_policy'] = True

        cookie_url = find_policy_url(soup, base_url, ['cookie-policy', 'cookie_policy', 'cookies'])
        if cookie_url:
            results['has_cookie_policy'] = True
        elif any(k in text for k in COOKIE_POLICY_KEYWORDS):
            results['has_cookie_policy'] = True

        terms_url = find_policy_url(soup, base_url, ['terms-and-conditions', 'terms_and_conditions', 'terms-of-service', 'terms-of-use', 'terms', 'legal'])
        if terms_url:
            results['has_terms_and_conditions'] = True
            results['terms_url'] = terms_url
            results['terms_text'] = fetch_policy_text(terms_url)
        elif any(k in text for k in TERMS_KEYWORDS):
            results['has_terms_and_conditions'] = True

        if results['privacy_policy_text']:
            if any(k in results['privacy_policy_text'].lower() for k in DATA_RETENTION_KEYWORDS):
                results['has_data_retention_policy'] = True
        elif any(k in text for k in DATA_RETENTION_KEYWORDS):
            results['has_data_retention_policy'] = True

        # --- Section 3: Consent & Cookie Management ---
        for sig in COOKIE_BANNER_SIGNATURES:
            if sig in all_html_lower:
                results['has_cookie_banner'] = True
                break

        for a in soup.find_all('a', href=True):
            link_text = a.get_text().lower()
            if any(k in link_text for k in ['cookie settings', 'cookie preferences', 'manage cookies']):
                results['has_cookie_preferences_link'] = True
                break

        for form in soup.find_all('form'):
            checkboxes = form.find_all('input', {'type': 'checkbox'})
            for cb in checkboxes:
                cb_str = str(cb).lower()
                if any(k in cb_str for k in ['consent', 'agree', 'gdpr', 'terms', 'privacy']):
                    results['has_form_consent_checkbox'] = True
                    break

        # --- Section 4: Data Collection ---
        forms = soup.find_all('form')
        for form in forms:
            form_text = form.get_text().lower()
            form_html = str(form).lower()
            inputs = form.find_all('input')
            input_types = [i.get('type', '').lower() for i in inputs]

            if 'email' in input_types or 'email' in form_html:
                if any(k in form_text for k in ['newsletter', 'subscribe', 'sign up', 'signup']):
                    results['has_newsletter_signup'] = True
                elif any(k in form_text for k in ['contact', 'message', 'enquiry', 'inquiry']):
                    results['has_contact_form'] = True

            if 'password' in input_types:
                results['has_login'] = True

        # Also check for login links/references in page text and HTML
        for indicator in LOGIN_INDICATORS:
            if indicator in all_html_lower:
                results['has_login'] = True
                break

        # --- Section 5: Third Party & Tracking ---
        scripts = [s.get('src', '') for s in soup.find_all('script', src=True)]
        inline_scripts = ' '.join([s.get_text() for s in soup.find_all('script', src=False)])
        all_scripts = ' '.join(scripts) + ' ' + inline_scripts

        for sig in TRACKER_SIGNATURES['google_analytics']:
            if sig in all_scripts:
                results['has_google_analytics'] = True
                break

        for sig in TRACKER_SIGNATURES['facebook_pixel']:
            if sig in all_scripts:
                results['has_facebook_pixel'] = True
                break

        other_found = []
        for sig in TRACKER_SIGNATURES['other']:
            if sig in all_scripts or sig in all_html_lower:
                name = sig.split('.')[0]
                if name not in other_found:
                    other_found.append(name)
        if other_found:
            results['has_other_trackers'] = True
            results['other_trackers_found'] = other_found

        live_chat_found = []
        for tool, sigs in LIVE_CHAT_SIGNATURES.items():
            for sig in sigs:
                if sig in all_html_lower:
                    if tool not in live_chat_found:
                        live_chat_found.append(tool)
                    break
        if live_chat_found:
            results['has_live_chat'] = True
            results['live_chat_tools_found'] = live_chat_found

        payment_found = []
        for processor, sigs in PAYMENT_SIGNATURES.items():
            for sig in sigs:
                if sig in all_html_lower:
                    if processor not in payment_found:
                        payment_found.append(processor)
                    break
        if payment_found:
            results['has_payment_processor'] = True
            results['payment_processors_found'] = payment_found

        cdn_found = []
        for cdn, sigs in CDN_SIGNATURES.items():
            for sig in sigs:
                if sig in all_html_lower:
                    if cdn not in cdn_found:
                        cdn_found.append(cdn)
                    break
        if cdn_found:
            results['has_cdn'] = True
            results['cdn_found'] = cdn_found

        for cms, sigs in CMS_SIGNATURES.items():
            for sig in sigs:
                if sig in all_html_lower:
                    results['cms_detected'] = cms
                    break
            if results['cms_detected']:
                break

        # --- Section 6: User Rights ---
        if 'unsubscribe' in text or 'opt out' in text or 'opt-out' in text:
            results['has_unsubscribe_mechanism'] = True

        if any(k in text for k in CONTACT_KEYWORDS):
            results['has_contact_info'] = True

        if any(k in text for k in DPO_KEYWORDS):
            results['has_dpo_info'] = True

        policy_text_lower = results['privacy_policy_text'].lower()
        if any(k in policy_text_lower for k in DATA_SUBJECT_RIGHTS_KEYWORDS):
            results['has_data_subject_rights'] = True
        elif any(k in text for k in DATA_SUBJECT_RIGHTS_KEYWORDS):
            results['has_data_subject_rights'] = True

    except requests.exceptions.ConnectionError:
        results['error'] = f'Could not connect to {domain}. The domain may not exist or is currently unreachable.'
        results['error_type'] = 'connection_error'
    except requests.exceptions.Timeout:
        results['error'] = f'Connection to {domain} timed out after 15 seconds.'
        results['error_type'] = 'timeout'
    except requests.exceptions.TooManyRedirects:
        results['error'] = f'{domain} has too many redirects and could not be scanned.'
        results['error_type'] = 'redirect_error'
    except requests.exceptions.HTTPError as e:
        results['error'] = f'{domain} returned an error: {e.response.status_code}.'
        results['error_type'] = 'http_error'
    except Exception as e:
        results['error'] = f'An unexpected error occurred while scanning {domain}.'
        results['error_type'] = 'unknown'

    return results