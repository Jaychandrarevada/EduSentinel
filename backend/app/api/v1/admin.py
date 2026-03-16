"""
Admin utility endpoints.

POST /admin/seed   — Seeds the database with default users, courses, and students.
                     Safe to call multiple times (idempotent).
                     ADMIN-only (production) or open once on a fresh database.
"""
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import case as sa_case, delete, func, select

from app.dependencies import get_db, require_role
from app.models.alert import Alert
from app.models.academic_record import AcademicRecord
from app.models.assignment import Assignment
from app.models.attendance import Attendance
from app.models.lms_activity import LMSActivity
from app.models.prediction import Prediction
from app.models.user import User, Role
from app.models.student import Student
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.core.security import hash_password

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.post("/seed", status_code=200)
async def seed_database(db: AsyncSession = Depends(get_db)):
    """
    Seed the database with default users, courses, and students.
    Idempotent — skips records that already exist.
    Call this once after initial deployment via:
        POST /api/v1/admin/seed
    """
    result = {"created": {}, "skipped": {}}

    # ── Admin user ────────────────────────────────────────────────────────────
    existing_admin = (await db.execute(
        select(User).where(User.email == "admin@edusentinel.dev")
    )).scalar_one_or_none()

    if existing_admin:
        result["skipped"]["admin"] = "admin@edusentinel.dev"
        admin = existing_admin
    else:
        admin = User(
            email="admin@edusentinel.dev",
            full_name="System Admin",
            hashed_password=hash_password("Admin@123"),
            role=Role.ADMIN,
            department="Administration",
        )
        db.add(admin)
        await db.flush()
        result["created"]["admin"] = "admin@edusentinel.dev"

    # ── Faculty user ──────────────────────────────────────────────────────────
    existing_faculty = (await db.execute(
        select(User).where(User.email == "faculty@edusentinel.dev")
    )).scalar_one_or_none()

    if existing_faculty:
        result["skipped"]["faculty"] = "faculty@edusentinel.dev"
        faculty = existing_faculty
    else:
        faculty = User(
            email="faculty@edusentinel.dev",
            full_name="Dr. Priya Sharma",
            hashed_password=hash_password("Faculty@123"),
            role=Role.FACULTY,
            department="Computer Science",
        )
        db.add(faculty)
        await db.flush()
        result["created"]["faculty"] = "faculty@edusentinel.dev"

    # ── Courses ───────────────────────────────────────────────────────────────
    course_data = [
        ("CS501", "Data Structures", 5, 4),
        ("CS502", "Operating Systems", 5, 4),
        ("CS503", "Database Systems", 5, 3),
    ]
    courses = []
    created_courses = 0
    for code, name, semester, credits in course_data:
        existing = (await db.execute(
            select(Course).where(Course.code == code)
        )).scalar_one_or_none()
        if existing:
            courses.append(existing)
        else:
            c = Course(
                code=code, name=name, department="Computer Science",
                semester=semester, credits=credits,
                academic_year="2024-25", faculty_id=faculty.id,
            )
            db.add(c)
            courses.append(c)
            created_courses += 1
    await db.flush()
    result["created"]["courses"] = created_courses
    result["skipped"]["courses"] = len(course_data) - created_courses

    # ── Students ──────────────────────────────────────────────────────────────
    students = []
    created_students = 0
    for i in range(1, 21):
        roll = f"CS2021{str(i).zfill(3)}"
        existing = (await db.execute(
            select(Student).where(Student.roll_no == roll)
        )).scalar_one_or_none()
        if existing:
            students.append(existing)
        else:
            s = Student(
                roll_no=roll,
                full_name=f"Student {i}",
                email=f"student{i}@test.edu",
                department="Computer Science",
                semester=5,
                batch_year=2021,
            )
            db.add(s)
            students.append(s)
            created_students += 1
    await db.flush()
    result["created"]["students"] = created_students
    result["skipped"]["students"] = 20 - created_students

    # ── Enrollments ───────────────────────────────────────────────────────────
    existing_enrollments = set(
        (row.student_id, row.course_id)
        for row in (await db.execute(select(Enrollment))).scalars().all()
    )
    new_enrollments = 0
    for s in students:
        for c in courses:
            if (s.id, c.id) not in existing_enrollments:
                db.add(Enrollment(student_id=s.id, course_id=c.id))
                new_enrollments += 1

    await db.commit()
    result["created"]["enrollments"] = new_enrollments

    return {
        "message": "Seed complete",
        "details": result,
        "credentials": {
            "admin": {"email": "admin@edusentinel.dev", "password": "Admin@123"},
            "faculty": {"email": "faculty@edusentinel.dev", "password": "Faculty@123"},
        },
    }


