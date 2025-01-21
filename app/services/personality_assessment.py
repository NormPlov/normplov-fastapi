import pandas as pd
import uuid
import logging
import json

from typing import Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import HTTPException
from sqlalchemy.orm import joinedload
from app.models import AssessmentType, Career, CareerMajor, SchoolMajor, Major, CareerPersonalityType, UserTest, \
    CareerCategory, CareerCategoryLink
from app.models.user_response import UserResponse
from app.models.user_assessment_score import UserAssessmentScore
from app.models.dimension import Dimension
from app.models.personality_type import PersonalityType
from app.models.personality_trait import PersonalityTrait
from app.models.personality_strength import PersonalityStrength
from app.models.personality_weakness import PersonalityWeakness
from app.services.test import create_user_test
from app.schemas.personality_assessment import (
    PersonalityAssessmentResponse,
    PersonalityTypeDetails,
    DimensionScore,
    PersonalityTraits, CategoryWithResponsibilities, MajorData, CareerData
)
from ml_models.model_loader import load_personality_models

logger = logging.getLogger(__name__)
dimension_models, personality_predictor, label_encoder = load_personality_models()


async def get_assessment_type_id(name: str, db: AsyncSession) -> int:
    stmt = select(AssessmentType.id).where(AssessmentType.name == name)
    result = await db.execute(stmt)
    assessment_type_id = result.scalars().first()
    if not assessment_type_id:
        raise HTTPException(status_code=404, detail=f"Assessment type '{name}' not found.")
    return assessment_type_id


async def process_personality_assessment(
    input_data: dict,
    db: AsyncSession,
    current_user,
    final_user_test: Optional[UserTest] = None
) -> PersonalityAssessmentResponse:
    try:
        # Get assessment type ID for "Personality"
        assessment_type_id = await get_assessment_type_id("Personality", db)

        # Create or reuse user test
        user_test = final_user_test if final_user_test else await create_user_test(db, current_user.id, assessment_type_id)

        # Predict dimension scores using models
        input_responses_df = pd.DataFrame([input_data])
        dimension_scores = {}
        for dimension, model in dimension_models.items():
            prediction = model.predict(input_responses_df)[0]
            dimension_scores[dimension] = prediction

        # Normalize dimension scores
        total_score = sum(dimension_scores.values())
        normalized_scores = {
            dim: {
                "score": round(score, 2),
                "percentage": round((score / total_score) * 100, 2)
            }
            for dim, score in dimension_scores.items()
        }

        # Determine personality type
        type_map = {
            "E": dimension_scores["E_Score"] >= dimension_scores["I_Score"],
            "N": dimension_scores["N_Score"] >= dimension_scores["S_Score"],
            "F": dimension_scores["F_Score"] >= dimension_scores["T_Score"],
            "J": dimension_scores["J_Score"] >= dimension_scores["P_Score"],
        }
        personality_code = "".join(
            key if value else key.replace("E", "I").replace("N", "S").replace("F", "T").replace("J", "P")
            for key, value in type_map.items()
        )

        # Retrieve personality type details
        personality_query = select(PersonalityType).where(PersonalityType.name == personality_code)
        result = await db.execute(personality_query)
        personality_details = result.scalars().first()

        if not personality_details:
            raise HTTPException(status_code=404, detail=f"Personality type '{personality_code}' not found.")

        # Create assessment scores
        assessment_scores = []
        for dimension_name, score_data in normalized_scores.items():
            dimension_query = select(Dimension).where(Dimension.name == dimension_name)
            result = await db.execute(dimension_query)
            dimension = result.scalars().first()

            if not dimension:
                logger.warning(f"Dimension not found for {dimension_name}. Skipping.")
                continue

            assessment_scores.append(
                UserAssessmentScore(
                    uuid=str(uuid.uuid4()),
                    user_id=current_user.id,
                    user_test_id=user_test.id,
                    assessment_type_id=assessment_type_id,
                    dimension_id=dimension.id,
                    score=score_data,
                    created_at=datetime.utcnow(),
                )
            )

        if not assessment_scores:
            raise HTTPException(status_code=400, detail="No valid dimensions found for scoring.")

        db.add_all(assessment_scores)

        # Fetch personality traits, strengths, and weaknesses
        traits_query = select(PersonalityTrait).where(PersonalityTrait.personality_type_id == personality_details.id)
        traits_result = await db.execute(traits_query)
        traits = traits_result.scalars().all()
        positive_traits = [trait.trait for trait in traits if trait.is_positive]
        negative_traits = [trait.trait for trait in traits if not trait.is_positive]

        strengths_query = select(PersonalityStrength).where(PersonalityStrength.personality_type_id == personality_details.id)
        strengths_result = await db.execute(strengths_query)
        strengths = [s.strength for s in strengths_result.scalars().all()]

        weaknesses_query = select(PersonalityWeakness).where(PersonalityWeakness.personality_type_id == personality_details.id)
        weaknesses_result = await db.execute(weaknesses_query)
        weaknesses = [w.weakness for w in weaknesses_result.scalars().all()]

        # Retrieve career recommendations
        career_query = (
            select(Career)
            .options(
                joinedload(Career.career_category_links).joinedload(CareerCategoryLink.career_category).joinedload(
                    CareerCategory.responsibilities
                ),
                joinedload(Career.majors).joinedload(CareerMajor.major).joinedload(Major.school_majors).joinedload(
                    SchoolMajor.school
                ),
            )
            .join(CareerPersonalityType, CareerPersonalityType.career_id == Career.id)
            .where(CareerPersonalityType.personality_type_id == personality_details.id)
            .where(Career.is_deleted == False)
            .distinct()
        )
        career_result = await db.execute(career_query)
        careers = career_result.unique().scalars().all()

        # Process career data and remove duplicates
        processed_careers = set()
        career_data = []
        for career in careers:
            if career.uuid in processed_careers:
                continue

            processed_careers.add(career.uuid)
            categories = [
                CategoryWithResponsibilities(
                    category_name=link.career_category.name,
                    responsibilities=[resp.description for resp in link.career_category.responsibilities],
                )
                for link in career.career_category_links
            ]
            majors = [
                MajorData(
                    major_name=major.name,
                    schools=[
                        school.en_name
                        for school_major in major.school_majors if not school_major.is_deleted
                        for school in [school_major.school] if school
                    ],
                )
                for career_major in career.majors if not career_major.is_deleted
                for major in [career_major.major]
            ]
            career_data.append(
                CareerData(
                    career_uuid=str(career.uuid),
                    career_name=career.name,
                    description=career.description,
                    categories=categories,
                    majors=majors,
                )
            )

        # Construct response
        response = PersonalityAssessmentResponse(
            user_uuid=current_user.uuid,
            test_uuid=str(user_test.uuid),
            test_name=user_test.name,
            personality_type=PersonalityTypeDetails(
                name=personality_details.name,
                title=personality_details.title,
                description=personality_details.description,
            ),
            dimensions=[
                DimensionScore(
                    dimension_name=dim,
                    score=data["score"],
                    percentage=f"{data['percentage']}%",
                )
                for dim, data in normalized_scores.items()
            ],
            traits=PersonalityTraits(positive=positive_traits, negative=negative_traits),
            strengths=strengths,
            weaknesses=weaknesses,
            career_recommendations=career_data,
        )

        # Save user response
        user_response = UserResponse(
            uuid=str(uuid.uuid4()),
            user_id=current_user.id,
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
        logger.exception("Error processing personality assessment.")
        raise HTTPException(status_code=400, detail="An unexpected error occurred during the assessment process.")
