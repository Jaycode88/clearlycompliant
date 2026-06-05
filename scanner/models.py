from django.db import models
from orders.models import Order


class ScanResult(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='scan_result')

    # Section 1 - Technical Security
    is_https = models.BooleanField(default=False)
    has_mixed_content = models.BooleanField(default=False)
    has_x_frame_options = models.BooleanField(default=False)
    has_content_security_policy = models.BooleanField(default=False)
    has_x_content_type_options = models.BooleanField(default=False)
    has_referrer_policy = models.BooleanField(default=False)

    # Section 2 - Privacy & Legal Documents
    has_privacy_policy = models.BooleanField(default=False)
    has_cookie_policy = models.BooleanField(default=False)
    has_terms_and_conditions = models.BooleanField(default=False)
    has_data_retention_policy = models.BooleanField(default=False)
    privacy_policy_url = models.URLField(blank=True, max_length=500)
    terms_url = models.URLField(blank=True, max_length=500)
    privacy_policy_text = models.TextField(blank=True)
    terms_text = models.TextField(blank=True)

    # Section 3 - Consent & Cookie Management
    has_cookie_banner = models.BooleanField(default=False)
    has_cookie_preferences_link = models.BooleanField(default=False)
    has_form_consent_checkbox = models.BooleanField(default=False)

    # Section 4 - Data Collection
    has_contact_form = models.BooleanField(default=False)
    has_newsletter_signup = models.BooleanField(default=False)
    has_login = models.BooleanField(default=False)
    has_ecommerce = models.BooleanField(default=False)
    ecommerce_platform = models.CharField(max_length=100, blank=True)

    # Section 5 - Third Party & Tracking
    has_google_analytics = models.BooleanField(default=False)
    has_facebook_pixel = models.BooleanField(default=False)
    has_other_trackers = models.BooleanField(default=False)
    other_trackers_found = models.JSONField(default=list)
    has_live_chat = models.BooleanField(default=False)
    live_chat_tools_found = models.JSONField(default=list)
    has_payment_processor = models.BooleanField(default=False)
    payment_processors_found = models.JSONField(default=list)
    has_cdn = models.BooleanField(default=False)
    cdn_found = models.JSONField(default=list)
    has_social_embeds = models.BooleanField(default=False)
    social_embeds_found = models.JSONField(default=list)
    cms_detected = models.CharField(max_length=100, blank=True)

    # Section 6 - User Rights
    has_unsubscribe_mechanism = models.BooleanField(default=False)
    has_contact_info = models.BooleanField(default=False)
    has_dpo_info = models.BooleanField(default=False)
    has_data_subject_rights = models.BooleanField(default=False)

    # Meta
    raw_html = models.TextField(blank=True)
    scanned_at = models.DateTimeField(auto_now_add=True)
    error = models.TextField(blank=True)

    def __str__(self):
        return f"Scan for {self.order.domain}"