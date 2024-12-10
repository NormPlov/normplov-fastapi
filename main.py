import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.endpoints.technique_image import learning_style_image_router
from app.core.database import engine, Base, get_db
from app.core.init import init_roles_and_admin
from contextlib import asynccontextmanager
from starlette.middleware.sessions import SessionMiddleware
from fastapi.staticfiles import StaticFiles
from app.api.v1.endpoints import (
    auth,
    user,
    assessment,
    ai_recommendation,
    test,
    draft,
    feedback,
    job_category,
    school,
    faculty,
    major,
    job,
    company,
    dimension
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async for db in get_db():
        await init_roles_and_admin(db)
        break

    yield


app = FastAPI(lifespan=lifespan)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
app.include_router(learning_style_image_router, prefix="/api/v1/technique-image", tags=["Learning Style Images"])
app.include_router(draft.draft_router, prefix="/api/v1/draft", tags=["Draft"])
app.include_router(feedback.feedback_router, prefix="/api/v1/feedback", tags=["Feedback"])
app.include_router(job_category.job_category_router, prefix="/api/v1/job-categories", tags=["Job Categories"])
app.include_router(school.school_router, prefix="/api/v1/schools", tags=["School"])
app.include_router(faculty.faculty_router, prefix="/api/v1/faculties", tags=["Faculty"])
app.include_router(major.major_router, prefix="/api/v1/majors", tags=["Major"])
app.include_router(job.job_router, prefix="/api/v1/jobs", tags=["Job"])
app.include_router(company.company_router, prefix="/api/v1/companies", tags=["Company"])

