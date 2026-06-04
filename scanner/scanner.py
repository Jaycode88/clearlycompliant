import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse


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
    ]
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
    'cookie policy',
]

CONTACT_KEYWORDS = [
    'contact us',
    'contact@',
    'dpo@',
    'data protection officer',
    'get in touch',
]


def normalise_domain(domain):
    """Ensure the domain has a scheme."""
    domain = domain.strip()
    if not domain.startswith(('http://', 'https://')):
        domain = 'https://' + domain
    return domain


def scan_domain(domain):
    """
    Crawl the domain and return a dict of GDPR check results.
    """
    domain = normalise_domain(domain)
    results = {
        'has_privacy_policy': False,
        'has_cookie_banner': False,
        'has_google_analytics': False,
        'has_facebook_pixel': False,
        'has_other_trackers': False,
        'other_trackers_found': [],
        'is_https': False,
        'has_contact_info': False,
        'raw_html': '',
        'error': '',
    }

    try:
        response = requests.get(
            domain,
            timeout=15,
            headers={'User-Agent': 'ClearlyCompliant GDPR Scanner/1.0'},
            allow_redirects=True,
        )
        html = response.text
        results['raw_html'] = html[:50000]  # cap storage at 50k chars
        results['is_https'] = response.url.startswith('https://')

        soup = BeautifulSoup(html, 'html.parser')
        text = soup.get_text(separator=' ').lower()
        all_html_lower = html.lower()

        # Privacy policy
        for keyword in PRIVACY_KEYWORDS:
            if keyword in text:
                results['has_privacy_policy'] = True
                break
        # Also check links
        for a in soup.find_all('a', href=True):
            href = a['href'].lower()
            link_text = a.get_text().lower()
            if any(k in href or k in link_text for k in ['privacy', 'cookie-policy', 'data-protection']):
                results['has_privacy_policy'] = True
                break

        # Cookie banner
        for sig in COOKIE_BANNER_SIGNATURES:
            if sig in all_html_lower:
                results['has_cookie_banner'] = True
                break

        # Trackers — scripts
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
                other_found.append(sig.split('.')[0])
        if other_found:
            results['has_other_trackers'] = True
            results['other_trackers_found'] = other_found

        # Contact info
        for keyword in CONTACT_KEYWORDS:
            if keyword in text:
                results['has_contact_info'] = True
                break

    except requests.exceptions.RequestException as e:
        results['error'] = str(e)

    return results