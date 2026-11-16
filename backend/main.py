"""
DisasterGuard FastAPI Application - Modular Entry Point
"""
from fastapi import FastAPI
from fastapi.responses import RedirectResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import os

# Import routers from routes module
from routes.auth import router as auth_router
from routes.weather import router as weather_router
from routes.ai import router as ai_router
from routes.admin import router as admin_router
from routes.earthquake import router as earthquake_router
from routes.flood_lstm import router as flood_lstm_router
from services.earthquake_service import _load_bundle as _load_earthquake_bundle
from services.flood_lstm_service import preload_model as _preload_flood_lstm
from database.db_config import test_connection


# Initialize FastAPI app
app = FastAPI(title="DisasterGuard API")


@app.on_event("startup")
def load_models_on_startup():
    import logging

    logger = logging.getLogger("disasterguard")
    try:
        _load_earthquake_bundle()
    except Exception as exc:  # pragma: no cover - logged for operators
        logger.error("Earthquake model failed to load: %s", exc)
    try:
        _preload_flood_lstm()
    except Exception as exc:  # pragma: no cover - logged for operators
        logger.error("Flood LSTM model failed to load: %s", exc)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ready")
def ready():
    checks = {}
    ready_state = True
    try:
        bundle = _load_earthquake_bundle()
        checks["earthquake_model"] = bundle["metadata"]["model_version"]
    except Exception as exc:
        ready_state = False
        checks["earthquake_model"] = f"unavailable: {exc}"
    try:
        from services.flood_lstm_service import model_info as _flood_info

        info = _flood_info()
        checks["flood_lstm_model"] = info["model"]["version"]
        checks["flood_lstm_lookback"] = info["model"]["lookback"]
    except Exception as exc:
        ready_state = False
        checks["flood_lstm_model"] = f"unavailable: {exc}"

    if not ready_state:
        from fastapi import HTTPException

        raise HTTPException(status_code=503, detail=checks)
    return {"status": "ready", **checks}

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all routers
app.include_router(auth_router)
app.include_router(weather_router)
app.include_router(ai_router)
app.include_router(admin_router)
app.include_router(earthquake_router)
app.include_router(flood_lstm_router)

# Root route
@app.get("/")
async def root():
    return RedirectResponse(url="/index.html")

# Admin route
@app.get("/admin")
async def admin_root():
    return RedirectResponse(url="/admin/admin-login.html")

@app.get("/admin/")
async def admin_root_trailing():
    return RedirectResponse(url="/admin/admin-login.html")

# Landing info route
@app.get("/api/landing/info")
async def get_landing_info():
    return {
        "success": True,
        "title": "DisasterGuard",
        "subtitle": "Protecting Communities with AI-Driven Disaster Prediction",
        "features": [
            {
                "icon": "fas fa-robot",
                "title": "AI-Powered Prediction",
                "description": "Advanced machine learning models predict natural disasters with high accuracy"
            },
            {
                "icon": "fas fa-bell",
                "title": "Real-Time Alerts",
                "description": "Instant notifications and emergency warnings via SMS and push notifications"
            },
            {
                "icon": "fas fa-map-marked-alt",
                "title": "Heatmap Visualization",
                "description": "Interactive disaster risk heatmaps and historical data analysis"
            }
        ],
        "stats": [
            {"number": "95%", "label": "Prediction Accuracy"},
            {"number": "5M+", "label": "Protected Users"},
            {"number": "10K+", "label": "Disasters Monitored"},
            {"number": "24/7", "label": "Real-Time Support"}
        ],
        "testimonials": [
            {
                "text": "DisasterGuard saved our community from a major flood. The early warnings gave us time to evacuate safely.",
                "name": "Sarah Johnson",
                "role": "Community Leader, Texas"
            },
            {
                "text": "The AI predictions are incredibly accurate. We've reduced our response time by 60% using this platform.",
                "name": "Dr. Michael Chen",
                "role": "Emergency Management Director"
            }
        ]
    }

# Database test route
@app.get("/api/db/test")
async def test_db_connection():
    return test_connection()

# Serve static frontend files (LAST to prevent overriding API routes)
frontend_dir = os.path.join(os.path.dirname(__file__), '..', 'frontend')

# Always revalidate frontend files so edits (and matching dashboard/page logic)
# are picked up instead of being served from the browser cache.
_NO_CACHE_HEADERS = {
    "Cache-Control": "no-cache, no-store, must-revalidate",
    "Pragma": "no-cache",
    "Expires": "0",
}


@app.get("/{path:path}")
async def serve_frontend(path: str):
    # Special handling for /admin or /admin/
    if path == "admin" or path == "admin/":
        return RedirectResponse(url="/admin/admin-login.html")
    
    file_path = os.path.join(frontend_dir, path)
    
    if os.path.isfile(file_path):
        return FileResponse(file_path, headers=_NO_CACHE_HEADERS)
    
    index_path = os.path.join(frontend_dir, "index.html")
    if os.path.isfile(index_path):
        return FileResponse(index_path, headers=_NO_CACHE_HEADERS)
    
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail="Not found")


if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "5000"))
    
    try:
        print("Database test:", test_connection())
    except Exception as e:
        print("Database test error:", str(e))
    
    uvicorn.run(app, host=host, port=port)
