import logging
from fastapi import HTTPException, status
from jose import jwt, JWTError
from app.core.config import settings

logger = logging.getLogger(__name__)


def decode_jwt_token(token: str) -> dict:

    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        user_uuid = payload.get("sub")
        if not user_uuid:
            logger.warning("Token payload missing 'sub' claim.")
            raise ValueError("Missing 'sub' in token payload.")
        return {"uuid": user_uuid}
    except JWTError as e:
        logger.error(f"JWT decoding failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Unexpected error decoding token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while decoding the token.",
        )


def decode_jwt_token_for_public(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        logger.debug(f"Decoded JWT payload (public): {payload}")

        # Extract 'sub' as 'uuid' without raising an error if missing
        user_uuid = payload.get("sub")
        if not user_uuid:
            logger.debug("Token payload for public endpoint does not contain 'sub'.")
            return {}

        return {"uuid": user_uuid}
    except JWTError as e:
        logger.warning(f"JWT decoding failed for public: {e}")
        return {}
    except Exception as e:
        logger.error(f"Unexpected error decoding token for public: {e}")
        return {}

