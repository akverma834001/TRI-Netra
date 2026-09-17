# ==============================================================================
# Project Trinetra (त्रिनेत्र) — Unified Fullstack Docker Container
# Stage 1: Build Frontend Assets (Vite + React)
# Stage 2: Headless Python 3.11 Backend (FastAPI + OpenCV + PyTorch)
# ==============================================================================

# STAGE 1: Frontend Build
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm install

COPY frontend/ ./
RUN npm run build

# STAGE 2: Python Backend & Static Host
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

WORKDIR /app

# Install system dependencies for headless image processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend /app/backend
COPY conftest.py /app/

# Copy built frontend from Stage 1 into /app/frontend/dist
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist

# Expose service port
EXPOSE 8000

# Start FastAPI application via uvicorn
CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
