# EduSentinel — Deployment & Local Run Guide

---

## Part A — Run Locally in VS Code

### Prerequisites
- Python 3.11+ installed
- Node.js 18+ installed
- Git installed

### 1. Clone & open in VS Code
```bash
git clone https://github.com/YOUR_USERNAME/edusentinel.git
cd EduSentinel
code .
```

### 2. Backend setup
Open a new VS Code terminal (`Ctrl+`` `).

```bash
# Enter backend directory
cd backend

# Create virtual environment (use D: drive if C: is full)
python -m venv .venv

# Activate (Windows CMD / PowerShell)
.venv\Scripts\activate

# Activate (Git Bash / WSL)
source .venv/Scripts/activate

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
copy .env.example .env      # Windows CMD
# or: cp .env.example .env   # Git Bash

# Edit .env — change DATABASE_URL for local SQLite:
#   DATABASE_URL=sqlite:///./edusentinel_dev.db
#   JWT_SECRET_KEY=any-random-string
#   CORS_ORIGINS=["http://localhost:3001"]

# Seed the database with admin + faculty + 20 students + courses + enrollments
python -m app.utils.seeder

# Start the backend server
uvicorn main:app --reload --port 8000
```

Backend is live at: **http://localhost:8000**
API Docs at: **http://localhost:8000/docs**

---

### 3. Frontend setup
Open a **second VS Code terminal**.

```bash
cd frontend

# Install Node dependencies
npm install

# Create .env.local
echo "NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1" > .env.local

# Start dev server (port 3001 because 3000 may be used by Grafana)
npm run dev -- --port 3001
```

Frontend is live at: **http://localhost:3001**

---

### 4. ML Service (optional — enables live predictions)
Open a **third VS Code terminal**.

```bash
cd ml_service
python -m venv .venv
source .venv/Scripts/activate    # or .venv\Scripts\activate on Windows

pip install -r requirements.txt
uvicorn main:app --reload --port 8001
```

---

### 5. Generate synthetic student data
With the backend running:
```bash
# Via API (in any terminal)
curl -X POST http://localhost:8000/api/v1/students/generate \
  -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"num_students": 500}'
```
Or run the standalone script:
```bash
cd backend
python app/utils/data_generator.py
```

---

### 6. Fix faculty dashboard (if students not showing)
Run once to create enrollment records for all students:
```bash
curl -X POST http://localhost:8000/api/v1/students/enroll-all \
  -H "Authorization: Bearer <ADMIN_TOKEN>"
```

---

### 7. Default credentials
| Role | Email | Password |
|------|-------|----------|
| Admin | admin@edusentinel.dev | Admin@123 |
| Faculty | faculty@edusentinel.dev | Faculty@123 |

---

### 8. Access URLs
| Service | URL |
|---------|-----|
| Frontend | http://localhost:3001 |
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| System Health | http://localhost:8000/system-health |

---

## Part B — Run with Docker Compose (local)

```bash
# Copy env file
cp .env.example .env
# Edit .env — fill in DB_PASSWORD, JWT_SECRET_KEY, REDIS_PASSWORD at minimum

# Build and start all services
docker compose up --build

# Seed the database (first time only)
docker compose exec backend python -m app.utils.seeder

# Enroll all students (first time only)
docker compose exec backend python -c "
import asyncio
from app.database import AsyncSessionLocal
from app.api.v1.data_generator import *
# or use curl against localhost:8000
"
```

Access at: http://localhost (nginx proxy) or http://localhost:3001 (frontend direct)

---

## Part C — Deploy to Render.com (Recommended)

Render offers a generous free tier for web services and managed PostgreSQL.

### Step 1: Push to GitHub
```bash
cd EduSentinel
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/edusentinel.git
git push -u origin main
```

### Step 2: Create PostgreSQL database on Render
1. Go to https://dashboard.render.com → **New → PostgreSQL**
2. Name: `edusentinel-db`
3. Plan: Free (or Starter for production)
4. Click **Create Database**
5. Copy the **Internal Database URL** (format: `postgresql://user:pass@host/db`)

### Step 3: Deploy the Backend
1. **New → Web Service** → Connect your GitHub repo
2. **Root Directory**: `backend`
3. **Runtime**: Python 3
4. **Build Command**:
   ```
   pip install -r requirements.txt
   ```
5. **Start Command**:
   ```
   uvicorn main:app --host 0.0.0.0 --port $PORT
   ```
6. **Environment Variables** (add all):
   ```
   APP_ENV=production
   DEBUG=false
   DATABASE_URL=<paste Internal Database URL from step 2, change postgresql:// to postgresql+asyncpg://>
   JWT_SECRET_KEY=<generate: python -c "import secrets; print(secrets.token_hex(32))">
   CORS_ORIGINS=["https://your-frontend.onrender.com"]
   ML_SERVICE_URL=https://your-ml-service.onrender.com
   ```
7. Click **Create Web Service**

8. After first deploy, open Render **Shell** and seed the DB:
   ```bash
   python -m app.utils.seeder
   python -c "
   import asyncio
   # Use curl or the admin enroll-all endpoint
   "
   ```

