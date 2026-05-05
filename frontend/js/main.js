// ============================================
// DISASTERGUARD - MAIN JAVASCRIPT
// ============================================

// Utility Functions
function $(selector) {
    return document.querySelector(selector);
}

function $$(selector) {
    return document.querySelectorAll(selector);
}

// Toast Notification System
class Toast {
    static show(message, type = 'info', duration = 3000) {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.innerHTML = `
            <i class="fas ${this.getIcon(type)}"></i>
            <span>${message}</span>
        `;
        
        const container = document.getElementById('toast-container') || this.createContainer();
        container.appendChild(toast);
        
        // Animate in
        requestAnimationFrame(() => {
            toast.style.transform = 'translateX(0)';
            toast.style.opacity = '1';
        });
        
        // Remove after duration
        setTimeout(() => {
            toast.style.transform = 'translateX(100%)';
            toast.style.opacity = '0';
            setTimeout(() => toast.remove(), 300);
        }, duration);
    }
    
    static createContainer() {
        const container = document.createElement('div');
        container.id = 'toast-container';
        container.style.cssText = `
            position: fixed;
            bottom: 2rem;
            right: 2rem;
            z-index: 9999;
            display: flex;
            flex-direction: column;
            gap: 0.75rem;
        `;
        document.body.appendChild(container);
        return container;
    }
    
    static getIcon(type) {
        const icons = {
            success: 'fa-check-circle',
            error: 'fa-exclamation-circle',
            warning: 'fa-exclamation-triangle',
            info: 'fa-info-circle'
        };
        return icons[type] || icons.info;
    }
}

