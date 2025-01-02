from typing import Dict

import pandas as pd
import logging
import uuid
import json

from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from fastapi import HTTPException
from app.models import (
    SkillCategory,
    DimensionCareer,
    UserAssessmentScore,
    UserResponse,
    AssessmentType,
    UserTest,
    CareerMajor,
    Major,
    School,
    SchoolMajor
)
from app.models.dimension import Dimension
from app.services.test import create_user_test
from app.schemas.skill_assessment import SkillAssessmentInput, SkillAssessmentResponse, CareerWithMajors, MajorWithSchools
from ml_models.model_loader import load_skill_model

logger = logging.getLogger(__name__)

# Load skill assessment model and encoders
skill_model, skill_encoders = load_skill_model()


async def get_assessment_type_id(name: str, db: AsyncSession) -> int:
    stmt = select(AssessmentType.id).where(AssessmentType.name == name)
    result = await db.execute(stmt)
    assessment_type_id = result.scalars().first()

    if not assessment_type_id:
        raise HTTPException(
            status_code=404, detail=f"Assessment type '{name}' not found."
        )

    return assessment_type_id


# async def predict_skills(
#     responses: Dict[str, float],
#     db: AsyncSession,
#     current_user
# ) -> SkillAssessmentResponse:
#
#     try:
#         user_id = current_user.id
#         user_uuid = current_user.uuid
#
#         assessment_type_id = await get_assessment_type_id("Skills", db)
#
#         try:
#             user_test = await create_user_test(db, current_user.id, assessment_type_id)
#             logger.debug(f"Created new test: uuid={user_test.uuid}, name={user_test.name}")
#         except Exception as e:
#             logger.error(f"Failed to create test for user_id={current_user.id}: {e}")
#             await db.rollback()
#             raise HTTPException(status_code=500, detail="Failed to create a new test.")
#
#         input_df = pd.DataFrame([responses])
#         input_df = input_df.reindex(columns=skill_model.feature_names_in_, fill_value=0)
#
#         predictions = skill_model.predict(input_df)
#
#         target_columns = list(skill_encoders.keys())
#         predicted_labels = {
#             column: skill_encoders[column].inverse_transform([predictions[0][idx]])[0]
#             for idx, column in enumerate(target_columns)
#         }
#
#         category_percentages = {}
#         total_skills_per_category = {}
#         top_category = None
#         skills_by_levels = {"Strong": [], "Average": [], "Weak": []}
#         suggested_careers = []
#
#         for skill, level in predicted_labels.items():
#             skill_with_level = f"{skill} Level" if not skill.endswith("Level") else skill
#             dimension_query = select(Dimension).where(Dimension.name == skill_with_level)
#             result = await db.execute(dimension_query)
#             dimension = result.scalars().first()
#
#             if not dimension:
#                 continue
#
#             skill_category_query = (
#                 select(SkillCategory)
#                 .options(joinedload(SkillCategory.dimension))
#                 .where(SkillCategory.dimension_id == dimension.id)
#             )
#             result = await db.execute(skill_category_query)
#             skill_category = result.scalars().first()
#
#             if not skill_category:
#                 continue
#
#             category_name = skill_category.category_name
#             category_level = "Strong" if level in ["Strong", "High"] else "Average" if level in ["Average", "Moderate"] else "Weak"
#
#             skills_by_levels[category_level].append({
#                 "skill": skill_with_level.replace(" Level", ""),
#                 "description": dimension.description,
#             })
#
#             if category_name not in category_percentages:
#                 category_percentages[category_name] = 0
#                 total_skills_per_category[category_name] = 0
#
#             total_skills_per_category[category_name] += 1
#             if category_level == "Strong":
#                 category_percentages[category_name] += 1
#
#             category_percentage = round(
#                 (category_percentages[category_name] / total_skills_per_category[category_name]) * 100, 2
#             )
#
#             if top_category is None or category_percentages[category_name] > category_percentages[top_category['name']]:
#                 top_category = {
#                     "name": category_name,
#                     "description": skill_category.category_description
#                 }
#
#             if category_level == "Strong":
#                 careers_query = (
#                     select(DimensionCareer)
#                     .options(joinedload(DimensionCareer.career))
#                     .where(DimensionCareer.dimension_id == dimension.id)
#                 )
#                 result = await db.execute(careers_query)
#                 careers = result.scalars().all()
#
#                 for career in careers:
#                     career_info = {
#                         "career_name": career.career.name,
#                         "description": career.career.description,
#                         "majors": []
#                     }
#
#                     career_majors_stmt = (
#                         select(Major)
#                         .join(CareerMajor, CareerMajor.major_id == Major.id)
#                         .where(CareerMajor.career_id == career.career.id, CareerMajor.is_deleted == False)
#                     )
#                     result = await db.execute(career_majors_stmt)
#                     majors = result.scalars().all()
#
#                     for major in majors:
#                         schools_stmt = (
#                             select(School)
#                             .join(SchoolMajor, SchoolMajor.school_id == School.id)
#                             .where(SchoolMajor.major_id == major.id, SchoolMajor.is_deleted == False)
#                         )
#                         result = await db.execute(schools_stmt)
#                         schools = result.scalars().all()
#
#                         career_info["majors"].append(MajorWithSchools(
#                             major_name=major.name,
#                             schools=[school.en_name for school in schools]
#                         ))
#
#                     suggested_careers.append(career_info)
#
#             category_percentage = round(
#                 (category_percentages.get(category_name, 0) / total_skills_per_category.get(category_name, 1)) * 100, 2
#             )
#
#             assessment_score = UserAssessmentScore(
#                 uuid=str(uuid.uuid4()),
#                 user_id=user_id,
#                 user_test_id=user_test.id,
#                 assessment_type_id=assessment_type_id,
#                 dimension_id=dimension.id,
#                 score={
#                     "level": level,
#                     "percentage": category_percentage
#                 },
#                 created_at=datetime.utcnow(),
#             )
#             db.add(assessment_score)
#
#         for category in category_percentages.keys():
#             total_skills = total_skills_per_category.get(category, 0)
#             strong_skills = category_percentages.get(category, 0)
#
#             if total_skills > 0:
#                 category_percentages[category] = round((strong_skills / total_skills) * 100, 2)
#             else:
#                 category_percentages[category] = 0
#
#             # Update top category logic
#             if top_category is None or category_percentages[category] > category_percentages.get(top_category['name'],
#                                                                                                  0):
#                 top_category = {
#                     "name": category,
#                     "description": skill_category.category_description
#                 }
#
#         suggested_careers = list({career["career_name"]: career for career in suggested_careers}.values())
#
#         # Final response
#         response = SkillAssessmentResponse(
#             user_uuid=user_uuid,
#             test_uuid=str(user_test.uuid),
#             test_name=user_test.name,
#             top_category=top_category,
#             category_percentages=category_percentages,
#             skills_grouped=skills_by_levels,
#             strong_careers=suggested_careers,
#         )
#
#         user_response = UserResponse(
#             uuid=str(uuid.uuid4()),
#             user_id=user_id,
#             user_test_id=user_test.id,
#             assessment_type_id=assessment_type_id,
#             response_data=json.dumps(response.dict()),
#             is_completed=True,
#             created_at=datetime.utcnow(),
#         )
#         db.add(user_response)
#
#         await db.commit()
#         return response
#
#     except Exception as e:
#         logger.exception("Error during skill prediction")
#         await db.rollback()
#         raise HTTPException(status_code=500, detail=str(e))

