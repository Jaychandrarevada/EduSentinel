"""
Student model — core entity representing a learner.
"""
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Student(Base):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    roll_no: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    department: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    semester: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    batch_year: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships (lazy=noload = never eagerly joined unless explicitly requested)
    enrollments = relationship("Enrollment", back_populates="student", lazy="noload")
    attendance_records = relationship("Attendance", back_populates="student", lazy="noload")
    academic_records = relationship("AcademicRecord", back_populates="student", lazy="noload")
    assignments = relationship("Assignment", back_populates="student", lazy="noload")
    lms_activities = relationship("LMSActivity", back_populates="student", lazy="noload")
    predictions = relationship("Prediction", back_populates="student", lazy="noload")
    alerts = relationship("Alert", back_populates="student", lazy="noload")

    def __repr__(self) -> str:
        return f"<Student id={self.id} roll_no={self.roll_no}>"
