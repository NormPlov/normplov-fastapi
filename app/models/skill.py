from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.core.database import Base


class Skill(Base):
    __tablename__ = "skills"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String, unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    skill_name = Column(String, nullable=False)
    skill_description = Column(String, nullable=True)
    skill_category_id = Column(Integer, ForeignKey("skill_categories.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=True, onupdate=func.now())

    # Relationships
    skill_category = relationship("SkillCategory", back_populates="skills")
    skill_career_associations = relationship("SkillCareerAssociation", back_populates="skill",
                                             cascade="all, delete-orphan")
    careers = relationship("Career", secondary="skill_career_associations", back_populates="skills")

