# EduSentinel

**Learning Analytics-Based Student Performance Monitoring System**

EduSentinel is a production-grade full-stack application that ingests academic data, trains ML models to predict at-risk students, and provides interactive dashboards for faculty and administrators.

---

## Architecture

```
┌─────────────┐    ┌─────────────┐    ┌──────────────┐    ┌──────────────┐
│  Next.js    │───▶│  FastAPI    │───▶│  ML Service  │    │  PostgreSQL  │
│  Frontend   │    │  Backend    │    │  (FastAPI)   │    │  Database    │
│  :3000      │    │  :8000      │    │  :8001       │    │  :5432       │
└─────────────┘    └──────┬──────┘    └──────────────┘    └──────────────┘
                          │                                        ▲
                          └────────────────────────────────────────┘
                          │
                    ┌─────▼──────┐
                    │   Redis    │
                    │  :6379     │
                    │ (Celery)   │
                    └────────────┘
```

---

## Tech Stack

| Layer       | Technology                                        |
|-------------|---------------------------------------------------|
| Frontend    | Next.js 14, TypeScript, Tailwind CSS, Recharts    |
| Backend     | FastAPI, SQLAlchemy (async), Alembic, Celery      |
| ML Service  | Scikit-learn, XGBoost, SHAP, FastAPI              |
| Database    | PostgreSQL 15                                     |
| Cache/Queue | Redis 7                                           |
| Deployment  | Docker, Docker Compose, Nginx                     |

---

## Features

- **Student data ingestion** — REST APIs for attendance, internal marks, assignments, and LMS activity (single + CSV bulk upload)
- **ML risk prediction** — Trains 4 models (Logistic Regression, Random Forest, Gradient Boosting, XGBoost), selects best by ROC-AUC, produces SHAP explanations
- **Interactive dashboards** — Admin overview, department analytics, individual student deep-dives, cohort insights
- **Role-based access control** — Admin (full access) and Faculty (scoped to assigned students) with JWT authentication
- **Automated alerts** — High-risk predictions trigger alerts; Celery Beat runs weekly prediction refresh
- **Visualizations** — 8 Recharts components (scatter, donut, area, bar, composed, trend)

---

## Project Structure

```
EduSentinel/
├── backend/                    # FastAPI application
│   ├── app/
│   │   ├── api/v1/             # Routers: auth, students, academic, attendance,
│   │   │                       #          assignments, lms_activity, predictions,
│   │   │                       #          analytics, faculty
│   │   ├── models/             # SQLAlchemy ORM models
│   │   ├── schemas/            # Pydantic v2 schemas
│   │   ├── services/           # Business logic
│   │   ├── core/               # Security, logging, exceptions
│   │   ├── middleware/         # Request audit logging
│   │   └── workers/            # Celery tasks (prediction, alerts)
│   ├── alembic/                # Database migrations
│   ├── tests/                  # Pytest integration + unit tests
│   └── main.py
│
├── frontend/                   # Next.js application
│   └── src/
│       ├── app/
│       │   ├── auth/login/     # Login page
│       │   └── dashboard/
│       │       ├── admin/      # Overview, Students, Courses, Users,
│       │       │               # Analytics, ML Config
│       │       ├── faculty/    # My Students, Alerts, Upload, Reports
│       │       ├── analytics/  # Student list + individual detail pages
│       │       ├── insights/   # Cohort analytics with 5 chart types
│       │       ├── alerts/     # Role-aware alert management
│       │       └── students/   # Role-aware redirect
│       ├── components/
│       │   ├── charts/         # 8 Recharts components
│       │   ├── dashboard/      # StatCard, RiskBadge
│       │   ├── layout/         # Sidebar, TopBar
│       │   └── ui/             # EmptyState, LoadingSpinner
│       ├── hooks/              # useStudents, useAnalytics, usePredictions
│       ├── lib/                # Axios instance with JWT interceptors
│       ├── store/              # Zustand auth store
│       └── types/              # Shared TypeScript types
│
├── ml_service/                 # Standalone ML microservice
│   └── app/
│       ├── api/                # /predict/single, /predict/batch, /train
│       ├── models/             # LR, RF, GB, XGBoost wrappers
│       ├── pipeline/           # Data loader, feature engineering,
│       │                       # preprocessor, trainer, predictor, evaluator
│       └── registry/           # Model artifact storage
│
├── data/
│   ├── generate_dataset.py     # Synthetic training data generator
│   └── training_data.csv       # 2000-row dataset (20% HIGH, 25% MEDIUM, 55% LOW)
│
├── infra/
│   ├── nginx/                  # nginx.conf (dev) + nginx.prod.conf (TLS)
│   ├── docker/postgres/        # init.sql
│   └── k8s/                    # (Kubernetes manifests — add as needed)
│
├── docker-compose.yml          # Local development
├── docker-compose.prod.yml     # Production overrides
├── Makefile                    # Common dev/ops commands
└── .env.example                # Environment variable template
```

