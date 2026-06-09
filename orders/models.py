from django.db import models
import uuid


class Order(models.Model):

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PAID = 'paid', 'Paid'
        SCANNING = 'scanning', 'Scanning'
        ANALYSING = 'analysing', 'Analysing'
        GENERATING = 'generating', 'Generating Report'
        EMAILING = 'emailing', 'Sending Email'
        COMPLETE = 'complete', 'Complete'
        FAILED = 'failed', 'Failed'

    class ReportType(models.TextChoices):
        FREE = 'free', 'Free'
        PAID = 'paid', 'Paid'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    domain = models.URLField()
    email = models.EmailField()
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    report_type = models.CharField(max_length=10, choices=ReportType.choices, default=ReportType.FREE)
    free_result_token = models.UUIDField(default=uuid.uuid4, unique=True)
    free_results_viewed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # UTM Tracking
    utm_source = models.CharField(max_length=200, blank=True)
    utm_medium = models.CharField(max_length=200, blank=True)
    utm_campaign = models.CharField(max_length=200, blank=True)
    utm_term = models.CharField(max_length=200, blank=True)
    utm_content = models.CharField(max_length=200, blank=True)
    referrer = models.URLField(max_length=500, blank=True)

    # Discount
    discount_code = models.CharField(max_length=100, blank=True)
    amount_paid = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.domain} — {self.report_type} — {self.status}"