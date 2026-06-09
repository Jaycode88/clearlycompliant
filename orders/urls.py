from django.urls import path
from . import views

urlpatterns = [
    path('', views.checkout, name='checkout'),
    path('start-scan/', views.start_free_scan, name='start_free_scan'),
    path('results/<uuid:token>/', views.free_results, name='free_results'),
    path('status/<uuid:order_id>/', views.order_status_page, name='order_status_page'),
    path('api/status/<uuid:order_id>/', views.order_status, name='order_status'),
    path('create-payment-intent/', views.create_payment_intent, name='create_payment_intent'),
    path('validate-discount/', views.validate_discount_code, name='validate_discount'),
    path('webhook/stripe/', views.stripe_webhook, name='stripe_webhook'),
    path('privacy-policy/', views.privacy_policy, name='privacy_policy'),
    path('terms-and-conditions/', views.terms_and_conditions, name='terms_and_conditions'),
    path('complete/', views.order_complete, name='order_complete'),
    path('rescan/<uuid:token>/', views.rescan_page, name='rescan_page'),
    path('rescan/<uuid:token>/start/', views.start_rescan, name='start_rescan'),
]