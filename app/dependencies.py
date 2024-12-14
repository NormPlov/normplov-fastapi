import logging

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
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


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:

    try:
        return decode_jwt_token(token)
    except Exception as e:
        logger.error(f"Error in get_current_user: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user_data(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    try:
        user_uuid = current_user.get("uuid")
        if not user_uuid:
            logger.error("Missing UUID in current user data.")
            raise format_http_exception(
                status_code=status.HTTP_401_UNAUTHORIZED,
                message="Authentication required.",
                details="Invalid user data.",
            )

        logger.info(f"Fetching user data for UUID: {user_uuid}")

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
            logger.warning(f"Blocked user attempted access: UUID {user.uuid}")
            raise format_http_exception(
                status_code=status.HTTP_403_FORBIDDEN,
                message="Permission denied.",
                details="User is blocked. Contact support.",
            )

        validate_authentication(user)

        return user
    except Exception as e:
        logger.error(f"Error in get_current_user_data: {e}")
        raise format_http_exception(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="An error occurred while retrieving user data.",
            details=str(e),
        )


async def is_admin_user(current_user: User = Depends(get_current_user_data)) -> User:
    try:

        validate_authentication(current_user)

        if not any(role.role.name == "ADMIN" for role in current_user.roles):
            logger.warning(f"Non-admin user attempted admin-only action: UUID {current_user.uuid}")
            raise format_http_exception(
                status_code=status.HTTP_403_FORBIDDEN,
                message="Permission denied.",
                details="You do not have permission to perform this action.",
            )

        return current_user
    except Exception as e:
        logger.error(f"Error in is_admin_user: {e}")
        raise format_http_exception(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="An error occurred while checking admin privileges.",
            details=str(e),
        )
