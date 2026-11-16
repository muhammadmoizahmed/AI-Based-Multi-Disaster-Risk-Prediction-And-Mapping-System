(function () {
    'use strict';

    var script = document.currentScript;
    var scriptUrl = script && script.src
        ? new URL(script.src, window.location.href)
        : new URL('/js/pwa.js', window.location.origin);
    var swUrl = new URL('../sw.js', scriptUrl);
    var swScope = new URL('../', scriptUrl).pathname;

    var DISMISS_KEY = 'dg_pwa_install_dismissed_at';
    var DISMISS_DAYS = 14;
    var deferredPrompt = null;
    var installUi = null;
    var iosTip = null;

    function isStandalone() {
        return window.matchMedia('(display-mode: standalone)').matches ||
            window.navigator.standalone === true;
    }

    function isDismissed() {
        try {
            var dismissedAt = Number(window.localStorage.getItem(DISMISS_KEY) || 0);
            return dismissedAt && (Date.now() - dismissedAt) < DISMISS_DAYS * 24 * 60 * 60 * 1000;
        } catch (error) {
            return false;
        }
    }

    function rememberDismissal() {
        try {
            window.localStorage.setItem(DISMISS_KEY, String(Date.now()));
        } catch (error) {
            console.warn('Install preference could not be saved:', error);
        }
    }

    function createInstallUi() {
        if (installUi) {
            return installUi;
        }

        installUi = document.createElement('div');
        installUi.className = 'pwa-install';
        installUi.hidden = true;
        installUi.innerHTML = [
            '<button class="pwa-install-main" type="button">',
            '<i class="fas fa-download" aria-hidden="true"></i>',
            '<span>Install app</span>',
            '</button>',
            '<button class="pwa-install-close" type="button" aria-label="Dismiss install prompt">',
            '<i class="fas fa-xmark" aria-hidden="true"></i>',
            '</button>'
        ].join('');

        installUi.querySelector('.pwa-install-main').addEventListener('click', async function () {
            if (deferredPrompt) {
                deferredPrompt.prompt();
                try {
                    await deferredPrompt.userChoice;
                } catch (error) {
                    console.warn('Install prompt closed without a choice:', error);
                }
                deferredPrompt = null;
                hideInstallUi();
                return;
            }
            showIosTip();
        });

        installUi.querySelector('.pwa-install-close').addEventListener('click', function () {
            rememberDismissal();
            hideInstallUi();
        });

        document.body.appendChild(installUi);
        return installUi;
    }

    function showInstallUi() {
        if (isStandalone() || isDismissed()) {
            return;
        }
        createInstallUi().hidden = false;
    }

    function hideInstallUi() {
        if (installUi) {
            installUi.hidden = true;
        }
        if (iosTip) {
            iosTip.hidden = true;
        }
    }

    function showIosTip() {
        if (installUi) {
            installUi.hidden = true;
        }
        if (iosTip) {
            iosTip.hidden = false;
            return;
        }

        iosTip = document.createElement('div');
        iosTip.className = 'pwa-ios-tip';
        iosTip.innerHTML = [
            '<button class="pwa-ios-tip-close" type="button" aria-label="Close install instructions">',
            '<i class="fas fa-xmark" aria-hidden="true"></i>',
            '</button>',
            '<strong>Install DisasterGuard</strong>',
            '<span>Tap the Share button, then choose <b>Add to Home Screen</b>.</span>'
        ].join('');
        iosTip.querySelector('.pwa-ios-tip-close').addEventListener('click', function () {
            rememberDismissal();
            hideInstallUi();
        });
        document.body.appendChild(iosTip);
    }

    function isIosSafari() {
        var ua = window.navigator.userAgent;
        var isIos = /iPad|iPhone|iPod/.test(ua) || (ua.includes('Macintosh') && 'ontouchend' in document);
        var isSafari = /Safari/.test(ua) && !/CriOS|FxiOS|EdgiOS|OPiOS/.test(ua);
        return isIos && isSafari;
    }

    function registerServiceWorker() {
        if (!('serviceWorker' in navigator) || !window.isSecureContext) {
            return;
        }
        navigator.serviceWorker.register(swUrl.href, { scope: swScope }).catch(function (error) {
            console.warn('Service worker registration failed:', error);
        });
    }

    if ('serviceWorker' in navigator && window.isSecureContext) {
        if (document.readyState === 'complete') {
            registerServiceWorker();
        } else {
            window.addEventListener('load', registerServiceWorker);
        }
    }

    if (window.top !== window.self || isStandalone()) {
        return;
    }

    window.addEventListener('beforeinstallprompt', function (event) {
        event.preventDefault();
        deferredPrompt = event;
        showInstallUi();
    });

    window.addEventListener('appinstalled', function () {
        deferredPrompt = null;
        hideInstallUi();
    });

    if (isIosSafari() && !isDismissed()) {
        window.setTimeout(showInstallUi, 2200);
    }
})();
