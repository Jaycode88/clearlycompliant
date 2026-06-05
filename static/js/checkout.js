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
        const response = await fetch('/orders/create-payment-intent/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken'),
            },
            body: JSON.stringify({ domain, email }),
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

        if (error) throw new Error(error.message);

        document.getElementById('checkout-form').style.display = 'none';
        successDiv.innerHTML = `
            <strong>Payment successful!</strong><br>
            We're now scanning <strong>${domain}</strong>.<br>
            Your report will be emailed to <strong>${email}</strong> within a few minutes.
        `;
        successDiv.style.display = 'block';

    } catch (err) {
        let message = err.message;
        if (message.includes('card was declined')) {
            message = 'Your card was declined. Please check your details or try a different card.';
        } else if (message.includes('insufficient funds')) {
            message = 'Your card has insufficient funds. Please try a different card.';
        } else if (message.includes('expired')) {
            message = 'Your card has expired. Please try a different card.';
        }
        errorDiv.textContent = message;
        errorDiv.style.display = 'block';
        btn.disabled = false;
        btnText.style.display = 'inline';
        btnSpinner.style.display = 'none';
    }
}