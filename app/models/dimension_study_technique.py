from sqlalchemy import Column, Integer, ForeignKey, PrimaryKeyConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base


class DimensionStudyTechnique(Base):
    __tablename__ = "dimension_study_techniques"

    dimension_id = Column(Integer, ForeignKey("dimensions.id", ondelete="CASCADE"), nullable=False)
    study_technique_id = Column(Integer, ForeignKey("study_techniques.id", ondelete="CASCADE"), nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint('dimension_id', 'study_technique_id', name='pk_dimension_study_techniques'),
    )

    dimension = relationship("Dimension", back_populates="learning_style_techniques")
    study_technique = relationship("StudyTechnique", back_populates="dimensions")