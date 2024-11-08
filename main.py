from fastapi import FastAPI
from app.api.v1.endpoints import auth
from app.core.database import Base, engine

Base.metadata.create_all(bind=engine)

app = FastAPI()

app.include_router(auth.router, prefix="/api/v1", tags=["auth"])
