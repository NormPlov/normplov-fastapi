from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from app.core.config import settings
from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.core.database import get_db
from app.models import UserRole
from app.models.user import User
from sqlalchemy.orm import joinedload

# Define the OAuth2 password flow
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # Decode JWT token
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        user_uuid: str = payload.get("sub")  # Extract the UUID
        if not user_uuid:
            raise credentials_exception
        return {"uuid": user_uuid}
    except JWTError:
        raise credentials_exception


# Dependency to fetch the current user from the database using their UUID
async def get_current_user_data(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(User).options(joinedload(User.roles).joinedload(UserRole.role)).where(User.uuid == current_user["uuid"])
    result = await db.execute(stmt)
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid user")
    return user