async def predict_skills(
    responses: Dict[str, float],
    db: AsyncSession,
    current_user
) -> SkillAssessmentResponse:

    try:
        user_id = current_user.id
        user_uuid = current_user.uuid

        assessment_type_id = await get_assessment_type_id("Skills", db)

        try:
            user_test = await create_user_test(db, current_user.id, assessment_type_id)
            logger.debug(f"Created new test: uuid={user_test.uuid}, name={user_test.name}")
        except Exception as e:
            logger.error(f"Failed to create test for user_id={current_user.id}: {e}")
            await db.rollback()
            raise HTTPException(status_code=500, detail="Failed to create a new test.")

        input_df = pd.DataFrame([responses])
        input_df = input_df.reindex(columns=skill_model.feature_names_in_, fill_value=0)

        predictions = skill_model.predict(input_df)

        target_columns = list(skill_encoders.keys())
        predicted_labels = {
            column: skill_encoders[column].inverse_transform([predictions[0][idx]])[0]
            for idx, column in enumerate(target_columns)
        }

        category_percentages = {}
        total_skills_per_category = {}
        top_category = None
        skills_by_levels = {"Strong": [], "Average": [], "Weak": []}
        suggested_careers = []

        for skill, level in predicted_labels.items():
            skill_with_level = f"{skill} Level" if not skill.endswith("Level") else skill
            dimension_query = select(Dimension).where(Dimension.name == skill_with_level)
            result = await db.execute(dimension_query)
            dimension = result.scalars().first()

            if not dimension:
                continue

            skill_category_query = (
                select(SkillCategory)
                .options(joinedload(SkillCategory.dimension))
                .where(SkillCategory.dimension_id == dimension.id)
            )
            result = await db.execute(skill_category_query)
            skill_category = result.scalars().first()

            if not skill_category:
                continue

            category_name = skill_category.category_name
            category_level = (
                "Strong" if level in ["Strong", "High"]
                else "Average" if level in ["Average", "Moderate"]
                else "Weak"
            )

            skills_by_levels[category_level].append({
                "skill": skill_with_level.replace(" Level", ""),
                "description": dimension.description,
            })

            if category_name not in category_percentages:
                category_percentages[category_name] = {"Strong": 0, "Average": 0, "Weak": 0}
                total_skills_per_category[category_name] = 0

            total_skills_per_category[category_name] += 1
            category_percentages[category_name][category_level] += 1

        overall_category_percentages = {}
        for category, levels in category_percentages.items():
            total_skills = total_skills_per_category.get(category, 0)
            if total_skills > 0:
                strong_percentage = round((levels["Strong"] / total_skills) * 100, 2)
                average_percentage = round((levels["Average"] / total_skills) * 100, 2)
                weak_percentage = round((levels["Weak"] / total_skills) * 100, 2)

                overall_score = round(
                    (levels["Strong"] * 1.0 + levels["Average"] * 0.5) / total_skills * 100, 2
                )

                overall_category_percentages[category] = max(overall_score, 0.01)  # Ensure non-zero percentage
            else:
                overall_category_percentages[category] = 0.0

            if (
                    top_category is None
                    or overall_category_percentages[category] > overall_category_percentages.get(top_category["name"],
                                                                                                 0)
            ):
                top_category = {
                    "name": category,
                    "description": skill_category.category_description,
                }

        suggested_careers = list({career["career_name"]: career for career in suggested_careers}.values())

        # Final response
        response = SkillAssessmentResponse(
            user_uuid=user_uuid,
            test_uuid=str(user_test.uuid),
            test_name=user_test.name,
            top_category=top_category,
            category_percentages=overall_category_percentages,  # Adjusted to be a dictionary of floats
            skills_grouped=skills_by_levels,
            strong_careers=suggested_careers,
        )

        user_response = UserResponse(
            uuid=str(uuid.uuid4()),
            user_id=user_id,
            user_test_id=user_test.id,
            assessment_type_id=assessment_type_id,
            response_data=json.dumps(response.dict()),
            is_completed=True,
            created_at=datetime.utcnow(),
        )
        db.add(user_response)

        await db.commit()
        return response

    except Exception as e:
        logger.exception("Error during skill prediction")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
