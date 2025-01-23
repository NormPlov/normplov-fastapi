import pandas as pd
import logging
import uuid
import json

from typing import Dict, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from fastapi import HTTPException
from app.models import (
    SkillCategory,
    DimensionCareer,
    UserResponse,
    AssessmentType,
    UserTest,
    CareerMajor,
    Major,
    SchoolMajor, Career, CareerCategoryLink, CareerCategory, SkillCareerAssociation, Skill
)
from app.models.dimension import Dimension
from app.services.test import create_user_test
from app.schemas.skill_assessment import SkillAssessmentResponse, CategoryWithResponsibilities, CareerData, \
    MajorWithSchools
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


async def predict_skills(
    responses: Dict[str, float],
    db: AsyncSession,
    current_user,
    final_user_test: Optional[UserTest] = None
) -> SkillAssessmentResponse:

    try:
        user_id = current_user.id
        user_uuid = current_user.uuid

        assessment_type_id = await get_assessment_type_id("Skills", db)

        user_test = final_user_test if final_user_test else await create_user_test(db, current_user.id, assessment_type_id)

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

        for skill, level in predicted_labels.items():
            skill_with_level = f"{skill} Level" if not skill.endswith("Level") else skill
            dimension_query = select(Dimension).where(Dimension.name == skill_with_level)
            result = await db.execute(dimension_query)
            dimension = result.scalars().first()

            if not dimension:
                continue

            skill_category_query = (
                select(SkillCategory)
                .where(SkillCategory.id == dimension.skill_category_id)  # Use the foreign key
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

                overall_category_percentages[category] = max(overall_score, 0.01)
            else:
                overall_category_percentages[category] = 0.0

            if (
                top_category is None
                or overall_category_percentages[category] > overall_category_percentages.get(top_category["name"], 0)
            ):
                # Fetch the description for the current category
                skill_category_query = select(SkillCategory).where(SkillCategory.category_name == category)
                result = await db.execute(skill_category_query)
                skill_category = result.scalars().first()

                if skill_category:
                    top_category = {
                        "name": category,
                        "description": skill_category.category_description,
                    }
        career_path = []
        unique_career_uuids = set()

        logger.debug("Starting to process top_category")
        if top_category:
            logger.debug("Top category: %s", top_category)

            try:
                # Build the query using SkillCareerAssociation and Skill
                skill_query = (
                    select(SkillCareerAssociation)
                    .options(
                        joinedload(SkillCareerAssociation.career).joinedload(Career.majors).joinedload(
                            CareerMajor.major).joinedload(Major.school_majors).joinedload(SchoolMajor.school),
                        joinedload(SkillCareerAssociation.career).joinedload(Career.career_category_links).joinedload(
                            CareerCategoryLink.career_category).joinedload(CareerCategory.responsibilities),
                    )
                    .join(Skill)
                    .join(SkillCategory)
                    .where(SkillCategory.category_name == top_category["name"])
                    .filter(SkillCareerAssociation.career.has(is_deleted=False))  # Filter non-deleted careers
                )

                logger.debug("Constructed skill_query: %s", skill_query)

                # Execute the query
                result = await db.execute(skill_query)
                skill_career_associations = result.unique().scalars().all()
                logger.debug("Fetched skill_career_associations count: %d", len(skill_career_associations))

                for sca in skill_career_associations:
                    career = sca.career
                    logger.debug("Processing career: %s", career.name if career else "No Career")

                    if career.uuid in unique_career_uuids:
                        logger.debug("Skipping duplicate career UUID: %s", career.uuid)
                        continue

                    unique_career_uuids.add(career.uuid)

                    # Process majors
                    majors = [
                        MajorWithSchools(
                            major_name=cm.major.name,
                            schools=[sm.school.en_name for sm in cm.major.school_majors if
                                     sm.school and not sm.is_deleted]
                        )
                        for cm in career.majors if not cm.is_deleted
                    ]
                    logger.debug("Majors for career %s: %s", career.name, majors)

                    # Process categories
                    categories = [
                        CategoryWithResponsibilities(
                            category_name=link.career_category.name,
                            responsibilities=[resp.description for resp in link.career_category.responsibilities]
                        )
                        for link in career.career_category_links
                    ]
                    logger.debug("Categories for career %s: %s", career.name, categories)

                    # Append to career_path
                    career_path.append(CareerData(
                        career_uuid=str(career.uuid),
                        career_name=career.name,
                        description=career.description,
                        categories=categories,
                        majors=majors
                    ))

                logger.debug("Final career_path: %s", career_path)

            except Exception as e:
                logger.error("Error processing careers: %s", str(e), exc_info=True)
        else:
            logger.warning("No top_category provided. Skipping career processing.")

        response = SkillAssessmentResponse(
            user_uuid=user_uuid,
            test_uuid=str(user_test.uuid),
            test_name=user_test.name,
            top_category=top_category,
            category_percentages=overall_category_percentages,
            skills_grouped=skills_by_levels,
            strong_careers=career_path,
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
        await db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"An unexpected error occurred during the prediction process. Please check your input or try again."
        )

    #     career_path = []
    #     unique_career_uuids = set()
    #
    #     logger.debug("Starting to process top_category")
    #     if top_category:
    #         logger.debug("Top category: %s", top_category)
    #
    #         try:
    #             # Build the dimension query
    #             dimension_query = (
    #                 select(DimensionCareer)
    #                 .options(
    #                     joinedload(DimensionCareer.career).joinedload(Career.majors).joinedload(
    #                         CareerMajor.major).joinedload(Major.school_majors).joinedload(SchoolMajor.school),
    #                     joinedload(DimensionCareer.career).joinedload(Career.career_category_links).joinedload(
    #                         CareerCategoryLink.career_category).joinedload(CareerCategory.responsibilities)
    #                 )
    #                 .join(Dimension)
    #                 .join(SkillCategory)
    #                 .where(SkillCategory.category_name == top_category["name"])
    #                 .filter(DimensionCareer.is_deleted == False)
    #             )
    #
    #             logger.debug("Constructed dimension_query: %s", dimension_query)
    #
    #             # Execute the query
    #             result = await db.execute(dimension_query)
    #             dimension_careers = result.unique().scalars().all()
    #             logger.debug("Fetched dimension_careers count: %d", len(dimension_careers))
    #
    #             for dc in dimension_careers:
    #                 career = dc.career
    #                 logger.debug("Processing career: %s", career.name if career else "No Career")
    #
    #                 if career.uuid in unique_career_uuids:
    #                     logger.debug("Skipping duplicate career UUID: %s", career.uuid)
    #                     continue
    #
    #                 unique_career_uuids.add(career.uuid)
    #
    #                 # Process majors
    #                 majors = [
    #                     MajorWithSchools(
    #                         major_name=cm.major.name,
    #                         schools=[sm.school.en_name for sm in cm.major.school_majors if
    #                                  sm.school and not sm.is_deleted]
    #                     )
    #                     for cm in career.majors if not cm.is_deleted
    #                 ]
    #                 logger.debug("Majors for career %s: %s", career.name, majors)
    #
    #                 # Process categories
    #                 categories = [
    #                     CategoryWithResponsibilities(
    #                         category_name=link.career_category.name,
    #                         responsibilities=[resp.description for resp in link.career_category.responsibilities]
    #                     )
    #                     for link in career.career_category_links
    #                 ]
    #                 logger.debug("Categories for career %s: %s", career.name, categories)
    #
    #                 # Append to career_path
    #                 career_path.append(CareerData(
    #                     career_uuid=str(career.uuid),
    #                     career_name=career.name,
    #                     description=career.description,
    #                     categories=categories,
    #                     majors=majors
    #                 ))
    #
    #             logger.debug("Final career_path: %s", career_path)
    #
    #         except Exception as e:
    #             logger.error("Error processing dimension careers: %s", str(e), exc_info=True)
    #     else:
    #         logger.warning("No top_category provided. Skipping dimension career processing.")
    #
    #     response = SkillAssessmentResponse(
    #         user_uuid=user_uuid,
    #         test_uuid=str(user_test.uuid),
    #         test_name=user_test.name,
    #         top_category=top_category,
    #         category_percentages=overall_category_percentages,
    #         skills_grouped=skills_by_levels,
    #         # strong_careers=suggested_careers,
    #         strong_careers=career_path,
    #     )
    #
    #     user_response = UserResponse(
    #         uuid=str(uuid.uuid4()),
    #         user_id=user_id,
    #         user_test_id=user_test.id,
    #         assessment_type_id=assessment_type_id,
    #         response_data=json.dumps(response.dict()),
    #         is_completed=True,
    #         created_at=datetime.utcnow(),
    #     )
    #     db.add(user_response)
    #
    #     await db.commit()
    #     return response
    #
    # except Exception as e:
    #     await db.rollback()
    #     raise HTTPException(
    #         status_code=400,
    #         detail=f"An unexpected error occurred during the prediction process. Please check your input or try again."
    #     )

