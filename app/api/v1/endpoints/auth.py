import logging

from fastapi import APIRouter, BackgroundTasks, status, Request, Depends, HTTPException
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import get_db
from app.schemas.payload import BaseResponse
from app.schemas.token import RefreshTokenRequest
from app.services.oauth import oauth
from app.utils.email import send_verification_email, send_reset_email
from app.services.auth import (
    get_or_create_user,
    generate_new_access_token,
    reset_user_password,
    generate_password_reset_code,
    verify_user, unset_jwt_cookies,
    resend_verification_code,
    register_new_user,
    perform_login, verify_reset_password, resend_reset_password_code
)
from app.schemas.user import (
    UserCreateRequest,
    LoginUser,
    PasswordResetRequest,
    PasswordResetComplete,
    VerifyRequest,
    ResendVerificationRequest, ResendResetPasswordRequest, VerifyResetPasswordResponse, VerifyResetPasswordRequest
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
logger = logging.getLogger(__name__)
auth_router = APIRouter()


@auth_router.get("/google")
async def google_login(request: Request):
    redirect_uri = settings.GOOGLE_REDIRECT_URI
    return await oauth.google.authorize_redirect(request, redirect_uri)


@auth_router.get("/google/callback", response_model=BaseResponse, status_code=status.HTTP_200_OK)
async def google_callback(request: Request, db: AsyncSession = Depends(get_db)):

    try:
        token = await oauth.google.authorize_access_token(request)
        user_info = token.get("userinfo")

        if not user_info:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Google token."
            )

        response = await get_or_create_user(db=db, user_info=user_info)
        return response

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error during Google OAuth callback: {str(e)}"
        )


@auth_router.post("/login", response_model=BaseResponse)
async def login_user(
    form_data: LoginUser,
    db: AsyncSession = Depends(get_db)
):
    return await perform_login(db, form_data.email, form_data.password)


@auth_router.post("/refresh", response_model=BaseResponse)
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
    response = await reset_user_password(
        email=data.email,
        reset_code=data.reset_code,
        new_password=data.new_password,
        db=db
    )
    return response


@auth_router.post(
    "/verify-reset-password",
    response_model=VerifyResetPasswordResponse,
    status_code=status.HTTP_200_OK
)
async def verify_reset_password_route(
    request: VerifyResetPasswordRequest,
    db: AsyncSession = Depends(get_db)
):
    return await verify_reset_password(request, db)


@auth_router.post("/resend-reset-password", response_model=BaseResponse)
async def resend_reset_password_code_endpoint(
    request: ResendResetPasswordRequest,
    db: AsyncSession = Depends(get_db)
):
    try:
        response = await resend_reset_password_code(request.email, db)
        return response
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while resending the reset password code: {str(e)}",
        )


@auth_router.post("/password-reset-request", response_model=BaseResponse)
async def request_password_reset_handler(
    data: PasswordResetRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    response = await generate_password_reset_code(data.email, db)
    username = response.payload.get("username")
    reset_code = response.payload["reset_code"]
    background_tasks.add_task(send_reset_email, data.email, reset_code, username)
    return response


@auth_router.post("/verify", response_model=BaseResponse)
async def verify_email(
    payload: VerifyRequest,
    db: AsyncSession = Depends(get_db)
):
    return await verify_user(payload.email, payload.verification_code, db)


@auth_router.post("/logout", response_model=BaseResponse)
async def logout_user():
    try:
        response = JSONResponse({
            "message": "Logout successful. See you again! 👋",
            "status": status.HTTP_200_OK
        })

        # Clear access and refresh cookies
        unset_jwt_cookies(response)
        return BaseResponse(
            date=datetime.utcnow().strftime("%d-%B-%Y"),
            status=status.HTTP_200_OK,
            message="Logout successful. See you again! 👋",
            payload={}
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@auth_router.post("/resend-verification-code", response_model=BaseResponse)
async def resend_code(
    payload: ResendVerificationRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    try:
        response = await resend_verification_code(payload.email, db)

        background_tasks.add_task(
            send_verification_email,
            email=response.payload["email"],
            username=response.payload["username"],
            verification_code=response.payload["verification_code"]
        )

        return response

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while resending the verification code: {str(e)}"
        )


@auth_router.post("/register", response_model=BaseResponse)
async def register_user(
    create_user: UserCreateRequest,
    db: AsyncSession = Depends(get_db)
):
    return await register_new_user(create_user, db)


