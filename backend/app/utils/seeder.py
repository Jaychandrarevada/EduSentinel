"""
Database seeder — creates sample users, students, courses for development.
Run: python -m app.utils.seeder
"""
import asyncio
from datetime import date

import structlog

from app.core.security import hash_password
from app.database import AsyncSessionLocal
from app.models.user import User, Role
from app.models.student import Student
from app.models.course import Course
from app.models.enrollment import Enrollment

log = structlog.get_logger()


async def seed() -> None:
    async with AsyncSessionLocal() as db:
        # ── Users ─────────────────────────────
        admin = User(
            email="admin@edusentinel.dev",
            full_name="System Admin",
            hashed_password=hash_password("Admin@123"),
            role=Role.ADMIN,
            department="Administration",
        )
        faculty = User(
            email="faculty@edusentinel.dev",
            full_name="Dr. Priya Sharma",
            hashed_password=hash_password("Faculty@123"),
            role=Role.FACULTY,
            department="Computer Science",
        )
        db.add_all([admin, faculty])
        await db.flush()

        # ── Courses ───────────────────────────
        courses = [
            Course(code="CS501", name="Data Structures", department="Computer Science",
                   semester=5, credits=4, academic_year="2024-25", faculty_id=faculty.id),
            Course(code="CS502", name="Operating Systems", department="Computer Science",
                   semester=5, credits=4, academic_year="2024-25", faculty_id=faculty.id),
            Course(code="CS503", name="Database Systems", department="Computer Science",
                   semester=5, credits=3, academic_year="2024-25", faculty_id=faculty.id),
        ]
        db.add_all(courses)
        await db.flush()

        # ── Students ──────────────────────────
        students = [
            Student(roll_no=f"CS2021{str(i).zfill(3)}", full_name=f"Student {i}",
                    email=f"student{i}@test.edu", department="Computer Science",
                    semester=5, batch_year=2021)
            for i in range(1, 21)
        ]
        db.add_all(students)
        await db.flush()  # get student IDs

        # ── Enrollments ───────────────────────
        # Enroll every student in every course so faculty can see them
        enrollments = [
            Enrollment(student_id=s.id, course_id=c.id)
            for s in students
            for c in courses
        ]
        db.add_all(enrollments)
        await db.commit()

        log.info(
            "seeder.complete",
            users=2,
            courses=len(courses),
            students=len(students),
            enrollments=len(enrollments),
        )
        print("\nSeeder complete:")
        print("  Admin:   admin@edusentinel.dev / Admin@123")
        print("  Faculty: faculty@edusentinel.dev / Faculty@123")
        print(f"  {len(students)} students seeded (CS2021001–CS2021020)")
        print(f"  {len(enrollments)} enrollments created")


if __name__ == "__main__":
    asyncio.run(seed())
