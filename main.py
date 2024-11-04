from fastapi import FastAPI
from app.api.v1.endpoints import users
from app.core.database import Base, engine

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI()

# Register API routes
app.include_router(users.router, prefix="/api/v1", tags=["users"])
