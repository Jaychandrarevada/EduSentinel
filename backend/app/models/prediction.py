"""
Prediction model — stores ML model output per student per semester.
"""
import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class RiskLabel(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class Prediction(Base):
    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True
    )
    semester: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    risk_label: Mapped[RiskLabel] = mapped_column(
        Enum(RiskLabel, name="risk_label"), nullable=False, index=True
    )
    # Stores list of {feature, impact, value} dicts from SHAP
    contributing_factors: Mapped[list | None] = mapped_column(JSON, nullable=True)
    model_version: Mapped[str] = mapped_column(String(30), nullable=False)
    predicted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    student = relationship("Student", back_populates="predictions", lazy="noload")

    def __repr__(self) -> str:
        return (
            f"<Prediction student={self.student_id} "
            f"risk={self.risk_label} score={self.risk_score:.2f}>"
        )
