# EduSentinel — 5-Minute Evaluator Demo Script

> **Setup before they arrive**
> - Backend running: `http://localhost:8000`
> - Frontend running: `http://localhost:3001`
> - Two browser tabs open: login page + API docs (`/docs`)
> - Screen at `http://localhost:3001/auth/login`

---

## Minute 0:30 — The Problem (spoken, no clicking)

> *"Every semester, faculty identify at-risk students only after they've already
> failed a mid-term — when it's too late to intervene. EduSentinel solves this
> by combining attendance, grades, assignment submissions, and LMS engagement
> into a single ML-powered early-warning system. Let me show you."*

---

## Minute 1:00 — Login as Admin

**Click:** Fill in admin credentials → Sign in

```
Email:    admin@edusentinel.dev
Password: Admin@123
```

> *"The system has role-based access. Admins see the entire institution;
> faculty see only their own students. I'll start as admin."*

**Point to:** the sidebar — Overview, Students, Courses, Users, Analytics, ML Config.

---

## Minute 1:30 — Admin Overview Dashboard

**Click:** Dashboard → **Overview** (already there)

> *"This is the admin command centre. At a glance:
> — total students enrolled,
> — risk distribution across LOW / MEDIUM / HIGH,
> — attendance and marks averages,
> — and any unresolved at-risk alerts."*

**Point to:** KPI cards at the top, then the risk distribution donut chart.

---

## Minute 2:00 — Student Management

**Click:** Sidebar → **Students**

> *"Every student's record is here — searchable, filterable by department
> or semester. Risk labels from the ML model are overlaid directly on the roster."*

**Do:** Type `"Student 1"` in the search bar — show the filtered result.

**Click:** **Analytics** link on any student row → show the performance deep-dive page.

> *"This page shows attendance trend, exam score breakdown, assignment
> completion rate, LMS engagement, and the latest ML risk prediction — all
> on one screen."*

---

## Minute 2:45 — Faculty Dashboard (switch accounts)

**Click:** User avatar (top-right) → **Logout**

**Login as Faculty:**
```
Email:    faculty@edusentinel.dev
Password: Faculty@123
```

> *"Now I'm Dr. Priya Sharma — a faculty member. She only sees students
> enrolled in her three courses."*

**Point to:** the scoped sidebar — My Students, Alerts, Upload Data, Reports.

**Click:** **My Students** → At Risk tab

> *"The At Risk tab shows predictions from the ML model, sorted by risk score.
> The top contributing factor for each student is shown inline — in this case
> it might be low attendance or missing assignments."*

**Click:** **All Students** tab

> *"The All Students tab shows the complete roster — 20 students — with a
> direct link to each student's analytics."*

---

## Minute 3:30 — Data Upload + Export

**Click:** Sidebar → **Upload Data**

> *"Faculty can bulk-upload attendance, marks, assignments, and LMS activity
> from CSV files — no manual entry. The system validates and inserts records
> in one shot."*

**Click:** Sidebar → **Reports** (or Export tab)

> *"And they can export the entire cohort's performance data as a CSV
> — for compliance, for sharing with a department head, whatever they need."*

---

## Minute 4:00 — ML & Explainability (back to Admin)

**Open second tab:** `http://localhost:8000/system-health`

> *"Here's our live system health endpoint — database is healthy, 20 students
> in the system, API is up. The ML service status is shown here too."*

**Back to frontend → Login as Admin → Sidebar → ML Config**

> *"The ML pipeline trains three models — Logistic Regression, Random Forest,
> and XGBoost — and selects the best by ROC-AUC. Metrics are displayed here."*

**Click:** Sidebar → **AI Explainability**

> *"This is the SHAP explainability layer. Global feature importance tells us
> which factors drive risk predictions across all students. Per-student force
> plots show exactly why a specific student was flagged."*

---

## Minute 4:30 — Faculty Self-Registration

**Open tab:** `http://localhost:3001/auth/faculty-register`

> *"Faculty don't need an admin to create their account. They register here,
> pick their department, set a password — and land directly in their
> dashboard. No manual provisioning."*

---

## Minute 5:00 — Architecture Close

> *"To summarise the tech stack:*
>
> - **FastAPI** backend with async SQLAlchemy and JWT auth
> - **Next.js 14** frontend with Tailwind CSS and Recharts
> - **SQLite locally / PostgreSQL in production**
> - **Scikit-learn + XGBoost** ML pipeline with SHAP explainability
> - **Celery + Redis** for scheduled prediction jobs
> - **Docker Compose** for one-command deployment
>
> *The entire system is containerised and ready to deploy to Render, Railway,
> or AWS EC2 — the guide is in DEPLOYMENT.md.*
>
> *Questions?"*

---

## Fallback: Live API Demo (if they ask "show the raw API")

**Open tab:** `http://localhost:8000/docs`

Run these in order using the **Try it out** button:

| # | Endpoint | What to show |
|---|----------|-------------|
| 1 | `POST /api/v1/auth/login` | Returns JWT tokens |
| 2 | `GET /api/v1/faculty/me/students` | Faculty-scoped student list |
| 3 | `GET /api/v1/students/{id}/performance` | Full performance snapshot |
| 4 | `GET /system-health` | System status JSON |
| 5 | `GET /export/student-data` | CSV download header |

---

## Quick Cheat Sheet

| Credential | Email | Password |
|-----------|-------|----------|
| Admin | admin@edusentinel.dev | Admin@123 |
| Faculty | faculty@edusentinel.dev | Faculty@123 |

| URL | Purpose |
|-----|---------|
| http://localhost:3001 | Frontend |
| http://localhost:8000/docs | Swagger API docs |
| http://localhost:8000/system-health | Live health check |

---

## Anticipated Evaluator Questions

**Q: Why SQLite locally instead of PostgreSQL?**
> "PostgreSQL is used in production via Docker. The backend auto-detects the
> driver — switching is a single env variable change: `DATABASE_URL=postgresql+asyncpg://...`"

**Q: How accurate is the ML model?**
> "We train Logistic Regression, Random Forest, and XGBoost and pick the
> best by ROC-AUC. On synthetic data it exceeds 0.85 AUC. On real institutional
> data, accuracy improves significantly with more semester history."

**Q: How does SHAP work here?**
> "SHAP (SHapley Additive exPlanations) assigns each feature a contribution
> value for every individual prediction. So we can tell a faculty member
> *'this student is HIGH risk primarily because attendance dropped below 60%
> in the last 3 weeks'* — not just a black-box score."

**Q: Is the email notification system live?**
> "The `notification_service.py` is built and wired up. It's toggled by
> `NOTIFICATION_ENABLED=true` in the env file — needs an SMTP server
> (Gmail App Password works). Off by default so the demo doesn't send emails."

**Q: How is faculty data isolation enforced?**
> "The `get_student_scope()` dependency in FastAPI returns a frozenset of
> student IDs that belong to the logged-in faculty's courses. Every query
> that touches student data is filtered by this scope before hitting the DB."
