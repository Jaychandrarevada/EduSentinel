# EduSentinel — Complete Project Documentation

> **What is this project?**
> EduSentinel is a Learning Analytics-Based Student Performance Monitoring System.
> It uses Machine Learning to predict which students are at risk of failing,
> and gives faculty and administrators a dashboard to monitor, intervene, and act.

---

## Table of Contents

1. [System Architecture — Big Picture](#1-system-architecture--big-picture)
2. [Project Folder Structure](#2-project-folder-structure)
3. [Backend — How It Works](#3-backend--how-it-works)
4. [Database — All Tables Explained](#4-database--all-tables-explained)
5. [How Data Flows Through the System](#5-how-data-flows-through-the-system)
6. [ML Pipeline — All 4 Algorithms Explained](#6-ml-pipeline--all-4-algorithms-explained)
7. [SHAP Explainability — Why This Student is at Risk](#7-shap-explainability--why-this-student-is-at-risk)
8. [Frontend — Pages and Components](#8-frontend--pages-and-components)
9. [Authentication and Role-Based Access](#9-authentication-and-role-based-access)
10. [API Reference — Every Endpoint](#10-api-reference--every-endpoint)
11. [Email Alert System](#11-email-alert-system)
12. [Background Jobs — Celery Workers](#12-background-jobs--celery-workers)
13. [Docker — All Services Together](#13-docker--all-services-together)
14. [Environment Variables — What Each One Does](#14-environment-variables--what-each-one-does)
15. [How the Demo Data is Generated](#15-how-the-demo-data-is-generated)

---

## 1. System Architecture — Big Picture

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER'S BROWSER                           │
│                    (Next.js on Vercel)                          │
│   Login → Dashboard → Charts → Upload CSV → Export → Alerts    │
└────────────────────────┬────────────────────────────────────────┘
                         │ HTTPS API calls (/api/v1/...)
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                   BACKEND (FastAPI on Railway)                  │
│                                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐   │
│  │   Auth   │  │ Students │  │Analytics │  │  Predictions │   │
│  │  Router  │  │  Router  │  │  Router  │  │    Router    │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────┬───────┘   │
│                                                    │           │
│  ┌──────────────────────────────────────────────── │ ───────┐  │
│  │              Services Layer                     │       │  │
│  │  auth_service  student_service  analytics_service│       │  │
│  └──────────────────────────────────────────────── │ ───────┘  │
│                                                    │           │
└─────────────────┬──────────────────────────────────┼───────────┘
                  │                                  │ HTTP call
                  ▼                                  ▼
┌─────────────────────────┐         ┌─────────────────────────────┐
│  PostgreSQL Database    │         │   ML Microservice (FastAPI) │
│  (Railway / local)      │         │   (port 8001)               │
│                         │         │                             │
│  students               │         │  Trains 4 models:           │
│  users                  │         │  - Logistic Regression      │
│  courses                │         │  - Random Forest            │
│  enrollments            │         │  - Gradient Boosting        │
│  attendance_records     │         │  - XGBoost                  │
│  academic_records       │         │                             │
│  assignments            │         │  Selects best by ROC-AUC    │
│  lms_activity           │         │  Returns risk score + SHAP  │
│  predictions            │         └─────────────────────────────┘
│  alerts                 │
└─────────────────────────┘
                  ▲
                  │ async tasks
┌─────────────────────────┐
│   Celery Workers        │
│   (Redis as broker)     │
│                         │
│  - Batch predictions    │
│  - Email alerts         │
└─────────────────────────┘
```

**In plain English:**
- The user opens the website (hosted on Vercel)
- They log in → the frontend calls the backend API on Railway
- The backend reads/writes data to PostgreSQL
- When predictions are needed, the backend calls the ML service
- The ML service runs the model and returns a risk score
- Background jobs (Celery) handle slow tasks like batch emails

---

## 2. Project Folder Structure

```
EduSentinel/
│
├── backend/                    ← Python FastAPI server
│   ├── main.py                 ← Entry point: starts the server
│   ├── railway.json            ← Railway deployment config
│   ├── Dockerfile              ← Docker container definition
│   ├── requirements.txt        ← All Python packages needed
│   ├── .env                    ← Local environment variables (not committed)
│   ├── .env.template           ← Template showing all env vars needed
│   │
│   └── app/
│       ├── config.py           ← Reads all env vars (DATABASE_URL, JWT_SECRET, etc.)
│       ├── database.py         ← Sets up database connection
│       ├── dependencies.py     ← Shared logic used by all routes (auth checks, DB session)
│       │
│       ├── core/
│       │   ├── security.py     ← Password hashing, JWT token create/verify
│       │   ├── exceptions.py   ← Custom error classes (NotFound, Unauthorized, etc.)
│       │   └── logging.py      ← Structured JSON logging setup
│       │
│       ├── models/             ← Database table definitions (SQLAlchemy ORM)
│       │   ├── user.py
│       │   ├── student.py
│       │   ├── course.py
│       │   ├── enrollment.py
│       │   ├── attendance.py
│       │   ├── academic_record.py
│       │   ├── assignment.py
│       │   ├── lms_activity.py
│       │   ├── prediction.py
│       │   └── alert.py
│       │
│       ├── schemas/            ← Request/Response data shapes (Pydantic)
│       │   ├── auth.py
│       │   ├── student.py
│       │   ├── prediction.py
│       │   ├── analytics.py
│       │   └── ...
│       │
│       ├── api/v1/             ← All HTTP route handlers
│       │   ├── router.py       ← Registers all routes together
│       │   ├── auth.py         ← Login, register, refresh token
│       │   ├── students.py     ← Student CRUD
│       │   ├── predictions.py  ← Get predictions, trigger ML run
│       │   ├── analytics.py    ← Dashboard stats
│       │   ├── faculty.py      ← Faculty-specific views
│       │   ├── alerts.py       ← Risk alerts, send emails
│       │   ├── upload.py       ← CSV file uploads
│       │   ├── export.py       ← CSV download
│       │   ├── ml.py           ← ML model info, SHAP values
│       │   ├── admin.py        ← Seed data, admin tools
│       │   └── ...
│       │
│       ├── services/           ← Business logic (called by routes)
│       │   ├── auth_service.py
│       │   ├── student_service.py
│       │   ├── prediction_service.py
│       │   ├── analytics_service.py
│       │   ├── notification_service.py
│       │   ├── data_ingestion_service.py
│       │   └── ...
│       │
│       ├── workers/            ← Background tasks (Celery)
│       │   ├── celery_app.py
│       │   ├── prediction_tasks.py
│       │   └── alert_tasks.py
│       │
│       └── middleware/
│           └── request_log.py  ← Logs every HTTP request
│
├── frontend/                   ← Next.js 14 React app
│   ├── vercel.json             ← Vercel deployment config
│   ├── next.config.js          ← Next.js settings
│   ├── tailwind.config.ts      ← CSS utility configuration
│   ├── package.json            ← Node.js packages
│   │
│   └── src/
│       ├── app/                ← Pages (Next.js App Router)
│       │   ├── layout.tsx      ← Root: wraps every page, sets up auth
│       │   ├── page.tsx        ← Root URL → redirects to login
│       │   ├── auth/
│       │   │   └── login/      ← Login page
│       │   └── dashboard/
│       │       ├── layout.tsx  ← Dashboard wrapper + sidebar
│       │       ├── admin/      ← Admin-only pages
│       │       └── faculty/    ← Faculty pages
│       │
│       ├── components/         ← Reusable UI pieces
│       │   ├── providers/
│       │   │   └── AuthProvider.tsx   ← Checks login on every page load
│       │   ├── layout/
│       │   │   ├── Sidebar.tsx        ← Left navigation menu
│       │   │   └── TopBar.tsx         ← Top header bar
│       │   ├── charts/                ← All chart components (Recharts)
│       │   ├── dashboard/
│       │   │   ├── RiskBadge.tsx      ← HIGH/MEDIUM/LOW badge
│       │   │   └── StatCard.tsx       ← KPI number card
│       │   └── ui/
│       │       ├── LoadingSpinner.tsx
│       │       └── EmptyState.tsx
│       │
│       ├── hooks/              ← Data fetching (custom React hooks)
│       │   ├── usePredictions.ts
│       │   ├── useStudents.ts
│       │   ├── useAnalytics.ts
│       │   └── useFacultyDashboard.ts
│       │
│       ├── store/
│       │   └── authStore.ts    ← Login state (Zustand)
│       │
│       ├── lib/
│       │   ├── api.ts          ← Axios HTTP client with auth token
│       │   └── utils.ts        ← Helper functions
│       │
│       └── types/
│           └── index.ts        ← TypeScript type definitions
│
├── ml_service/                 ← Separate ML Python service (port 8001)
│   ├── main.py                 ← FastAPI entry point for ML
│   └── app/
│       ├── models/             ← 4 ML algorithm implementations
│       │   ├── logistic_regression.py
│       │   ├── random_forest.py
│       │   ├── gradient_boosting.py
│       │   └── xgboost_model.py
│       ├── pipeline/           ← Data processing + training steps
│       │   ├── data_loader.py
│       │   ├── feature_engineering.py
│       │   ├── preprocessor.py
│       │   ├── trainer.py
│       │   ├── evaluator.py
│       │   └── predictor.py
│       ├── registry/
│       │   └── model_registry.py   ← Save/load trained models to disk
│       └── api/
│           ├── train.py            ← POST /train
│           └── predict.py          ← POST /predict
│
├── docker-compose.yml          ← Run everything locally with one command
├── render.yaml                 ← Render.com deployment blueprint
├── SETUP_AND_DEPLOYMENT.md     ← Local + deployment how-to guide
└── PROJECT_DOCUMENTATION.md   ← This file
```

---

## 3. Backend — How It Works

### Entry Point: `backend/main.py`

This is where everything starts when the server boots up.

```
Server starts
    ↓
setup_logging()          ← structured JSON logs
    ↓
lifespan() runs:
    ↓
  create DB tables       ← auto-creates all tables if they don't exist
    ↓
app = FastAPI(...)
    ↓
Add middleware:
  1. RequestLogMiddleware     ← logs every request
  2. SlowAPIMiddleware        ← rate limiting (200 req/min per IP)
  3. CORSMiddleware           ← allows frontend origin
    ↓
Register all routes under /api/v1
    ↓
Server ready on port 8000
```

### The 3-Layer Architecture

Every request goes through exactly 3 layers:

```
HTTP Request
    ↓
┌─────────────────────────────┐
│  LAYER 1: Route (api/v1/)   │  Validates request shape, checks auth,
│  e.g. predictions.py        │  calls the right service function
└──────────────┬──────────────┘
               ↓
┌─────────────────────────────┐
│  LAYER 2: Service           │  Contains the actual business logic.
│  e.g. prediction_service.py │  Calls database, calls ML service,
│                             │  computes results
└──────────────┬──────────────┘
               ↓
┌─────────────────────────────┐
│  LAYER 3: Database / ML     │  SQLAlchemy async queries to
│  PostgreSQL / ML service    │  PostgreSQL, or httpx call to
│                             │  ML microservice
└─────────────────────────────┘
               ↓
HTTP Response (JSON)
```

### `dependencies.py` — The Shared Toolkit

Every route uses this file. Key functions:

| Function | What it does |
|----------|-------------|
| `get_db()` | Opens a DB session, yields it, commits or rolls back after request |
| `get_current_user()` | Reads JWT token from `Authorization: Bearer ...` header, returns the User |
| `require_role(Role.ADMIN)` | Returns error if user is not the required role |
| `get_student_scope()` | Returns set of student IDs the current user can see. Admin → None (all). Faculty → only their enrolled students |
| `assert_student_access()` | Raises 403 if faculty tries to access a student not in their scope |

---

## 4. Database — All Tables Explained

### Table Relationships

```
users ──────────────── courses (faculty_id)
                           │
students ──── enrollments ─┘
    │
    ├── attendance_records (student_id, course_id, date, status P/A/L)
    ├── academic_records   (student_id, course_id, exam_type, score)
    ├── assignments        (student_id, course_id, title, score, is_submitted)
    ├── lms_activity       (student_id, date, login_count, time_spent_minutes)
    ├── predictions        (student_id, semester, risk_score, risk_label, contributing_factors)
    └── alerts             (student_id, alert_type, severity, is_resolved)
```

### Every Table in Detail

#### `users`
Stores faculty and admin accounts.
| Column | Type | Description |
|--------|------|-------------|
| id | int | Primary key |
| email | string | Unique login email |
| full_name | string | Display name |
| hashed_password | string | bcrypt hash — never stored plain |
| role | enum | `ADMIN` or `FACULTY` |
| department | string | e.g. "Computer Science" |
| is_active | bool | False = account disabled |

#### `students`
One row per student.
| Column | Type | Description |
|--------|------|-------------|
| id | int | Primary key |
| roll_no | string | Unique reg number e.g. "CS2021001" |
| full_name | string | Student's full name |
| email | string | Student email |
| department | string | e.g. "Computer Science" |
| semester | int | Current semester (1–8) |
| batch_year | int | Year of admission e.g. 2021 |

#### `courses`
One row per subject/course.
| Column | Type | Description |
|--------|------|-------------|
| id | int | Primary key |
| code | string | Unique code e.g. "CS501" |
| name | string | Subject name |
| faculty_id | int | FK → users.id (who teaches it) |
| semester | int | Which semester this course is in |
| credits | int | Credit hours |

#### `enrollments`
Links students to courses (many-to-many).
| Column | Type | Description |
|--------|------|-------------|
| student_id | int | FK → students.id |
| course_id | int | FK → courses.id |

> **Why this matters:** Faculty can only see students enrolled in their courses.
> The `get_student_scope()` function queries enrollments to build this list.

#### `attendance_records`
One row per student per course per date.
| Column | Type | Description |
|--------|------|-------------|
| student_id | int | FK → students.id |
| course_id | int | FK → courses.id |
| date | date | e.g. 2025-03-15 |
| status | enum | `P` (Present), `A` (Absent), `L` (Leave) |
| recorded_by | int | FK → users.id (who entered this) |

#### `academic_records`
Internal assessment marks.
| Column | Type | Description |
|--------|------|-------------|
| student_id | int | FK → students.id |
| course_id | int | FK → courses.id |
| exam_type | enum | IA1, IA2, IA3, MIDTERM, FINAL, QUIZ, PRACTICAL |
| score | float | Marks obtained |
| max_score | float | Maximum possible marks |
| exam_date | date | When the exam was held |

#### `assignments`
Assignment submission tracking.
| Column | Type | Description |
|--------|------|-------------|
| student_id | int | FK → students.id |
| course_id | int | FK → courses.id |
| title | string | Assignment name |
| score | float | Marks given (null if not submitted) |
| max_score | float | Total marks |
| is_submitted | bool | Whether student submitted |
| is_late | bool | Whether submitted after deadline |

#### `lms_activity`
LMS (Learning Management System) daily engagement — one row per student per day.
| Column | Type | Description |
|--------|------|-------------|
| student_id | int | FK → students.id |
| date | date | Activity date |
| login_count | int | Times logged into LMS |
| content_views | int | Course materials viewed |
| quiz_attempts | int | Quizzes attempted |
| forum_posts | int | Discussion posts made |
| time_spent_minutes | float | Total time on LMS |

#### `predictions`
ML model output — one row per student per semester run.
| Column | Type | Description |
|--------|------|-------------|
| student_id | int | FK → students.id |
| semester | string | e.g. "2025-ODD" |
| risk_score | float | 0.0 to 1.0 — higher = more at risk |
| risk_label | enum | `LOW`, `MEDIUM`, or `HIGH` |
| contributing_factors | JSON | List of `{feature, impact, value}` from SHAP |
| model_version | string | Which model version made this prediction |
| predicted_at | datetime | When this prediction was made |

> **Risk thresholds:**
> - score ≥ 0.70 → HIGH
> - 0.40 ≤ score < 0.70 → MEDIUM
> - score < 0.40 → LOW

#### `alerts`
Notifications triggered when students are at risk.
| Column | Type | Description |
|--------|------|-------------|
| student_id | int | FK → students.id |
| alert_type | enum | HIGH_RISK_PREDICTED, ATTENDANCE_DROP, MARKS_DECLINE, etc. |
| severity | enum | LOW, MEDIUM, HIGH, CRITICAL |
| message | string | Human-readable description |
| is_resolved | bool | Whether faculty acknowledged it |
| resolved_by | int | FK → users.id |
| resolved_at | datetime | When it was resolved |

---

## 5. How Data Flows Through the System

### Flow 1 — Student Login and View Dashboard

```
1. Faculty opens https://frontend-two-cyan-53.vercel.app
2. Browser loads the Next.js app from Vercel's CDN

3. AuthProvider.tsx runs:
   - Reads token from localStorage
   - Calls GET /api/v1/auth/me on Railway backend
   - If valid → sets auth status = "authenticated"
   - If not → redirects to /auth/login

4. Faculty enters email + password → clicks Login
   - POST /api/v1/auth/login → backend validates password with bcrypt
   - Backend creates JWT token (expires in 60 min)
   - Frontend stores token in localStorage + cookie
   - Redirects to /dashboard/faculty

5. Dashboard loads:
   - GET /api/v1/faculty/me/dashboard
   - Backend queries: students, predictions, attendance, assignments
   - Returns: { stats, risk_distribution, subject_performance }
   - Frontend renders KPI cards + charts
```

### Flow 2 — Faculty Uploads a CSV File

```
1. Faculty goes to Upload page → drags a CSV file
2. Browser sends: POST /api/v1/upload/student-data
   with: file (CSV), semester="2025-ODD", department="CS"

3. Backend (upload.py route) receives file:
   - Validates it's a .csv, under 10 MB
   - Calls data_ingestion_service.ingest_student_data_csv()

4. data_ingestion_service.py:
   - Reads CSV with pandas
   - Checks required columns exist
   - For each row:
     a. Creates Student record if roll_no is new
     b. Calls ML service POST /predict/single with student features
     c. If ML service unreachable → uses heuristic scoring
     d. Creates Prediction record (risk_score, risk_label)
     e. If HIGH risk → creates Alert record

5. Backend returns: { students_created, predictions_created, errors }
6. Frontend shows success summary
7. Dashboard auto-refreshes and shows new predictions
```

### Flow 3 — Risk Prediction Run

```
1. Admin clicks "Run Predictions" in ML Config page
2. Browser sends: POST /api/v1/predictions/run
   with: { semester: "2025-ODD" }

3. prediction_service.trigger_prediction_run():
   - Calls POST http://ml_service:8001/predict/batch
   - ML service runs the trained model on all students
   - Returns list of { student_id, risk_score, risk_label, contributing_factors }

4. For each prediction:
   - Creates/updates Prediction record in DB
   - If risk_label == "HIGH" → creates Alert record

5. Returns: { message, semester, students_scored }
6. Dashboard updates with new risk labels
```

### Flow 4 — How a Risk Score is Calculated (ML Pipeline)

```
Raw data in DB for one student:
  attendance_records  → 22 present out of 30 days = 73.3%
  academic_records    → IA1: 35/50, IA2: 38/50 = avg 72%
  assignments         → 3 submitted out of 5 = 60% completion, avg score 65%
  lms_activity        → avg 1.2 logins/day, 45 min/day

Feature engineering produces this vector:
  attendance_pct         = 73.3
  ia1_score              = 70.0   (35/50 × 100)
  ia2_score              = 76.0   (38/50 × 100)
  ia3_score              = 72.0   (assumed or from IA3)
  assignment_avg_score   = 65.0
  assignment_completion  = 0.60
  lms_login_frequency    = 8.4    (1.2 × 7 days)
  lms_time_spent_hours   = 5.25   (45 min × 7 / 60)
  lms_content_views      = 12.6
  previous_gpa           = 6.8

This 10-feature vector goes into the trained model:
  → risk_score = 0.61
  → risk_label = "MEDIUM" (0.40 ≤ 0.61 < 0.70)

SHAP explains which features pushed the score up:
  attendance_pct: -0.12  (73% is near threshold, pushing risk up)
  assignment_completion: -0.09  (60% below average)
  ia1_score: +0.04  (not bad)
```

---

## 6. ML Pipeline — All 4 Algorithms Explained

### Where the ML Code Lives
```
ml_service/
└── app/
    ├── models/          ← Algorithm definitions
    ├── pipeline/        ← Training, evaluation, prediction steps
    └── registry/        ← Save/load trained models
```

### The 10 Input Features

Every prediction uses these exact 10 features computed from the database:

| Feature | Source Table | How Computed |
|---------|-------------|--------------|
| `attendance_pct` | attendance_records | (present days / total days) × 100 |
| `ia1_score` | academic_records | score / max_score × 100 for IA1 |
| `ia2_score` | academic_records | score / max_score × 100 for IA2 |
| `ia3_score` | academic_records | score / max_score × 100 for IA3 |
| `assignment_avg_score` | assignments | mean of (score/max_score × 100) |
| `assignment_completion_rate` | assignments | submitted / total assignments |
| `lms_login_frequency` | lms_activity | avg logins per week |
| `lms_time_spent_hours` | lms_activity | avg hours per week |
| `lms_content_views` | lms_activity | avg content items viewed per week |
| `previous_gpa` | student profile | GPA from previous semester (0–10) |

### The Target Label (What We Predict)

The model predicts a single value: **is this student at risk?**

```
risk_score (0.0 to 1.0)
    ↓
≥ 0.70  →  HIGH    (urgent, faculty should intervene immediately)
≥ 0.40  →  MEDIUM  (monitor closely, may need support)
< 0.40  →  LOW     (performing well, no action needed)
```

---

### Algorithm 1 — Logistic Regression

**What it is:** The simplest and most interpretable classifier.
Think of it as drawing a straight line (or a flat plane in 10 dimensions)
that separates at-risk students from safe students.

**How it works:**
```
risk_score = sigmoid(w1×attendance + w2×ia1 + w3×ia2 + ... + w10×gpa + bias)

sigmoid(x) = 1 / (1 + e^-x)
→ always outputs a value between 0 and 1
```
The training process finds the best weights (w1...w10) that minimise
prediction errors across all training examples.

**Settings used:**
```python
LogisticRegression(
    C=1.0,          # regularisation strength (prevents overfitting)
    solver='lbfgs', # optimisation algorithm
    max_iter=500    # maximum training iterations
)
```

**Pros:** Fast, highly interpretable, good baseline
**Cons:** Can't capture non-linear patterns (e.g. "low attendance only hurts if marks are also low")
**Typical AUC:** 0.78–0.82

---

### Algorithm 2 — Random Forest

**What it is:** An ensemble of many decision trees.
Each tree independently votes on whether a student is at risk.
The final answer is the majority vote.

**How it works:**
```
Train 200 decision trees, each on a random subset of:
  - Training data rows (bootstrapping)
  - Features (random feature subset at each split)

For prediction:
  Tree 1 says: HIGH
  Tree 2 says: LOW
  Tree 3 says: HIGH
  ...
  Tree 200 says: HIGH

  → 142 say HIGH, 58 say LOW
  → risk_score = 142/200 = 0.71 → HIGH
```

Each tree asks questions like:
```
Is attendance_pct < 65%?
  YES → Is assignment_completion < 0.5?
          YES → HIGH RISK (score 0.89)
          NO  → MEDIUM RISK (score 0.52)
  NO  → Is ia1_score < 40?
          YES → MEDIUM RISK (score 0.45)
          NO  → LOW RISK (score 0.18)
```

**Settings used:**
```python
RandomForestClassifier(
    n_estimators=200,  # 200 trees
    random_state=42    # reproducible results
)
```

**Pros:** Handles non-linear patterns, resistant to overfitting, no feature scaling needed
**Cons:** Slower to train, harder to interpret than LR
**Typical AUC:** 0.85–0.90

---

### Algorithm 3 — Gradient Boosting

**What it is:** Also an ensemble of decision trees, but built sequentially.
Each new tree tries to correct the mistakes of all previous trees.

**How it works:**
```
Start with a simple prediction (e.g. always predict 0.5)

Round 1: Tree 1 looks at errors → corrects them slightly
Round 2: Tree 2 looks at remaining errors → corrects more
Round 3: Tree 3 corrects further
...
Round 150: Final model = sum of all 150 corrections

Each correction is multiplied by learning_rate=0.1
(small steps = more stable, less overfitting)
```

**Settings used:**
```python
GradientBoostingClassifier(
    n_estimators=150,    # 150 sequential trees
    learning_rate=0.1,   # step size per correction
    max_depth=4          # each tree has max 4 levels
)
```

**Pros:** Very accurate, handles complex patterns, good with imbalanced data
**Cons:** Slower than Random Forest, many hyperparameters to tune
**Typical AUC:** 0.86–0.91

---

### Algorithm 4 — XGBoost

**What it is:** An optimised, faster version of Gradient Boosting.
The "X" stands for "eXtreme" — it adds regularisation (L1 + L2)
to prevent overfitting and uses parallelisation for speed.

**How it works:** Same core idea as Gradient Boosting, but:
- Adds L1 (lasso) and L2 (ridge) penalty on tree weights
- Uses second-order derivatives for better gradient steps
- Handles missing values natively
- Uses CPU cores in parallel

**Settings used:**
```python
XGBClassifier(
    n_estimators=150,          # 150 trees
    eta=0.1,                   # learning rate (same as learning_rate)
    max_depth=5,               # slightly deeper trees than GBM
    use_label_encoder=False,   # suppress deprecation warning
    eval_metric='logloss'
)
```

**Pros:** State-of-the-art accuracy, fast, built-in regularisation, handles missing data
**Cons:** More hyperparameters, slightly harder to tune than GBM
**Typical AUC:** 0.87–0.93

---

### Model Selection — How the Best One is Chosen

After training all 4 models, `trainer.py` runs **5-fold cross-validation**:

```
All training data (e.g. 1000 students)
Split into 5 equal parts (folds):

Fold 1: [ TEST  | train | train | train | train ]  → AUC = 0.88
Fold 2: [ train | TEST  | train | train | train ]  → AUC = 0.87
Fold 3: [ train | train | TEST  | train | train ]  → AUC = 0.89
Fold 4: [ train | train | train | TEST  | train ]  → AUC = 0.86
Fold 5: [ train | train | train | train | TEST  ]  → AUC = 0.88

Mean AUC = 0.876 ± 0.010

Do this for all 4 models → pick the one with highest mean AUC
```

**ROC-AUC score explained:**
- 1.0 = perfect (never wrong)
- 0.5 = random guessing
- 0.85+ = very good (correctly ranks 85% of at-risk students above safe students)

The selected model is saved to disk via `model_registry.py` and loaded
automatically when the ML service starts.

---

## 7. SHAP Explainability — Why This Student is at Risk

**What is SHAP?**
SHAP (SHapley Additive exPlanations) answers the question:
"Which features pushed this specific student's risk score up or down?"

**Example output stored in `predictions.contributing_factors`:**
```json
[
  { "feature": "attendance_pct",      "impact": 0.31, "value": 58.3 },
  { "feature": "assignment_completion","impact": 0.18, "value": 0.40 },
  { "feature": "ia1_score",           "impact": 0.15, "value": 34.0 },
  { "feature": "lms_login_frequency", "impact": 0.09, "value": 0.8  },
  { "feature": "previous_gpa",        "impact": 0.04, "value": 5.2  }
]
```

Reading this: "58.3% attendance was the biggest reason (31% impact) why this student
was predicted HIGH risk. Low assignment completion rate (40%) was the second factor."

**How it's computed (in `predictor.py`):**
```python
# For tree-based models (RF, GBM, XGBoost):
explainer = shap.TreeExplainer(trained_model)
shap_values = explainer.shap_values(student_features)
# shap_values[i] = how much feature i pushed the score up or down

# For Logistic Regression:
explainer = shap.LinearExplainer(trained_model, background_data)
shap_values = explainer.shap_values(student_features)
```

**Where it appears in the app:**
- **Per-student page** `/dashboard/analytics/[id]` → shows top 5 factors as a card
- **Admin SHAP page** `/dashboard/admin/ai-explainability` → global average across all students
- **Email alerts** → contributing factors table in the HTML email

---

## 8. Frontend — Pages and Components

### Authentication Flow

```
User opens any page
        ↓
AuthProvider.tsx runs (in layout.tsx):
  - status = "initializing"
  - reads token from localStorage
  - calls GET /api/v1/auth/me
        ↓
  Token valid?
    YES → status = "authenticated", stores user object in Zustand store
    NO  → status = "unauthenticated"
        ↓
Dashboard layout.tsx checks:
  "initializing" → show blank (wait)
  "authenticated" → show dashboard
  "unauthenticated" → redirect to /auth/login
```

### Role-Based Navigation

The sidebar shows different menu items based on `user.role`:

**ADMIN sees:**
- System Overview
- All Students
- User Management
- Courses
- ML Config
- AI Explainability
- Model Evaluation
- Generate Data
- Analytics

**FACULTY sees:**
- My Dashboard
- My Students
- Alerts
- Reports
- Upload Data
- Export CSV

### Key Pages

| Page | Route | What it shows |
|------|-------|---------------|
| Login | `/auth/login` | Email/password form |
| Faculty Dashboard | `/dashboard/faculty` | KPIs, risk chart, at-risk table, email button |
| Student Analytics | `/dashboard/analytics/[id]` | Individual student: attendance graph, marks, SHAP factors |
| Upload | `/dashboard/faculty/upload` | Drag-drop CSV upload for 4 data types |
| Export | `/dashboard/faculty/export` | Filter by semester + risk → download CSV |
| ML Config | `/dashboard/admin/ml-config` | Model comparison table, AUC scores, run predictions |
| AI Explainability | `/dashboard/admin/ai-explainability` | SHAP global feature importance chart |
| Alerts | `/dashboard/alerts` | List of unresolved risk alerts |

### Custom Hooks — How Data Gets to the Page

Instead of fetching data directly in each page, the app uses custom hooks:

```typescript
// useFacultyDashboard.ts
export function useFacultyDashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get('/faculty/me/dashboard')
      .then(res => setData(res.data))
      .finally(() => setLoading(false));
  }, []);

  return { data, loading };
}

// In the page component:
const { data: dash, loading } = useFacultyDashboard();
if (loading) return <PageLoading />;
return <KpiCard value={dash.stats.total_students} />;
```

### Axios API Client (`lib/api.ts`)

All API calls go through one configured Axios instance:

```
Every request:
  1. Reads JWT token from cookie
  2. Adds header: Authorization: Bearer <token>
  3. Sends to: https://edusentinel-backend-production.up.railway.app/api/v1/...

Every response:
  - If HTTP 200-299 → pass through normally
  - If HTTP 401 → token expired:
      a. Clear token from localStorage + cookie
      b. Set auth status to "unauthenticated"
      c. Redirect to /auth/login
```

---

## 9. Authentication and Role-Based Access

### JWT Token Structure

When a user logs in, the backend creates a JWT token:

```json
Header: { "alg": "HS256", "typ": "JWT" }

Payload: {
  "sub": "42",           ← user ID
  "role": "FACULTY",     ← user role
  "exp": 1710000000,     ← expiry timestamp
  "type": "access"
}

Signature: HMACSHA256(header + payload, JWT_SECRET_KEY)
```

The token is a string like:
`eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiI0MiJ9.abc123`

### How Faculty Sees Only Their Students

This is handled by `get_student_scope()` in `dependencies.py`:

```python
async def get_student_scope(current_user, db):
    if current_user.role == Role.ADMIN:
        return None  # None means "no restriction, see everything"

    # Faculty: find all students enrolled in their courses
    result = await db.execute(
        select(Enrollment.student_id)
        .join(Course, Course.id == Enrollment.course_id)
        .where(Course.faculty_id == current_user.id)
    )
    student_ids = {row[0] for row in result.all()}
    return frozenset(student_ids)  # e.g. frozenset({12, 34, 56, 78})
```

Every faculty endpoint then filters queries using this scope:
```python
# in predictions.py route:
if scope is not None:
    query = query.where(Prediction.student_id.in_(list(scope)))
```

---

## 10. API Reference — Every Endpoint

### Authentication
| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/auth/register` | Create new user account | None |
| POST | `/auth/login` | Login, get JWT token | None |
| POST | `/auth/refresh` | Get new token using refresh token | None |
| GET | `/auth/me` | Get current logged-in user info | Required |

### Students
| Method | Path | Description |
|--------|------|-------------|
| GET | `/students` | List students (faculty-scoped) |
| POST | `/students` | Create new student |
| GET | `/students/{id}` | Get one student |
| PUT | `/students/{id}` | Update student |
| DELETE | `/students/{id}` | Delete student (Admin only) |

### Predictions & Risk
| Method | Path | Description |
|--------|------|-------------|
| GET | `/predictions` | List predictions with filters |
| POST | `/predictions/run` | Trigger ML prediction batch run |
| GET | `/predictions/summary` | Risk counts (HIGH/MEDIUM/LOW) |

### Data Upload
| Method | Path | Description |
|--------|------|-------------|
| POST | `/upload/student-data` | Unified CSV: creates students + predictions |
| POST | `/upload/attendance` | Attendance CSV |
| POST | `/upload/marks` | Marks / academic CSV |
| POST | `/upload/assignments` | Assignments CSV |
| POST | `/upload/lms` | LMS activity CSV |

### Analytics & Dashboard
| Method | Path | Description |
|--------|------|-------------|
| GET | `/analytics/cohort-overview` | System-wide stats |
| GET | `/analytics/department-stats` | Stats by department |
| GET | `/faculty/me/dashboard` | Faculty dashboard metrics |
| GET | `/faculty/me/students-summary` | Faculty students with metrics |

### Alerts & Emails
| Method | Path | Description |
|--------|------|-------------|
| GET | `/alerts` | List unresolved alerts |
| POST | `/alerts/{id}/resolve` | Mark alert resolved |
| POST | `/alerts/send-emails` | Send risk alert emails to students |

### Export
| Method | Path | Description |
|--------|------|-------------|
| GET | `/export/student-data` | Download students as CSV |

### ML Service
| Method | Path | Description |
|--------|------|-------------|
| GET | `/ml/model-comparison` | AUC scores for all 4 models |
| GET | `/ml/shap/global` | Global SHAP feature importance |
| GET | `/ml/shap/{student_id}` | SHAP values for one student |

### Admin
| Method | Path | Description |
|--------|------|-------------|
| POST | `/admin/seed` | Seed default admin + faculty + 20 students |
| POST | `/admin/seed-demo` | Seed 500 demo students with full data |

---

## 11. Email Alert System

### How Emails Are Sent

```
Trigger: POST /alerts/send-emails
  with: { risk_label: "HIGH", semester: "2025-ODD" }

notification_service.send_risk_alerts_batch():
  For each HIGH-risk student:
    1. Build HTML email body (_build_html())
    2. Create MIMEMultipart email object
    3. Connect to SMTP server (gmail / sendgrid / etc.)
    4. Send via STARTTLS (encrypted)
    5. Log success or failure
```

### Email Content

Each email contains:
- Student's name and risk score as a large badge
- Table of top 5 SHAP contributing factors
- Personalised improvement suggestions based on weak areas:
  - Low attendance → "Attend at least 75% of classes"
  - Low assignment score → "Submit all pending assignments"
  - Low LMS activity → "Spend at least 2 hours/day on LMS"

### To Enable Email (currently disabled)

Set these in Railway environment variables:
```
NOTIFICATION_ENABLED=true
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-16-char-app-password
SMTP_FROM_EMAIL=noreply@edusentinel.dev
```

> For Gmail: use an App Password, not your main password.
> Generate at: myaccount.google.com → Security → App Passwords

---

## 12. Background Jobs — Celery Workers

Celery allows running slow tasks in the background without blocking API responses.

### Setup
```
Redis (message broker) ← Celery Beat (scheduler) sends tasks
         ↓
Celery Worker picks up task and executes it
         ↓
Results written back to PostgreSQL
```

### Scheduled Tasks (`workers/`)

| Task | Schedule | What it does |
|------|----------|-------------|
| `run_batch_predictions` | Sunday 02:00 UTC | Runs ML predictions for all students |
| `check_and_send_alerts` | Every hour | Finds new HIGH-risk students, sends emails |

### In Production (Docker)
```yaml
# docker-compose.yml defines:
celery_worker:  # runs tasks
celery_beat:    # schedules tasks on timer
```

> **Note:** Celery workers are not running on Railway's free tier.
> Predictions are triggered manually via the admin dashboard.
> To enable auto-scheduling, deploy with Docker Compose.

---

## 13. Docker — All Services Together

Running `docker-compose up` starts **8 services** in the right order:

```
docker-compose up
        ↓
1. postgres:16    → starts first (database)
2. redis:7        → starts next (message broker)
3. ml_service     → waits for postgres + redis, then starts
4. backend        → waits for postgres + redis + ml_service
5. celery_worker  → waits for backend
6. celery_beat    → waits for backend
7. frontend       → waits for backend
8. nginx          → starts last, routes traffic to backend/frontend
```

### Ports
| Service | Port | URL |
|---------|------|-----|
| nginx (entry point) | 80 | http://localhost |
| backend (direct) | 8000 | http://localhost:8000 |
| frontend (direct) | 3001 | http://localhost:3001 |
| ml_service | 8001 | http://localhost:8001 |
| postgres | 5432 | internal only |
| redis | 6379 | internal only |

### Quick Docker Commands
```powershell
# Start everything
docker-compose up

# Start in background
docker-compose up -d

# View logs
docker-compose logs -f backend

# Stop everything
docker-compose down

# Rebuild after code changes
docker-compose up --build
```

---

## 14. Environment Variables — What Each One Does

All environment variables for the backend, with what happens if they're wrong:

| Variable | Example Value | What it does | If missing/wrong |
|----------|--------------|--------------|-----------------|
| `APP_ENV` | `production` | Enables production mode | Defaults to development |
| `DEBUG` | `false` | Hides API docs in prod | If true, /docs is public |
| `DATABASE_URL` | `postgresql://user:pass@host/db` | Database connection | Server crashes on start |
| `DB_POOL_SIZE` | `5` | Max persistent DB connections | Defaults to 20 |
| `JWT_SECRET_KEY` | `abc123...` | Signs all JWT tokens | Server crashes |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | Token lifetime | Defaults to 30 min |
| `CORS_ORIGINS` | `["https://app.vercel.app"]` | Allowed frontend origins | Login fails (CORS blocked) |
| `ML_SERVICE_URL` | `http://localhost:8001` | ML microservice address | Falls back to heuristic |
| `NOTIFICATION_ENABLED` | `false` | Turns email alerts on/off | No emails sent |
| `SMTP_HOST` | `smtp.gmail.com` | Email server address | Emails silently skipped |

---

## 15. How the Demo Data is Generated

The `POST /admin/seed-demo` endpoint creates realistic data for 500 students.
Here is exactly how it works:

### Step 1 — Create Users and Courses
```
3 faculty accounts created:
  faculty1@demo.com → teaches Mathematics + Physics
  faculty2@demo.com → teaches Machine Learning
  faculty3@demo.com → teaches Computer Science + Data Structures

5 courses created:
  DEMO-MA101  Mathematics
  DEMO-PH101  Physics
  DEMO-CS201  Computer Science
  DEMO-DS301  Data Structures
  DEMO-ML401  Machine Learning
```

### Step 2 — Create 500 Students
```
Names randomly chosen from 40 first names × 24 last names
Departments randomly from: CS, Electronics, Mechanical, Civil, IT
Semesters randomly from: 3, 5, or 7
Roll numbers: DEMO0001 through DEMO0500
```

### Step 3 — Assign Risk Profiles
```
Each student gets a hidden risk profile:
  15% chance → HIGH risk  (poor attendance ~48%, marks ~42%)
  30% chance → MEDIUM risk (moderate attendance ~68%, marks ~58%)
  55% chance → LOW risk    (good attendance ~84%, marks ~74%)
```

### Step 4 — Generate Academic Data
```
For each student, for each enrolled course:

  Attendance (30 working days):
    Each day: random.random() < att_base → PRESENT else ABSENT
    HIGH risk students: att_base ≈ 0.48 (48% chance of being present)
    LOW risk students:  att_base ≈ 0.84 (84% chance of being present)

  Marks (IA1 + IA2):
    score = marks_base + gaussian_noise(mean=0, std=10)
    HIGH risk students: marks_base ≈ 42
    LOW risk students:  marks_base ≈ 74

  Assignments (3 per course):
    is_submitted = random.random() < (0.5 + assign_base/200)
    score = assign_base + gaussian_noise()
    15% chance of late submission

  LMS Activity (14 days):
    For each day:
      active = random.random() < (0.3 + assign_base/200)
      if active:
        login_count = random.randint(1, 5)
        time_spent_minutes = random.randint(20, 120)
```

### Step 5 — Compute Predictions
```
For each student:
  Query actual attendance% from DB
  Query actual marks% from DB

  risk_score = (1 - att_pct/100) × 0.5 + (1 - marks_pct/100) × 0.5 + noise

  risk_score ≥ 0.55 → HIGH
  risk_score ≥ 0.35 → MEDIUM
  else               → LOW

  Store Prediction record with contributing_factors
```

The result: a realistic dataset where ~15% of students are HIGH risk, ~30% MEDIUM, ~55% LOW — matching typical real-world at-risk distributions in educational institutions.
