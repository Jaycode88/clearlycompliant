(function() {
    if (localStorage.getItem('cookie-notice-dismissed')) return;
    const notice = document.createElement('div');
    notice.id = 'cookie-notice';
    notice.innerHTML = `
        <div id="cookie-notice-inner">
            <p>We use only essential cookies required for the site to function — no tracking or advertising cookies. <a href="/privacy-policy/">Learn more</a></p>
            <div id="cookie-notice-buttons">
                <button id="cookie-settings-btn" onclick="showCookieSettingsPanel()">Cookie Settings</button>
                <button id="cookie-accept-btn" onclick="dismissCookieNotice()">OK, got it</button>
            </div>
        </div>
        <div id="cookie-settings-panel" style="display:none;">
            <h4>Cookie Settings</h4>
            <div class="cookie-category">
                <div class="cookie-category-header">
                    <div>
                        <strong>Essential Cookies</strong>
                        <p>Required for the website to function. Cannot be disabled.</p>
                    </div>
                    <span class="cookie-always-on">Always on</span>
                </div>
                <p class="cookie-examples">Includes: session cookie, CSRF protection token</p>
            </div>
            <div class="cookie-category">
                <div class="cookie-category-header">
                    <div>
                        <strong>Analytics Cookies</strong>
                        <p>Help us understand how visitors use the site.</p>
                    </div>
                    <span class="cookie-not-used">Not used</span>
                </div>
            </div>
            <div class="cookie-category">
                <div class="cookie-category-header">
                    <div>
                        <strong>Marketing Cookies</strong>
                        <p>Used for advertising and tracking across sites.</p>
                    </div>
                    <span class="cookie-not-used">Not used</span>
                </div>
            </div>
            <button id="cookie-close-btn" onclick="dismissCookieNotice()">Save & Close</button>
        </div>
    `;
    document.body.appendChild(notice);
})();

function showCookieSettingsPanel() {
    const existing = document.getElementById('cookie-notice');
    if (existing) {
        document.getElementById('cookie-notice-inner').style.display = 'none';
        document.getElementById('cookie-settings-panel').style.display = 'block';
        return;
    }
    localStorage.removeItem('cookie-notice-dismissed');
    location.reload();
}

function dismissCookieNotice() {
    localStorage.setItem('cookie-notice-dismissed', '1');
    const notice = document.getElementById('cookie-notice');
    if (notice) notice.remove();
}
