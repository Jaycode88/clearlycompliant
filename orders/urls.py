from django.urls import path
from . import views

urlpatterns = [
    path('create-payment-intent/', views.create_payment_intent, name='create_payment_intent'),
    path('webhook/stripe/', views.stripe_webhook, name='stripe_webhook'),
    path('', views.checkout, name='checkout'),
    path('privacy-policy/', views.privacy_policy, name='privacy_policy'),
    path('terms-and-conditions/', views.terms_and_conditions, name='terms_and_conditions'),
    path('validate-discount/', views.validate_discount_code, name='validate_discount'),
]