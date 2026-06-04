from django.db import models
from orders.models import Order


class ScanResult(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='scan_result')
    has_privacy_policy = models.BooleanField(default=False)
    has_cookie_banner = models.BooleanField(default=False)
    has_google_analytics = models.BooleanField(default=False)
    has_facebook_pixel = models.BooleanField(default=False)
    has_other_trackers = models.BooleanField(default=False)
    other_trackers_found = models.JSONField(default=list)
    is_https = models.BooleanField(default=False)
    has_contact_info = models.BooleanField(default=False)
    raw_html = models.TextField(blank=True)
    scanned_at = models.DateTimeField(auto_now_add=True)
    error = models.TextField(blank=True)

    def __str__(self):
        return f"Scan for {self.order.domain}"