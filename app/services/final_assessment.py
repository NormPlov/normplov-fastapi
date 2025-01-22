import logging
import json
import os
import uuid
import numpy as np
import pandas as pd

from datetime import datetime
from sqlalchemy.orm import joinedload
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
from app.models import UserTest, AssessmentType, UserResponse, User, Career, School, Major, CareerMajor, SchoolMajor, \
    CareerCategoryResponsibility, CareerCategory, CareerCategoryLink
from app.models.user_test_reference import UserTestReference
from app.schemas.final_assessment import AllAssessmentsResponse, PredictCareersRequest
from sqlalchemy.future import select
from app.schemas.interest_assessment import InterestAssessmentResponse
from app.schemas.learning_style_assessment import LearningStyleResponse
from app.services.test import create_user_test
from app.utils.prepare_model_input import prepare_model_input
from ml_models.model_loader import load_career_recommendation_model
from app.schemas.personality_assessment import PersonalityTypeDetails, PersonalityAssessmentResponse, PersonalityTraits
from app.schemas.skill_assessment import SkillAssessmentResponse, MajorWithSchools, SkillGroupedByLevel
from app.schemas.value_assessment import (
    ValueAssessmentResponse,
    CareerData,
    KeyImprovement,
    MajorData,
    ValueCategoryDetails,
    ChartData
)

logger = logging.getLogger(__name__)


async def get_user_test_details_service(test_uuid: str, db: AsyncSession):
    try:
        # Fetch the main UserTest details
        stmt_user_test = (
            select(UserTest)
            .options(
                joinedload(UserTest.assessment_type),  # Load assessment type
                joinedload(UserTest.test_references)  # Load test references
            )
            .where(UserTest.uuid == test_uuid)
        )
        result_user_test = await db.execute(stmt_user_test)
        user_test = result_user_test.scalar()

        if not user_test:
            raise HTTPException(
                status_code=404,
                detail=f"User test with UUID '{test_uuid}' not found."
            )

        # Get referenced test UUIDs
        referenced_test_uuids = [
            str(reference.test_uuid) for reference in user_test.test_references
        ]

        if not referenced_test_uuids:
            return {
                "test_uuid": str(user_test.uuid),
                "test_name": user_test.name,
                "assessment_type": user_test.assessment_type.name.replace(" ", ""),
                "is_completed": user_test.is_completed,
                "is_deleted": user_test.is_deleted,
                "created_at": user_test.created_at,
                "referenced_test_uuids": {}
            }

        # Fetch assessment type names for referenced tests using UserTest
        stmt_referenced_tests = (
            select(UserTest.uuid, AssessmentType.name.label("assessment_type"))
            .join(AssessmentType, UserTest.assessment_type_id == AssessmentType.id)
            .where(UserTest.uuid.in_([uuid.UUID(ref_uuid) for ref_uuid in referenced_test_uuids]))
        )
        result_referenced_tests = await db.execute(stmt_referenced_tests)
        response_mapping = {
            row.assessment_type.replace(" ", ""): {"test_uuid": str(row.uuid)}
            for row in result_referenced_tests.fetchall()
        }

        # Construct final response
        return {
            "test_uuid": str(user_test.uuid),
            "test_name": user_test.name,
            "assessment_type": user_test.assessment_type.name.replace(" ", ""),
            "is_completed": user_test.is_completed,
            "is_deleted": user_test.is_deleted,
            "created_at": user_test.created_at,
            "referenced_test_uuids": response_mapping
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred: {str(e)}"
        )


async def get_assessment_type_id(name: str, db: AsyncSession) -> int:
    stmt = select(AssessmentType.id).where(AssessmentType.name == name)
    result = await db.execute(stmt)
    assessment_type_id = result.scalars().first()
    if not assessment_type_id:
        raise HTTPException(status_code=404, detail=f"Assessment type '{name}' not found.")
    return assessment_type_id


