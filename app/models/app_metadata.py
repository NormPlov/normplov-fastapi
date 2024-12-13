from sqlalchemy import Table, Column, Boolean
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class AppMetadata(Base):
    __tablename__ = "app_metadata"
    initialized = Column(Boolean, primary_key=True, default=False)
