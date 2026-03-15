"""Internal marks endpoints – stub."""
from fastapi import APIRouter
router = APIRouter()

@router.get("")
async def list_marks():
    return []
