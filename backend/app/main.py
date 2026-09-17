import os
import sys
from pathlib import Path

# Add backend directory to sys.path so app modules can be imported anywhere
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .config import settings, STORAGE_DIR
from .database import init_db, SessionLocal, Patient
from .auth import seed_users
from .demo_cases import seed_demo_cases

# Import Routers
from .routes import (
    auth_routes,
    patient_routes,
    screening_routes,
    workflow_routes,
    demo_routes,
    ai_routes,
    review_routes,
    referral_routes,
    telemedicine_routes,
    sync_routes,
    simulation_routes,
    training_routes,
    validation_routes,
    device_routes,
    audit_routes,
    realtime_routes
)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Distributed, Explainable Retinal Screening & Telemedicine Operational Engine",
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Middleware - allows frontend from Vercel, Render, or localhost
cors_origins_env = os.environ.get("CORS_ORIGINS", "*")
allowed_origins = [orig.strip() for orig in cors_origins_env.split(",") if orig.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins if allowed_origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Static Storage Directory for retinal image and mask serving
app.mount("/storage", StaticFiles(directory=str(STORAGE_DIR)), name="storage")

# Include Modular Routers
app.include_router(auth_routes.router)
app.include_router(patient_routes.router)
app.include_router(screening_routes.router)
app.include_router(workflow_routes.router)
app.include_router(demo_routes.router)
app.include_router(ai_routes.router)
app.include_router(review_routes.router)
app.include_router(referral_routes.router)
app.include_router(telemedicine_routes.router)
app.include_router(sync_routes.router)
app.include_router(simulation_routes.router)
app.include_router(training_routes.router)
app.include_router(validation_routes.router)
app.include_router(device_routes.router)
app.include_router(audit_routes.router)
app.include_router(realtime_routes.router)

@app.on_event("startup")
def on_startup():
    print(f"[*] Initializing {settings.PROJECT_NAME} database...")
    init_db()
    db = SessionLocal()
    try:
        print("[*] Seeding default RBAC users...")
        seed_users(db)
        
        # Check if demo cases exist; if not, stage benchmark demo cases so prototype is immediately operational
        demo_count = db.query(Patient).filter(Patient.id.like("PAT-DEMO-%")).count()
        if demo_count == 0:
            print("[*] Staging benchmark clinical demonstration cases...")
            seed_demo_cases(db)
            print("[*] Clinical demo cases staged successfully.")
        else:
            print(f"[*] Clinical demo cases ready: {demo_count} cases staged.")
            
        print("[*] Project Trinetra Backend Ready.")
    finally:
        db.close()

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "disclaimer": settings.DISCLAIMER,
        "engine_architecture": "SEE (Optical Gatekeeper) • UNDERSTAND (Anatomy & Neuro-Symbolic AI) • ACT (Review & Telemedicine)"
    }

# Unified Fullstack Serving: Check for built frontend in dist directory
FRONTEND_DIST = (BACKEND_DIR.parent / "frontend" / "dist").resolve()
if not FRONTEND_DIST.exists():
    alt_dist = Path("frontend/dist").resolve()
    if alt_dist.exists():
        FRONTEND_DIST = alt_dist

if FRONTEND_DIST.exists():
    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="frontend-assets")

    @app.get("/{full_path:path}")
    async def serve_spa_frontend(full_path: str):
        # Don't intercept API or docs routes
        if full_path.startswith(("docs", "redoc", "openapi.json")):
            return {"detail": "Not Found"}
        target_file = FRONTEND_DIST / full_path
        if full_path and target_file.exists() and target_file.is_file():
            return FileResponse(target_file)
        index_file = FRONTEND_DIST / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return {"detail": "Frontend index.html not found"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=port, reload=False)
