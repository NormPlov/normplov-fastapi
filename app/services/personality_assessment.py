from typing import Optional

import pandas as pd
import uuid
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
import logging
import json

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
        assessment_type_id = await get_assessment_type_id("Personality", db)

        user_test = final_user_test if final_user_test else await create_user_test(db, current_user.id, assessment_type_id)

        input_responses_df = pd.DataFrame([input_data])
        dimension_scores = {}
        for dimension, model in dimension_models.items():
            prediction = model.predict(input_responses_df)[0]
            dimension_scores[dimension] = prediction

        total_score = sum(dimension_scores.values())
        normalized_scores = {
            dim: {
                "score": round(score, 2),
                "percentage": round((score / total_score) * 100, 2)
            }
            for dim, score in dimension_scores.items()
        }

        input_data_for_prediction = pd.DataFrame([dimension_scores])
        predicted_class = personality_predictor.predict(input_data_for_prediction)
        predicted_personality = label_encoder.inverse_transform(predicted_class)[0]

        personality_query = select(PersonalityType).where(PersonalityType.name == predicted_personality)
        result = await db.execute(personality_query)
        personality_details = result.scalars().first()

        if not personality_details:
            raise HTTPException(status_code=400, detail="Personality details not found for the predicted class.")

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
            raise HTTPException(
                status_code=500,
                detail="Failed to resolve dimension IDs for personality assessment scores.",
            )

        db.add_all(assessment_scores)

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

        # career_query = (
        #     select(Career)
        #     .join(CareerPersonalityType, CareerPersonalityType.career_id == Career.id)
        #     .where(CareerPersonalityType.personality_type_id == personality_details.id)
        #     .distinct()
        # )
        # career_result = await db.execute(career_query)
        # careers = career_result.scalars().all()
        #
        # career_data = []
        # for career in careers:
        #     career_majors_stmt = (
        #         select(Major)
        #         .join(CareerMajor, CareerMajor.major_id == Major.id)
        #         .where(CareerMajor.career_id == career.id, CareerMajor.is_deleted == False)
        #     )
        #     result = await db.execute(career_majors_stmt)
        #     majors = result.scalars().all()
        #
        #     majors_with_schools = []
        #     for major in majors:
        #         schools_stmt = (
        #             select(School)
        #             .join(SchoolMajor, SchoolMajor.school_id == School.id)
        #             .where(SchoolMajor.major_id == major.id, SchoolMajor.is_deleted == False)
        #         )
        #         result = await db.execute(schools_stmt)
        #         schools = result.scalars().all()
        #         majors_with_schools.append({
        #             "major_name": major.name,
        #             "schools": [school.en_name for school in schools]
        #         })
        #
        #     career_data.append({
        #         "career_name": career.name,
        #         "description": career.description,
        #         "majors": majors_with_schools
        #     })

        # Update the career query
        # career_query = (
        #     select(Career)
        #     .options(
        #         joinedload(Career.career_category_links).joinedload(CareerCategoryLink.career_category).joinedload(
        #             CareerCategory.responsibilities),
        #         joinedload(Career.majors).joinedload(CareerMajor.major).joinedload(Major.school_majors).joinedload(
        #             SchoolMajor.school)
        #     )
        #     .join(CareerPersonalityType, CareerPersonalityType.career_id == Career.id)
        #     .where(CareerPersonalityType.personality_type_id == personality_details.id)
        #     .where(Career.is_deleted == False)
        #     .distinct()
        # )
        # career_result = await db.execute(career_query)
        # careers = career_result.unique().scalars().all()
        #
        # # Process career data
        # career_data = []
        # for career in careers:
        #     categories = []
        #     for link in career.career_category_links:
        #         category = link.career_category
        #         responsibilities = [resp.description for resp in category.responsibilities]
        #         categories.append(CategoryWithResponsibilities(
        #             category_name=category.name,
        #             responsibilities=responsibilities
        #         ))
        #
        #     majors_with_schools = []
        #     for career_major in career.majors:
        #         if not career_major.is_deleted:
        #             major = career_major.major
        #             schools = []
        #             for sm in major.school_majors:
        #                 if not sm.is_deleted and sm.school is not None and sm.school.en_name is not None:
        #                     schools.append(sm.school.en_name)
        #
        #             if schools:  # Only add the major if it has associated schools
        #                 majors_with_schools.append(MajorData(
        #                     major_name=major.name,
        #                     schools=schools
        #                 ))
        #
        #     career_data.append(CareerData(
        #         career_uuid=str(career.uuid),
        #         career_name=career.name,
        #         description=career.description,
        #         categories=categories,
        #         majors=majors_with_schools
        #     ))
        #
        # response = PersonalityAssessmentResponse(
        #     user_uuid=current_user.uuid,
        #     test_uuid=str(user_test.uuid),
        #     test_name=user_test.name,
        #     personality_type=PersonalityTypeDetails(
        #         name=personality_details.name,
        #         title=personality_details.title,
        #         description=personality_details.description,
        #     ),
        #     dimensions=[DimensionScore(
        #         dimension_name=dim,
        #         score=data["score"],
        #         percentage=f"{data['percentage']}%"
        #     ) for dim, data in normalized_scores.items()],
        #     traits=PersonalityTraits(positive=positive_traits, negative=negative_traits),
        #     strengths=strengths,
        #     weaknesses=weaknesses,
        #     career_recommendations=career_data,
        # )
        #
        # user_response = UserResponse(
        #     uuid=str(uuid.uuid4()),
        #     user_id=current_user.id,
        #     user_test_id=user_test.id,
        #     assessment_type_id=assessment_type_id,
        #     response_data=json.dumps(response.dict()),
        #     is_completed=True,
        #     created_at=datetime.utcnow(),
        # )
        # db.add(user_response)
        #
        # await db.commit()
        #
        # return response
        career_query = (
            select(Career)
            .options(
                joinedload(Career.career_category_links).joinedload(CareerCategoryLink.career_category).joinedload(
                    CareerCategory.responsibilities),
                joinedload(Career.majors).joinedload(CareerMajor.major).joinedload(Major.school_majors).joinedload(
                    SchoolMajor.school)
            )
            .join(CareerPersonalityType, CareerPersonalityType.career_id == Career.id)
            .where(CareerPersonalityType.personality_type_id == personality_details.id)
            .where(Career.is_deleted == False)
            .distinct()
        )
        career_result = await db.execute(career_query)
        careers = career_result.unique().scalars().all()

        # Process career data
        career_data = []
        processed_career_uuids = set()

        for career in careers:
            if career.uuid in processed_career_uuids:
                continue  # Skip duplicate careers

            processed_career_uuids.add(career.uuid)

            categories = []
            for link in career.career_category_links:
                category = link.career_category
                responsibilities = [resp.description for resp in category.responsibilities]
                categories.append(CategoryWithResponsibilities(
                    category_name=category.name,
                    responsibilities=responsibilities
                ))

            majors_with_schools = []
            for career_major in career.majors:
                if not career_major.is_deleted:
                    major = career_major.major
                    schools = []
                    for sm in major.school_majors:
                        if not sm.is_deleted and sm.school is not None and sm.school.en_name is not None:
                            schools.append(sm.school.en_name)

                    if schools:  # Only add the major if it has associated schools
                        majors_with_schools.append(MajorData(
                            major_name=major.name,
                            schools=schools
                        ))

            career_data.append(CareerData(
                career_uuid=str(career.uuid),
                career_name=career.name,
                description=career.description,
                categories=categories,
                majors=majors_with_schools
            ))

        response = PersonalityAssessmentResponse(
            user_uuid=current_user.uuid,
            test_uuid=str(user_test.uuid),
            test_name=user_test.name,
            personality_type=PersonalityTypeDetails(
                name=personality_details.name,
                title=personality_details.title,
                description=personality_details.description,
            ),
            dimensions=[DimensionScore(
                dimension_name=dim,
                score=data["score"],
                percentage=f"{data['percentage']}%"
            ) for dim, data in normalized_scores.items()],
            traits=PersonalityTraits(positive=positive_traits, negative=negative_traits),
            strengths=strengths,
            weaknesses=weaknesses,
            career_recommendations=career_data,
        )

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
        raise HTTPException(
            status_code=400,
            detail=f"An unexpected error occurred during the prediction process. Please check your input or try again."
        )