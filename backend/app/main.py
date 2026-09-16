import os
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import settings, STORAGE_DIR
from .database import init_db, SessionLocal
from .auth import seed_users
from .demo_cases import seed_demo_cases, clear_demo_cases

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

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Static Storage Directory for image serving
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
        print("[*] Normal mode active: zero-patient clean database ready.")
        # Ensure normal mode starts clean with 0 patients; benchmark demo cases are available via /demo/seed
        clear_demo_cases(db)
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