---

## Quick Start (Local Development)

### Prerequisites

- Docker Desktop ≥ 24 (with Compose v2)
- Node.js ≥ 18 (only if running frontend outside Docker)
- Python 3.11+ (only if running backend outside Docker)

### 1. Clone and configure

```bash
git clone <repo-url> EduSentinel
cd EduSentinel
cp .env.example .env
# Edit .env — minimum: set SECRET_KEY to a random 32-char string
```

### 2. Start all services

```bash
make dev-up
# or: docker compose up --build -d
```

Services start at:
| Service      | URL                            |
|--------------|-------------------------------|
| Frontend     | http://localhost:3001          |
| Backend API  | http://localhost:8000/docs     |
| ML Service   | http://localhost:8001/docs     |
| PostgreSQL   | localhost:5432                 |
| Redis        | localhost:6379                 |
| Grafana      | http://localhost:3000 (external) |

### 3. Seed the database

```bash
docker compose exec backend python -m app.utils.seeder
```

Default credentials:
| Role    | Email                        | Password    |
|---------|------------------------------|-------------|
| Admin   | admin@edusentinel.dev        | Admin@123   |
| Faculty | faculty@edusentinel.dev      | Faculty@123 |

### 4. Train the ML model

```bash
docker compose exec ml_service python -m app.pipeline.trainer
# Or via the Admin dashboard → ML Config → Start Training
```

---

## Environment Variables

Copy `.env.example` to `.env` and configure:

```env
# App
APP_ENV=development          # development | production
SECRET_KEY=change-me-32chars
APP_VERSION=1.0.0

# Database
DB_HOST=postgres
DB_PORT=5432
DB_NAME=edusentinel
DB_USER=edu_user
DB_PASSWORD=edu_password

# Redis / Celery
REDIS_URL=redis://redis:6379/0
REDIS_PASSWORD=               # Required in production

# ML Service
ML_SERVICE_URL=http://ml_service:8001
ML_REQUEST_TIMEOUT=120

# CORS
CORS_ORIGINS=["http://localhost:3000"]

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

---

## API Reference

The FastAPI backend auto-generates interactive docs at `/docs` (development only).

### Authentication

| Method | Endpoint                  | Description                          |
|--------|---------------------------|--------------------------------------|
| POST   | `/api/v1/auth/register`   | Register user (Admin only in prod)   |
| POST   | `/api/v1/auth/login`      | Login → access + refresh tokens      |
| POST   | `/api/v1/auth/refresh`    | Refresh token pair                   |
| GET    | `/api/v1/auth/me`         | Current user profile                 |
| POST   | `/api/v1/auth/change-password` | Change own password             |

### Students

| Method | Endpoint                         | ADMIN | FACULTY       |
|--------|----------------------------------|-------|---------------|
| GET    | `/api/v1/students`               | All   | Scoped        |
| POST   | `/api/v1/students`               | Yes   | No            |
| GET    | `/api/v1/students/{id}`          | Yes   | Scoped        |
| PUT    | `/api/v1/students/{id}`          | Yes   | No            |
| DELETE | `/api/v1/students/{id}`          | Yes   | No            |
| GET    | `/api/v1/students/{id}/performance` | Yes | Scoped     |

### Predictions & Alerts

| Method | Endpoint                                | Description                      |
|--------|-----------------------------------------|----------------------------------|
| GET    | `/api/v1/predictions`                   | List predictions (scoped)        |
| GET    | `/api/v1/predictions/summary`           | Risk count summary               |
| POST   | `/api/v1/predictions/run`               | Trigger batch prediction (Admin) |
| GET    | `/api/v1/predictions/alerts`            | List alerts (scoped)             |
| PATCH  | `/api/v1/predictions/alerts/{id}/resolve` | Resolve an alert               |

### Data Ingestion (Admin or Faculty)

All endpoints support single-record (`POST /`) and bulk (`POST /bulk`, max 500 records):

- `/api/v1/attendance`
- `/api/v1/academic`
- `/api/v1/assignments`
- `/api/v1/lms-activity`

### Analytics (Admin only)

- `GET /api/v1/analytics/cohort-overview`
- `GET /api/v1/analytics/department-stats`

---

## ML Pipeline

The ML service trains 4 algorithms and selects the best by ROC-AUC with a minimum recall constraint of 85%.

### Features

| Feature                     | Description                              |
|-----------------------------|------------------------------------------|
| `attendance_pct`            | Attendance percentage                    |
| `ia1_score`, `ia2_score`, `ia3_score` | Internal assessment scores     |
| `assignment_avg_score`      | Mean assignment score                    |
| `assignment_completion_rate`| Fraction of assignments submitted        |
| `lms_login_frequency`       | Average logins per week                  |
| `lms_time_spent_hours`      | Hours spent on LMS per week              |
| `lms_content_views`         | Content views per week                   |
| `previous_gpa`              | Previous semester GPA                    |
| `avg_ia_score` (engineered) | Mean of IA1–IA3                          |
| `ia_trend` (engineered)     | Linear slope across IA scores            |
| `combined_risk_score` (engineered) | Weighted composite risk indicator |

### Quality Gates

A trained model is accepted into production only if:
- ROC-AUC ≥ 0.80
- Recall ≥ 0.75 (at tuned threshold)
- F1 ≥ 0.70

### Training

```bash
# Synthetic data (default)
python -m app.pipeline.trainer

