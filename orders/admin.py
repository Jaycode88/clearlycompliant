from django.contrib import admin
from .models import Order


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        'domain', 'email', 'report_type', 'status',
        'free_results_viewed', 'utm_source', 'utm_medium',
        'utm_campaign', 'amount_paid', 'created_at'
    ]
    list_filter = [
        'report_type', 'status', 'free_results_viewed',
        'utm_source', 'utm_medium', 'utm_campaign'
    ]
    search_fields = ['domain', 'email', 'utm_source', 'utm_campaign']
    readonly_fields = [
        'id', 'free_result_token', 'created_at', 'updated_at',
        'utm_source', 'utm_medium', 'utm_campaign',
        'utm_term', 'utm_content', 'referrer',
        'stripe_payment_intent_id',
    ]
    fieldsets = [
        ('Order Details', {
            'fields': ['id', 'domain', 'email', 'status', 'report_type', 'stripe_payment_intent_id']
        }),
        ('Free Report', {
            'fields': ['free_result_token', 'free_results_viewed']
        }),
        ('Payment', {
            'fields': ['discount_code', 'amount_paid']
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at']
        }),
        ('Traffic Source', {
            'fields': ['utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content', 'referrer']
        }),
    ]