from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from app.schemas.user import UserCreateRequest, UserResponse
from app.services.auth_service import register_user
from app.core.database import get_db

router = APIRouter()

@router.post("/register", response_model=UserResponse)
async def register(data: UserCreateRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    return await register_user(data, db, background_tasks)