# From CSV
python -m app.pipeline.trainer --source csv --path /data/training_data.csv

# With hyperparameter tuning
python -m app.pipeline.trainer --tune --n 5000
```

---

## RBAC Summary

| Operation                       | ADMIN | FACULTY     |
|---------------------------------|-------|-------------|
| View all students               | Yes   | Own students|
| Create / update / delete student| Yes   | No          |
| View analytics                  | Yes   | No          |
| View predictions / alerts       | Yes   | Own students|
| Trigger prediction run          | Yes   | No          |
| Upload attendance / marks       | Yes   | Yes         |
| Manage faculty accounts         | Yes   | No          |
| View own profile (`/faculty/me`)| No    | Yes         |

---

## Running Tests

```bash
# Backend unit + integration tests
cd backend
pytest -v

# ML service tests
cd ml_service
pytest -v

# Frontend type check
cd frontend
npm run type-check
```

---

## Production Deployment

```bash
# 1. Set all required env vars (especially REDIS_PASSWORD, SECRET_KEY)
cp .env.example .env
vim .env

# 2. Generate SSL certificates (or copy Let's Encrypt certs to infra/nginx/ssl/)
make ssl-self-signed

# 3. Build and start production stack
make prod-up

# 4. Run database migrations
make prod-migrate
```

See [DOCKER.md](DOCKER.md) for full production deployment guide including Let's Encrypt, environment variables reference, and troubleshooting.

---

## Data Upload Format

Download templates from the Upload page or use these column specs:

**Attendance CSV:**
```
student_id,date,status
1,2024-01-15,PRESENT
2,2024-01-15,ABSENT
```

**Internal Marks CSV:**
```
student_id,course_id,assessment_type,score,max_score,exam_date
1,1,IA1,38,50,2024-01-20
```

**Assignments CSV:**
```
student_id,course_id,title,score,max_score,is_submitted,is_late,due_date
1,1,Lab 1,85,100,true,false,2024-02-01
```

**LMS Activity CSV:**
```
student_id,date,login_count,content_views,time_spent_minutes,forum_posts
1,2024-01-15,3,12,45,1
```

---

## Makefile Commands

```bash
make dev-up          # Start all services (development)
make dev-down        # Stop all services
make dev-build       # Rebuild all images
make prod-up         # Start production stack
make prod-down       # Stop production stack
make prod-migrate    # Run Alembic migrations in production
make ssl-self-signed # Generate self-signed SSL certificate
make logs            # Tail all service logs
make ps              # Show running containers
make shell-db        # psql shell into the database
make clean           # Remove containers, volumes, and images
make help            # List all targets
```

---

## License

MIT
