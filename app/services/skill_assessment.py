import pandas as pd
import uuid
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload

from app.models import SkillCategory, DimensionCareer
from app.models.user_response import UserResponse
from app.models.user_assessment_score import UserAssessmentScore
from app.models.dimension import Dimension
from app.models.user import User
from app.schemas.skill_assessment import SkillAssessmentResponse
from ml_models.model_loader import load_skill_model
import logging
import json

logger = logging.getLogger(__name__)

skill_model, skill_encoders = load_skill_model()


async def predict_skills(data: "SkillAssessmentInputDto", db: AsyncSession, user: User):
    try:
        # Convert input data into a DataFrame
        input_df = pd.DataFrame([data.scores])

        # Make predictions using the model
        predictions = skill_model.predict(input_df)

        # Decode predictions using label encoders
        target_columns = list(skill_encoders.keys())
        predicted_labels = {}
        for idx, column in enumerate(target_columns):
            predicted_labels[column] = skill_encoders[column].inverse_transform([predictions[0][idx]])[0]

        # Prepare results
        category_percentages = {}
        skills_by_levels = {"Strong": [], "Average": [], "Weak": []}
        suggested_careers = []
        total_skills_per_category = {}

        for skill, level in predicted_labels.items():
            # Find the dimension
            dimension = await db.execute(select(Dimension).where(Dimension.name == skill))
            dimension = dimension.scalars().first()

            if not dimension:
                logger.warning(f"Dimension not found for skill: {skill}")
                continue

            # Find the skill category and description
            skill_category_stmt = (
                select(SkillCategory)
                .options(joinedload(SkillCategory.dimension))
                .where(SkillCategory.dimension_id == dimension.id)
            )
            skill_category = await db.execute(skill_category_stmt)
            skill_category = skill_category.scalars().first()

            if not skill_category:
                logger.warning(f"Skill category not found for dimension ID: {dimension.id}")
                continue

            category_name = skill_category.category_name

            # Categorize levels into Strong, Average, Weak
            if level in ["Strong", "High"]:
                category_level = "Strong"
            elif level in ["Average", "Moderate"]:
                category_level = "Average"
            else:
                category_level = "Weak"

            # Group skills by level
            skills_by_levels[category_level].append({
                "skill": skill,
                "description": dimension.description,
            })

            # Add careers to the suggestions for strong skills
            if category_level == "Strong":
                careers_stmt = (
                    select(DimensionCareer)
                    .options(joinedload(DimensionCareer.career))
                    .where(DimensionCareer.dimension_id == dimension.id)
                )
                careers = await db.execute(careers_stmt)
                careers = careers.scalars().all()

                suggested_careers.extend(
                    {"career_name": career.career.name}
                    for career in careers if career.career
                )

            # Calculate category percentages
            if category_name not in category_percentages:
                category_percentages[category_name] = 0
                total_skills_per_category[category_name] = 0

            total_skills_per_category[category_name] += 1
            if category_level == "Strong":
                category_percentages[category_name] += 1

            # Save the user's assessment score
            user_assessment_score = UserAssessmentScore(
                user_id=user.id,
                assessment_type_id=4,
                dimension_id=dimension.id,
                score={"level": level},
                created_at=datetime.utcnow(),
            )
            db.add(user_assessment_score)

        # Calculate final category percentages
        for category in category_percentages.keys():
            category_percentages[category] = round(
                (category_percentages[category] / total_skills_per_category[category]) * 100, 2
            )

        # Remove duplicate career suggestions
        suggested_careers = list({career["career_name"]: career for career in suggested_careers}.values())

        response = SkillAssessmentResponse(
            category_percentages=category_percentages,
            skills_grouped=skills_by_levels,
            strong_careers=suggested_careers
        )

        user_response = UserResponse(
            uuid=str(uuid.uuid4()),
            user_id=user.id,
            assessment_type_id=4,
            response_data=json.dumps(response.dict()),
            created_at=datetime.utcnow(),
        )
        db.add(user_response)

        await db.commit()

        return response.dict()

    except Exception as e:
        logger.exception("An error occurred during skill prediction.")
        await db.rollback()
        raise RuntimeError("Internal Server Error")
