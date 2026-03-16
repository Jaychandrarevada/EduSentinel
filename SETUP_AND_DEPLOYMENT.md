# EduSentinel — Complete Setup & Deployment Guide

> **Which terminal to use on Windows?**
> Use **PowerShell** for everything in this guide.
> Open it by pressing `Win + X` → "Windows PowerShell" or "Terminal".
> Do NOT use CMD (too limited) or Git Bash (path issues with npm/npx on Windows).

---

## Table of Contents

1. [Live Links (Already Deployed)](#1-live-links-already-deployed)
2. [Run Locally on Your Machine](#2-run-locally-on-your-machine)
3. [Deploy to Production (Railway + Vercel)](#3-deploy-to-production-railway--vercel)
4. [Redeploy After Code Changes](#4-redeploy-after-code-changes)
5. [Troubleshooting](#5-troubleshooting)

---

## 1. Live Links (Already Deployed)

| Service | URL |
|---------|-----|
| Frontend (Vercel) | https://frontend-two-cyan-53.vercel.app |
| Backend (Railway) | https://edusentinel-backend-production.up.railway.app |

### Login Credentials

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@edusentinel.dev | Admin@123 |
| Faculty | faculty@edusentinel.dev | Faculty@123 |
| Demo Faculty 1 | faculty1@demo.com | demo123 |
| Demo Faculty 2 | faculty2@demo.com | demo123 |
| Demo Faculty 3 | faculty3@demo.com | demo123 |

---

## 2. Run Locally on Your Machine

### What You Need Installed First

| Tool | Download | Check if installed |
|------|----------|--------------------|
| Python 3.12 | https://python.org/downloads | `python --version` |
| Node.js 18+ | https://nodejs.org | `node --version` |
| Git | https://git-scm.com | `git --version` |

---

### You Need EXACTLY 2 Terminals Running at the Same Time

```
Terminal 1  →  Backend  (FastAPI on port 8000)
Terminal 2  →  Frontend (Next.js on port 3000)
```

Open two separate PowerShell windows side by side.

---

### Terminal 1 — Backend

```powershell
# Navigate to backend folder
cd D:\EduSentinel\backend

# First time only: create a virtual environment
python -m venv venv

# First time only: activate it
.\venv\Scripts\Activate

# First time only: install all dependencies
pip install -r requirements.txt

# Every time after that: just activate and run
.\venv\Scripts\Activate
uvicorn main:app --reload --port 8000
```

**You will see this when it's ready:**
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

**Backend is now running at:** http://localhost:8000

> **Note:** The local backend uses SQLite (a file-based database).
> No PostgreSQL installation needed. The file `edusentinel_dev.db`
> is created automatically in the backend folder on first run.

---

### Terminal 2 — Frontend

```powershell
# Navigate to frontend folder
cd D:\EduSentinel\frontend

# First time only: install dependencies
npm install

# Every time: start the dev server
npm run dev
```

**You will see this when it's ready:**
```
▲ Next.js 14.2.0
- Local: http://localhost:3000
```

**Frontend is now running at:** http://localhost:3000

---

### After Both Terminals Are Running

1. Open browser → go to http://localhost:3000
2. Login with: `admin@edusentinel.dev` / `Admin@123`
3. Seed demo data so the dashboard has content:
   - Open a third PowerShell window and run:
   ```powershell
   curl -X POST http://localhost:8000/api/v1/admin/seed-demo
   ```
   Or just open http://localhost:8000/api/v1/admin/seed in browser
   (GET works too in browser for quick check)

---

### Local Environment Summary

| Terminal | Folder | Command | URL |
|----------|--------|---------|-----|
| PowerShell 1 | `backend` | `uvicorn main:app --reload` | http://localhost:8000 |
| PowerShell 2 | `frontend` | `npm run dev` | http://localhost:3000 |

**To stop:** Press `Ctrl + C` in each terminal.

---

### Local .env File (backend)

The file `backend/.env` already exists with local settings.
You do not need to change anything to run locally. It uses SQLite automatically.

```
APP_ENV=development
DATABASE_URL=sqlite:///./edusentinel_dev.db   ← local file, no setup needed
JWT_SECRET_KEY=local-dev-secret-key
CORS_ORIGINS=["http://localhost:3001","http://localhost:3000"]
```

---

## 3. Deploy to Production (Railway + Vercel)

### Overview

| Service | Platform | Auto-deploys? |
|---------|----------|---------------|
| Backend | Railway | YES — every `git push` redeploys automatically |
| Frontend | Vercel | NO — run one command manually |

---

### One-Time Setup (first deployment ever)

#### Prerequisites

```powershell
# Check Node is installed
node --version   # should show v18 or higher

# Check Git is installed and logged in
git --version
git config user.email   # should show your email
```

#### Step 1 — Login to Vercel (one time only)

```powershell
npx vercel login
```

- A browser window opens automatically
- Click **Continue with GitHub**
- Authorize Vercel
- Come back to terminal — you'll see: `Congratulations! You are now logged in.`

You only do this once. After that, you stay logged in permanently.

#### Step 2 — Connect Railway to GitHub (one time only, in browser)

1. Go to https://railway.app → log in with GitHub
2. New Project → Deploy from GitHub repo → select `EduSentinel`
3. Set the root directory to `backend`
4. Add environment variables (see section below)
5. Railway deploys automatically

#### Step 3 — Set Railway Environment Variables (one time only)

In Railway dashboard → your backend service → **Variables** tab, add:

| Variable | Value |
|----------|-------|
| `APP_ENV` | `production` |
| `DEBUG` | `false` |
| `JWT_SECRET_KEY` | any random 64-char string (generate below) |
| `CORS_ORIGINS` | `["https://your-vercel-url.vercel.app","http://localhost:3000"]` |
| `NOTIFICATION_ENABLED` | `false` |

**Generate a secure JWT secret key:**
```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```
Copy the output and paste it as the value for `JWT_SECRET_KEY`.

#### Step 4 — Deploy Frontend to Vercel

```powershell
cd D:\EduSentinel\frontend

npx vercel --prod --yes `
  --build-env NEXT_PUBLIC_API_URL=https://edusentinel-backend-production.up.railway.app `
  --env NEXT_PUBLIC_API_URL=https://edusentinel-backend-production.up.railway.app
```

> **PowerShell note:** Use the backtick ` for line continuation in PowerShell.
> If you prefer one line:
> ```powershell
> npx vercel --prod --yes --build-env NEXT_PUBLIC_API_URL=https://edusentinel-backend-production.up.railway.app --env NEXT_PUBLIC_API_URL=https://edusentinel-backend-production.up.railway.app
> ```

The command prints your live URL at the end. Done.

---

## 4. Redeploy After Code Changes

### Backend (automatic — nothing to do)

```powershell
cd D:\EduSentinel

git add .
git commit -m "describe your change here"
git push origin main
```

Railway detects the push and redeploys the backend automatically in ~2 minutes.

### Frontend (one command)

```powershell
cd D:\EduSentinel\frontend

npx vercel --prod --yes --build-env NEXT_PUBLIC_API_URL=https://edusentinel-backend-production.up.railway.app --env NEXT_PUBLIC_API_URL=https://edusentinel-backend-production.up.railway.app
```

### Both Together (full redeploy in one go)

```powershell
# From the project root
cd D:\EduSentinel

# Push backend changes to Railway
git add .
git commit -m "your change description"
git push origin main

# Redeploy frontend to Vercel
cd frontend
npx vercel --prod --yes --build-env NEXT_PUBLIC_API_URL=https://edusentinel-backend-production.up.railway.app --env NEXT_PUBLIC_API_URL=https://edusentinel-backend-production.up.railway.app
```

---

## 5. Troubleshooting

### "Can't reach backend" after the site has been idle

**Cause:** Railway free tier suspends the service when monthly $5 credit runs out.

**Fix:**
1. Go to https://railway.app → Account Settings → Billing
2. Add a credit card (you won't be charged — usage stays under $5/month for a demo project)
3. Railway resumes the service immediately

**Why it happens:** Railway's free trial gives a one-time $5 credit. Once exhausted, the service stops. Adding a card gives you $5 free credit every month.

---

### How many people can use the live site at once

| Layer | Capacity |
|-------|----------|
| Frontend (Vercel) | Unlimited — Vercel scales globally for free |
| Backend API (Railway) | 30–50 concurrent users comfortably |
| Database (Railway PostgreSQL) | 25 simultaneous connections (free tier hard limit) |

For a college demo or presentation with up to 50 people: fully stable.
For 100+ concurrent users: upgrade Railway to Hobby plan ($5/month, 8 GB RAM).

---

### Login works locally but fails on live site

CORS is not configured. Go to Railway → Variables → update `CORS_ORIGINS`:
```
["https://your-vercel-app.vercel.app","http://localhost:3000"]
```
Replace with your actual Vercel URL.

---

### Backend shows error on Railway but works locally

Check Railway logs:
1. Railway dashboard → your service → **Deployments** → click latest deployment → **View Logs**
2. Look for red error lines
3. Most common: missing environment variable → add it in the Variables tab

---

### "vercel: command not found"

```powershell
# Use npx instead (always works without global install)
npx vercel --version
```

---

### Frontend build fails on Vercel

```powershell
# Test the build locally first
cd D:\EduSentinel\frontend
npm run build
```

Fix any errors shown, then redeploy.

---

### Virtual environment not activating (backend)

If `.\venv\Scripts\Activate` gives a permissions error in PowerShell:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Then try again.

---

## Quick Reference Card

### Local Development

```
Terminal 1 (backend):   cd D:\EduSentinel\backend  →  .\venv\Scripts\Activate  →  uvicorn main:app --reload
Terminal 2 (frontend):  cd D:\EduSentinel\frontend  →  npm run dev
Browser:                http://localhost:3000
```

### Push Code Changes

```
cd D:\EduSentinel  →  git add .  →  git commit -m "msg"  →  git push origin main
```

### Redeploy Frontend

```
cd D:\EduSentinel\frontend
npx vercel --prod --yes --build-env NEXT_PUBLIC_API_URL=https://edusentinel-backend-production.up.railway.app --env NEXT_PUBLIC_API_URL=https://edusentinel-backend-production.up.railway.app
```

### Live URLs

```
Frontend:  https://frontend-two-cyan-53.vercel.app
Backend:   https://edusentinel-backend-production.up.railway.app
```
