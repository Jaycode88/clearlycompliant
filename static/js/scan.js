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

async function handleScan() {
    const domain = document.getElementById('domain').value.trim();
    const email = document.getElementById('email').value.trim();
    const errorDiv = document.getElementById('error-message');
    const btn = document.getElementById('submit-btn');
    const btnText = document.getElementById('btn-text');
    const btnSpinner = document.getElementById('btn-spinner');

    errorDiv.style.display = 'none';

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

        const response = await fetch('/orders/start-scan/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken'),
            },
            body: JSON.stringify({
                domain,
                email,
                ...utmParams,
            }),
        });

        const data = await response.json();

        if (data.error) throw new Error(data.error);

        window.location.href = `/orders/status/${data.order_id}/`;

    } catch (err) {
        errorDiv.textContent = err.message;
        errorDiv.style.display = 'block';
        btn.disabled = false;
        btnText.style.display = 'inline';
        btnSpinner.style.display = 'none';
    }
}