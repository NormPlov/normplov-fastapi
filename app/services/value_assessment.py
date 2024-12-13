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
from app.models import UserTest, School, SchoolMajor, CareerMajor, Major
from app.models.dimension import Dimension
from app.schemas.value_assessment import (
    ValueAssessmentResponse,
    ChartData,
    ValueCategoryDetails,
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
    logger.debug(f"Normalizing scores with min: {min_score}, max: {max_score}")

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


async def process_value_assessment(responses, db: AsyncSession, current_user, test_uuid: str | None = None) -> ValueAssessmentResponse:
    try:
        assessment_type_id = await get_assessment_type_id("Values", db)

        if test_uuid:
            test_query = select(UserTest).where(UserTest.uuid == test_uuid, UserTest.user_id == current_user.id)
            test_result = await db.execute(test_query)
            user_test = test_result.scalars().first()

            if not user_test:
                raise HTTPException(status_code=404, detail="Test not found.")
            logger.info(f"Updating existing test with UUID: {test_uuid}")
        else:
            user_test = await create_user_test(db, current_user.id, assessment_type_id)

        input_data = pd.DataFrame([responses])
        logger.debug(f"User responses converted to DataFrame: {input_data}")

        feature_scores = {}
        for feature, model in feature_score_models.items():
            feature_scores[feature] = model.predict(input_data)[0]
        feature_scores_df = pd.DataFrame([feature_scores])
        logger.debug(f"Predicted feature scores: {feature_scores_df}")

        normalized_feature_scores = normalize_scores(feature_scores_df)
        logger.debug(f"Normalized feature scores: {normalized_feature_scores}")

        total_score = normalized_feature_scores.iloc[0].sum()
        logger.debug(f"Total normalized score: {total_score}")

        top_3_features = normalized_feature_scores.iloc[0].nlargest(3).index.tolist()
        logger.debug(f"Top 3 features extracted: {top_3_features}")

        chart_data = []
        value_details = []
        career_recommendations = []
        assessment_scores = []

        for category, score in normalized_feature_scores.iloc[0].items():
            chart_data.append(
                ChartData(
                    label=category.replace(" Score", ""),
                    score=round(score, 2),
                )
            )

        for feature in top_3_features:
            feature_name = feature.replace(" Score", "").strip()

            logger.debug(f"Processing feature: {feature_name}")

            category_query = select(ValueCategory).where(ValueCategory.name == feature_name, ValueCategory.is_deleted == False)
            result = await db.execute(category_query)
            value_category = result.scalars().first()

            if not value_category:
                logger.warning(f"No ValueCategory found for feature: {feature_name}")
                continue

            dimension_query = select(Dimension.id).where(Dimension.name == f"{feature_name} Score")
            dimension_result = await db.execute(dimension_query)
            dimension_id = dimension_result.scalars().first()

            if not dimension_id:
                logger.error(f"Dimension not found for feature: {feature_name} Score. Skipping.")
                continue

            score_value = normalized_feature_scores.iloc[0][feature]
            percentage = (score_value / total_score) * 100

            value_details.append(
                ValueCategoryDetails(
                    name=value_category.name,
                    definition=value_category.definition,
                    characteristics=value_category.characteristics,
                    percentage=f"{round(percentage, 2)}%"
                )
            )

            assessment_scores.append(
                UserAssessmentScore(
                    uuid=str(uuid.uuid4()),
                    user_id=current_user.id,
                    user_test_id=user_test.id,
                    assessment_type_id=assessment_type_id,
                    dimension_id=dimension_id,
                    score={
                        "score": round(score_value, 2),
                        "percentage": round(percentage, 2),
                    },
                    created_at=datetime.utcnow(),
                )
            )

            careers_query = select(Career).where(Career.value_category_id == value_category.id)
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
                    majors_with_schools.append({
                        "major_name": major.name,
                        "schools": [school.en_name for school in schools]
                    })

                career_recommendations.append({
                    "career_name": career.name,
                    "description": career.description,
                    "majors": majors_with_schools
                })

        career_recommendations = list({career["career_name"]: career for career in career_recommendations}.values())

        db.add_all(assessment_scores)

        response = ValueAssessmentResponse(
            user_uuid=current_user.uuid,
            test_uuid=str(user_test.uuid),
            test_name=user_test.name,
            chart_data=chart_data,
            value_details=value_details,
            career_recommendations=career_recommendations,
        )

        user_response = UserResponse(
            uuid=str(uuid.uuid4()),
            user_id=current_user.id,
            user_test_id=user_test.id,
            assessment_type_id=assessment_type_id,
            response_data=json.dumps(response.dict()),
            created_at=datetime.utcnow(),
        )
        db.add(user_response)

        await db.commit()

        return response

    except Exception as e:
        logger.exception("Error processing value assessment.")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