### Step 4: Deploy the ML Service
1. **New → Web Service** → Same repo
2. **Root Directory**: `ml_service`
3. **Build Command**: `pip install -r requirements.txt`
4. **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Add `DATABASE_URL` env var (same as backend)

### Step 5: Deploy the Frontend
1. **New → Static Site** or **Web Service** → Same repo
2. **Root Directory**: `frontend`
3. **Build Command**: `npm install && npm run build`
4. **Start Command**: `npm start`
5. **Environment Variables**:
   ```
   NEXT_PUBLIC_API_URL=https://your-backend.onrender.com/api/v1
   NODE_ENV=production
   ```

### Step 6: Update CORS on backend
Set `CORS_ORIGINS=["https://your-frontend.onrender.com"]` in backend env vars.

### Result
| Service | URL |
|---------|-----|
| Frontend | https://edusentinel.onrender.com |
| Backend | https://edusentinel-api.onrender.com |
| API Docs | https://edusentinel-api.onrender.com/docs (disabled in prod) |
| Health | https://edusentinel-api.onrender.com/system-health |

---

## Part D — Deploy to Railway.app

### Step 1: Install Railway CLI
```bash
npm install -g @railway/cli
railway login
```

### Step 2: Initialize project
```bash
cd EduSentinel
railway init
```

### Step 3: Add PostgreSQL
```bash
railway add postgresql
# Railway auto-sets DATABASE_URL in your environment
```

### Step 4: Deploy backend
```bash
cd backend
railway up
```
Set env vars in Railway dashboard (same as Render list above).

### Step 5: Deploy frontend
```bash
cd ../frontend
railway up
```
Set `NEXT_PUBLIC_API_URL=https://your-backend.railway.app/api/v1`

Railway auto-generates public URLs for each service.

---

## Part E — Deploy to AWS EC2

### Step 1: Launch EC2 instance
- AMI: Ubuntu 22.04 LTS
- Type: t3.medium (2 vCPU, 4 GB RAM) minimum
- Security Groups: Allow 22 (SSH), 80 (HTTP), 443 (HTTPS), 8000 (API dev)

### Step 2: SSH in and install dependencies
```bash
ssh -i your-key.pem ubuntu@YOUR_EC2_IP

# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker ubuntu
newgrp docker

# Install Docker Compose
sudo apt install docker-compose-plugin -y

# Install Git
sudo apt install git -y
```

### Step 3: Clone and configure
```bash
git clone https://github.com/YOUR_USERNAME/edusentinel.git
cd edusentinel
cp .env.example .env
nano .env   # fill in all required values
```

### Step 4: Run with Docker Compose
```bash
# Production mode
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

# Seed database (first time only)
docker compose exec backend python -m app.utils.seeder
docker compose exec backend curl -X POST http://localhost:8000/api/v1/students/enroll-all \
  -H "Authorization: Bearer $(python -c "...")"
```

### Step 5: Set up Nginx + SSL (Let's Encrypt)
```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d yourdomain.com
sudo certbot renew --dry-run   # test auto-renewal
```

Update `infra/nginx/nginx.prod.conf` with your domain and restart nginx.

### Step 6: Configure DNS
In your domain registrar, add:
- A record: `@` → `YOUR_EC2_IP`
- A record: `api` → `YOUR_EC2_IP`
- CNAME: `www` → `@`

---

## Part F — Environment Variables Quick Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | ✅ | PostgreSQL connection string (use `+asyncpg` driver) |
| `JWT_SECRET_KEY` | ✅ | Random 32-byte hex string |
| `REDIS_URL` | ✅ | Redis connection (include password in prod) |
| `CORS_ORIGINS` | ✅ | JSON array of allowed frontend URLs |
| `APP_ENV` | ✅ | `development` or `production` |
| `ML_SERVICE_URL` | ✅ | URL of the ML microservice |
| `NEXT_PUBLIC_API_URL` | ✅ | Public URL of the backend API |
| `SMTP_HOST` / `SMTP_USER` | ⚠️ | Required only if email alerts enabled |
| `NOTIFICATION_ENABLED` | ⚠️ | Set `true` to send emails |
| `REDIS_PASSWORD` | ⚠️ | Required in production |
| `DEBUG` | ❌ | Default `false` in production |

---

## Part G — Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| Faculty sees 0 students | Missing enrollment records | `POST /api/v1/students/enroll-all` |
| `ModuleNotFoundError: pandas` | Incomplete pip install | `pip install pandas numpy` |
| `bcrypt` / `passlib` error | Version mismatch | security.py already uses `bcrypt` directly |
| Frontend 404 on `/` | Missing root page | Root `page.tsx` redirects to `/auth/login` |
| `EADDRINUSE :3001` | Old process still running | `npx kill-port 3001` |
| Backend CORS error | Frontend URL not in CORS_ORIGINS | Update `.env` and restart backend |
| Docker build fails (C: drive full) | No disk space | Move project to D: drive, set `TEMP=D:/tmp` |
