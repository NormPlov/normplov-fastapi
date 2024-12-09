import logging

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

logger = logging.getLogger(__name__)


SQLALCHEMY_DATABASE_URL = settings.database_url
engine = create_async_engine(SQLALCHEMY_DATABASE_URL, echo=True)

SessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

Base = declarative_base()


async def get_db():
    async with SessionLocal() as db:
        try:
            yield db
        except Exception as e:
            logger.error(f"Error occurred in database session: {str(e)}")
            raise
        finally:
            await db.close()
