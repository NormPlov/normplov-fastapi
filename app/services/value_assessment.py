from typing import Optional

import pandas as pd
import uuid
import logging
import json

from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import HTTPException
from app.models.value_category import ValueCategory
from app.models.career import Career
from app.models.user_response import UserResponse
from app.models.user_assessment_score import UserAssessmentScore
from app.models.assessment_type import AssessmentType
from app.models import UserTest, School, SchoolMajor, CareerMajor, Major, CareerValueCategory, \
    ValueCategoryKeyImprovement, CareerCategoryResponsibility, CareerCategoryLink, CareerCategory
from app.models.dimension import Dimension
from app.schemas.value_assessment import (
    ValueAssessmentResponse,
    ChartData,
    ValueCategoryDetails, CareerData, CategoryWithResponsibilities, MajorWithSchools,
)
from app.services.test import create_user_test
from ml_models.model_loader import load_feature_score_models, load_target_value_model


logger = logging.getLogger(__name__)

try:
    feature_score_models = load_feature_score_models()
    target_value_model = load_target_value_model()
except RuntimeError as e:
    logger.error(f"Error loading models: {e}")
    raise

expected_features = [
    "Work-Life Balance Score",
    "Financial Stability Score",
    "Creativity and Innovation Score",
    "Helping Others Score",
    "Personal Growth Score",
    "Recognition and Achievement Score",
    "Social Impact Score",
    "Independence and Flexibility Score",
    "Stability and Security Score",
    "Teamwork and Collaboration Score",
    "Leadership and Influence Score",
]


def normalize_scores(scores_df, target_min=1, target_max=10):
    min_score, max_score = scores_df.min().min(), scores_df.max().max()
    logger.debug(f"normalizing scores with min: {min_score}, max: {max_score}")

    if max_score == min_score:
        return scores_df.applymap(lambda _: (target_min + target_max) / 2)

    return scores_df.applymap(lambda x: target_min + (x - min_score) * (target_max - target_min) / (max_score - min_score))


async def get_assessment_type_id(name: str, db: AsyncSession) -> int:
    stmt = select(AssessmentType.id).where(AssessmentType.name == name)
    result = await db.execute(stmt)
    assessment_type_id = result.scalars().first()
    if not assessment_type_id:
        raise HTTPException(status_code=404, detail=f"Assessment type '{name}' not found.")
    return assessment_type_id


