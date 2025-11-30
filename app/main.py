from fastapi import FastAPI
from app.routes import store, settings, camera, zone, analytics, video_pipeline, ai_inference, alert_engine, license_plate_detection
from app.database import engine, Base, get_db
import time
import psycopg2
import os
import logging
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
import httpx
from sqlalchemy.orm import Session

# Import all models to ensure they are registered with SQLAlchemy
from app.db.models import Store, Settings, Camera, Zone, Analytics, AlertEngine, LicensePlateDetection

# Step 1: Initialize DB models/tables
# Only create tables automatically in dev, not production
if os.getenv("ENV", "production") != "production":
    print("Development mode: Creating tables if they don't exist...")
    # Create tables in correct order (only if they don't exist)
    Base.metadata.create_all(bind=engine)
    print("✅ Tables created successfully")
    
    # Seed the database with initial data
    from app.init_db import seed
    seed()
    print("✅ Database seeded successfully")

# Step 2: Initialize FastAPI app
app = FastAPI(
    title="Retail Dashboard Backend",
    docs_url="/docs",           # default is "/docs"
    redoc_url="/redoc",         # default is "/redoc"
    openapi_url="/openapi.json" # default is "/openapi.json"
)

# Configure logging to show API requests
logging.getLogger("uvicorn.access").setLevel(logging.INFO)
logging.getLogger("fastapi").setLevel(logging.INFO)

# CORS configuration
origins = [
    # Frontend origins
    "http://localhost:3000",     # Next.js development server
    "http://127.0.0.1:3000",    # Next.js development server alternative
    "http://frontend:3000",      # Docker service name
    
    # Nginx proxy origins (for requests coming through nginx)
    "http://localhost",          # nginx proxy
    "http://localhost:80",       # nginx proxy explicit port
    "http://127.0.0.1",         # nginx proxy alternative
    "http://127.0.0.1:80",      # nginx proxy explicit port
]

# Add production origins if in production
if os.getenv("ENV") == "production":
    origins.extend([
        # Add your production frontend URLs here
        # "https://your-production-domain.com",
    ])

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Step 3: Include routes
try:
    app.include_router(camera.router)
except Exception as e:
    print("Failed to load camera routes:", e)

try:
    app.include_router(zone.router)
except Exception as e:
    print("Failed to load zone routes:", e)

try:
    app.include_router(store.router, prefix="/api/v1/store", tags=["Store"])
except Exception as e:
    print("Failed to load store routes:", e)

try:
    app.include_router(settings.router, prefix="/api/v1/settings", tags=["Settings"])
except Exception as e:
    print("Failed to load settings routes:", e)

try:
    app.include_router(analytics.router)
except Exception as e:
    print("Failed to load analytics routes:", e)

try:
    app.include_router(alert_engine.router)
except Exception as e:
    print("Failed to load alert engine routes:", e)

try:
    app.include_router(video_pipeline.router)
except Exception as e:
    print("Failed to load video pipeline routes:", e)

try:
    app.include_router(ai_inference.router)
except Exception as e:
    print("Failed to load AI inference routes:", e)

try:
    app.include_router(license_plate_detection.router)
except Exception as e:
    print("Failed to load license plate detection routes:", e)

# @app.get("/")
# def health():
#    return {"ok": True}

@app.get("/health")
def health():
    """Health check endpoint for Docker health checks"""
    try:
        # Test database connection
        from app.database import engine
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}

@app.on_event("startup")
async def startup_event():
    """Initialize cameras and services on application startup"""
    print("🚀 BACKEND STARTUP: Starting application initialization...")
    
    try:
        # Get database session
        db = next(get_db())
        
        # Initialize cameras on startup
        async with httpx.AsyncClient() as client:
            await camera.initialize_cameras_on_startup(db, client)
        
        print("✅ BACKEND STARTUP: Application initialization completed successfully")
        
    except Exception as e:
        print(f"❌ BACKEND STARTUP ERROR: Failed to initialize application: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        if 'db' in locals():
            db.close()

@app.get("/test-log")
def test_log():
    """Test endpoint to verify logging works"""
    import logging
    logger = logging.getLogger(__name__)
    logger.info("🧪 TEST LOG: This should appear in backend logs!")
    print("🧪 PRINT LOG: This should appear in backend logs!")
    return {"message": "Test log endpoint called", "timestamp": "2025-10-05"}