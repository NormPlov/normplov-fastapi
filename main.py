from fastapi import FastAPI
from app.api.v1.endpoints import auth, user, assessment, ai_recommendation, test, draft, feedback
from app.api.v1.endpoints.technique_image import learning_style_image_router
from app.core.database import engine, Base, get_db
from app.core.init import init_roles_and_admin
from contextlib import asynccontextmanager
from starlette.middleware.sessions import SessionMiddleware
import os


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables after loading all models
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async for db in get_db():
        await init_roles_and_admin(db)
        break

    yield


app = FastAPI(lifespan=lifespan)


# Add SessionMiddleware for OAuth
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SECRET_KEY", "8d5f01d7a83a4c8abf0e3cb75fbdc8d56e4e23d063c08a3f6f0e5d3d62c12345"),
    session_cookie="oauth_session",
)


app.include_router(auth.auth_router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(user.user_router, prefix="/api/v1/user", tags=["user"])
app.include_router(assessment.assessment_router, prefix="/api/v1/assessment", tags=["assessment"])
app.include_router(test.test_router, prefix="/api/v1/test", tags=["test"])
app.include_router(ai_recommendation.ai_recommendation_router, prefix="/api/v1/ai", tags=["recommendations"])
app.include_router(learning_style_image_router, prefix="/api/v1/technique-image", tags=["Learning Style Images"])
app.include_router(draft.draft_router, prefix="/api/v1/draft", tags=["Draft"])
app.include_router(feedback.feedback_router, prefix="/api/v1/feedback", tags=["Feedback"])
