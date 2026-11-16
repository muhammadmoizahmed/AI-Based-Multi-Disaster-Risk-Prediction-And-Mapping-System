const CACHE_NAME = 'disasterguard-v2';

const PRECACHE_URLS = [
    '/',
    '/index.html',
    '/offline.html',
    '/login.html',
    '/dashboard.html',
    '/manifest.webmanifest',
    '/favicon.svg',
    '/css/styles.css',
    '/css/theme.css',
    '/js/api-config.js',
    '/js/location.js',
    '/js/main.js',
    '/js/mobile-nav.js',
    '/js/ui.js',
    '/js/pwa.js',
    '/assets/icons/icon-192.png',
    '/assets/icons/icon-512.png',
    '/assets/icons/icon-maskable-512.png',
    '/assets/icons/apple-touch-icon.png',
    '/assets/icons/favicon-32.png',
    '/pages/alerts.html',
    '/pages/earthquake.html',
    '/pages/flood.html',
    '/pages/wildfire.html',
    '/pages/weather.html',
    '/pages/heatmap.html',
    '/pages/forecast.html',
    '/pages/history.html',
    '/privacy.html',
    '/terms.html'
];

const STATIC_DESTINATIONS = new Set(['style', 'script', 'image', 'font']);

self.addEventListener('install', (event) => {
    event.waitUntil((async () => {
        const cache = await caches.open(CACHE_NAME);
        await Promise.all(PRECACHE_URLS.map(async (url) => {
            try {
                const response = await fetch(url, { cache: 'reload' });
                if (response.ok) {
                    await cache.put(url, response);
                }
            } catch (error) {
                console.warn('Precache skipped:', url, error);
            }
        }));
        await self.skipWaiting();
    })());
});

self.addEventListener('activate', (event) => {
    event.waitUntil((async () => {
        const keys = await caches.keys();
        await Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key)));
        await self.clients.claim();
    })());
});

self.addEventListener('message', (event) => {
    if (event.data && event.data.type === 'SKIP_WAITING') {
        self.skipWaiting();
    }
});

function isStaticRequest(url) {
    return url.pathname.startsWith('/css/') ||
        url.pathname.startsWith('/js/') ||
        url.pathname.startsWith('/assets/') ||
        url.pathname === '/favicon.svg' ||
        url.pathname === '/manifest.webmanifest' ||
        /\.(?:css|js|png|jpe?g|webp|svg|ico|woff2?|ttf|webmanifest)$/i.test(url.pathname);
}

async function networkFirst(request) {
    try {
        const response = await fetch(request);
        if (response && response.ok) {
            const cache = await caches.open(CACHE_NAME);
            cache.put(request, response.clone());
        }
        return response;
    } catch (error) {
        const cached = await caches.match(request, { ignoreSearch: true });
        if (cached) {
            return cached;
        }
        const offline = await caches.match('/offline.html');
        return offline || Response.error();
    }
}

async function staleWhileRevalidate(request) {
    const cached = await caches.match(request, { ignoreSearch: true });
    const network = fetch(request).then(async (response) => {
        if (response && response.ok) {
            const cache = await caches.open(CACHE_NAME);
            await cache.put(request, response.clone());
        }
        return response;
    }).catch(() => null);

    return cached || (await network) || Response.error();
}

self.addEventListener('fetch', (event) => {
    const { request } = event;

    if (request.method !== 'GET') {
        return;
    }

    const url = new URL(request.url);
    if (url.origin !== self.location.origin || url.pathname.startsWith('/api/')) {
        return;
    }

    if (request.mode === 'navigate') {
        event.respondWith(networkFirst(request));
        return;
    }

    if (STATIC_DESTINATIONS.has(request.destination) || isStaticRequest(url)) {
        event.respondWith(staleWhileRevalidate(request));
    }
});
