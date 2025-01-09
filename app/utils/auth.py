import logging
from fastapi import HTTPException, status
from jose import jwt, JWTError
from app.core.config import settings

logger = logging.getLogger(__name__)


def decode_jwt_token_for_data(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])

        user_uuid = payload.get("sub")
        if not user_uuid:
            raise ValueError("Missing 'sub' in token payload.")

        return {"uuid": user_uuid}
    except JWTError as e:
        logger.error(f"JWT decoding failed for data: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token for user data.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while decoding the token for user data.",
        )


def decode_jwt_token_for_public(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])

        user_uuid = payload.get("sub")
        if not user_uuid:
            return {}

        return {"uuid": user_uuid}
    except JWTError as e:
        return {}
    except Exception as e:
        return {}

