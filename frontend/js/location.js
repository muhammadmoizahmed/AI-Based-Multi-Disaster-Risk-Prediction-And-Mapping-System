const LOCATION_CACHE_KEY = "disasterguard_user_location";
const SELECTED_LOCATION_KEY = "disasterguard_selected_location";
const LOCATION_CACHE_TTL = 10 * 60 * 1000;

function readCachedLocation() {
    try {
        const raw = localStorage.getItem(LOCATION_CACHE_KEY);
        if (!raw) return null;
        const parsed = JSON.parse(raw);
        if (!parsed || !parsed.timestamp || Date.now() - parsed.timestamp > LOCATION_CACHE_TTL) {
            localStorage.removeItem(LOCATION_CACHE_KEY);
            return null;
        }
        return parsed.value;
    } catch (error) {
        return null;
    }
}

function writeCachedLocation(value) {
    try {
        localStorage.setItem(LOCATION_CACHE_KEY, JSON.stringify({ value, timestamp: Date.now() }));
    } catch (error) {
        // Ignore storage errors.
    }
}

function getSelectedLocation() {
    for (const store of [sessionStorage, localStorage]) {
        try {
            const raw = store.getItem(SELECTED_LOCATION_KEY);
            if (raw) return JSON.parse(raw);
        } catch (error) {
            // try the next store
        }
    }
    return null;
}

function setSelectedLocation(value) {
    for (const store of [sessionStorage, localStorage]) {
        try {
            store.setItem(SELECTED_LOCATION_KEY, JSON.stringify(value));
        } catch (error) {
            // Ignore storage errors.
        }
    }
}

function clearSelectedLocation() {
    for (const store of [sessionStorage, localStorage]) {
        try {
            store.removeItem(SELECTED_LOCATION_KEY);
        } catch (error) {
            // Ignore storage errors.
        }
    }
}

function gpsPosition() {
    return new Promise((resolve, reject) => {
        if (!navigator.geolocation) {
            reject(new Error("Geolocation is not supported"));
            return;
        }
        navigator.geolocation.getCurrentPosition(resolve, reject, {
            enableHighAccuracy: true,
            timeout: 10000,
            maximumAge: 300000
        });
    });
}

async function reverseCityFromWeather(lat, lon) {
    try {
        const response = await fetch(`/api/weather/current?lat=${encodeURIComponent(lat)}&lon=${encodeURIComponent(lon)}`);
        if (!response.ok) return null;
        const data = await response.json();
        return data && data.name ? data.name : null;
    } catch (error) {
        return null;
    }
}

async function ipLocation() {
    const response = await fetch("/api/weather/my-location");
    if (!response.ok) throw new Error(`IP location returned ${response.status}`);
    const data = await response.json();
    const location = data.location || {};
    return {
        latitude: Number(location.lat || location.latitude || 0),
        longitude: Number(location.lon || location.longitude || 0),
        city: location.city || "Unknown",
        country: location.country || location.country_name || "Unknown",
        source: "ip"
    };
}

async function browserIpLocation() {
    try {
        const response = await fetch("https://ipwho.is/", { cache: "no-store" });
        if (!response.ok) return null;
        const data = await response.json();
        if (!data || data.success === false) return null;
        const latitude = Number(data.latitude);
        const longitude = Number(data.longitude);
        if (!isFinite(latitude) || !isFinite(longitude) || (latitude === 0 && longitude === 0)) {
            return null;
        }
        return {
            latitude,
            longitude,
            city: data.city || "Current location",
            country: data.country || "Unknown",
            source: "ip"
        };
    } catch (error) {
        return null;
    }
}

async function detectOwnLocation(force = false) {
    if (!force) {
        const cached = readCachedLocation();
        if (cached) return cached;
    }

    try {
        const position = await gpsPosition();
        const latitude = position.coords.latitude;
        const longitude = position.coords.longitude;
        const city = await reverseCityFromWeather(latitude, longitude);
        const value = {
            latitude,
            longitude,
            city: city || "Current location",
            country: "Unknown",
            source: "gps"
        };
        writeCachedLocation(value);
        return value;
    } catch (error) {
        // Prefer the browser's own public IP location so it reflects the real user,
        // not the server hosting the backend.
        const browserValue = await browserIpLocation();
        if (browserValue) {
            writeCachedLocation(browserValue);
            return browserValue;
        }
        try {
            const value = await ipLocation();
            if (value.latitude || value.longitude) {
                writeCachedLocation(value);
                return value;
            }
        } catch (fallbackError) {
            // keep going to default
        }
        const value = {
            latitude: 30.3753,
            longitude: 69.3451,
            city: "Pakistan",
            country: "Pakistan",
            source: "default"
        };
        writeCachedLocation(value);
        return value;
    }
}

async function searchLocation(city) {
    const response = await fetch(`/api/weather/search?city=${encodeURIComponent(city)}`);
    if (!response.ok) throw new Error(`Location search returned ${response.status}`);
    const data = await response.json();
    const place = data.city || {};
    const value = {
        latitude: Number(place.lat || 0),
        longitude: Number(place.lng || place.lon || 0),
        city: place.name || city,
        country: place.province || "Pakistan",
        source: "search"
    };
    setSelectedLocation(value);
    return value;
}

async function getActiveLocation(forceOwn = false) {
    if (!forceOwn) {
        const selected = getSelectedLocation();
        if (selected) return selected;
    }
    return detectOwnLocation(forceOwn);
}

window.DisasterLocation = {
    detectOwn: detectOwnLocation,
    detect: getActiveLocation,
    search: searchLocation,
    clearSelected: clearSelectedLocation,
    getSelected: getSelectedLocation
};

async function initGlobalLocation() {
    try {
        await DisasterLocation.detectOwn();
    } catch (error) {
        // Location detection is best-effort; pages still load.
    }
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initGlobalLocation);
} else {
    initGlobalLocation();
}
