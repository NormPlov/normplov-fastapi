from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from app.core.config import settings
from app.core.database import get_db
from app.models import UserRole
from app.models.user import User
import logging

logger = logging.getLogger(__name__)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:

    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        user_uuid: str = payload.get("sub")
        if not user_uuid:
            logger.warning("Token payload missing 'sub' claim.")
            raise credentials_exception
        return {"uuid": user_uuid}
    except JWTError as e:
        logger.error(f"JWT validation error: {str(e)}")
        raise credentials_exception
    except Exception as e:
        logger.error(f"Unexpected error in token processing: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred during authentication.",
        )


async def get_current_user_data(

    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    try:
        stmt = (
            select(User)
            .options(joinedload(User.roles).joinedload(UserRole.role))
            .where(User.uuid == current_user["uuid"])
        )
        result = await db.execute(stmt)
        user = result.scalars().first()

        if not user:
            logger.warning(f"User with UUID {current_user['uuid']} not found.")
            raise HTTPException(status_code=401, detail="Invalid user.")

        if user.is_blocked:
            logger.warning(f"Blocked user attempted access: UUID {user.uuid}")
            raise HTTPException(status_code=403, detail="User is blocked. Contact support.")

        return user
    except Exception as e:
        logger.error(f"Error fetching user data: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while retrieving user data.",
        )


async def is_admin_user(
    current_user: User = Depends(get_current_user_data),
):
    if not any(user_role.role.name == "ADMIN" for user_role in current_user.roles):
        raise HTTPException(
            status_code=403, detail="You do not have permission to perform this action."
        )
    return current_user
