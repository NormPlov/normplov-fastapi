import logging
import jwt
import httpx

from fastapi import APIRouter, BackgroundTasks, status, Depends, HTTPException
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import get_db
from app.models import RefreshToken
from app.schemas.payload import BaseResponse
from app.schemas.token import RefreshTokenRequest, OAuthCallbackRequest
from app.services.token import create_refresh_token, create_access_token
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


@auth_router.post("/facebook", response_model=BaseResponse, status_code=200)
async def facebook_callback(
        request: OAuthCallbackRequest,
        db: AsyncSession = Depends(get_db)
):
    logger.info("Received Facebook auth request")

    try:
        async with httpx.AsyncClient() as client:
            token_url = "https://graph.facebook.com/v12.0/oauth/access_token"
            data = {
                "code": request.code,
                "client_id": settings.FACEBOOK_CLIENT_ID,
                "client_secret": settings.FACEBOOK_CLIENT_SECRET,
                "redirect_uri": "http://localhost:5173/auth/facebook/callback",
            }

            response = await client.post(token_url, params=data)
            token_data = response.json()

            if "access_token" not in token_data:
                raise HTTPException(
                    status_code=401,
                    detail=f"Invalid token response from Facebook: {token_data}",
                )

        access_token = token_data["access_token"]

        user_info_url = "https://graph.facebook.com/me"
        params = {
            "fields": "id,name,email,picture",
            "access_token": access_token,
        }
        user_info_response = await client.get(user_info_url, params=params)
        user_info = user_info_response.json()

        if "email" not in user_info:
            raise HTTPException(
                status_code=400,
                detail="Email permission not granted. Unable to retrieve email address.",
            )

        user_response = await get_or_create_user(db, user_info)
        user = user_response["user"]

        app_access_token = create_access_token({"sub": user.uuid})
        app_refresh_token = create_refresh_token({"sub": user.uuid})

        refresh_token_entry = RefreshToken(
            user_id=user.id,
            token=app_refresh_token,
            expires_at=datetime.utcnow() + timedelta(days=7)
        )
        db.add(refresh_token_entry)
        await db.commit()

        return BaseResponse(
            status=200,
            message="Facebook authentication successful",
            date=datetime.utcnow(),
            payload={
                "user": user_response["payload"],
                "access_token": app_access_token,
                "refresh_token": app_refresh_token,
            },
        )

    except HTTPException as http_exc:
        raise http_exc

    except Exception as e:
        logger.error(f"Error during Facebook authentication: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error during Facebook OAuth: {str(e)}",
        )


# @auth_router.post("/google", response_model=BaseResponse, status_code=200)
# async def google_callback(
#         request: OAuthCallbackRequest,
#         db: AsyncSession = Depends(get_db)
# ):
#     logger.info("Received Google auth request")
#
#     try:
#         async with httpx.AsyncClient() as client:
#             token_url = "https://oauth2.googleapis.com/token"
#             data = {
#                 "code": request.code,
#                 "client_id": settings.GOOGLE_CLIENT_ID,
#                 "client_secret": settings.GOOGLE_CLIENT_SECRET,
#                 "redirect_uri": "http://localhost:3000/auth/google/callback",
#                 "grant_type": "authorization_code",
#             }
#
#             response = await client.post(token_url, data=data)
#             token_data = response.json()
#
#             if "id_token" not in token_data:
#                 raise HTTPException(
#                     status_code=401,
#                     detail=f"Invalid token response from Google: {token_data}",
#                 )
#
#         id_token = token_data["id_token"]
#         user_info = jwt.decode(id_token, algorithms=["RS256"], options={"verify_signature": False})
#         logger.info(f"Decoded user info: {user_info}")
#
#         user_response = await get_or_create_user(db, user_info)
#         user = user_response["payload"]
#
#         access_token = create_access_token({"sub": user.uuid})
#         refresh_token = create_refresh_token({"sub": user.uuid})
#
#         refresh_token_entry = RefreshToken(
#             user_id=user.id,
#             token=refresh_token,
#             expires_at=datetime.utcnow() + timedelta(days=7)
#         )
#         db.add(refresh_token_entry)
#         await db.commit()
#
#         response_payload = {
#             "status": 200,
#             "message": "Google authentication successful",
#             "date": datetime.utcnow().isoformat(),
#             "user": {
#                 "payload": user_response["payload"],
#             },
#         }
#
#         response = JSONResponse(content=response_payload)
#         response.set_cookie(
#             key="access_token",
#             value=access_token,
#             httponly=True,
#             secure=True,
#             samesite="Lax",
#             max_age=60 * 15  # 15 minutes
#         )
#         response.set_cookie(
#             key="refresh_token",
#             value=refresh_token,
#             httponly=True,
#             secure=True,
#             samesite="Lax",
#             max_age=60 * 60 * 24 * 7  # 7 days
#         )
#
#         return response
#
#     except HTTPException as http_exc:
#         raise http_exc
#
#     except Exception as e:
#         logger.error(f"Error during Google authentication: {str(e)}")
#         raise HTTPException(
#             status_code=500,
#             detail=f"Unexpected error during Google OAuth: {str(e)}",
#         )

@auth_router.post("/google", response_model=dict, status_code=200)
async def google_callback(
        request: OAuthCallbackRequest,
        db: AsyncSession = Depends(get_db)
):
    logger.info("Received Google auth request")

    try:
        async with httpx.AsyncClient() as client:
            token_url = "https://oauth2.googleapis.com/token"
            data = {
                "code": request.code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": "http://localhost:3000/auth/google/callback",
                "grant_type": "authorization_code",
            }

            response = await client.post(token_url, data=data)
            token_data = response.json()

            if "id_token" not in token_data:
                raise HTTPException(
                    status_code=401,
                    detail=f"Invalid token response from Google: {token_data}",
                )

        id_token = token_data["id_token"]
        user_info = jwt.decode(id_token, algorithms=["RS256"], options={"verify_signature": False})
        logger.info(f"Decoded user info: {user_info}")

        user = await get_or_create_user(db, user_info)

        access_token = create_access_token(data={"sub": user["uuid"]})
        refresh_token = create_refresh_token(data={"sub": user["uuid"]})

        refresh_token_entry = RefreshToken(
            user_id=user["id"],
            token=refresh_token,
            expires_at=datetime.utcnow() + timedelta(days=7)
        )
        db.add(refresh_token_entry)
        await db.commit()

        response_payload = {
            "accessToken": access_token,
            "payload": {
                "uuid": user["uuid"],
                "username": user["username"],
                "email": user["email"],
                "avatar": user["avatar"],
                "roles": user["roles"],
            },
            "tokenType": "bearer",
            "message": "Google authentication successful"
        }

        response = JSONResponse(content=response_payload)
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=True,
            samesite="Lax",
            max_age=60 * 15  # 15 minutes
        )
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=True,
            samesite="Lax",
            max_age=60 * 60 * 24 * 7  # 7 days
        )

        return response

    except HTTPException as http_exc:
        raise http_exc

    except Exception as e:
        logger.error(f"Error during Google authentication: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error during Google OAuth: {str(e)}",
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
