from fastapi import APIRouter, Depends, BackgroundTasks, status, HTTPException, Security, Request
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer
from datetime import timedelta, date, datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.schemas.token import Token, RefreshTokenRequest
from app.utils.email_utils import send_reset_email
from app.schemas.payload import BaseResponse
from app.services.oauth import oauth
from app.utils.email_utils import send_verification_email
from app.core.database import get_db
import logging
from app.schemas.user import (
    UserCreateRequest,
    LoginUser,
    PasswordResetRequest,
    PasswordResetComplete,
    VerifyRequest,
    ResendVerificationRequest
)
from app.services.auth import (
    register_new_user,
    verify_user,
    validate_user_credentials,
    generate_password_reset_code,
    generate_new_access_token,
    reset_user_password,
    set_access_cookies,
    unset_jwt_cookies,
    get_or_create_user, resend_verification_code

)
from app.services.token import (
    create_access_token,
    create_refresh_token,
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
logger = logging.getLogger(__name__)
auth_router = APIRouter()


# Redirect to Google OAuth
@auth_router.get("/google")
async def google_login(request: Request):
    redirect_uri = settings.GOOGLE_REDIRECT_URI
    return await oauth.google.authorize_redirect(request, redirect_uri)


# Handle Google OAuth callback
@auth_router.get("/google/callback")
async def google_callback(request: Request, db: AsyncSession = Depends(get_db)):
    try:
        token = await oauth.google.authorize_access_token(request)
        user_info = token.get("userinfo")
        if not user_info:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Google token.")

        user = await get_or_create_user(db, user_info)
        access_token = create_access_token(data={"sub": user.uuid})
        return {"access_token": access_token, "token_type": "bearer"}
    except Exception as e:
        logger.exception("Unexpected error in Google OAuth callback.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@auth_router.post("/refresh", response_model=dict, status_code=status.HTTP_200_OK)
async def refresh_access_token(
    data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    return await generate_new_access_token(data.refresh_token, db)


@auth_router.post("/reset-password", response_model=BaseResponse)
async def reset_password(
    data: PasswordResetComplete,
    db: AsyncSession = Depends(get_db)
):
    await reset_user_password(data.email, data.token, data.new_password, db)

    return BaseResponse(
        date=datetime.utcnow().date(),
        status=status.HTTP_200_OK,
        message="Password has been reset successfully.",
        payload={"email": data.email}
    )


@auth_router.post("/password-reset-request", response_model=BaseResponse)
async def request_password_reset_handler(
    data: PasswordResetRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    user, reset_code = await generate_password_reset_code(data.email, db)

    background_tasks.add_task(send_reset_email, user.email, reset_code, user.username)

    return BaseResponse(
        date=datetime.utcnow().date(),
        status=status.HTTP_200_OK,
        message="Password reset email has been sent.",
        payload={"email": user.email}
    )


@auth_router.post("/logout", response_model=BaseResponse)
async def logout_user():
    try:
        response = JSONResponse({
            "message": "Logout successful. See you again! 👋",
            "status": status.HTTP_200_OK
        })

        # Clear access and refresh cookies
        unset_jwt_cookies(response)
        return response

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@auth_router.post("/login", response_model=Token)
async def login_user(
    form_data: LoginUser,
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

    # Create a response and set cookies
    response = JSONResponse({
        "message": f"Welcome back, {user.username}! Login successful 🎉",
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    })

    # Set access and refresh cookies
    set_access_cookies(response, access_token, refresh_token)

    return response


@auth_router.post("/resend-verification-code", status_code=status.HTTP_200_OK)
async def resend_code(
    payload: ResendVerificationRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    user, new_verification_code = await resend_verification_code(payload.email, db)

    background_tasks.add_task(
        send_verification_email,
        email=user.email,
        username=user.username,
        verification_code=new_verification_code
    )

    logger.info(f"Verification code resent to {user.email}")

    return {
        "date": datetime.utcnow().date(),
        "status": status.HTTP_200_OK,
        "payload": f"Verification code resent to {user.email}. Please check your inbox.🥰",
        "message": "Verification code resent successfully."
    }


@auth_router.post("/verify", status_code=status.HTTP_200_OK)
async def verify_email(payload: VerifyRequest, db: AsyncSession = Depends(get_db)):
    return await verify_user(payload.email, payload.verification_code, db)


@auth_router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_user(
    create_user: UserCreateRequest,
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




