from app.models.role import Role
from app.models.user_role import UserRole
from app.models.user import User
from app.models.assessment_type import AssessmentType
from app.models.user_response import UserResponse
from app.models.dimension import Dimension
from app.models.question import Question
from app.models.user_assessment_score import UserAssessmentScore
from app.models.ai_recommendation import AIRecommendation
from app.models.learning_style_study_technique import LearningStyleStudyTechnique
from app.models.dimension_career import DimensionCareer
from app.models.skill_category import SkillCategory
from app.models.user_test import UserTest
from app.models.career import Career
from app.models.user_feedback import UserFeedback
from app.models.job import Job
from app.models.province import Province
from app.models.school import School
from app.models.major import Major
from app.models.school_major import SchoolMajor
from app.models.career_major import CareerMajor
from app.models.faculty import Faculty


__all__ = ["Role",
           "UserRole",
           "User",
           "AssessmentType",
           "UserResponse",
           "Question",
           "Dimension",
           "UserAssessmentScore",
           "AIRecommendation",
           "LearningStyleStudyTechnique",
           "DimensionCareer",
           "SkillCategory",
           "UserTest",
           "UserFeedback",
           "Job",
           "School",
           "Major",
           "SchoolMajor",
           "Faculty",
           "CareerMajor",
           "Province"
           ]

