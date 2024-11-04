from sqlalchemy.orm import Session
from fastapi import HTTPException, BackgroundTasks
from datetime import datetime, timedelta

from app.models.user import User
from app.schemas.user import UserCreateRequest
from app.core.security import get_password_hash, generate_verification_code
from app.utils.email_utils import send_verification_email

def generate_code_expiration(minutes: int) -> datetime:
    return datetime.utcnow() + timedelta(minutes=minutes)

async def register_user(data: UserCreateRequest, db: Session, background_tasks: BackgroundTasks):
    existing_user = db.query(User).filter(
        (User.email == data.email) | (User.username == data.username)
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=422,
            detail="Username or email is already registered."
        )

    # Generate verification code and its expiration time
    verification_code = generate_verification_code()
    expiration_time = generate_code_expiration(minutes=15)

    new_user = User(
        username=data.username,
        email=data.email,
        password=get_password_hash(data.password),
        verification_code=verification_code,
        verification_code_expiration=expiration_time,
        is_active=False,
        is_verified=False,
        registered_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    background_tasks.add_task(
        send_verification_email,
        email=new_user.email,
        username=new_user.username,
        verification_code=verification_code
    )

    return new_user
