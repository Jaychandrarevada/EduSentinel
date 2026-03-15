"""Course model."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    department: Mapped[str] = mapped_column(String(100), nullable=False)
    semester: Mapped[int] = mapped_column(Integer, nullable=False)
    credits: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    academic_year: Mapped[str] = mapped_column(String(20), nullable=False)  # e.g. "2024-25"
    faculty_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    faculty = relationship("User", back_populates="courses", lazy="noload")
    enrollments = relationship("Enrollment", back_populates="course", lazy="noload")
    attendance_records = relationship("Attendance", back_populates="course", lazy="noload")
    academic_records = relationship("AcademicRecord", back_populates="course", lazy="noload")

    def __repr__(self) -> str:
        return f"<Course id={self.id} code={self.code}>"
