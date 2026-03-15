"""
LMS (Learning Management System) activity log model.
One row per student per calendar date — daily aggregated metrics.
"""
from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint, Date, DateTime, Float, ForeignKey,
    Integer, UniqueConstraint, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class LMSActivity(Base):
    __tablename__ = "lms_activity"
    __table_args__ = (
        UniqueConstraint("student_id", "date", name="uq_lms_student_date"),
        CheckConstraint("login_count >= 0", name="ck_login_count_non_negative"),
        CheckConstraint("time_spent_minutes >= 0", name="ck_time_spent_non_negative"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True
    )
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    login_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    content_views: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    quiz_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    forum_posts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    time_spent_minutes: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    student = relationship("Student", back_populates="lms_activities", lazy="noload")
