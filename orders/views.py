import json
import re
import stripe
import threading
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.shortcuts import render, get_object_or_404
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
        if promotion:
            coupon_id = getattr(promotion, 'coupon', None)
            if coupon_id:
                return stripe.Coupon.retrieve(coupon_id)
    except Exception as e:
        print(f'>>> promotion path error: {e}')
    try:
        coupon = getattr(promo, 'coupon', None)
        if coupon:
            if isinstance(coupon, str):
                return stripe.Coupon.retrieve(coupon)
            return coupon
    except Exception as e:
        print(f'>>> direct coupon error: {e}')
    return None


def checkout(request):
    """Homepage — domain and email input only, no payment."""
    return render(request, 'orders/checkout.html')


def free_results(request, token):
    """Show free results teaser page."""
    order = get_object_or_404(Order, free_result_token=token)

    # Mark as viewed
    if not order.free_results_viewed:
        order.free_results_viewed = True
        order.save()

    # Get scan result if available
    scan_result = None
    try:
        scan_result = order.scan_result
    except Exception:
        pass

    context = {
        'order': order,
        'scan_result': scan_result,
        'stripe_publishable_key': settings.STRIPE_PUBLISHABLE_KEY,
    }
    return render(request, 'orders/free_results.html', context)


@require_POST
def start_free_scan(request):
    """Accept domain and email, create order, start scan."""
    try:
        data = json.loads(request.body)
        domain = data.get('domain', '').strip()
        email = data.get('email', '').strip()

        domain = re.sub(r'^https?://', '', domain).strip('/')

        if not domain or not email:
            return JsonResponse({'error': 'Domain and email are required.'}, status=400)

        if not is_valid_domain(domain):
            return JsonResponse({'error': 'Please enter a valid domain name, e.g. example.com'}, status=400)

        order = Order.objects.create(
            domain=domain,
            email=email,
            report_type=Order.ReportType.FREE,
            utm_source=data.get('utm_source', ''),
            utm_medium=data.get('utm_medium', ''),
            utm_campaign=data.get('utm_campaign', ''),
            utm_term=data.get('utm_term', ''),
            utm_content=data.get('utm_content', ''),
            referrer=data.get('referrer', ''),
        )

        thread = threading.Thread(target=run_scan_sync, args=(str(order.id),))
        thread.daemon = True
        thread.start()

        return JsonResponse({
            'free': True,
            'order_id': str(order.id),
            'domain': order.domain,
            'email': order.email,
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


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
        token = data.get('token', '').strip()
        promo_code_id = data.get('promo_code_id', '').strip()

        # Get existing order by token
        try:
            order = Order.objects.get(free_result_token=token)
        except Order.DoesNotExist:
            return JsonResponse({'error': 'Invalid session. Please start a new scan.'}, status=400)

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

        # Update order to paid type
        order.report_type = Order.ReportType.PAID
        order.discount_code = discount_code
        order.amount_paid = amount
        order.save()

        # If 100% discount, skip payment entirely
        if amount == 0:
            order.status = Order.Status.PAID
            order.save()
            from mailer.tasks import send_confirmation_email
            send_confirmation_email(str(order.id))
            thread = threading.Thread(target=send_full_report_sync, args=(str(order.id),))
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
                'domain': order.domain,
                'email': order.email,
            }
        )

        order.stripe_payment_intent_id = intent.id
        order.save()

        return JsonResponse({
            'client_secret': intent.client_secret,
            'order_id': str(order.id),
            'amount': amount,
            'amount_display': f'£{amount / 100:.2f}',
            'domain': order.domain,
            'email': order.email,
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def send_full_report_sync(order_id):
    """Generate and send the full PDF report for an already-scanned order."""
    from reports.tasks import generate_report_task
    generate_report_task(order_id)


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
            order.report_type = Order.ReportType.PAID
            order.save()
            from mailer.tasks import send_confirmation_email
            send_confirmation_email(str(order.id))
            thread = threading.Thread(target=send_full_report_sync, args=(str(order.id),))
            thread.daemon = True
            thread.start()
        except Order.DoesNotExist:
            pass

    return HttpResponse(status=200)


def order_status(request, order_id):
    try:
        order = Order.objects.get(id=order_id)
        return JsonResponse({
            'status': order.status,
            'domain': order.domain,
            'email': order.email,
            'token': str(order.free_result_token),
        })
    except Order.DoesNotExist:
        return JsonResponse({'error': 'Order not found'}, status=404)


def order_status_page(request, order_id):
    try:
        order = Order.objects.get(id=order_id)
        return render(request, 'orders/status.html', {'order': order})
    except Order.DoesNotExist:
        return render(request, 'orders/status.html', {'order': None})


def privacy_policy(request):
    return render(request, 'legal/privacy_policy.html')


def terms_and_conditions(request):
    return render(request, 'legal/terms_and_conditions.html')


def order_complete(request):
    domain = request.GET.get('domain', '')
    email = request.GET.get('email', '')
    return render(request, 'orders/order_complete.html', {
        'domain': domain,
        'email': email,
    })
