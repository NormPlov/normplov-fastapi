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

logger = logging.getLogger(__name__)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_optional_token(authorization: str = Depends(oauth2_scheme)) -> Optional[str]:
    logger.debug(f"Raw Authorization header: {authorization}")
    if not authorization:
        logger.debug("Authorization header missing.")
        return None
    return authorization


async def get_current_user(token: Optional[str] = Depends(get_optional_token)) -> Optional[dict]:
    if not token:
        return None

    try:
        decoded_token = decode_jwt_token(token)
        return decoded_token
    except Exception as e:
        return None


async def get_current_user_public(
    current_user: Optional[dict] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    if not current_user:
        logger.debug("No current user found. Proceeding as public access.")
        return None

    try:
        user_uuid = current_user.get("sub")
        stmt = (
            select(User)
            .options(joinedload(User.roles).joinedload(UserRole.role))
            .where(User.uuid == user_uuid)
        )
        result = await db.execute(stmt)
        user = result.scalars().first()
        if user:
            logger.debug(f"Authenticated user: {user.username} (UUID: {user_uuid})")
        else:
            logger.debug(f"No user found for UUID: {user_uuid}.")
        return user
    except Exception as e:
        logger.error(f"Error retrieving public user data: {e}")
        return None


async def get_current_user_data(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    if not current_user:
        logger.error("Authentication failed: No current user.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": True,
                "message": "Authentication required.",
                "details": "User is not authenticated. Please log in.",
            },
        )

    user_uuid = current_user.get("uuid")
    logger.debug(f"User UUID from token: {user_uuid}")
    if not user_uuid:
        logger.error("Token missing 'uuid' claim.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User UUID not found in token.",
        )

    stmt = select(User).where(User.uuid == user_uuid)
    result = await db.execute(stmt)
    user = result.scalars().first()

    if not user:
        logger.error(f"User with UUID {user_uuid} not found in database.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found. Please log in.",
        )

    return user


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