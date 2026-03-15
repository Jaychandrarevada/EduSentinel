"""
Import all models here so Alembic autogenerate detects them.
Order matters: referenced tables must be imported before referencing ones.
"""
from app.models.user import User           # noqa: F401
from app.models.student import Student     # noqa: F401
from app.models.course import Course       # noqa: F401
from app.models.enrollment import Enrollment  # noqa: F401
from app.models.attendance import Attendance  # noqa: F401
from app.models.academic_record import AcademicRecord  # noqa: F401
from app.models.assignment import Assignment  # noqa: F401
from app.models.lms_activity import LMSActivity  # noqa: F401
from app.models.prediction import Prediction  # noqa: F401
from app.models.alert import Alert         # noqa: F401
