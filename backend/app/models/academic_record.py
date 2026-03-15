"""
Academic Record model — internal assessment marks per student per course.
Covers IA1, IA2, IA3, Mid-term, Final, etc.
"""
import enum
from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint, Date, DateTime, Enum, Float,
    ForeignKey, Integer, String, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ExamType(str, enum.Enum):
    IA1 = "IA1"
    IA2 = "IA2"
    IA3 = "IA3"
    MIDTERM = "MIDTERM"
    FINAL = "FINAL"
    QUIZ = "QUIZ"
    PRACTICAL = "PRACTICAL"


class AcademicRecord(Base):
    __tablename__ = "academic_records"
    __table_args__ = (
        CheckConstraint("score >= 0 AND score <= max_score", name="ck_score_range"),
        CheckConstraint("max_score > 0", name="ck_max_score_positive"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True
    )
    course_id: Mapped[int] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    exam_type: Mapped[ExamType] = mapped_column(
        Enum(ExamType, name="exam_type"), nullable=False
    )
    score: Mapped[float] = mapped_column(Float, nullable=False)
    max_score: Mapped[float] = mapped_column(Float, nullable=False, default=100.0)
    exam_date: Mapped[date] = mapped_column(Date, nullable=False)
    remarks: Mapped[str | None] = mapped_column(String(500), nullable=True)
    recorded_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    student = relationship("Student", back_populates="academic_records", lazy="noload")
    course = relationship("Course", back_populates="academic_records", lazy="noload")

    @property
    def percentage(self) -> float:
        return round((self.score / self.max_score) * 100, 2) if self.max_score else 0.0
