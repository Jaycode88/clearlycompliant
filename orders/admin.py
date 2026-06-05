from django.contrib import admin
from .models import Order


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['domain', 'email', 'status', 'utm_source', 'utm_medium', 'utm_campaign', 'created_at']
    list_filter = ['status', 'utm_source', 'utm_medium', 'utm_campaign']
    search_fields = ['domain', 'email', 'utm_source', 'utm_campaign']
    readonly_fields = [
        'id', 'created_at', 'updated_at',
        'utm_source', 'utm_medium', 'utm_campaign',
        'utm_term', 'utm_content', 'referrer',
        'stripe_payment_intent_id',
    ]
    fieldsets = [
        ('Order Details', {
            'fields': ['id', 'domain', 'email', 'status', 'stripe_payment_intent_id']
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at']
        }),
        ('Traffic Source', {
            'fields': ['utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content', 'referrer']
        }),
    ]