# Get Career Prediction
async def predict_careers_service(
    request: PredictCareersRequest,
    db: AsyncSession,
    current_user: User,
):
    try:
        aggregated_response = await get_aggregated_tests_service(request.test_uuids, db, current_user)
        user_input = prepare_model_input(aggregated_response)

        # Load the training dataset to fit the model in server
        # dataset_path = "/app/datasets/train_testing.csv"

        # Load the training dataset to fit the model from local computer
        dataset_path = os.path.join(
            os.getcwd(),
            r"D:\CSTAD Scholarship Program\python for data analytics\NORMPLOV_PROJECT\normplov-fastapi\datasets\train_testing.csv",
        )

        career_model = load_career_recommendation_model(dataset_path=dataset_path)
        model_features = career_model.get_feature_columns()
        user_input_aligned = {feature: user_input.get(feature, 0) for feature in model_features}

        top_recommendations = career_model.predict(user_input_aligned, top_n=request.top_n)
        if isinstance(top_recommendations, pd.DataFrame):
            top_recommendations = top_recommendations.to_dict(orient="records")
        elif isinstance(top_recommendations, np.ndarray):
            top_recommendations = [{"Career": row[0], "Similarity": row[1]} for row in top_recommendations]

        career_responses = []
        for recommendation in top_recommendations:
            career_name = recommendation["Career"]
            similarity = recommendation["Similarity"]

            stmt_career = select(Career).where(Career.name == career_name)
            result_career = await db.execute(stmt_career)
            career = result_career.scalars().first()

            if not career:
                logger.warning(f"Career not found: {career_name}")
                continue

            stmt_majors = (
                select(Major)
                .join(CareerMajor, CareerMajor.major_id == Major.id)
                .where(CareerMajor.career_id == career.id, CareerMajor.is_deleted == False)
            )
            result_majors = await db.execute(stmt_majors)
            majors = result_majors.scalars().all()

            majors_with_schools = []
            for major in majors:
                stmt_schools = (
                    select(School.en_name)
                    .join(SchoolMajor, SchoolMajor.school_id == School.id)
                    .where(SchoolMajor.major_id == major.id, SchoolMajor.is_deleted == False)
                )
                result_schools = await db.execute(stmt_schools)
                schools = [school for school in result_schools.scalars().all()]  # Use the strings directly

                majors_with_schools.append({
                    "major_name": major.name,
                    "schools": schools,
                })

                # Fetch related categories and responsibilities
                stmt_categories = (
                    select(CareerCategory)
                    .join(CareerCategoryLink, CareerCategoryLink.career_category_id == CareerCategory.id)
                    .where(CareerCategoryLink.career_id == career.id)
                )
                result_categories = await db.execute(stmt_categories)
                categories = result_categories.scalars().all()

                categories_with_responsibilities = []
                for category in categories:
                    responsibilities_stmt = (
                        select(CareerCategoryResponsibility.description)
                        .where(CareerCategoryResponsibility.career_category_id == category.id)
                    )
                    responsibilities_result = await db.execute(responsibilities_stmt)
                    responsibilities = [resp for resp in responsibilities_result.scalars().all()]

                    categories_with_responsibilities.append({
                        "category_name": category.name,
                        "responsibilities": responsibilities,
                    })

                career_responses.append({
                    "career_uuid": str(career.uuid),
                    "career_name": career_name,
                    "description": career.description,
                    "similarity": similarity,
                    "categories": categories_with_responsibilities,
                    "majors": majors_with_schools,
                })

        assessment_type_id = await get_assessment_type_id("All Tests", db)
        user_test = await create_user_test(db, current_user.id, assessment_type_id)

        for test_uuid in request.test_uuids:
            user_test_reference = UserTestReference(
                user_test_id=user_test.id,
                test_uuid=test_uuid,
            )
            db.add(user_test_reference)

        response_data = {
            "all_assessments": aggregated_response.dict(),
            "recommendations": career_responses,
        }
        new_user_response = UserResponse(
            uuid=uuid.uuid4(),
            user_id=current_user.id,
            assessment_type_id=assessment_type_id,
            user_test_id=user_test.id,
            response_data=response_data,
            is_completed=True,
        )

        db.add(new_user_response)
        await db.commit()
        await db.refresh(new_user_response)

        return {
            "status": 200,
            "message": "Career recommendations predicted and saved successfully.",
            "payload": {
                "test_uuid": str(user_test.uuid),
                "recommendations": response_data,
            },
        }

    except Exception as e:
        logger.error(f"Error during career prediction service: {e}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")


# Validate each major in the majors list
def validate_major(major):
    if isinstance(major, dict):
        return MajorWithSchools(**major)
    elif isinstance(major, MajorWithSchools):
        return major
    else:
        raise ValueError(f"Invalid major data: {major}")


