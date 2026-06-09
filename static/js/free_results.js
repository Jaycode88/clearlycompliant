// Calculate scores
const sections = [
    {
        title: '1. Technical Security',
        checks: [
            scanData.is_https,
            !scanData.has_mixed_content,
            scanData.has_x_frame_options,
            scanData.has_content_security_policy,
            scanData.has_x_content_type_options,
            scanData.has_referrer_policy,
        ]
    },
    {
        title: '2. Privacy & Legal Documents',
        checks: [
            scanData.has_privacy_policy,
            scanData.has_cookie_policy,
            scanData.has_terms_and_conditions,
            scanData.has_data_retention_policy,
        ]
    },
    {
        title: '3. Consent & Cookie Management',
        checks: [
            scanData.has_cookie_banner,
            scanData.has_cookie_preferences_link,
            scanData.has_form_consent_checkbox,
        ]
    },
    {
        title: '4. Data Collection',
        checks: [
            !scanData.has_contact_form || scanData.has_privacy_policy_for_check,
            !scanData.has_newsletter_signup || scanData.has_cookie_banner,
            !scanData.has_login || scanData.has_privacy_policy_for_check,
            !scanData.has_ecommerce || scanData.has_privacy_policy_for_check,
        ]
    },
    {
        title: '5. Third-Party & Tracking',
        checks: [
            !scanData.has_google_analytics,
            !scanData.has_facebook_pixel,
        ]
    },
    {
        title: '6. User Rights',
        checks: [
            scanData.has_unsubscribe_mechanism,
            scanData.has_contact_info,
            scanData.has_dpo_info,
            scanData.has_data_subject_rights,
        ]
    },
];

const allChecks = sections.flatMap(s => s.checks);
const totalPassed = allChecks.filter(Boolean).length;
const totalChecks = allChecks.length;
const score = Math.round((totalPassed / totalChecks) * 100);

// Set score display
const scoreEl = document.getElementById('score-number');
const labelEl = document.getElementById('score-label');
const subEl = document.getElementById('score-sub');
const circleEl = document.getElementById('score-circle');

scoreEl.textContent = score + '%';
subEl.textContent = `${totalPassed} of ${totalChecks} checks passed`;

if (score >= 80) {
    labelEl.textContent = 'Good';
    circleEl.style.borderColor = '#22c55e';
    scoreEl.style.color = '#22c55e';
    labelEl.style.color = '#22c55e';
} else if (score >= 50) {
    labelEl.textContent = 'Needs Improvement';
    circleEl.style.borderColor = '#f59e0b';
    scoreEl.style.color = '#f59e0b';
    labelEl.style.color = '#f59e0b';
} else {
    labelEl.textContent = 'Poor';
    circleEl.style.borderColor = '#ef4444';
    scoreEl.style.color = '#ef4444';
    labelEl.style.color = '#ef4444';
}

// Render section rows
const rowsEl = document.getElementById('section-rows');
sections.forEach(section => {
    const passed = section.checks.filter(Boolean).length;
    const total = section.checks.length;
    const sScore = Math.round((passed / total) * 100);
    const failed = total - passed;

    let colour = '#22c55e';
    if (sScore < 80) colour = '#f59e0b';
    if (sScore < 50) colour = '#ef4444';

    const row = document.createElement('div');
    row.className = 'section-row';
    row.innerHTML = `
        <div class="section-row-title">${section.title}</div>
        <div class="section-row-stats">
            <span class="passed">${passed} passed</span>
            <span class="failed">${failed} failed</span>
            <span class="section-score" style="color:${colour}">${sScore}%</span>
        </div>
        <div class="section-bar">
            <div class="section-bar-fill" style="width:${sScore}%; background:${colour};"></div>
        </div>
    `;
    rowsEl.appendChild(row);
});

// Stripe
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
    const errorDiv = document.getElementById('upgrade-error');
    if (event.error) {
        errorDiv.textContent = event.error.message;
        errorDiv.style.display = 'block';
    } else {
        errorDiv.style.display = 'none';
    }
});

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

let appliedPromoCodeId = '';
let finalPrice = 2999;

async function applyDiscount() {
    const code = document.getElementById('discount-code').value.trim().toUpperCase();
    const msgDiv = document.getElementById('discount-message');
    const applyBtn = document.getElementById('apply-btn');

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
            if (finalPrice === 0) {
                document.getElementById('pay-btn-text').textContent = 'Unlock Full Report — Free';
            } else {
                document.getElementById('pay-btn-text').textContent = `Unlock Full Report — ${data.final_price_display}`;
            }
        } else {
            appliedPromoCodeId = '';
            finalPrice = 2999;
            msgDiv.textContent = data.error;
            msgDiv.style.color = '#c2410c';
            msgDiv.style.display = 'block';
            document.getElementById('pay-btn-text').textContent = 'Unlock Full Report — £29.99';
        }
    } catch (err) {
        msgDiv.textContent = 'Could not validate code. Please try again.';
        msgDiv.style.color = '#c2410c';
        msgDiv.style.display = 'block';
    }

    applyBtn.disabled = false;
    applyBtn.textContent = 'Apply';
}

async function handleUpgrade() {
    const errorDiv = document.getElementById('upgrade-error');
    const successDiv = document.getElementById('upgrade-success');
    const btn = document.getElementById('pay-btn');
    const btnText = document.getElementById('pay-btn-text');
    const btnSpinner = document.getElementById('pay-btn-spinner');

    errorDiv.style.display = 'none';
    successDiv.style.display = 'none';

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
            body: JSON.stringify({
                token: orderToken,
                promo_code_id: appliedPromoCodeId,
            }),
        });

        const data = await response.json();
        if (data.error) throw new Error(data.error);

        if (data.free) {
            window.location.href = `/orders/complete/?domain=${encodeURIComponent(data.domain)}&email=${encodeURIComponent(data.email)}&token=${encodeURIComponent(orderToken)}`;
            return;
        }

        const { error, paymentIntent } = await stripe.confirmCardPayment(
            data.client_secret,
            {
                payment_method: {
                    card: cardElement,
                    billing_details: {},
                }
            }
        );

        if (error) throw new Error(error.message);

        window.location.href = `/orders/complete/?domain=${encodeURIComponent(data.domain)}&email=${encodeURIComponent(data.email)}&token=${encodeURIComponent(orderToken)}`;

    } catch (err) {
        errorDiv.textContent = err.message;
        errorDiv.style.display = 'block';
        btn.disabled = false;
        btnText.style.display = 'inline';
        btnSpinner.style.display = 'none';
    }
}