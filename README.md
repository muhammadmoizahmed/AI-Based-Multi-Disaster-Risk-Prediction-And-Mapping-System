# DisasterGuard - Pakistan Disaster Prediction System

![DisasterGuard Logo](frontend/assets/logo2.png)

An AI-powered disaster prediction and early warning system specifically designed for Pakistan. The system monitors floods, earthquakes, and wildfires using real-time data from NASA, USGS, NOAA, and other satellite sources.

---

## Table of Contents
1. [Project Overview](#project-overview)
2. [Tech Stack](#tech-stack)
3. [Project Structure](#project-structure)
4. [Frontend Pages & Features](#frontend-pages--features)
5. [Backend API Documentation](#backend-api-detailed-documentation)
6. [Data Sources & Integrations](#data-sources--integrations)
7. [Services Layer](#services-layer-documentation)
8. [Database Layer](#database-layer-documentation)
9. [Setup & Installation](#setup--installation)
10. [Running the Application](#running-the-application)
11. [Incomplete Features](#incomplete-features)
12. [Future Enhancements](#future-enhancements)
13. [Contact](#contact)

---

## Project Overview

**DisasterGuard** is a comprehensive disaster prediction and management system for Pakistan. It integrates multiple real-time data sources, AI-powered chat assistance, user authentication, and admin management.

### What has been completed?
- ✅ **Full Stack Architecture**: FastAPI backend with HTML/CSS/JS frontend
- ✅ **User Authentication System**: Email/password, OAuth2 (Google/GitHub), email verification
- ✅ **AI Chat Assistant**: Gemini-based chatbot for disaster management queries
- ✅ **Weather Integration**: OpenWeatherMap integration for real-time weather/forecasts
- ✅ **Admin Dashboard**: User management, API monitoring
- ✅ **Static File Serving**: Frontend served directly by FastAPI
- ✅ **Database Layer**: SQLite/PostgreSQL support for users
- ✅ **API Testing Scripts**: Comprehensive testing of external data sources
- ✅ **Email Service**: SMTP integration for verification/reset emails

### What is incomplete?
- ❌ **Machine Learning Models**: Flood/earthquake/wildfire prediction models not trained/deployed
- ❌ **Redis Caching**: In-memory cache only, no Redis integration
- ❌ **WebSocket Updates**: No real-time WebSocket push notifications
- ❌ **PostgreSQL by Default**: SQLite not fully set up (USE_SQLITE flag in db_config)
- ❌ **Mobile App**: No React Native or cross-platform app
- ❌ **SMS Alerts**: No SMS integration for emergency alerts
- ❌ **NDMA Integration**: No official NDMA data integration

---

## Tech Stack

### Frontend
- **HTML5**: Semantic markup
- **CSS3**: Custom styling with dark theme
- **JavaScript (ES6+)**: Interactive functionality
- **Leaflet.js**: Interactive maps (planned)
- **Chart.js**: Data visualization (admin panel)
- **Font Awesome**: Icons
- **Google Fonts (Inter)**: Typography

### Backend
- **FastAPI**: Modern, async web framework for APIs
- **Python 3.8+**: Core backend language
- **Pydantic**: Data validation
- **python-dotenv**: Environment management
- **requests**: HTTP client for external APIs
- **uvicorn**: ASGI server
- **smtplib**: Email sending
- **jose**: JWT token handling
- **psycopg2-binary**: PostgreSQL driver (optional)

### External APIs
- **OpenWeatherMap**: Weather data & forecasts
- **NASA EONET**: Natural event monitoring
- **NASA POWER**: Rainfall & climate data
- **USGS Earthquake API**: Seismic activity
- **NOAA NGDC**: Tsunami historical data
- **GDACS**: Disaster alerts (RSS/JSON)
- **Google Gemini 2.5 Flash Lite**: AI chat assistant
- **Google OAuth2**: Social login
- **GitHub OAuth2**: Social login
- **ipapi.co**: IP-based geolocation

---

## Project Structure

```
fyp-master/
├── backend/                          # Backend application
│   ├── database/                     # Database layer
│   │   ├── __init__.py
│   │   ├── db_config.py              # Database configuration
│   │   └── db_users.py               # User database operations
│   ├── models/                       # Pydantic models
│   │   ├── __init__.py
│   │   ├── auth_models.py            # Auth request models
│   │   └── user_models.py            # User models
│   ├── routes/                       # API endpoints
│   │   ├── __init__.py
│   │   ├── auth.py                   # Authentication endpoints
│   │   ├── weather.py                # Weather endpoints
│   │   ├── ai.py                     # AI chat endpoints
│   │   └── admin.py                  # Admin endpoints
│   ├── services/                     # Business logic layer
│   │   ├── __init__.py
│   │   ├── email_service.py          # Email sending
│   │   ├── gemini_service.py         # AI chat service
│   │   ├── oauth_service.py          # OAuth2 integration
│   │   └── weather_service.py        # Weather data service
│   ├── utils/                        # Utility functions
│   │   ├── __init__.py
│   │   ├── dependencies.py           # Auth dependencies (admin_only)
│   │   ├── helpers.py                # Helper functions
│   │   └── security.py               # Security/hashing/JWT
│   ├── add_test_users.py             # Add test users script
│   ├── db_setup.sql                  # Database setup script
│   ├── flood.py                      # Flood module
│   ├── init_db.py                    # Database initialization
│   ├── main.py                       # FastAPI application entry point
│   ├── requirements.txt              # Python dependencies
│   └── test_get_users.py             # User API test script
├── frontend/                         # Frontend application
│   ├── admin/                        # Admin pages
│   │   ├── admin-login.html          # Admin login
│   │   ├── admin-settings.html       # Admin settings
│   │   ├── api-monitor.html          # API monitoring
│   │   ├── config.html               # Alert config
│   │   ├── dashboard.html            # Admin dashboard
│   │   ├── index.html                # Admin index redirect
│   │   ├── logs.html                 # System logs
│   │   ├── models.html               # ML model management
│   │   └── users.html                # User management
│   ├── assets/                       # Static assets
│   │   └── logo.svg
│   ├── css/                          # Stylesheets
│   │   └── styles.css                # Main styles
│   ├── js/                           # JavaScript
│   │   └── main.js                   # Main JS (APIManager, AuthManager)
│   ├── pages/                        # User pages
│   │   ├── alerts.html               # Alerts
│   │   ├── earthquake.html           # Earthquake monitoring
│   │   ├── flood.html                # Flood monitoring
│   │   ├── forecast.html             # Weather forecast
│   │   ├── heatmap.html              # Risk heatmap
│   │   ├── history.html              # Activity history
│   │   ├── live-chat.html            # AI live chat
│   │   ├── profile.html              # User profile
│   │   ├── settings.html             # Settings
│   │   ├── weather.html              # Weather page
│   │   └── wildfire.html             # Wildfire monitoring
│   ├── dashboard.html                # User dashboard
│   ├── forgot-password.html          # Forgot password
│   ├── index.html                    # Landing page
│   ├── login.html                    # Login page
│   ├── oauth-callback.html           # OAuth callback
│   ├── privacy.html                  # Privacy policy
│   ├── register.html                 # Register page
│   ├── terms.html                    # Terms of service
│   └── verify-email.html             # Email verification
├── datasets/                         # Datasets for ML
│   ├── pakistan_cyclone_2020_2025.csv
│   ├── pakistan_earthquake_2020_2025.csv
│   ├── pakistan_flood_dataset_2020_2025 (1).csv
│   ├── pakistan_heatwave_2020_2025.csv
│   ├── pakistan_landslide_2020_2025.csv
│   ├── pakistan_tsunami_2020_2025.csv
│   └── pakistan_wildfire_2020_2025.csv
├── api_testing.py                    # Comprehensive API testing script
├── test_chatbot.py                   # Chatbot API test script
├── frontend_screenshort.pdf          # UI screenshots
├── output api.pdf                    # API test output
├── .gitignore
└── README.md                         # This file!
```

---

## Frontend Pages & Features

### Public Pages
| Page | Path | Purpose |
|------|------|---------|
| Landing | `/index.html` | Hero section, features, stats, call to action |
| Login | `/login.html` | Email/password login + social login (Google/GitHub) |
| Register | `/register.html` | User registration with email verification PIN |
| Verify Email | `/verify-email.html` | Enter PIN to verify email |
| Forgot Password | `/forgot-password.html` | Password reset via PIN |
| OAuth Callback | `/oauth-callback.html` | Handle OAuth2 redirects |
| Terms | `/terms.html` | Terms of service |
| Privacy | `/privacy.html` | Privacy policy |

### User Pages (Auth Required)
| Page | Path | Purpose |
|------|------|---------|
| Dashboard | `/dashboard.html` | User dashboard, risk scores, stats |
| Weather | `/pages/weather.html` | Real-time weather & forecasts |
| Flood | `/pages/flood.html` | Flood monitoring |
| Earthquake | `/pages/earthquake.html` | Earthquake monitoring |
| Wildfire | `/pages/wildfire.html` | Wildfire monitoring |
| Alerts | `/pages/alerts.html` | Emergency alerts |
| Forecast | `/pages/forecast.html` | Weather forecasts |
| Heatmap | `/pages/heatmap.html` | Risk heatmap |
| History | `/pages/history.html` | Activity history |
| Live Chat | `/pages/live-chat.html` | AI disaster chat assistant |
| Profile | `/pages/profile.html` | User profile management |
| Settings | `/pages/settings.html` | User settings |

### Admin Pages (Admin Role Required)
| Page | Path | Purpose |
|------|------|---------|
| Admin Login | `/admin/admin-login.html` | Admin authentication |
| Admin Dashboard | `/admin/dashboard.html` | System stats & overview |
| User Management | `/admin/users.html` | Manage users (list, update, delete) |
| Model Management | `/admin/models.html` | ML model management |
| API Monitor | `/admin/api-monitor.html` | API health & usage |
| Alert Config | `/admin/config.html` | Configure alerts |
| Logs | `/admin/logs.html` | System logs |
| Admin Settings | `/admin/admin-settings.html` | Admin settings |

---

## Backend API Detailed Documentation

### Base URL
**Local Development**: `http://localhost:5000`

### Authentication Endpoints (`/api/auth`)

| Method | Endpoint | Request Body/Params | Description | Response |
|--------|----------|---------------------|-------------|----------|
| `POST` | `/login` | `{ email, password }` | Login with email/password | `{ success, message, user, token }` |
| `POST` | `/register` | `{ name, email, password }` | Register new user, send PIN | `{ success, message }` |
| `POST` | `/verify-pin` | `{ email, pin }` | Verify email PIN | `{ success, message }` |
| `POST` | `/forgot-password` | `{ email }` | Send password reset PIN | `{ success, message }` |
| `GET` | `/google` | - | Get Google OAuth URL | `{ auth_url }` |
| `GET` | `/google/callback` | `code` (query) | Google OAuth callback | Redirect to `/oauth-callback.html` |
| `GET` | `/github` | - | Get GitHub OAuth URL | `{ auth_url }` |
| `GET` | `/github/callback` | `code` (query) | GitHub OAuth callback | Redirect to `/oauth-callback.html` |

### Weather Endpoints (`/api/weather`)

| Method | Endpoint | Params | Description | Response |
|--------|----------|--------|-------------|----------|
| `GET` | `/api-key` | - | Get OpenWeather API key | `{ api_key }` |
| `GET` | `/current` | `lat`, `lon` | Current weather for coordinates | OpenWeather current weather JSON |
| `GET` | `/forecast` | `lat`, `lon` | 5-day forecast | OpenWeather forecast JSON |
| `GET` | `/my-location` | - | Weather for user's IP location | `{ location, current, forecast }` |
| `GET` | `/pakistan-cities` | - | Weather for major Pakistani cities | `{ cities: [...] }` |
| `GET` | `/search` | `city` | Search weather for Pakistan city | `{ city, current, forecast }` |
| `GET` | `/autocomplete` | `query` | City name autocomplete | `{ suggestions: [...] }` |

### AI Endpoints (`/api/ai`)

| Method | Endpoint | Request Body | Description | Response |
|--------|----------|--------------|-------------|----------|
| `POST` | `/chat` | `{ message }` | Chat with DisasterGuard AI | `{ response }` |

### Admin Endpoints (`/api/admin`)

| Method | Endpoint | Params/Body | Auth? | Description | Response |
|--------|----------|-------------|-------|-------------|----------|
| `GET` | `/users` | `page`, `search` | Yes (Admin) | Get paginated users | `{ success, users, total_users, current_page, total_pages }` |
| `GET` | `/users/{user_id}` | - | Yes (Admin) | Get single user by ID | `{ success, user }` |
| `PUT` | `/users/{user_id}` | `{ name, email, role, phone, location, status }` | Yes (Admin) | Update user | `{ success }` |
| `DELETE` | `/users/{user_id}` | - | Yes (Admin) | Delete user | `{ success }` |

### General Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Redirect to `/index.html` |
| `GET` | `/admin` | Redirect to `/admin/admin-login.html` |
| `GET` | `/api/landing/info` | Get landing page info/stats |
| `GET` | `/api/db/test` | Test database connection |
| `GET` | `/{path}` | Serve static frontend files |

---

## Data Sources & Integrations

### What data comes from where?

1. **User Authentication & Profiles**
   - Stored locally in SQLite/PostgreSQL database
   - OAuth user data from Google/GitHub APIs
   - Emails sent via SMTP (configurable)

2. **Weather & Forecast Data**
   - **Source**: OpenWeatherMap API
   - **Endpoints used**: Current Weather, 5-Day Forecast
   - **Caching**: 5-minute in-memory cache
   - **Request flow**:
     ```
     Frontend → /api/weather/current → weather_service.py → OpenWeatherMap API → Frontend
     ```

3. **AI Chat Responses**
   - **Source**: Google Gemini 2.5 Flash Lite API
   - **System prompt**: Specialized for Pakistan disaster management
   - **Request flow**:
     ```
     Frontend → /api/ai/chat → gemini_service.py → Gemini API → Frontend
     ```

4. **Disaster Data (NASA, USGS, NOAA, GDACS)**
   - **Used in**: `api_testing.py` script (not integrated into live API yet)
   - **Sources**:
     - NASA EONET (Natural events)
     - NASA POWER (Rainfall)
     - USGS Earthquake API
     - NOAA NGDC (Tsunamis)
     - GDACS (Disaster alerts)

### API Request Flows

#### 1. User Login Flow
```
┌─────────────┐         ┌─────────────┐         ┌─────────────┐         ┌─────────────┐
│   Frontend  │────────▶│ /api/auth/  │────────▶│ db_users.py │────────▶│  Database   │
│  (login.js) │  POST   │   /login    │  Query  │  (verify)   │  Select  │  (users)    │
└─────────────┘         └─────────────┘         └─────────────┘         └─────────────┘
       │                       │
       │◀──────────────────────┘
       │  { success, token, user }
       ▼
  Store token in localStorage
```

#### 2. Weather Data Flow
```
┌─────────────┐         ┌─────────────┐         ┌─────────────┐         ┌─────────────┐
│   Frontend  │────────▶│ /api/weather│────────▶│   Weather   │────────▶│OpenWeather  │
│(weather.js) │   GET   │  /current   │  Call   │  Service    │  HTTP    │    API      │
└─────────────┘         └─────────────┘         └─────────────┘         └─────────────┘
       │                       │                       │
       │◀──────────────────────┘◀──────────────────────┘
       │   { temperature, humidity, ... }
       ▼
   Display to user
```

#### 3. OAuth (Google) Flow
```
┌─────────────┐         ┌─────────────┐         ┌─────────────┐
│   Frontend  │────────▶│ /api/auth/  │────────▶│    Google   │
│  (login.js) │   GET   │   /google   │  Redirect│   OAuth     │
└─────────────┘         └─────────────┘         └─────────────┘
       │                                               │
       │◀──────────────────────────────────────────────┘
       │          User grants permission
       ▼
┌─────────────┐         ┌─────────────┐         ┌─────────────┐
│  Frontend   │◀────────│Google Callback│◀────────│  Get User   │
│  (oauth-    │ Redirect│   Route     │  Fetch   │   Info      │
│ callback)   │         └─────────────┘         └─────────────┘
       │
       ▼
  Store user/token, login
```

#### 4. AI Chat Flow
```
┌─────────────┐         ┌─────────────┐         ┌─────────────┐
│   Frontend  │────────▶│ /api/ai/    │────────▶│   Gemini    │
│(live-chat)  │  POST   │   /chat     │  HTTP    │    API      │
└─────────────┘         └─────────────┘         └─────────────┘
       │                       │                       │
       │◀──────────────────────┘◀──────────────────────┘
       │      { response: "AI message..." }
       ▼
  Display chat message
```

---

## Services Layer Documentation

| Service | File | Purpose | Key Functions |
|---------|------|---------|---------------|
| **Weather Service** | `services/weather_service.py` | Weather data from OpenWeatherMap | `get_current_weather()`, `get_weather_forecast()`, `get_pakistan_cities_weather()`, `search_city_weather()` |
| **OAuth Service** | `services/oauth_service.py` | Google/GitHub OAuth2 | `get_google_auth_url()`, `get_google_user_info()`, `get_github_auth_url()`, `get_github_user_info()` |
| **Gemini Service** | `services/gemini_service.py` | AI chat responses | `get_ai_response()` |
| **Email Service** | `services/email_service.py` | Email sending | `send_email()`, `send_verification_email()`, `send_password_reset_email()` |

---

## Database Layer Documentation

### Database Configuration
- File: `database/db_config.py`
- Default: **PostgreSQL** (USE_SQLITE = False)
- SQLite option available (set USE_SQLITE = True)

### User Table Schema
| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| name | String | User's full name |
| email | String | Unique email |
| password | String | Hashed password (SHA256) |
| role | String | 'user' or 'admin' |
| phone | String | Phone number |
| location | String | User location |
| ip_address | String | Last login IP |
| provider | String | 'local', 'google', 'github' |
| provider_id | String | OAuth provider ID |
| profile_picture | String | Profile picture URL |
| status | String | Account status |
| created_at | DateTime | Account creation date |
| last_active | DateTime | Last activity timestamp |

### User DB Functions (database/db_users.py)
- `get_all_users()`: Get all users
- `get_user_by_id(user_id)`: Get user by ID
- `get_user_by_email(email)`: Get user by email
- `verify_user(email, password)`: Verify user credentials
- `create_user(...)`: Create new user
- `update_user(...)`: Update user info
- `delete_user(user_id)`: Delete user
- `search_users(query)`: Search users by name/email
- `get_user_count()`: Get total user count

---

## Setup & Installation

### Prerequisites
- Python 3.8 or higher
- `pip` package manager
- (Optional) PostgreSQL database
- API keys for external services

### 1. Environment Variables
Create a `.env` file in the **root directory** of the project:

```env
# OpenWeatherMap API (required for weather features)
openweathermap_api_key=YOUR_OPENWEATHER_API_KEY

# Gemini AI API (required for chat)
gemini_key=YOUR_GEMINI_API_KEY

# SMTP Email Configuration (required for email verification)
SMTP_EMAIL=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587

# OAuth2 Configuration
google_client_id=YOUR_GOOGLE_CLIENT_ID
google_client_secret=YOUR_GOOGLE_CLIENT_SECRET
github_client_id=YOUR_GITHUB_CLIENT_ID
github_client_secret=YOUR_GITHUB_CLIENT_SECRET

# Security
SECRET_KEY=your-strong-secret-key-here-change-in-production

# Database (PostgreSQL)
DB_HOST=localhost
DB_PORT=5432
DB_NAME=disasterguard
DB_USER=postgres
DB_PASSWORD=your-db-password
```

### 2. Install Python Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 3. Database Setup (PostgreSQL)
1. Create a PostgreSQL database named `disasterguard`
2. Run `db_setup.sql` to create tables
3. (Optional) Run `init_db.py` or `add_test_users.py` to add test data

---

## Running the Application

### 1. Start the Backend Server
```bash
cd backend
python main.py
```
OR
```bash
uvicorn backend.main:app --host 0.0.0.0 --port 5000 --reload
```

The server will start on:
- **API Base URL**: `http://localhost:5000`
- **API Docs (Swagger UI)**: `http://localhost:5000/docs`
- **API Docs (ReDoc)**: `http://localhost:5000/redoc`

### 2. Access the Frontend
Open your browser and navigate to:
- **Landing Page**: `http://localhost:5000/index.html`
- **Login Page**: `http://localhost:5000/login.html`
- **Admin Login**: `http://localhost:5000/admin/admin-login.html`

### 3. Running Test Scripts
```bash
# Test chatbot API
python test_chatbot.py

# Test all external data sources
python api_testing.py
```

---

## Incomplete Features

List of features that are planned or partially implemented:

| Feature | Status | Notes |
|---------|--------|-------|
| **Machine Learning Prediction Models** | ❌ Not Implemented | Datasets exist in `datasets/`, but no trained models integrated |
| **Redis Caching** | ❌ Not Implemented | In-memory dict cache only; no Redis |
| **WebSocket Real-Time Updates** | ❌ Not Implemented | No real-time push notifications |
| **SMS Alerts** | ❌ Not Implemented | No SMS integration (Twilio, etc.) |
| **NDMA Integration** | ❌ Not Implemented | No official Pakistani disaster management data |
| **Mobile Application** | ❌ Not Implemented | No React Native/Flutter app |
| **PostgreSQL Default Setup** | ⚠️ Partial | SQLite code exists, but USE_SQLITE is False by default; tables not auto-created |
| **API Monitoring Dashboard** | ⚠️ Static Page | HTML page exists, but no live stats |
| **Risk Heatmap** | ⚠️ Static Page | HTML page exists, but no interactive Leaflet map |

---

## Future Enhancements

1. **Train & Deploy ML Models**
   - Flood prediction using LSTM on rainfall data
   - Earthquake risk assessment using Random Forest
   - Wildfire hotspot detection using satellite imagery

2. **Real-Time Features**
   - WebSocket for live updates
   - Push notifications (browser/mobile)

3. **Data Persistence**
   - Redis for caching
   - Complete PostgreSQL integration with auto-migrations

4. **Mobile App**
   - React Native cross-platform app
   - Offline functionality

5. **Additional Integrations**
   - NDMA official data
   - SMS alerts (Twilio)
   - Pakistan-specific weather services (PMD)

6. **Enhanced UI**
   - Complete Leaflet map integration
   - Chart.js data visualization
   - Responsive design improvements

---

## Contact

**Developed by Muhammad Moiz Ahmed** - Final Year Project

---

## Additional Notes

- The frontend `main.js` has a base URL mismatch: it points to `http://localhost:5001` but the server runs on port `5000` by default
- Email verification PINs are stored in-memory and will be lost on server restart (use Redis in production)
- Password hashing uses SHA256; consider bcrypt for production
- CORS is open to all origins in development; restrict in production

