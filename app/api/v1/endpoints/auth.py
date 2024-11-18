from fastapi import APIRouter, Depends, BackgroundTasks, status
from datetime import timedelta, date, datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.schemas.token import Token
from app.utils.email_utils import send_reset_email
from app.schemas.payload import BaseResponse
from app.schemas.user import (
    UserCreateRequestDto,
    LoginUserDto,
    PasswordResetRequestDto,
    PasswordResetCompleteDto
)
from app.services.auth import (
    register_new_user,
    verify_user,
    validate_user_credentials,
    generate_password_reset_code,
    generate_and_save_verification_code,
    generate_new_access_token,
    reset_user_password
)
from app.services.token import (
    create_access_token,
    create_refresh_token,
)
from app.utils.email_utils import send_verification_email
from app.core.database import get_db

auth_router = APIRouter()


@auth_router.post("/auth/refresh")
async def refresh_access_token(refresh_token: str, db: AsyncSession = Depends(get_db)):
    return await generate_new_access_token(refresh_token, db)


@auth_router.post("/reset-password", response_model=BaseResponse)
async def reset_password(
    data: PasswordResetCompleteDto,
    db: AsyncSession = Depends(get_db)
):
    await reset_user_password(data.email, data.token, data.new_password, db)

    return BaseResponse(
        status=status.HTTP_200_OK,
        message="Password has been reset successfully.",
        payload={"email": data.email}
    )


@auth_router.post("/request-password-reset", response_model=BaseResponse)
async def request_password_reset(
    data: PasswordResetRequestDto,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):

    user, reset_code = await generate_password_reset_code(data.email, db)

    background_tasks.add_task(send_reset_email, user.email, reset_code, user.username)

    return BaseResponse(
        status=status.HTTP_200_OK,
        message="Password reset email has been sent.",
        payload={"email": user.email}
    )


@auth_router.post("/login", response_model=Token)
async def login_user(
    form_data: LoginUserDto,
    db: AsyncSession = Depends(get_db)
):
    # Authenticate the user
    user = await validate_user_credentials(db, form_data.email, form_data.password)

    # Token expiration
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    # Generate tokens
    access_token = create_access_token(
        data={"sub": str(user.uuid)},
        expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(
        data={"sub": str(user.uuid)}
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "message": f"Welcome back, {user.username}! Login successful 🎉"
    }


@auth_router.post("/resend-verification-code", status_code=status.HTTP_200_OK)
async def resend_code(email: str, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    user, new_verification_code = await generate_and_save_verification_code(email, db)

    background_tasks.add_task(
        send_verification_email,
        email=user.email,
        username=user.username,
        verification_code=new_verification_code
    )

    return BaseResponse(
        date=datetime.utcnow().date(),
        status=status.HTTP_200_OK,
        payload=f"Verification code resent to {user.email}. Please check your inbox.🥰",
        message="Verification code resent successfully."
    )



@auth_router.post("/verify", status_code=status.HTTP_200_OK)
async def verify_email(email: str, verification_code: str, db: AsyncSession = Depends(get_db)):
    return await verify_user(email, verification_code, db)



@auth_router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_user(
    create_user: UserCreateRequestDto,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    new_user = await register_new_user(create_user, db)

    background_tasks.add_task(
        send_verification_email,
        email=new_user.email,
        username=new_user.username,
        verification_code=new_user.verification_code
    )

    return BaseResponse(
        date=date.today(),
        status=int(status.HTTP_201_CREATED),
        payload=f"Please check your email to verify your account 😉: {new_user.email}",
        message="User has been registered successfully"
    )




