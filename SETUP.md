# EduSentinel — Local Development Setup Guide

Complete step-by-step instructions for running the project in VS Code on Windows.

---

## Prerequisites

| Tool | Version | Check |
|------|---------|-------|
| Python | 3.10+ | `python --version` |
| Node.js | 18+ | `node --version` |
| npm | 9+ | `npm --version` |
| Git | any | `git --version` |

> **Note:** PostgreSQL is optional for local dev — the project auto-falls back to SQLite.

---

## 1. Clone & Open in VS Code

```bash
git clone <your-repo-url> EduSentinel
cd EduSentinel
code .
```

---

## 2. Backend Setup

Open a new terminal in VS Code (`Ctrl+\``) and run:

```bash
cd backend

# Create virtual environment
python -m venv .venv

# Activate (Windows CMD / PowerShell)
.venv\Scripts\activate

# Activate (Git Bash / WSL)
source .venv/Scripts/activate

# Install all dependencies
pip install -r requirements.txt

# If you get space errors on C: drive, redirect TEMP first:
# set TEMP=D:\tmp && set TMP=D:\tmp
# pip install -r requirements.txt
```

---

## 3. Configure Environment Variables

Copy the example file and edit it:

```bash
# Windows
copy .env.example .env

# Or create manually — minimum required for SQLite dev:
```

Minimum `.env` for local SQLite development:

```env
APP_ENV=development
DEBUG=true
DATABASE_URL=sqlite:///./edusentinel_dev.db
REDIS_URL=redis://localhost:6379/0
JWT_SECRET_KEY=local-dev-secret-key-change-in-production
ML_SERVICE_URL=http://localhost:8001
CORS_ORIGINS=["http://localhost:3001","http://localhost:3000"]

# Optional: enable email notifications
NOTIFICATION_ENABLED=false
# SMTP_HOST=smtp.gmail.com
# SMTP_PORT=587
# SMTP_USER=your@gmail.com
# SMTP_PASSWORD=your-app-password
```

---

## 4. Database Setup

### Option A: SQLite (Recommended for local dev — zero config)

The database is created automatically on first run. No setup needed.

### Option B: PostgreSQL

Install PostgreSQL and create a database:

```sql
CREATE DATABASE edusentinel;
CREATE USER edu_user WITH PASSWORD 'password';
GRANT ALL PRIVILEGES ON DATABASE edusentinel TO edu_user;
```

Update `.env`:
```env
DATABASE_URL=postgresql://edu_user:password@localhost:5432/edusentinel
```

---

## 5. Run Backend Server

```bash
cd backend
source .venv/Scripts/activate   # activate venv if not already

uvicorn main:app --reload --host 127.0.0.1 --port 8080
```

On first start, the DB tables are created automatically.

**Seed demo data:**

```bash
python -m app.utils.seeder
```

This creates:
- Admin: `admin@edusentinel.dev` / `Admin@123`
- Faculty: `faculty@edusentinel.dev` / `Faculty@123`
- 20 sample students

**Backend URLs:**
- API:  http://localhost:8080/api/v1
- Docs: http://localhost:8080/docs
- Health: http://localhost:8080/health/live

---

## 6. Frontend Setup

Open a second terminal:

```bash
cd frontend

# Install dependencies
npm install

# Create env file
echo "NEXT_PUBLIC_API_URL=http://localhost:8080/api/v1" > .env.local

# Start dev server (port 3001 — 3000 is reserved for Grafana)
npm run dev -- --port 3001
```

**Frontend URL:** http://localhost:3001

---

## 7. ML Service Setup (Optional)

The ML service is optional — the backend falls back to demo data when it is offline.

```bash
cd ml_service

python -m venv .venv
source .venv/Scripts/activate

pip install -r requirements.txt

# Start ML service
uvicorn main:app --host 127.0.0.1 --port 8001 --reload
```

**ML Service URL:** http://localhost:8001

---

## 8. Run ML Training Pipeline

```bash
cd ml_service
source .venv/Scripts/activate

# Train with synthetic data (default, 1000 samples)
python -m app.pipeline.trainer

# Train with more samples
python -m app.pipeline.trainer --source synthetic --samples 2000

# Train from CSV
python -m app.pipeline.trainer --source csv --path ../data/students.csv

# With hyperparameter tuning (slower)
python -m app.pipeline.trainer --tune
```

---

## 9. Run Student Data Generator

**Via API (recommended):**

```bash
curl -X POST http://localhost:8080/api/v1/students/generate \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"num_students": 500, "semester": "2025-ODD"}'
```

**Via Python script:**

```bash
cd backend
source .venv/Scripts/activate

python -c "
import asyncio
from app.database import AsyncSessionLocal
from app.utils.data_generator import generate_and_insert_students

async def run():
    async with AsyncSessionLocal() as db:
        result = await generate_and_insert_students(db, 500, '2025-ODD')
        print(result)

asyncio.run(run())
"
```

---