# ── Demo seed ─────────────────────────────────────────────────────────────────

@router.post("/seed-demo", status_code=200)
async def seed_demo(db: AsyncSession = Depends(get_db)):
    """
    Seed realistic demo data for presentation:
      - 3 faculty accounts (faculty1-3@demo.com / demo123)
      - 5 subjects (Mathematics, Physics, CS, Data Structures, ML)
      - 500 students distributed across subjects
      - Attendance, academic records, assignments, LMS activity
      - ML risk predictions for each student
    Idempotent — safe to call multiple times.
    """
    import random
    import math
    from datetime import date, timedelta
    from app.models.attendance import Attendance, AttendanceStatus
    from app.models.academic_record import AcademicRecord, ExamType
    from app.models.assignment import Assignment
    from app.models.lms_activity import LMSActivity
    from app.models.prediction import Prediction, RiskLabel

    rng = random.Random(42)

    result: dict = {"created": {}, "skipped": {}}

    # ── Demo faculty ──────────────────────────────────────────────────────────
    demo_faculty_data = [
        ("faculty1@demo.com", "Prof. Ananya Krishnan",   "Mathematics",      "demo123"),
        ("faculty2@demo.com", "Prof. Vikram Nair",       "Machine Learning", "demo123"),
        ("faculty3@demo.com", "Prof. Sunita Reddy",      "Computer Science", "demo123"),
    ]
    faculty_users: list[User] = []
    for email, name, dept, pwd in demo_faculty_data:
        existing = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
        if existing:
            result["skipped"].setdefault("faculty", []).append(email)
            faculty_users.append(existing)
        else:
            u = User(email=email, full_name=name, hashed_password=hash_password(pwd),
                     role=Role.FACULTY, department=dept)
            db.add(u)
            result["created"].setdefault("faculty", []).append(email)
            faculty_users.append(u)
    await db.flush()

    # ── Demo courses (one per subject area) ───────────────────────────────────
    courses_spec = [
        ("DEMO-MA101", "Mathematics",       "Mathematics",      4, faculty_users[0]),
        ("DEMO-PH101", "Physics",           "Physics",          4, faculty_users[0]),
        ("DEMO-CS201", "Computer Science",  "Computer Science", 4, faculty_users[2]),
        ("DEMO-DS301", "Data Structures",   "Computer Science", 3, faculty_users[2]),
        ("DEMO-ML401", "Machine Learning",  "Computer Science", 3, faculty_users[1]),
    ]
    demo_courses: list[Course] = []
    for code, name, dept, credits, fac in courses_spec:
        existing = (await db.execute(select(Course).where(Course.code == code))).scalar_one_or_none()
        if existing:
            result["skipped"].setdefault("courses", []).append(code)
            demo_courses.append(existing)
        else:
            c = Course(code=code, name=name, department=dept, semester=5, credits=credits,
                       academic_year="2024-25", faculty_id=fac.id)
            db.add(c)
            result["created"].setdefault("courses", []).append(code)
            demo_courses.append(c)
    await db.flush()

    # Course→faculty mapping for enrollment scoping
    # faculty1 → Math + Physics, faculty2 → ML, faculty3 → CS + DS
    faculty_course_map = {
        faculty_users[0].id: [demo_courses[0], demo_courses[1]],
        faculty_users[1].id: [demo_courses[4]],
        faculty_users[2].id: [demo_courses[2], demo_courses[3]],
    }

    # ── Demo students ─────────────────────────────────────────────────────────
    FIRST = ["Aarav","Aditi","Arjun","Bhavya","Chirag","Deepa","Dinesh","Esha",
             "Farhan","Gayatri","Harsh","Isha","Jay","Kavya","Kunal","Lakshmi",
             "Manish","Nisha","Om","Priya","Rahul","Riya","Rohit","Sakshi",
             "Sanjay","Sara","Shivam","Sneha","Suresh","Tanvi","Uma","Varun",
             "Vidya","Yash","Zara","Anil","Bindu","Chetan","Dhruv","Elina"]
    LAST  = ["Sharma","Patel","Reddy","Nair","Iyer","Singh","Kumar","Gupta",
             "Joshi","Mehta","Rao","Pillai","Mishra","Chopra","Shah","Verma",
             "Bhat","Das","Pandey","Tiwari","Agarwal","Malhotra","Saxena","Bose"]
    DEPTS = ["Computer Science", "Electronics", "Mechanical", "Civil", "IT"]

    students_created = 0
    all_demo_students: list[Student] = []
    for i in range(1, 501):
        roll = f"DEMO{str(i).zfill(4)}"
        existing = (await db.execute(select(Student).where(Student.roll_no == roll))).scalar_one_or_none()
        if existing:
            all_demo_students.append(existing)
            continue
        fname = rng.choice(FIRST)
        lname = rng.choice(LAST)
        dept  = rng.choice(DEPTS)
        s = Student(
            roll_no=roll, full_name=f"{fname} {lname}",
            email=f"demo.student{i}@college.edu",
            department=dept, semester=rng.choice([3, 5, 7]),
            batch_year=2022,
        )
        db.add(s)
        all_demo_students.append(s)
        students_created += 1
    await db.flush()
    result["created"]["students"] = students_created

    # ── Enrollments ───────────────────────────────────────────────────────────
    existing_enroll = set(
        (r[0], r[1]) for r in (await db.execute(
            select(Enrollment.student_id, Enrollment.course_id)
        )).all()
    )
    enroll_created = 0
    # Distribute 500 students: each gets 1-2 courses based on index
    for idx, student in enumerate(all_demo_students):
        # Each student goes into 2 courses chosen by index for reproducibility
        course_a = demo_courses[idx % len(demo_courses)]
        course_b = demo_courses[(idx + 2) % len(demo_courses)]
        for course in {course_a, course_b}:
            if (student.id, course.id) not in existing_enroll:
                db.add(Enrollment(student_id=student.id, course_id=course.id))
                existing_enroll.add((student.id, course.id))
                enroll_created += 1
    await db.flush()
    result["created"]["enrollments"] = enroll_created

    # ── Academic data (attendance, marks, assignments, LMS) ──────────────────
    today = date.today()
    att_created = marks_created = assign_created = lms_created = 0

    for student in all_demo_students:
        # Determine risk profile for this student
        risk_profile = rng.choices(["high", "medium", "low"], weights=[15, 30, 55])[0]
        if risk_profile == "high":
            att_base, marks_base, assign_base = 0.48, 42, 48
        elif risk_profile == "medium":
            att_base, marks_base, assign_base = 0.68, 58, 62
        else:
            att_base, marks_base, assign_base = 0.84, 74, 78

        # Get enrolled courses for this student
        enrolled_course_ids = [
            r[0] for r in (await db.execute(
                select(Enrollment.course_id).where(Enrollment.student_id == student.id)
            )).all()
        ]

        for course_id in enrolled_course_ids:
            # Attendance — 30 days
            for days_ago in range(30, 0, -1):
                record_date = today - timedelta(days=days_ago)
                if record_date.weekday() >= 5:  # skip weekends
                    continue
                existing_att = (await db.execute(
                    select(Attendance).where(
                        Attendance.student_id == student.id,
                        Attendance.course_id == course_id,
                        Attendance.date == record_date,
                    )
                )).scalar_one_or_none()
                if existing_att:
                    continue
                present = rng.random() < (att_base + rng.gauss(0, 0.08))
                status = AttendanceStatus.PRESENT if present else AttendanceStatus.ABSENT
                db.add(Attendance(student_id=student.id, course_id=course_id,
                                  date=record_date, status=status))
                att_created += 1

            # Academic records (IA1 + IA2)
            for exam_type, max_s in [(ExamType.IA1, 50), (ExamType.IA2, 50)]:
                existing_mark = (await db.execute(
                    select(AcademicRecord).where(
                        AcademicRecord.student_id == student.id,
                        AcademicRecord.course_id == course_id,
                        AcademicRecord.exam_type == exam_type,
                    )
                )).scalar_one_or_none()
                if existing_mark:
                    continue
                raw = marks_base + rng.gauss(0, 10)
                score = max(0, min(max_s, round(raw * max_s / 100)))
                db.add(AcademicRecord(
                    student_id=student.id, course_id=course_id,
                    exam_type=exam_type, score=score, max_score=max_s,
                    exam_date=today - timedelta(days=rng.randint(10, 60)),
                ))
                marks_created += 1

            # Assignments (3 per course)
            for a_num in range(1, 4):
                existing_a = (await db.execute(
                    select(Assignment).where(
                        Assignment.student_id == student.id,
                        Assignment.course_id == course_id,
                        Assignment.title == f"Assignment {a_num}",
                    )
                )).scalar_one_or_none()
                if existing_a:
                    continue
                submitted = rng.random() < (0.5 + assign_base / 200)
                raw_score  = assign_base + rng.gauss(0, 10) if submitted else 0
                score      = max(0, min(100, round(raw_score)))
                db.add(Assignment(
                    student_id=student.id, course_id=course_id,
                    title=f"Assignment {a_num}", max_score=100,
                    score=score, is_submitted=submitted, is_late=rng.random() < 0.15,
                    due_date=today - timedelta(days=rng.randint(5, 45)),
                ))
                assign_created += 1

        # LMS Activity — 14 days
        for days_ago in range(14, 0, -1):
            record_date = today - timedelta(days=days_ago)
            existing_lms = (await db.execute(
                select(LMSActivity).where(
                    LMSActivity.student_id == student.id,
                    LMSActivity.date == record_date,
                )
            )).scalar_one_or_none()
            if existing_lms:
                continue
            active = rng.random() < (0.3 + assign_base / 200)
            db.add(LMSActivity(
                student_id=student.id, date=record_date,
                login_count=rng.randint(1, 5) if active else 0,
                content_views=rng.randint(2, 10) if active else 0,
                quiz_attempts=rng.randint(0, 2) if active else 0,
                forum_posts=rng.randint(0, 3) if active else 0,
                time_spent_minutes=rng.randint(20, 120) if active else 0,
            ))
            lms_created += 1

    await db.flush()
    result["created"]["attendance_records"] = att_created
    result["created"]["academic_records"]   = marks_created
    result["created"]["assignments"]        = assign_created
    result["created"]["lms_activity"]       = lms_created

    # ── ML Predictions ────────────────────────────────────────────────────────
    pred_created = 0
    for student in all_demo_students:
        existing_pred = (await db.execute(
            select(Prediction).where(
                Prediction.student_id == student.id,
                Prediction.semester == "2024-ODD",
            )
        )).scalar_one_or_none()
        if existing_pred:
            continue

        # Compute risk score from actual attendance + marks
        att_pct_row = (await db.execute(
            select(
                func.avg(sa_case((Attendance.status == AttendanceStatus.PRESENT, 1), else_=0)) * 100
            ).where(Attendance.student_id == student.id)
        )).scalar_one()
        att_pct = float(att_pct_row or 70)

        marks_row = (await db.execute(
            select(func.avg(AcademicRecord.score / AcademicRecord.max_score * 100))
            .where(AcademicRecord.student_id == student.id, AcademicRecord.max_score > 0)
        )).scalar_one()
        marks_pct = float(marks_row or 60)

        # Simple scoring: low attendance + low marks = high risk
        risk_score = max(0.0, min(1.0,
            (1 - att_pct / 100) * 0.5 + (1 - marks_pct / 100) * 0.5
            + rng.gauss(0, 0.05)
        ))
        if risk_score >= 0.55:
            label = RiskLabel.HIGH
        elif risk_score >= 0.35:
            label = RiskLabel.MEDIUM
        else:
            label = RiskLabel.LOW

        db.add(Prediction(
            student_id=student.id,
            semester="2024-ODD",
            risk_score=round(risk_score, 4),
            risk_label=label,
            contributing_factors=[
                {"feature": "attendance_pct",       "impact": round(abs(1 - att_pct/100) * 0.5, 3),  "value": round(att_pct, 1)},
                {"feature": "ia1_score",             "impact": round(abs(1 - marks_pct/100) * 0.3, 3), "value": round(marks_pct * 0.5, 1)},
                {"feature": "assignment_avg_score",  "impact": round(rng.uniform(0.01, 0.1), 3),       "value": round(marks_pct * 0.9, 1)},
                {"feature": "lms_engagement_score",  "impact": round(rng.uniform(0.01, 0.08), 3),      "value": round(rng.uniform(20, 80), 1)},
            ],
            model_version="demo-v1",
        ))
        pred_created += 1

    await db.commit()
    result["created"]["predictions"] = pred_created

    return {
        "message": "Demo seed complete",
        "details": result,
        "demo_credentials": [
            {"email": "faculty1@demo.com", "password": "demo123", "subject": "Mathematics & Physics"},
            {"email": "faculty2@demo.com", "password": "demo123", "subject": "Machine Learning"},
            {"email": "faculty3@demo.com", "password": "demo123", "subject": "Computer Science & Data Structures"},
        ],
    }


