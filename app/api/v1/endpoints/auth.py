from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, status
from sqlalchemy.orm import Session
from datetime import timedelta

from app.core.config import settings
from app.schemas.user import UserCreateRequest, UserResponse, LoginUserDto, PasswordResetRequest, PasswordResetComplete
from app.schemas.token import Token
from app.utils.email_utils import send_reset_email
from app.services.auth import register_user, verify_user, authenticate_user, create_access_token, create_refresh_token, create_password_reset_code, verify_password_reset_code, reset_password, resend_verification_code
from app.core.database import get_db
from app.models.user import User

router = APIRouter()

@router.post("/request-password-reset")
async def request_password_reset(
    data: PasswordResetRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User with this email does not exist."
        )

    # Generate and save the reset code
    reset_code = create_password_reset_code(user, db)

    # Send reset email with the reset code
    background_tasks.add_task(send_reset_email, user.email, reset_code, user.username)

    return {"message": "Password reset email has been sent."}


@router.post("/reset-password")
async def reset_password_route(data: PasswordResetComplete, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.reset_password_code == data.token).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired token."
        )

    # Verify the reset code
    if not verify_password_reset_code(user, data.token):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset code."
        )

    # Reset the password
    reset_password(user, data.new_password, db)

    return {"message": "Password reset successful."}


@router.post("/login", response_model=Token)
async def login_for_access_token(
        form_data: LoginUserDto,
        db: Session = Depends(get_db)
):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(
        data={"sub": user.username}
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.post("/resend-verification-code")
async def resend_code(email: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    return resend_verification_code(email, db, background_tasks)


@router.post("/verify")
def verify_email(email: str, verification_code: str, db: Session = Depends(get_db)):
    return verify_user(email, verification_code, db)


@router.post("/register", response_model=UserResponse)
async def register(data: UserCreateRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    return await register_user(data, db, background_tasks)

