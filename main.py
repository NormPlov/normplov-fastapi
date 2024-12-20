import asyncio
import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.database import engine, Base, get_db
from app.core.init import init_roles_and_admin, create_static_users_batched
from contextlib import asynccontextmanager
from starlette.middleware.sessions import SessionMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.future import select
from app.models.app_metadata import AppMetadata
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from app.services.job import disable_expired_jobs_with_raw_query
from app.api.v1.endpoints import (
    auth,
    user,
    assessment,
    ai_recommendation,
    test,
    draft,
    feedback,
    school,
    faculty,
    major,
    job,
    dimension,
    province,
    admin
)

scheduler = AsyncIOScheduler()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def disable_expired_jobs_task():
    logger.info("Running scheduled task: Disabling expired jobs.")
    try:
        await disable_expired_jobs_with_raw_query()
        logger.info("Successfully disabled expired jobs.")
    except Exception as e:
        logger.error(f"Error in scheduled task: {str(e)}")
    logger.info("Scheduled task completed.")


def setup_scheduled_jobs():
    logger.info("Setting up scheduled jobs...")
    scheduler.add_job(
        lambda: asyncio.run(disable_expired_jobs_task()),
        trigger=IntervalTrigger(seconds=30),
        id="disable_expired_jobs",
        replace_existing=True,
    )
    logger.info("Scheduled job 'disable_expired_jobs' added.")
    scheduler.start()
    logger.info("Scheduler started.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async for db in get_db():
        metadata_stmt = select(AppMetadata).limit(1)
        result = await db.execute(metadata_stmt)
        metadata = result.scalars().first()

        if not metadata:
            metadata = AppMetadata(initialized=False)
            db.add(metadata)
            await db.commit()
            await db.refresh(metadata)

        if not metadata.initialized:
            await init_roles_and_admin(db)
            await create_static_users_batched(db, num_users=100)

            metadata.initialized = True
            await db.commit()

        break

    yield


app = FastAPI(lifespan=lifespan)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://normplov-api.shinoshike.studio",
        "https://dev-normplov.shinoshike.studio",
        "https://deploy-norm-plov-v4.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["authorization", "content-type"],
    max_age=600,
)


# Add SessionMiddleware for OAuth
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SECRET_KEY", "8d5f01d7a83a4c8abf0e3cb75fbdc8d56e4e23d063c08a3f6f0e5d3d62c12345"),
    session_cookie="oauth_session",
)


app.include_router(auth.auth_router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(user.user_router, prefix="/api/v1/user", tags=["User"])
app.include_router(assessment.assessment_router, prefix="/api/v1/assessment", tags=["Assessment"])
app.include_router(dimension.dimension_router, prefix="/api/v1/dimension", tags=["Dimension"])
app.include_router(test.test_router, prefix="/api/v1/test", tags=["Test"])
app.include_router(ai_recommendation.ai_recommendation_router, prefix="/api/v1/ai", tags=["Recommendation"])
app.include_router(draft.draft_router, prefix="/api/v1/draft", tags=["Draft"])
app.include_router(feedback.feedback_router, prefix="/api/v1/feedback", tags=["Feedback"])
app.include_router(province.province_router, prefix="/api/v1/provinces", tags=["Province"])
app.include_router(school.school_router, prefix="/api/v1/schools", tags=["School"])
app.include_router(faculty.faculty_router, prefix="/api/v1/faculties", tags=["Faculty"])
app.include_router(major.major_router, prefix="/api/v1/majors", tags=["Major"])
app.include_router(job.job_router, prefix="/api/v1/jobs", tags=["Job"])
app.include_router(admin.admin_router, prefix="/api/v1/admin", tags=["Admin"])


@app.on_event("startup")
async def startup_event():
    logger.info("Application startup event triggered.")
    setup_scheduled_jobs()


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down scheduler...")
    scheduler.shutdown(wait=False)


