"""Course endpoints — list, create, update, delete."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, require_role
from app.models.course import Course
from app.models.user import Role

router = APIRouter(prefix="/courses", tags=["Courses"])


@router.get("", status_code=200)
async def list_courses(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(Course).order_by(Course.code))).scalars().all()
    return [
        {
            "id": c.id, "code": c.code, "name": c.name,
            "department": c.department, "semester": c.semester,
            "credits": c.credits, "academic_year": c.academic_year,
            "faculty_id": c.faculty_id,
        }
        for c in rows
    ]


@router.post("", status_code=201)
async def create_course(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_role(Role.ADMIN)),
):
    course = Course(**{k: v for k, v in payload.items() if k != "id"})
    db.add(course)
    await db.commit()
    await db.refresh(course)
    return {"id": course.id, "code": course.code, "name": course.name}


@router.put("/{course_id}", status_code=200)
async def update_course(
    course_id: int,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_role(Role.ADMIN)),
):
    course = (await db.execute(select(Course).where(Course.id == course_id))).scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    for k, v in payload.items():
        if k not in ("id",) and hasattr(course, k):
            setattr(course, k, v)
    await db.commit()
    return {"id": course.id, "code": course.code, "name": course.name}


@router.delete("/{course_id}", status_code=204)
async def delete_course(
    course_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_role(Role.ADMIN)),
):
    course = (await db.execute(select(Course).where(Course.id == course_id))).scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    await db.delete(course)
    await db.commit()