# ── Bulk-delete generated students ────────────────────────────────────────────

class ResetStudentsResponse(BaseModel):
    students_deleted: int
    message: str


@router.post("/reset-students", response_model=ResetStudentsResponse, status_code=200)
async def reset_students(
    mode: Literal["last_n", "keep_first_n", "generated_all"] = Query(...),
    count: Optional[int] = Query(None, ge=1, le=10000),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(Role.ADMIN)),
):
    """
    Bulk-delete generated students and all their related data.
    Pass parameters as query strings: ?mode=last_n&count=300

    Modes
    ─────
    last_n        — delete the most recently created N students
    keep_first_n  — keep the oldest N, delete everyone else
    generated_all — delete every student whose roll_no starts with GEN
    """
    if mode in ("last_n", "keep_first_n") and count is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="`count` is required for last_n and keep_first_n modes.",
        )

    if mode == "last_n":
        ids = (await db.execute(
            select(Student.id).order_by(Student.id.desc()).limit(count)
        )).scalars().all()
    elif mode == "keep_first_n":
        keep = (await db.execute(
            select(Student.id).order_by(Student.id.asc()).limit(count)
        )).scalars().all()
        ids = (await db.execute(
            select(Student.id).where(Student.id.notin_(keep))
        )).scalars().all()
    else:
        ids = (await db.execute(
            select(Student.id).where(Student.roll_no.like("GEN%"))
        )).scalars().all()

    if ids:
        await db.execute(delete(Alert).where(Alert.student_id.in_(ids)))
        await db.execute(delete(Prediction).where(Prediction.student_id.in_(ids)))
        await db.execute(delete(LMSActivity).where(LMSActivity.student_id.in_(ids)))
        await db.execute(delete(Assignment).where(Assignment.student_id.in_(ids)))
        await db.execute(delete(AcademicRecord).where(AcademicRecord.student_id.in_(ids)))
        await db.execute(delete(Attendance).where(Attendance.student_id.in_(ids)))
        await db.execute(delete(Enrollment).where(Enrollment.student_id.in_(ids)))
        await db.execute(delete(Student).where(Student.id.in_(ids)))
        await db.commit()

    mode_label = {
        "last_n": f"last {count}",
        "keep_first_n": f"all except first {count}",
        "generated_all": "all generated (GEN prefix)",
    }[mode]

    return ResetStudentsResponse(
        students_deleted=len(ids),
        message=f"Deleted {len(ids)} student(s) ({mode_label}) and all their related records.",
    )
