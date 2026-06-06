function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function getUtmParams() {
    const params = new URLSearchParams(window.location.search);
    return {
        utm_source: params.get('utm_source') || sessionStorage.getItem('utm_source') || '',
        utm_medium: params.get('utm_medium') || sessionStorage.getItem('utm_medium') || '',
        utm_campaign: params.get('utm_campaign') || sessionStorage.getItem('utm_campaign') || '',
        utm_term: params.get('utm_term') || sessionStorage.getItem('utm_term') || '',
        utm_content: params.get('utm_content') || sessionStorage.getItem('utm_content') || '',
        referrer: sessionStorage.getItem('referrer') || document.referrer || '',
    };
}

(function() {
    const params = new URLSearchParams(window.location.search);
    if (params.get('utm_source')) sessionStorage.setItem('utm_source', params.get('utm_source'));
    if (params.get('utm_medium')) sessionStorage.setItem('utm_medium', params.get('utm_medium'));
    if (params.get('utm_campaign')) sessionStorage.setItem('utm_campaign', params.get('utm_campaign'));
    if (params.get('utm_term')) sessionStorage.setItem('utm_term', params.get('utm_term'));
    if (params.get('utm_content')) sessionStorage.setItem('utm_content', params.get('utm_content'));
    if (document.referrer && !sessionStorage.getItem('referrer')) {
        sessionStorage.setItem('referrer', document.referrer);
    }
})();

const stripe = Stripe(stripePublishableKey);
const elements = stripe.elements();

const cardElement = elements.create('card', {
    style: {
        base: {
            fontSize: '14px',
            color: '#1a1a2e',
            '::placeholder': { color: '#9ca3af' },
        }
    },
    hidePostalCode: true,
});
cardElement.mount('#card-element');

cardElement.on('change', function(event) {
    const errorDiv = document.getElementById('error-message');
    if (event.error) {
        errorDiv.textContent = event.error.message;
        errorDiv.style.display = 'block';
    } else {
        errorDiv.style.display = 'none';
    }
});

let appliedPromoCodeId = '';
let finalPrice = 2999;

async function applyDiscount() {
    const code = document.getElementById('discount-code').value.trim().toUpperCase();
    const msgDiv = document.getElementById('discount-message');
    const applyBtn = document.getElementById('apply-btn');
    const priceDisplay = document.getElementById('price-display');

    if (!code) {
        msgDiv.textContent = 'Please enter a discount code.';
        msgDiv.style.color = '#c2410c';
        msgDiv.style.display = 'block';
        return;
    }

    applyBtn.disabled = true;
    applyBtn.textContent = 'Checking...';

    try {
        const response = await fetch('/orders/validate-discount/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken'),
            },
            body: JSON.stringify({ code }),
        });

        const data = await response.json();

        if (data.valid) {
            appliedPromoCodeId = data.promo_code_id;
            finalPrice = data.final_price;
            msgDiv.textContent = `✓ Code applied — ${data.discount_label}`;
            msgDiv.style.color = '#15803d';
            msgDiv.style.display = 'block';
            priceDisplay.innerHTML = `${data.final_price_display} <span>one-off payment</span> <span style="text-decoration:line-through; color:#9ca3af; font-size:18px;">£29.99</span>`;
            document.getElementById('btn-text').textContent = `Get My Report — ${data.final_price_display}`;
        } else {
            appliedPromoCodeId = '';
            finalPrice = 2999;
            msgDiv.textContent = data.error;
            msgDiv.style.color = '#c2410c';
            msgDiv.style.display = 'block';
            priceDisplay.innerHTML = '£29.99 <span>one-off payment</span>';
            document.getElementById('btn-text').textContent = 'Get My Report — £29.99';
        }
    } catch (err) {
        msgDiv.textContent = 'Could not validate code. Please try again.';
        msgDiv.style.color = '#c2410c';
        msgDiv.style.display = 'block';
    }

    applyBtn.disabled = false;
    applyBtn.textContent = 'Apply';
}

async function handleSubmit() {
    const domain = document.getElementById('domain').value.trim();
    const email = document.getElementById('email').value.trim();
    const errorDiv = document.getElementById('error-message');
    const successDiv = document.getElementById('success-message');
    const btn = document.getElementById('submit-btn');
    const btnText = document.getElementById('btn-text');
    const btnSpinner = document.getElementById('btn-spinner');

    errorDiv.style.display = 'none';
    successDiv.style.display = 'none';

    if (!domain || !email) {
        errorDiv.textContent = 'Please enter your domain and email address.';
        errorDiv.style.display = 'block';
        return;
    }

    btn.disabled = true;
    btnText.style.display = 'none';
    btnSpinner.style.display = 'inline';

    try {
        const utmParams = getUtmParams();

        const response = await fetch('/orders/create-payment-intent/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken'),
            },
            body: JSON.stringify({
                domain,
                email,
                promo_code_id: appliedPromoCodeId,
                ...utmParams,
            }),
        });

        const data = await response.json();

        if (data.error) throw new Error(data.error);

        const { error, paymentIntent } = await stripe.confirmCardPayment(
            data.client_secret,
            {
                payment_method: {
                    card: cardElement,
                    billing_details: { email },
                }
            }
        );

        if (error) {
            let message = error.message;
            if (message.includes('card was declined')) {
                message = 'Your card was declined. Please check your details or try a different card.';
            } else if (message.includes('insufficient funds')) {
                message = 'Your card has insufficient funds. Please try a different card.';
            } else if (message.includes('expired')) {
                message = 'Your card has expired. Please try a different card.';
            }
            throw new Error(message);
        }

        document.getElementById('checkout-form').style.display = 'none';
        successDiv.innerHTML = `
            <strong>Payment successful!</strong><br>
            We're now scanning <strong>${domain}</strong>.<br>
            Your report will be emailed to <strong>${email}</strong> within a few minutes.
        `;
        successDiv.style.display = 'block';

    } catch (err) {
        errorDiv.textContent = err.message;
        errorDiv.style.display = 'block';
        btn.disabled = false;
        btnText.style.display = 'inline';
        btnSpinner.style.display = 'none';
    }
}