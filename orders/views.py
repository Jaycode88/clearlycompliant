import json
import re
import stripe
import threading
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.shortcuts import render
from .models import Order

stripe.api_key = settings.STRIPE_SECRET_KEY

REPORT_PRICE_PENCE = 2999  # £29.99


def is_valid_domain(domain):
    domain = domain.strip().lower()
    domain = re.sub(r'^https?://', '', domain)
    pattern = r'^([a-z0-9]+(-[a-z0-9]+)*\.)+[a-z]{2,}$'
    return bool(re.match(pattern, domain))


def run_scan_sync(order_id):
    print(f'>>> run_scan_sync started for {order_id}')
    from scanner.tasks import run_scan
    run_scan(order_id)


@require_POST
def create_payment_intent(request):
    try:
        data = json.loads(request.body)
        domain = data.get('domain', '').strip()
        email = data.get('email', '').strip()

        if not domain or not email:
            return JsonResponse({'error': 'Domain and email are required.'}, status=400)

        if not is_valid_domain(domain):
            return JsonResponse({'error': 'Please enter a valid domain name, e.g. example.com'}, status=400)

        # Normalise — strip scheme
        domain = re.sub(r'^https?://', '', domain).strip('/')

        order = Order.objects.create(domain=domain, email=email)

        intent = stripe.PaymentIntent.create(
            amount=REPORT_PRICE_PENCE,
            currency='gbp',
            metadata={
                'order_id': str(order.id),
                'domain': domain,
                'email': email,
            }
        )

        order.stripe_payment_intent_id = intent.id
        order.save()

        return JsonResponse({
            'client_secret': intent.client_secret,
            'order_id': str(order.id),
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_POST
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except (ValueError, stripe.error.SignatureVerificationError):
        return HttpResponse(status=400)

    if event['type'] == 'payment_intent.succeeded':
        intent = event['data']['object']
        order_id = intent['metadata']['order_id']

        try:
            order = Order.objects.get(id=order_id)
            order.status = Order.Status.PAID
            order.save()
            thread = threading.Thread(target=run_scan_sync, args=(str(order.id),))
            thread.daemon = True
            thread.start()
        except Order.DoesNotExist:
            pass

    return HttpResponse(status=200)


def checkout(request):
    return render(request, 'orders/checkout.html', {
        'stripe_publishable_key': settings.STRIPE_PUBLISHABLE_KEY,
    })

def privacy_policy(request):
    return render(request, 'legal/privacy_policy.html')

def terms_and_conditions(request):
    return render(request, 'legal/terms_and_conditions.html')