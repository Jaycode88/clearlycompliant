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


def get_coupon_from_promo(promo):
    """Extract and retrieve the coupon from a promotion code object."""
    try:
        promotion = getattr(promo, 'promotion', None)
        print(f'>>> promotion: {promotion}')
        if promotion:
            coupon_id = getattr(promotion, 'coupon', None)
            print(f'>>> coupon_id: {coupon_id}')
            if coupon_id:
                coupon = stripe.Coupon.retrieve(coupon_id)
                print(f'>>> retrieved coupon: {coupon}')
                return coupon
    except Exception as e:
        print(f'>>> promotion path error: {e}')
    try:
        coupon = getattr(promo, 'coupon', None)
        print(f'>>> direct coupon: {coupon}')
        if coupon:
            if isinstance(coupon, str):
                return stripe.Coupon.retrieve(coupon)
            return coupon
    except Exception as e:
        print(f'>>> direct coupon error: {e}')
    return None


@require_POST
def validate_discount_code(request):
    try:
        data = json.loads(request.body)
        code = data.get('code', '').strip()

        if not code:
            return JsonResponse({'valid': False, 'error': 'Please enter a discount code.'})

        promotion_codes = stripe.PromotionCode.list(code=code, active=True, limit=1)

        if not promotion_codes.data:
            return JsonResponse({'valid': False, 'error': 'Invalid or expired discount code.'})

        promo = promotion_codes.data[0]
        coupon = get_coupon_from_promo(promo)

        if not coupon:
            return JsonResponse({'valid': False, 'error': 'Invalid discount code.'})

        percent_off = getattr(coupon, 'percent_off', None)
        amount_off = getattr(coupon, 'amount_off', None)

        if percent_off:
            discount_pence = int(REPORT_PRICE_PENCE * percent_off / 100)
            final_price = REPORT_PRICE_PENCE - discount_pence
            discount_label = f'{int(percent_off)}% off'
        elif amount_off:
            final_price = max(0, REPORT_PRICE_PENCE - amount_off)
            discount_label = f'£{amount_off / 100:.2f} off'
        else:
            return JsonResponse({'valid': False, 'error': 'Invalid discount code.'})

        return JsonResponse({
            'valid': True,
            'promo_code_id': promo['id'],
            'final_price': final_price,
            'final_price_display': f'£{final_price / 100:.2f}',
            'discount_label': discount_label,
        })

    except Exception as e:
        print(f'>>> Discount validation error: {type(e).__name__}: {e}')
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

        amount = REPORT_PRICE_PENCE
        discount_code = ''

        if promo_code_id:
            try:
                promo = stripe.PromotionCode.retrieve(promo_code_id)
                discount_code = promo['code']
                coupon = get_coupon_from_promo(promo)
                if coupon:
                    percent_off = getattr(coupon, 'percent_off', None)
                    amount_off = getattr(coupon, 'amount_off', None)
                    if percent_off:
                        amount = int(REPORT_PRICE_PENCE * (1 - percent_off / 100))
                    elif amount_off:
                        amount = max(0, REPORT_PRICE_PENCE - amount_off)
            except Exception as e:
                print(f'>>> Promo retrieval error: {e}')

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

        # If 100% discount, skip payment entirely
        if amount == 0:
            order.status = Order.Status.PAID
            order.save()
            thread = threading.Thread(target=run_scan_sync, args=(str(order.id),))
            thread.daemon = True
            thread.start()
            return JsonResponse({
                'free': True,
                'order_id': str(order.id),
            })

        intent = stripe.PaymentIntent.create(
            amount=amount,
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
