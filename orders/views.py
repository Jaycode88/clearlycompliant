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
def validate_discount_code(request):
    try:
        data = json.loads(request.body)
        code = data.get('code', '').strip()

        if not code:
            return JsonResponse({'valid': False, 'error': 'Please enter a discount code.'})

        # Validate against Stripe
        promotion_codes = stripe.PromotionCode.list(code=code, active=True, limit=1)

        if not promotion_codes.data:
            return JsonResponse({'valid': False, 'error': 'Invalid or expired discount code.'})

        promo = promotion_codes.data[0]
        coupon = promo.coupon

        # Calculate discounted price
        if coupon.percent_off:
            discount_pence = int(REPORT_PRICE_PENCE * coupon.percent_off / 100)
            final_price = REPORT_PRICE_PENCE - discount_pence
            discount_label = f'{int(coupon.percent_off)}% off'
        elif coupon.amount_off:
            final_price = max(0, REPORT_PRICE_PENCE - coupon.amount_off)
            discount_label = f'£{coupon.amount_off / 100:.2f} off'
        else:
            return JsonResponse({'valid': False, 'error': 'Invalid discount code.'})

        return JsonResponse({
            'valid': True,
            'promo_code_id': promo.id,
            'final_price': final_price,
            'final_price_display': f'£{final_price / 100:.2f}',
            'discount_label': discount_label,
        })

    except Exception as e:
        return JsonResponse({'valid': False, 'error': 'Could not validate code. Please try again.'})


@require_POST
def create_payment_intent(request):
    try:
        data = json.loads(request.body)
        domain = data.get('domain', '').strip()
        email = data.get('email', '').strip()
        promo_code_id = data.get('promo_code_id', '').strip()

        if not domain or not email:
            return JsonResponse({'error': 'Domain and email are required.'}, status=400)

        if not is_valid_domain(domain):
            return JsonResponse({'error': 'Please enter a valid domain name, e.g. example.com'}, status=400)

        domain = re.sub(r'^https?://', '', domain).strip('/')

        # Calculate final price
        amount = REPORT_PRICE_PENCE
        discount_code = ''

        if promo_code_id:
            try:
                promo = stripe.PromotionCode.retrieve(promo_code_id)
                coupon = promo.coupon
                discount_code = promo.code
                if coupon.percent_off:
                    amount = int(REPORT_PRICE_PENCE * (1 - coupon.percent_off / 100))
                elif coupon.amount_off:
                    amount = max(0, REPORT_PRICE_PENCE - coupon.amount_off)
            except Exception:
                pass

        order = Order.objects.create(
            domain=domain,
            email=email,
            utm_source=data.get('utm_source', ''),
            utm_medium=data.get('utm_medium', ''),
            utm_campaign=data.get('utm_campaign', ''),
            utm_term=data.get('utm_term', ''),
            utm_content=data.get('utm_content', ''),
            referrer=data.get('referrer', ''),
            discount_code=discount_code,
            amount_paid=amount,
        )

        intent_params = {
            'amount': amount,
            'currency': 'gbp',
            'metadata': {
                'order_id': str(order.id),
                'domain': domain,
                'email': email,
            }
        }

        if promo_code_id:
            intent_params['discounts'] = [{'promotion_code': promo_code_id}]

        intent = stripe.PaymentIntent.create(**intent_params)

        order.stripe_payment_intent_id = intent.id
        order.save()

        return JsonResponse({
            'client_secret': intent.client_secret,
            'order_id': str(order.id),
            'amount': amount,
            'amount_display': f'£{amount / 100:.2f}',
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