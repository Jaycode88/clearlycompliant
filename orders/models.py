from django.db import models
import uuid


class Order(models.Model):

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PAID = 'paid', 'Paid'
        SCANNING = 'scanning', 'Scanning'
        COMPLETE = 'complete', 'Complete'
        FAILED = 'failed', 'Failed'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    domain = models.URLField()
    email = models.EmailField()
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # UTM Tracking
    utm_source = models.CharField(max_length=200, blank=True)
    utm_medium = models.CharField(max_length=200, blank=True)
    utm_campaign = models.CharField(max_length=200, blank=True)
    utm_term = models.CharField(max_length=200, blank=True)
    utm_content = models.CharField(max_length=200, blank=True)
    referrer = models.URLField(max_length=500, blank=True)

    def __str__(self):
        return f"{self.domain} — {self.status}"