async def get_aggregated_tests_service(
    test_uuids: List[str],
    db: AsyncSession,
    current_user
) -> AllAssessmentsResponse:
    try:
        stmt = (
            select(UserTest)
            .options(
                joinedload(UserTest.assessment_type),
                joinedload(UserTest.user_responses)
            )
            .where(
                UserTest.uuid.in_(test_uuids),
                UserTest.is_deleted == False,
                UserTest.user_id == current_user.id
            )
        )
        result = await db.execute(stmt)
        user_tests = result.unique().scalars().all()

        if not user_tests:
            raise HTTPException(
                status_code=404,
                detail="No tests found for the provided UUIDs."
            )

        personality = None
        learning_style = None
        interest = None
        skill = None
        value = None

        for user_test in user_tests:
            response_data = None
            if user_test.user_responses:
                raw_data = user_test.user_responses[0].response_data
                response_data = json.loads(raw_data) if isinstance(raw_data, str) else raw_data

            if user_test.assessment_type.name.lower() == "personality" and response_data:
                personality = PersonalityAssessmentResponse(
                    user_uuid=str(current_user.uuid),
                    test_uuid=str(user_test.uuid),
                    test_name=user_test.name,
                    personality_type=PersonalityTypeDetails(
                        name=response_data.get("personality_type", {}).get("name", ""),
                        title=response_data.get("personality_type", {}).get("title", ""),
                        description=response_data.get("personality_type", {}).get("description", "")
                    ),
                    dimensions=response_data.get("dimensions", []),
                    traits=response_data.get("traits", {"positive": [], "negative": []}),
                    strengths=response_data.get("strengths", []),
                    weaknesses=response_data.get("weaknesses", []),
                    career_recommendations=response_data.get("career_recommendations", [])
                ).dict()

            elif user_test.assessment_type.name.lower().replace(" ", "") == "learningstyle" and response_data:

                learning_style = LearningStyleResponse(
                    user_uuid=str(current_user.uuid),
                    test_uuid=str(user_test.uuid),
                    test_name=user_test.name,
                    learning_style=response_data.get("learning_style", "Unknown"),
                    probability=response_data.get("probability", 0.0),
                    details=response_data.get("details", {}),
                    chart=response_data.get("chart", {}),
                    dimensions=response_data.get("dimensions", []),
                    recommended_techniques=response_data.get("recommended_techniques", []),
                    related_careers=response_data.get("related_careers", [])
                ).dict()

            if user_test.assessment_type.name.lower() == "interests" and response_data:

                if isinstance(response_data, list):
                    response_data = response_data[0]  # Take the first object in the array

                interest = InterestAssessmentResponse(
                    user_uuid=str(current_user.uuid),
                    test_uuid=str(user_test.uuid),
                    test_name=user_test.name,
                    holland_code=response_data.get("holland_code", ""),
                    type_name=response_data.get("type_name", ""),
                    description=response_data.get("description", ""),
                    key_traits=response_data.get("key_traits", []),
                    career_path=response_data.get("career_path", []),
                    chart_data=response_data.get("chart_data", []),
                    dimension_descriptions=response_data.get("dimension_descriptions", [])
                ).dict()

            elif user_test.assessment_type.name.lower().replace(" ", "") == "skills" and response_data:
                logger.debug("Parsing skills assessment response")
                # Inside the skills assessment section
                try:
                    strong_careers = []
                    for career in response_data.get("strong_careers", []):
                        try:
                            majors = [
                                MajorWithSchools(**major) if isinstance(major, dict) else major
                                for major in career.get("majors", [])
                            ]
                            strong_careers.append(
                                CareerData(
                                    career_name=career.get("career_name", "Unknown"),
                                    description=career.get("description", ""),
                                    majors=majors
                                )
                            )
                        except Exception as e:
                            logger.error(f"Error parsing career: {career}. Error: {e}")
                            continue

                    top_category = response_data.get("top_category", {})
                    if isinstance(top_category, str):
                        top_category = json.loads(top_category)

                    skill_data = SkillAssessmentResponse(
                        user_uuid=str(current_user.uuid),
                        test_uuid=str(user_test.uuid),
                        test_name=user_test.name,
                        top_category=top_category,
                        category_percentages=response_data.get("category_percentages", {}),
                        skills_grouped={
                            level: [SkillGroupedByLevel(**skill) for skill in skills]
                            for level, skills in response_data.get("skills_grouped", {}).items()
                        },
                        strong_careers=strong_careers
                    )

                except Exception as e:
                    logger.exception(f"Error parsing skill assessment for test {user_test.uuid}: {e}")
                    raise HTTPException(
                        status_code=500,
                        detail="An error occurred while processing skill assessment."
                    )

            if user_test.assessment_type.name.lower() == "values" and response_data:
                # Convert chart_data from a list of dictionaries to a list of ChartData objects
                chart_data = [
                    ChartData(label=item["label"], score=item["score"])
                    for item in response_data.get("chart_data", [])
                ]

                value = ValueAssessmentResponse(
                    user_uuid=str(current_user.uuid),
                    test_uuid=str(user_test.uuid),
                    test_name=user_test.name,
                    chart_data=chart_data,
                    value_details=[
                        ValueCategoryDetails(
                            name=detail["name"],
                            definition=detail["definition"],
                            characteristics=detail["characteristics"],
                            percentage=detail["percentage"],
                        )
                        for detail in response_data.get("value_details", [])
                    ],
                    key_improvements=[
                        KeyImprovement(
                            category=improvement["category"],
                            improvements=improvement["improvements"],
                        )
                        for improvement in response_data.get("key_improvements", [])
                    ],
                    career_recommendations=[
                        CareerData(
                            career_name=career["career_name"],
                            description=career.get("description"),
                            majors=[
                                MajorData(
                                    major_name=major["major_name"],
                                    schools=major["schools"],
                                )
                                for major in career.get("majors", [])
                            ],
                        )
                        for career in response_data.get("career_recommendations", [])
                    ],
                ).dict()

        return AllAssessmentsResponse(
            skill=skill_data.dict() if skill_data else None,
            interest=interest,
            learning_style=learning_style,
            personality=personality,
            value=value
        )

    except Exception as e:
        logger.exception("Error retrieving tests")
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
