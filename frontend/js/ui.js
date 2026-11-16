(function () {
    'use strict';

    var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    function staggerChildren() {
        if (reduceMotion) return;

        var groups = document.querySelectorAll(
            '.stats-grid, .features-grid, .alerts-list, .chart-grid, .admin-grid, .dashboard-grid'
        );

        groups.forEach(function (group) {
            Array.prototype.forEach.call(group.children, function (child, index) {
                child.style.setProperty('--dg-delay', Math.min(index * 55, 330) + 'ms');
            });
        });
    }

    function prepareReveals() {
        if (reduceMotion || !('IntersectionObserver' in window)) return;

        var selectors = [
            '.card-3d',
            '.stat-card',
            '.feature-card',
            '.risk-card',
            '.chart-container',
            '.data-table',
            '.map-container',
            '.alert-item',
            '.legal-section',
            '.auth-footer'
        ];

        var elements = document.querySelectorAll(selectors.join(','));
        var observer = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (!entry.isIntersecting) return;
                entry.target.classList.add('dg-in');
                observer.unobserve(entry.target);
            });
        }, { threshold: 0.08, rootMargin: '0px 0px -32px 0px' });

        elements.forEach(function (element) {
            if (element.closest('.hero-text, .hero-visual')) return;
            element.classList.add('dg-reveal');
            observer.observe(element);
        });

        window.setTimeout(function () {
            elements.forEach(function (element) {
                element.classList.add('dg-in');
            });
            observer.disconnect();
        }, 1600);
    }

    function animateCounters() {
        var values = document.querySelectorAll('.stat-value, .risk-score');
        if (!values.length) return;

        values.forEach(function (element) {
            if (element.dataset.dgCounted === 'true') return;

            var original = element.textContent.trim();
            var match = original.match(/^([^\d+-]*)([\d,]+(?:\.\d+)?)(.*)$/);
            if (!match) return;

            var prefix = match[1];
            var raw = match[2];
            var suffix = match[3];
            var target = parseFloat(raw.replace(/,/g, ''));
            if (!isFinite(target)) return;

            element.dataset.dgCounted = 'true';

            if (reduceMotion) return;

            var decimals = (raw.split('.')[1] || '').length;
            var useComma = raw.indexOf(',') !== -1 && raw.indexOf('.') === -1;
            var duration = 950;
            var start = null;

            function format(value) {
                var rounded = decimals ? value.toFixed(decimals) : String(Math.round(value));
                if (useComma) {
                    rounded = Number(rounded).toLocaleString('en-US', {
                        minimumFractionDigits: decimals,
                        maximumFractionDigits: decimals
                    });
                }
                return prefix + rounded + suffix;
            }

            element.textContent = format(0);

            function step(timestamp) {
                if (start === null) start = timestamp;
                var progress = Math.min((timestamp - start) / duration, 1);
                var eased = 1 - Math.pow(1 - progress, 3);
                element.textContent = format(target * eased);

                if (progress < 1) {
                    window.requestAnimationFrame(step);
                } else {
                    element.textContent = original;
                }
            }

            window.requestAnimationFrame(step);
        });
    }

    function markInteractiveCards() {
        if (reduceMotion) return;

        document.querySelectorAll('.card-3d').forEach(function (card) {
            if (card.dataset.dgInteractive === 'true') return;
            card.dataset.dgInteractive = 'true';
            card.addEventListener('pointerenter', function () {
                card.style.willChange = 'transform, box-shadow';
            });
            card.addEventListener('pointerleave', function () {
                card.style.willChange = 'auto';
            });
        });
    }

    function init() {
        document.body.classList.add('dg-ready');
        staggerChildren();
        prepareReveals();
        animateCounters();
        markInteractiveCards();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init, { once: true });
    } else {
        init();
    }
})();
