"""
Aggregated APIRouter — registers all v1 subrouters.
Imported by main.py as the single include point.
"""
from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.students import router as students_router
from app.api.v1.academic import router as academic_router
from app.api.v1.attendance import router as attendance_router
from app.api.v1.assignments import router as assignments_router
from app.api.v1.lms_activity import router as lms_router
from app.api.v1.predictions import router as predictions_router
from app.api.v1.analytics import router as analytics_router
from app.api.v1.faculty import router as faculty_router
from app.api.v1.data_generator import router as data_generator_router
from app.api.v1.export import router as export_router
from app.api.v1.ml import router as ml_router
from app.api.v1.admin import router as admin_router
from app.api.v1.courses import router as courses_router
from app.api.v1.upload import router as upload_router
from app.api.v1.alerts import router as alerts_router

api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(students_router)
api_router.include_router(data_generator_router)   # POST /students/generate
api_router.include_router(academic_router)
api_router.include_router(attendance_router)
api_router.include_router(assignments_router)
api_router.include_router(lms_router)
api_router.include_router(predictions_router)
api_router.include_router(analytics_router)
api_router.include_router(faculty_router)
api_router.include_router(export_router)            # GET  /export/student-data
api_router.include_router(ml_router)                # GET  /ml/model-comparison, /ml/shap/*
api_router.include_router(admin_router)             # POST /admin/seed
api_router.include_router(courses_router)           # GET/POST/PUT/DELETE /courses
api_router.include_router(upload_router)            # POST /upload/student-data, /upload/attendance, etc.
api_router.include_router(alerts_router)            # GET  /alerts, POST /alerts/{id}/resolve, POST /alerts/send-emails
