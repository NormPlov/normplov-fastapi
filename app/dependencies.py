import logging

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.exceptions.formatters import format_http_exception
from app.utils.auth import decode_jwt_token
from app.core.database import get_db
from app.utils.auth_validators import validate_authentication
from sqlalchemy.orm import joinedload
from app.models import User, UserRole

logger = logging.getLogger(__name__)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    try:
        return decode_jwt_token(token)
    except Exception as e:
        logger.error(f"Error in get_current_user: {e}")
        raise format_http_exception(
            status_code=status.HTTP_401_UNAUTHORIZED,
            message="🚫 Oops! No credentials found. Are you even allowed here? 🤔",
            details={"icon": "🔒", "hint": "Check your login details and try again."}
        )


async def get_current_user_data(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    try:
        user_uuid = current_user.get("uuid")
        if not user_uuid:
            raise format_http_exception(
                status_code=status.HTTP_401_UNAUTHORIZED,
                message="Authentication required.",
                details="Invalid user data.",
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
    except Exception as e:
        raise format_http_exception(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="An error occurred while retrieving user data.",
            details=str(e),
        )


async def is_admin_user(current_user: User = Depends(get_current_user_data)) -> User:
    try:
        if not current_user:
            raise format_http_exception(
                status_code=status.HTTP_401_UNAUTHORIZED,
                message="🔒 Whoops! You need to log in first.",
                details="No current user found. Please log in to access this resource.",
            )

        # Validate user authentication (e.g., not blocked, etc.)
        validate_authentication(current_user)

        # Check if the user has the "ADMIN" role
        if not current_user.roles or not any(role.role.name == "ADMIN" for role in current_user.roles):
            raise format_http_exception(
                status_code=status.HTTP_403_FORBIDDEN,
                message="⛔ Access Denied! Not so fast, partner.",
                details="It seems you left your admin badge at home. Only admins can perform this action.",
            )

        # Return the authenticated admin user
        return current_user

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Unexpected error while checking admin privileges: {e}")
        raise format_http_exception(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="⚠️ Something went wrong while verifying admin status.",
            details=str(e),
        )

