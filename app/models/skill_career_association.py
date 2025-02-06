from sqlalchemy import Column, Integer, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class SkillCareerAssociation(Base):
    __tablename__ = "skill_career_associations"

    skill_id = Column(Integer, ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True)
    career_id = Column(Integer, ForeignKey("careers.id", ondelete="CASCADE"), primary_key=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    # Define relationships with overlap resolution
    skill = relationship("Skill", back_populates="skill_career_associations",
                         overlaps="careers,skill_career_associations")
    career = relationship("Career", back_populates="skill_career_associations",
                          overlaps="skills,skill_career_associations")
