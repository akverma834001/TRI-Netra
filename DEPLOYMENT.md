# Project Trinetra (त्रिनेत्र) — Deployment Guide

This guide provides instructions for deploying Project Trinetra to **Render**, **Vercel**, or **Docker**, as well as running it locally.

---

## Architecture Overview

Project Trinetra consists of:
1. **Backend**: FastAPI (Python) serving REST APIs, real-time capture evaluation, and the neuro-symbolic AI pipeline (PyTorch + OpenCV).
2. **Frontend**: React (TypeScript + Vite) single-page application with dark/light clinical themes and Hindi/English localization.
3. **Artifact Storage**: Fundus images, CLAHE-enhanced views, vessel masks, lesion masks, and Grad-CAM heatmaps stored in `/storage`.

---

## Option 1: Split Architecture — Frontend on Vercel + Backend on Render (Recommended)

This is the most scalable setup. Vercel's global CDN serves the frontend at edge speeds, while Render hosts the Python AI engine.

### Step 1: Deploy Backend to Render

1. Sign in to [Render](https://render.com) and click **New +** > **Web Service**.
2. Connect your GitHub repository: `TRI-Netra`.
3. Configure the Web Service:
   - **Name**: `trinetra-api`
   - **Region**: Oregon (or nearest)
   - **Language**: `Python`
   - **Branch**: `main` (or your active branch)
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type**: `Free`
4. In **Environment Variables**, add:
   - `PYTHON_VERSION`: `3.11.9`
   - `CORS_ORIGINS`: `*`
5. Click **Create Web Service**.
6. Once deployed, copy your backend URL (e.g., `https://trinetra-api.onrender.com`).
7. Test the health endpoint in your browser: `https://trinetra-api.onrender.com/health`.

### Step 2: Deploy Frontend to Vercel

1. Sign in to [Vercel](https://vercel.com) and click **Add New...** > **Project**.
2. Import the `TRI-Netra` repository.
3. Configure Project Settings:
   - **Framework Preset**: `Vite`
   - **Root Directory**: Click `Edit` and select `frontend` (or leave default if using root).
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
4. In **Environment Variables**, add:
   - **Name**: `VITE_API_BASE_URL`
   - **Value**: `https://trinetra-api.onrender.com` *(use your actual Render backend URL from Step 1)*
5. Click **Deploy**.
6. Once deployed, open your Vercel URL (e.g., `https://tri-netra.vercel.app`).
   - Client-side routing is configured via `frontend/vercel.json` (no 404 on page reload).

---

## Option 2: Unified Fullstack on Render (Single Free Service)

If you prefer deploying everything under a single free service on Render:

1. In Render, click **New +** > **Web Service**.
2. Connect your repository.
3. Set **Language** to `Docker` (Render will build via the included `Dockerfile`):
   - **Name**: `trinetra-fullstack`
   - **Dockerfile Path**: `Dockerfile`
   - **Instance Type**: `Free`
4. Click **Deploy**.
5. The container will:
   - Build the React Vite frontend into `frontend/dist`.
   - Start the FastAPI backend with uvicorn.
   - Serve the React frontend on `/` and the APIs on `/health`, `/auth`, `/patients`, etc.
   - Serve retinal images and masks on `/storage`.

---

## Option 3: Render Blueprint (Infrastructure as Code)

1. In Render, click **New +** > **Blueprint**.
2. Connect the `TRI-Netra` repository.
3. Render will read [`render.yaml`](./render.yaml) and automatically create both:
   - `trinetra-api` (Python Web Service)
   - `trinetra-frontend` (Static Site with SPA rewrites)
4. Click **Apply**.

---

## Option 4: Local Development

To run the site locally:

### 1. Terminal 1 — Start Backend
```bash
# From repository root
pip install -r requirements.txt
python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```
- API Docs: `http://localhost:8000/docs`
- Health Check: `http://localhost:8000/health`

### 2. Terminal 2 — Start Frontend
```bash
cd frontend
npm install
npm run dev
```
- Open `http://localhost:5173` in your browser.
- Vite automatically proxies `/health`, `/auth`, `/storage`, etc. to `http://localhost:8000`.

---

## Pre-Flight Checklist

| Check | Status | Note |
| :--- | :---: | :--- |
| **Requirements Encoding** | UTF-8 | Fixed UTF-16LE corruption |
| **Linux Headless Support** | Passed | Uses `opencv-python-headless` |
| **Dynamic API Base URL** | Passed | Reads `VITE_API_BASE_URL` or falls back gracefully |
| **Vercel SPA Rewrites** | Passed | `vercel.json` handles direct URLs |
| **Automated Tests** | 30/30 Passed | `python -m pytest backend/tests` |
| **Frontend Production Build**| Passed | `npm run build` exits 0 |
| **AI Layer Resolution** | Passed | Auto-normalizes `/storage/` paths |
| **Benchmark Demo Cases** | Seeded | 10 clinical cases ready out of the box |