// API Manager (will connect to FastAPI backend)
class APIManager {
    constructor(baseURL = 'http://localhost:5000/api') {
        this.baseURL = baseURL;
        this.headers = {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('auth_token') || ''}`
        };
    }
    
    async get(endpoint) {
        try {
            const response = await fetch(`${this.baseURL}${endpoint}`, {
                method: 'GET',
                headers: this.headers
            });
            return await response.json();
        } catch (error) {
            console.error('API GET Error:', error);
            throw error;
        }
    }
    
    async post(endpoint, data) {
        try {
            const response = await fetch(`${this.baseURL}${endpoint}`, {
                method: 'POST',
                headers: this.headers,
                body: JSON.stringify(data)
            });
            return await response.json();
        } catch (error) {
            console.error('API POST Error:', error);
            throw error;
        }
    }
    
    async put(endpoint, data) {
        try {
            const response = await fetch(`${this.baseURL}${endpoint}`, {
                method: 'PUT',
                headers: this.headers,
                body: JSON.stringify(data)
            });
            return await response.json();
        } catch (error) {
            console.error('API PUT Error:', error);
            throw error;
        }
    }
    
    async delete(endpoint) {
        try {
            const response = await fetch(`${this.baseURL}${endpoint}`, {
                method: 'DELETE',
                headers: this.headers
            });
            return await response.json();
        } catch (error) {
            console.error('API DELETE Error:', error);
            throw error;
        }
    }
}

// Auth Manager
class AuthManager {
    static isAuthenticated() {
        return !!localStorage.getItem('auth_token');
    }
    
    static getUser() {
        try {
            return JSON.parse(localStorage.getItem('user_data') || '{}');
        } catch {
            return {};
        }
    }
    
    static logout() {
        localStorage.removeItem('auth_token');
        localStorage.removeItem('user_data');
        window.location.href = '/login.html';
    }
    
    static requireAuth() {
        if (!this.isAuthenticated()) {
            window.location.href = '/login.html';
            return false;
        }
        return true;
    }
    
    static setAuth(token, userData) {
        localStorage.setItem('auth_token', token);
        localStorage.setItem('user_data', JSON.stringify(userData));
    }
}

// Chart Manager for Data Visualization
class ChartManager {
    static createRiskChart(canvasId, labels, data, type = 'line') {
        // Placeholder for Chart.js integration
        // Will be implemented when Chart.js is added
        console.log(`Creating ${type} chart on ${canvasId}`, { labels, data });
    }
    
    static updateChart(chart, newData) {
        // Update chart with new data
        console.log('Updating chart with:', newData);
    }
}

// Map Manager
class MapManager {
    constructor(containerId) {
        this.containerId = containerId;
        this.map = null;
        this.markers = [];
    }
    
    init(center = [30.3753, 69.3451], zoom = 6) {
        if (typeof L === 'undefined') {
            console.error('Leaflet not loaded');
            return;
        }
        
        this.map = L.map(this.containerId).setView(center, zoom);
        
        // Dark theme tiles
        L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
            maxZoom: 19
        }).addTo(this.map);
        
        return this.map;
    }
    
    addMarker(lat, lng, options = {}) {
        const marker = L.marker([lat, lng], options).addTo(this.map);
        this.markers.push(marker);
        return marker;
    }
    
    addRiskZone(lat, lng, radius, riskLevel) {
        const colors = {
            low: '#00c853',
            moderate: '#ffd600',
            high: '#ff6d00',
            extreme: '#ff1744'
        };
        
        const circle = L.circle([lat, lng], {
            radius: radius,
            fillColor: colors[riskLevel] || colors.low,
            color: '#fff',
            weight: 2,
            opacity: 1,
            fillOpacity: 0.3
        }).addTo(this.map);
        
        return circle;
    }
    
    clearMarkers() {
        this.markers.forEach(m => this.map.removeLayer(m));
        this.markers = [];
    }
}

// Risk Calculator
class RiskCalculator {
    static calculateFloodRisk(rainfall, riverLevel, soilSaturation) {
        // Simplified flood risk calculation (0-1 scale)
        const rainfallWeight = 0.4;
        const riverWeight = 0.35;
        const soilWeight = 0.25;
        
        const risk = (rainfall * rainfallWeight) + 
                     (riverLevel * riverWeight) + 
                     (soilSaturation * soilWeight);
        
        return Math.min(Math.max(risk, 0), 1);
    }
    
    static calculateEarthquakeRisk(magnitude, depth, distance) {
        // Simplified earthquake risk calculation
        const magWeight = 0.5;
        const depthWeight = 0.2;
        const distWeight = 0.3;
        
        const normalizedDepth = 1 - (depth / 700); // Deeper = less risk
        const normalizedDist = 1 / (1 + (distance / 100));
        
        const risk = (magnitude / 10 * magWeight) + 
                     (normalizedDepth * depthWeight) + 
                     (normalizedDist * distWeight);
        
        return Math.min(Math.max(risk, 0), 1);
    }
    
    static calculateWildfireRisk(temperature, humidity, windSpeed, vegetation) {
        // Simplified wildfire risk calculation
        const tempWeight = 0.3;
        const humidityWeight = 0.25;
        const windWeight = 0.25;
        const vegWeight = 0.2;
        
        const normalizedTemp = temperature / 50;
        const normalizedHumidity = 1 - (humidity / 100);
        const normalizedWind = windSpeed / 100;
        
        const risk = (normalizedTemp * tempWeight) + 
                     (normalizedHumidity * humidityWeight) + 
                     (normalizedWind * windWeight) + 
                     (vegetation * vegWeight);
        
        return Math.min(Math.max(risk, 0), 1);
    }
    
    static getRiskLabel(score) {
        if (score < 0.3) return { label: 'Low', class: 'low', color: '#00c853' };
        if (score < 0.6) return { label: 'Moderate', class: 'moderate', color: '#ffd600' };
        if (score < 0.8) return { label: 'High', class: 'high', color: '#ff6d00' };
        return { label: 'Extreme', class: 'extreme', color: '#ff1744' };
    }
}

// Data Manager
class DataManager {
    static save(key, data) {
        localStorage.setItem(key, JSON.stringify(data));
    }
    
    static load(key, defaultValue = null) {
        try {
            const data = localStorage.getItem(key);
            return data ? JSON.parse(data) : defaultValue;
        } catch {
            return defaultValue;
        }
    }
    
    static remove(key) {
        localStorage.removeItem(key);
    }
    
    static clear() {
        localStorage.clear();
    }
}

// Animation Helpers
const Animations = {
    fadeIn(element, duration = 300) {
        element.style.opacity = '0';
        element.style.display = 'block';
        
        requestAnimationFrame(() => {
            element.style.transition = `opacity ${duration}ms ease`;
            element.style.opacity = '1';
        });
    },
    
    fadeOut(element, duration = 300) {
        element.style.transition = `opacity ${duration}ms ease`;
        element.style.opacity = '0';
        
        setTimeout(() => {
            element.style.display = 'none';
        }, duration);
    },
    
    slideIn(element, direction = 'right', duration = 300) {
        const transforms = {
            right: 'translateX(100%)',
            left: 'translateX(-100%)',
            up: 'translateY(-100%)',
            down: 'translateY(100%)'
        };
        
        element.style.transform = transforms[direction];
        element.style.display = 'block';
        
        requestAnimationFrame(() => {
            element.style.transition = `transform ${duration}ms ease`;
            element.style.transform = 'translate(0)';
        });
    },
    
    pulse(element, duration = 1000) {
        element.style.animation = `pulse ${duration}ms ease-in-out infinite`;
    }
};

// Form Validation
class Validator {
    static email(email) {
        const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return re.test(email);
    }
    
    static password(password) {
        // At least 8 chars, 1 uppercase, 1 number, 1 special
        const re = /^(?=.*[A-Z])(?=.*[0-9])(?=.*[!@#$%^&*])(?=.{8,})/;
        return re.test(password);
    }
    
    static phone(phone) {
        const re = /^[+]?[(]?[0-9]{3}[)]?[-\s.]?[0-9]{3}[-\s.]?[0-9]{4,6}$/;
        return re.test(phone);
    }
    
    static required(value) {
        return value && value.trim().length > 0;
    }
}

// Date Helpers
const DateHelpers = {
    format(date, format = 'YYYY-MM-DD HH:mm') {
        const d = new Date(date);
        const pad = (n) => n.toString().padStart(2, '0');
        
        return format
            .replace('YYYY', d.getFullYear())
            .replace('MM', pad(d.getMonth() + 1))
            .replace('DD', pad(d.getDate()))
            .replace('HH', pad(d.getHours()))
            .replace('mm', pad(d.getMinutes()))
            .replace('ss', pad(d.getSeconds()));
    },
    
    timeAgo(date) {
        const seconds = Math.floor((new Date() - new Date(date)) / 1000);
        
        const intervals = {
            year: 31536000,
            month: 2592000,
            week: 604800,
            day: 86400,
            hour: 3600,
            minute: 60
        };
        
        for (const [unit, secondsInUnit] of Object.entries(intervals)) {
            const interval = Math.floor(seconds / secondsInUnit);
            if (interval >= 1) {
                return `${interval} ${unit}${interval > 1 ? 's' : ''} ago`;
            }
        }
        
        return 'Just now';
    }
};

// Export functions for global access
window.Toast = Toast;
window.APIManager = APIManager;
window.AuthManager = AuthManager;
window.ChartManager = ChartManager;
window.MapManager = MapManager;
window.RiskCalculator = RiskCalculator;
window.DataManager = DataManager;
window.Animations = Animations;
window.Validator = Validator;
window.DateHelpers = DateHelpers;

// DOM Ready Event
document.addEventListener('DOMContentLoaded', () => {
    console.log('🛡️ DisasterGuard Initialized');
    
    // Add smooth scroll to all anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({ behavior: 'smooth' });
            }
        });
    });
    
    // Add ripple effect to buttons
    document.querySelectorAll('.btn').forEach(button => {
        button.addEventListener('click', function(e) {
            const rect = this.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            
            const ripple = document.createElement('span');
            ripple.style.cssText = `
                position: absolute;
                background: rgba(255, 255, 255, 0.3);
                border-radius: 50%;
                transform: scale(0);
                animation: ripple 0.6s ease-out;
                pointer-events: none;
                width: 100px;
                height: 100px;
                left: ${x - 50}px;
                top: ${y - 50}px;
            `;
            
            this.style.position = 'relative';
            this.style.overflow = 'hidden';
            this.appendChild(ripple);
            
            setTimeout(() => ripple.remove(), 600);
        });
    });
});

// Add ripple animation keyframes
const style = document.createElement('style');
style.textContent = `
    @keyframes ripple {
        to {
            transform: scale(4);
            opacity: 0;
        }
    }
    
    .toast {
        background: var(--bg-card);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: var(--radius-md);
        padding: 1rem 1.5rem;
        display: flex;
        align-items: center;
        gap: 0.75rem;
        box-shadow: var(--shadow-3d);
        transform: translateX(100%);
        opacity: 0;
        transition: all 0.3s ease;
    }
    
    .toast-success i { color: var(--risk-low); }
    .toast-error i { color: var(--risk-extreme); }
    .toast-warning i { color: var(--risk-moderate); }
    .toast-info i { color: var(--accent-primary); }
`;
document.head.appendChild(style);

// Social Login Function
async function socialLogin(provider) {
    if (provider === 'google') {
        try {
            const response = await fetch('http://localhost:5000/api/auth/google');
            const data = await response.json();
            
            if (data.auth_url) {
                window.location.href = data.auth_url;
            } else {
                Toast.show(data.message || 'Google OAuth not configured', 'error');
            }
        } catch (error) {
            console.error('Google login error:', error);
            Toast.show('Failed to connect to Google. Make sure backend is running.', 'error');
        }
    } else if (provider === 'github') {
        try {
            const response = await fetch('http://localhost:5000/api/auth/github');
            const data = await response.json();
            
            if (data.auth_url) {
                window.location.href = data.auth_url;
            } else {
                Toast.show(data.message || 'GitHub OAuth not configured', 'error');
            }
        } catch (error) {
            console.error('GitHub login error:', error);
            Toast.show('Failed to connect to GitHub. Make sure backend is running.', 'error');
        }
    }
}
