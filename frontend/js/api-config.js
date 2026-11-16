(function () {
    var configured = window.DISASTERGUARD_API_ORIGIN;
    try {
        configured = configured || localStorage.getItem('api_origin');
    } catch (e) {}
    var fallbackOrigin = window.location.origin;
    if (window.location.protocol === 'file:') {
        fallbackOrigin = 'http://localhost:5000';
    } else if (window.location.protocol === 'http:' && window.location.port !== '5000') {
        fallbackOrigin = 'http://' + window.location.hostname + ':5000';
    }
    var origin = (configured || fallbackOrigin).replace(/\/$/, '');

    if (origin === window.location.origin) {
        return;
    }

    var nativeFetch = window.fetch.bind(window);
    window.fetch = function (input, init) {
        if (typeof input === 'string' && input.indexOf('/api/') === 0) {
            input = origin + input;
        }
        return nativeFetch(input, init);
    };
})();