async def process_value_assessment(
        responses,
        db: AsyncSession,
        current_user,
        final_user_test: Optional[UserTest] = None
) -> ValueAssessmentResponse:
    try:
        assessment_type_id = await get_assessment_type_id("Values", db)

        user_test = final_user_test if final_user_test else await create_user_test(db, current_user.id, assessment_type_id)

        input_data = pd.DataFrame([responses])

        feature_scores = {}
        for feature, model in feature_score_models.items():
            feature_scores[feature] = model.predict(input_data)[0]
        feature_scores_df = pd.DataFrame([feature_scores])

        normalized_feature_scores = normalize_scores(feature_scores_df)

        total_score = normalized_feature_scores.iloc[0].sum()

        top_3_features = normalized_feature_scores.iloc[0].nlargest(3).index.tolist()

        chart_data = []
        value_details = []
        career_recommendations = []
        key_improvements = []
        assessment_scores = []

        for category, score in normalized_feature_scores.iloc[0].items():
            chart_data.append(
                ChartData(
                    label=category.replace(" Score", ""),
                    score=round(score, 2),
                )
            )
            if score < 2:
                category_name = category.replace(" Score", "").strip()
                improvement_query = select(ValueCategoryKeyImprovement.improvement_text).join(ValueCategory).where(
                    ValueCategory.name == category_name,
                    ValueCategoryKeyImprovement.is_deleted == False,
                )
                improvements_result = await db.execute(improvement_query)
                improvements = improvements_result.scalars().all()
                if improvements:
                    key_improvements.append({
                        "category": category_name,
                        "improvements": improvements
                    })

        for feature in top_3_features:
            feature_name = feature.replace(" Score", "").strip()

            logger.debug(f"processing feature: {feature_name}")

            category_query = select(ValueCategory).where(ValueCategory.name == feature_name, ValueCategory.is_deleted == False)
            result = await db.execute(category_query)
            value_category = result.scalars().first()

            logger.debug("Value_Category", value_category.name)

            logger.debug(f"Processing feature: {feature_name}")
            if not value_category:
                logger.warning(f"No ValueCategory found for feature: {feature_name}")
                continue

            category_query = select(ValueCategory).where(ValueCategory.name == feature_name,
                                                         ValueCategory.is_deleted == False)
            result = await db.execute(category_query)
            value_category = result.scalars().first()

            if not value_category:
                logger.error(f"ValueCategory not found for feature: {feature_name}. Skipping.")
                continue

            score_value = normalized_feature_scores.iloc[0][feature]
            percentage = (score_value / total_score) * 100

            value_details.append(
                ValueCategoryDetails(
                    name=value_category.name or "Unknown",
                    definition=value_category.definition or "Unknown",
                    characteristics=value_category.characteristics or "Unknown",
                    percentage=f"{round(percentage, 2)}%" or "Unknown"
                )
            )

            # assessment_scores.append(
            #     UserAssessmentScore(
            #         uuid=str(uuid.uuid4()),
            #         user_id=current_user.id,
            #         user_test_id=user_test.id,
            #         assessment_type_id=assessment_type_id,
            #         dimension_id=dimension_id,
            #         score={
            #             "score": round(score_value, 2),
            #             "percentage": round(percentage, 2),
            #         },
            #         created_at=datetime.utcnow(),
            #     )
            # )

            # careers_query = (
            #     select(Career)
            #     .join(CareerValueCategory, CareerValueCategory.career_id == Career.id)
            #     .where(CareerValueCategory.value_category_id == value_category.id)
            #     .distinct()
            # )
            # careers_result = await db.execute(careers_query)
            # careers = careers_result.scalars().all()
            #
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
            #     career_recommendations.append({
            #         "career_name": career.name,
            #         "description": career.description,
            #         "majors": majors_with_schools
            #     })

            # Query all of the career that the model predict getting from the value category
            careers_query = (
                select(Career)
                .join(CareerValueCategory, CareerValueCategory.career_id == Career.id)
                .where(CareerValueCategory.value_category_id == value_category.id)
                .distinct()
            )
            careers_result = await db.execute(careers_query)
            careers = careers_result.scalars().all()

            for career in careers:
                career_majors_stmt = (
                    select(Major)
                    .join(CareerMajor, CareerMajor.major_id == Major.id)
                    .where(CareerMajor.career_id == career.id, CareerMajor.is_deleted == False)
                )
                result = await db.execute(career_majors_stmt)
                majors = result.scalars().all()

                majors_with_schools = []
                for major in majors:
                    schools_stmt = (
                        select(School)
                        .join(SchoolMajor, SchoolMajor.school_id == School.id)
                        .where(SchoolMajor.major_id == major.id, SchoolMajor.is_deleted == False)
                    )
                    result = await db.execute(schools_stmt)
                    schools = result.scalars().all()
                    majors_with_schools.append(MajorWithSchools(
                        major_name=major.name,
                        schools=[
                            {
                                "school_uuid": str(school.uuid),
                                "school_name": school.en_name
                            }
                            for school in schools
                        ]
                    ))

                categories_query = (
                    select(CareerCategory)
                    .join(CareerCategoryLink, CareerCategoryLink.career_category_id == CareerCategory.id)
                    .where(CareerCategoryLink.career_id == career.id)
                )
                categories_result = await db.execute(categories_query)
                categories = categories_result.scalars().all()

                categories_with_responsibilities = []
                for category in categories:
                    responsibilities_query = (
                        select(CareerCategoryResponsibility.description)
                        .where(CareerCategoryResponsibility.career_category_id == category.id)
                    )
                    responsibilities_result = await db.execute(responsibilities_query)
                    responsibilities = responsibilities_result.scalars().all()

                    categories_with_responsibilities.append(CategoryWithResponsibilities(
                        category_name=category.name,
                        responsibilities=responsibilities
                    ))

                career_recommendations.append(CareerData(
                    career_uuid=str(career.uuid),
                    career_name=career.name,
                    description=career.description,
                    categories=categories_with_responsibilities,
                    majors=majors_with_schools
                ))

        career_recommendations = list({career.career_name: career for career in career_recommendations}.values())
        career_recommendations = [career for career in career_recommendations if isinstance(career, CareerData)]

        db.add_all(assessment_scores)

        response = ValueAssessmentResponse(
            user_uuid=current_user.uuid,
            test_uuid=str(user_test.uuid),
            test_name=user_test.name,
            chart_data=chart_data,
            value_details=value_details,
            key_improvements=key_improvements,
            career_recommendations=career_recommendations,
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
