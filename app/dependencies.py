import logging

from typing import Optional
from fastapi import Depends, status, HTTPException
from fastapi.security import OAuth2PasswordBearer, SecurityScopes
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from app.exceptions.formatters import format_http_exception
from app.models import UserRole
from app.utils.auth import decode_jwt_token
from app.core.database import get_db
from app.models.user import User
from app.utils.auth_validators import validate_authentication
from fastapi.security.utils import get_authorization_scheme_param

logger = logging.getLogger(__name__)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


async def get_optional_token(
    security_scopes: SecurityScopes, authorization: str = Depends(oauth2_scheme)
) -> Optional[str]:
    scheme, token = get_authorization_scheme_param(authorization)
    if not token:
        return None
    return token



async def get_current_user(token: Optional[str] = Depends(get_optional_token)) -> Optional[dict]:
    if not token:
        return None

    try:
        return decode_jwt_token(token)
    except Exception as e:
        logger.error(f"JWT decoding failed: {e}")
        return None


async def get_current_user_public(
    current_user: Optional[dict] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    if not current_user:
        return None

    try:
        user_uuid = current_user.get("uuid")
        stmt = (
            select(User)
            .options(joinedload(User.roles).joinedload(UserRole.role))
            .where(User.uuid == user_uuid)
        )
        result = await db.execute(stmt)
        return result.scalars().first()
    except Exception as e:
        logger.error(f"Error retrieving public user data: {e}")
        return None


async def get_current_user_data(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": True,
                "message": "Authentication required.",
                "details": "User is not authenticated. Please log in.",
            },
        )
    try:
        user_uuid = current_user.get("uuid")
        if not user_uuid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": True,
                    "message": "Authentication required.",
                    "details": "User UUID not found in token.",
                },
            )

        stmt = (
            select(User)
            .options(joinedload(User.roles).joinedload(UserRole.role))
            .where(User.uuid == user_uuid)
        )
        result = await db.execute(stmt)
        user = result.scalars().first()

        if not user:
            logger.warning(f"User with UUID {user_uuid} not found.")
            raise format_http_exception(
                status_code=status.HTTP_401_UNAUTHORIZED,
                message="Authentication required.",
                details="User not found.",
            )

        if user.is_blocked:
            raise format_http_exception(
                status_code=status.HTTP_403_FORBIDDEN,
                message="Permission denied.",
                details="User is blocked. Contact support.",
            )

        validate_authentication(user)

        return user
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise format_http_exception(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="An error occurred while retrieving user data.",
            details=str(e),
        )


async def is_admin_user(current_user: User = Depends(get_current_user_data)) -> User:
    try:
        validate_authentication(current_user)

        if not any(role.role.name == "ADMIN" for role in current_user.roles):
            raise format_http_exception(
                status_code=status.HTTP_403_FORBIDDEN,
                message="Permission denied.",
                details="You do not have permission to perform this action.",
            )

        return current_user
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise format_http_exception(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="An error occurred while checking admin privileges.",
            details=str(e),
        )