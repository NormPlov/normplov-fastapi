import pandas as pd
import uuid
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
)
from app.models.dimension import Dimension
from app.services.test import create_user_test
from app.schemas.skill_assessment import SkillAssessmentInput, SkillAssessmentResponse
from ml_models.model_loader import load_skill_model
import logging
import json

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
    data: SkillAssessmentInput,
    db: AsyncSession,
    current_user
) -> SkillAssessmentResponse:
    """
    Predict the user's skills based on the input and store the results.

    Args:
        data (SkillAssessmentInput): Input data containing skill scores and optional test UUID.
        db (AsyncSession): Database session.
        current_user: The current user object.

    Returns:
        SkillAssessmentResponse: Skill prediction results and associated details.
    """
    try:
        user_id = current_user.id

        # Fetch the dynamic assessment type ID for "Skill"
        assessment_type_id = await get_assessment_type_id("Skills", db)

        # Check if `test_uuid` is provided, otherwise create a new test
        if data.test_uuid:
            # Validate the provided test_uuid
            test_query = select(UserTest).where(UserTest.uuid == data.test_uuid, UserTest.user_id == user_id)
            test_result = await db.execute(test_query)
            user_test = test_result.scalars().first()
            if not user_test:
                raise HTTPException(status_code=404, detail="Invalid test UUID provided.")
        else:
            user_test = await create_user_test(db, user_id, "Skills")

        # Process the input data
        input_df = pd.DataFrame([data.responses])
        logger.debug(f"Input DataFrame: {input_df}")

        # Predict skill levels
        predictions = skill_model.predict(input_df)
        logger.debug(f"Model Predictions: {predictions}")

        # Decode predictions
        target_columns = list(skill_encoders.keys())
        predicted_labels = {
            column: skill_encoders[column].inverse_transform([predictions[0][idx]])[0]
            for idx, column in enumerate(target_columns)
        }
        logger.debug(f"Predicted Labels: {predicted_labels}")

        category_percentages = {}
        skills_by_levels = {"Strong": [], "Average": [], "Weak": []}
        suggested_careers = []
        total_skills_per_category = {}

        for skill, level in predicted_labels.items():
            # Add " Level" only if the skill name does not already include "Level"
            if not skill.endswith("Level"):
                skill_with_level = f"{skill} Level"
            else:
                skill_with_level = skill
            logger.debug(f"Querying for skill: {skill_with_level}")

            # Fetch the corresponding Dimension
            dimension_query = select(Dimension).where(Dimension.name == skill_with_level)
            result = await db.execute(dimension_query)
            dimension = result.scalars().first()

            if not dimension:
                logger.warning(f"No dimension found for skill: {skill_with_level}")
                continue

            # Fetch the skill category
            skill_category_query = (
                select(SkillCategory)
                .options(joinedload(SkillCategory.dimension))
                .where(SkillCategory.dimension_id == dimension.id)
            )
            result = await db.execute(skill_category_query)
            skill_category = result.scalars().first()

            if not skill_category:
                logger.warning(f"No skill category found for dimension ID: {dimension.id}")
                continue

            category_name = skill_category.category_name

            # Categorize skill level
            if level in ["Strong", "High"]:
                category_level = "Strong"
            elif level in ["Average", "Moderate"]:
                category_level = "Average"
            else:
                category_level = "Weak"

            # Group skills by levels
            skills_by_levels[category_level].append({
                "skill": skill_with_level,
                "description": dimension.description,
            })

            if category_level == "Strong":
                # Fetch related careers for strong skills
                careers_query = (
                    select(DimensionCareer)
                    .options(joinedload(DimensionCareer.career))
                    .where(DimensionCareer.dimension_id == dimension.id)
                )
                result = await db.execute(careers_query)
                careers = result.scalars().all()

                if not careers:
                    logger.warning(f"No careers found for dimension ID: {dimension.id}")
                else:
                    suggested_careers.extend(
                        {"career_name": career.career.name}
                        for career in careers if career.career
                    )

            # Update category percentage calculations
            if category_name not in category_percentages:
                category_percentages[category_name] = 0
                total_skills_per_category[category_name] = 0

            total_skills_per_category[category_name] += 1
            if category_level == "Strong":
                category_percentages[category_name] += 1

            # Calculate percentage for this skill's category
            category_percentage = round(
                (category_percentages.get(category_name, 0) / total_skills_per_category.get(category_name, 1)) * 100, 2
            )

            # Save the assessment score with only level and percentage
            assessment_score = UserAssessmentScore(
                uuid=str(uuid.uuid4()),
                user_id=user_id,
                user_test_id=user_test.id,
                assessment_type_id=assessment_type_id,
                dimension_id=dimension.id,
                score={
                    "level": level,
                    "percentage": category_percentage
                },
                created_at=datetime.utcnow(),
            )
            db.add(assessment_score)

        # Calculate category percentages
        for category in category_percentages.keys():
            category_percentages[category] = round(
                (category_percentages[category] / total_skills_per_category[category]) * 100, 2
            )
        logger.debug(f"Final Category Percentages: {category_percentages}")

        # Build the response
        suggested_careers = list({career["career_name"]: career for career in suggested_careers}.values())
        response = SkillAssessmentResponse(
            category_percentages=category_percentages,
            skills_grouped=skills_by_levels,
            strong_careers=suggested_careers,
        )

        user_response = UserResponse(
            uuid=str(uuid.uuid4()),
            user_id=user_id,
            user_test_id=user_test.id,
            assessment_type_id=assessment_type_id,
            response_data=json.dumps(response.dict()),
            created_at=datetime.utcnow(),
        )
        db.add(user_response)

        await db.commit()
        return response

    except Exception as e:
        logger.exception("Error during skill prediction")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
