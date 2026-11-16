(function () {
    var configured = window.DISASTERGUARD_API_ORIGIN;
    try {
        configured = configured || localStorage.getItem('api_origin');
    } catch (e) {}
    var origin = (configured || 'http://localhost:5000').replace(/\/$/, '');
    var backendPort = '';
    try {
        backendPort = new URL(origin).port;
    } catch (e) {}

    var servedByBackend = window.location.protocol.indexOf('http') === 0 && window.location.port === backendPort;
    if (servedByBackend) {
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