## 10. Access the Application

| Service | URL | Credentials |
|---------|-----|-------------|
| Frontend (Login) | http://localhost:3001/auth/login | - |
| Admin Dashboard | http://localhost:3001/dashboard/admin | admin@edusentinel.dev / Admin@123 |
| Faculty Dashboard | http://localhost:3001/dashboard/faculty | faculty@edusentinel.dev / Faculty@123 |
| Backend API Docs | http://localhost:8080/docs | JWT token required |
| ML Service Docs | http://localhost:8001/docs | No auth |

---

## 11. New Features — Quick Access

| Feature | URL |
|---------|-----|
| Model Evaluation | http://localhost:3001/dashboard/admin/model-evaluation |
| AI Explainability (SHAP) | http://localhost:3001/dashboard/admin/ai-explainability |
| Generate Student Data | http://localhost:3001/dashboard/admin/generate-data |
| Export CSV | http://localhost:3001/dashboard/faculty/export |

---

## 12. All API Endpoints

### Authentication
```
POST /api/v1/auth/login
POST /api/v1/auth/refresh
GET  /api/v1/auth/me
```

### Students
```
GET    /api/v1/students
POST   /api/v1/students
GET    /api/v1/students/{id}
PUT    /api/v1/students/{id}
DELETE /api/v1/students/{id}
POST   /api/v1/students/generate        ← NEW (Feature 2)
```

### ML & Explainability
```
GET  /api/v1/ml/model-comparison        ← NEW (Feature 1)
GET  /api/v1/ml/shap/global             ← NEW (Feature 5)
POST /api/v1/ml/shap/student            ← NEW (Feature 5)
GET  /api/v1/ml/training-status
POST /api/v1/ml/train-all
```

### Export
```
GET  /api/v1/export/student-data        ← NEW (Feature 3) — returns CSV
```

### Predictions
```
GET  /api/v1/predictions
POST /api/v1/predictions/run
GET  /api/v1/predictions/summary
POST /api/v1/predictions/predict-risk
```

### Analytics
```
GET  /api/v1/analytics/cohort-overview
GET  /api/v1/analytics/departments
```

---

## 13. VS Code Recommended Extensions

Install these for the best development experience:

```json
{
  "recommendations": [
    "ms-python.python",
    "ms-python.vscode-pylance",
    "bradlc.vscode-tailwindcss",
    "esbenp.prettier-vscode",
    "ms-vscode.vscode-typescript-next",
    "dbaeumer.vscode-eslint",
    "humao.rest-client"
  ]
}
```

---

## 14. Enable Email Notifications

To send risk alert emails when a student is predicted HIGH risk:

1. Get an app password from your email provider (e.g., Gmail → Security → App Passwords)
2. Update `.env`:

```env
NOTIFICATION_ENABLED=true
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your@gmail.com
SMTP_PASSWORD=your-16-char-app-password
SMTP_FROM_EMAIL=noreply@edusentinel.dev
```

3. Emails are sent automatically when a HIGH risk prediction is created via `/api/v1/predictions/run`.

---

## 15. Running Tests

```bash
cd backend
source .venv/Scripts/activate
pytest tests/ -v

cd ../ml_service
source .venv/Scripts/activate
pytest tests/ -v
```

---

## 16. Project Structure

```
EduSentinel/
├── backend/                    FastAPI + SQLAlchemy
│   ├── app/
│   │   ├── api/v1/            All API routers (47 endpoints)
│   │   ├── models/            SQLAlchemy ORM models (11 tables)
│   │   ├── schemas/           Pydantic request/response schemas
│   │   ├── services/          Business logic
│   │   │   └── notification_service.py  ← NEW email system
│   │   └── utils/
│   │       └── data_generator.py        ← NEW synthetic data
│   ├── main.py                FastAPI app entry point
│   └── requirements.txt
│
├── frontend/                   Next.js 14 + TypeScript
│   └── src/app/dashboard/
│       ├── admin/
│       │   ├── model-evaluation/        ← NEW Feature 1
│       │   ├── ai-explainability/       ← NEW Feature 5
│       │   └── generate-data/          ← NEW Feature 2
│       └── faculty/
│           └── export/                 ← NEW Feature 3
│
├── ml_service/                 FastAPI ML microservice
│   └── app/pipeline/           LR + RF + XGBoost training
│
├── SETUP.md                    ← This file
└── docker-compose.yml          Full stack (Docker)
```

---

## Common Issues

| Problem | Solution |
|---------|----------|
| `pip install` fails (no space) | `set TEMP=D:\tmp && pip install ...` |
| Port 8000 already in use | Use `--port 8080` |
| Port 3000 already in use | Use `--port 3001` |
| `ModuleNotFoundError: faker` | `pip install faker` |
| ML service 404 | Normal — backend uses demo data when ML service is offline |
| Login returns 500 | Check backend is running on port 8080 and `NEXT_PUBLIC_API_URL` is set correctly |
