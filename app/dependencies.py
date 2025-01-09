import logging
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from app.exceptions.formatters import format_http_exception
from app.models import UserRole
from app.utils.auth import decode_jwt_token_for_data, decode_jwt_token_for_public
from app.core.database import get_db
from app.models.user import User
from app.utils.auth_validators import validate_authentication

logger = logging.getLogger(__name__)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


async def get_optional_token(authorization: str = Depends(oauth2_scheme)) -> Optional[str]:
    if not authorization:
        return None
    return authorization


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    try:
        # Decode the token and return the user dictionary
        return decode_jwt_token_for_data(token)
    except Exception as e:
        logger.error(f"Error in get_current_user: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
        )


async def get_current_user_public(
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    try:
        if not token:
            logger.debug("No token provided.")
            return None

        logger.debug(f"Received token: {token}")

        # Decode the token
        decoded_token = decode_jwt_token_for_public(token)
        logger.debug(f"Decoded token: {decoded_token}")

        user_uuid = decoded_token.get("uuid")  # Use 'uuid' instead of 'sub'
        if not user_uuid:
            logger.debug("Decoded token does not contain 'uuid'.")
            return None

        logger.debug(f"Decoded user UUID from token: {user_uuid}")

        # Query the user in the database
        stmt = select(User).where(User.uuid == user_uuid)
        result = await db.execute(stmt)
        user = result.scalars().first()

        if user:
            logger.debug(f"Authenticated user found: {user.username}")
        else:
            logger.debug(f"No user found for UUID: {user_uuid}.")

        return user
    except Exception as e:
        return None


async def get_current_user_data(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    try:
        user_uuid = current_user.get("uuid")
        if not user_uuid:
            logger.error(f"Invalid current_user structure: {current_user}")
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
            logger.warning(f"User {user_uuid} is blocked.")
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
            raise format_http_exception(
                status_code=status.HTTP_403_FORBIDDEN,
                message="Permission denied.",
                details="You do not have permission to perform this action.",
            )

        return current_user
    except Exception as e:
        raise format_http_exception(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="An error occurred while checking admin privileges.",
            details=str(e),
        )