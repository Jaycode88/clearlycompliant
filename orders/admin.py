from django.contrib import admin
from .models import Order


class PaidFilter(admin.SimpleListFilter):
    title = 'Payment Status'
    parameter_name = 'payment_status'

    def lookups(self, request, model_admin):
        return [
            ('paid', 'Paid (full report purchased)'),
            ('not_paid', 'Not paid (free scan only)'),
            ('rescan', 'Re-scan'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'paid':
            return queryset.filter(report_type='paid')
        if self.value() == 'not_paid':
            return queryset.filter(report_type='free')
        if self.value() == 'rescan':
            return queryset.filter(report_type='rescan')
        return queryset


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        'domain', 'email', 'report_type', 'status',
        'free_results_viewed', 'utm_source', 'utm_medium',
        'utm_campaign', 'amount_paid', 'created_at'
    ]
    list_filter = [
        PaidFilter,
        'status',
        'free_results_viewed',
        'utm_source',
        'utm_medium',
        'utm_campaign',
        ('created_at', admin.DateFieldListFilter),
    ]
    search_fields = ['domain', 'email', 'utm_source', 'utm_campaign', 'discount_code']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    readonly_fields = [
        'id', 'free_result_token', 'created_at', 'updated_at',
        'utm_source', 'utm_medium', 'utm_campaign',
        'utm_term', 'utm_content', 'referrer',
        'stripe_payment_intent_id', 'rescan_eligible',
        'rescan_days_remaining',
    ]
    fieldsets = [
        ('Order Details', {
            'fields': ['id', 'domain', 'email', 'status', 'report_type', 'stripe_payment_intent_id']
        }),
        ('Free Report', {
            'fields': ['free_result_token', 'free_results_viewed']
        }),
        ('Re-scan', {
            'fields': ['rescan_of', 'rescan_eligible', 'rescan_days_remaining']
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