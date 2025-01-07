import logging
import json
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
from app.models import UserTest
from app.schemas.final_assessment import AllAssessmentsResponse
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from app.schemas.interest_assessment import InterestAssessmentResponse
from app.schemas.learning_style_assessment import LearningStyleResponse, CareerWithMajors
from app.schemas.personality_assessment import PersonalityTypeDetails, PersonalityAssessmentResponse, PersonalityTraits
from app.schemas.skill_assessment import SkillAssessmentResponse, MajorWithSchools, SkillGroupedByLevel
from app.schemas.value_assessment import ValueAssessmentResponse, CareerData, KeyImprovement, MajorData, \
    ValueCategoryDetails, ChartData

logger = logging.getLogger(__name__)


# Validate each major in the majors list
def validate_major(major):
    if isinstance(major, dict):  # Convert dictionary to MajorWithSchools
        return MajorWithSchools(**major)
    elif isinstance(major, MajorWithSchools):  # Already valid
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
                    logger.debug("Parsing skills assessment response")

                    strong_careers = []
                    for career in response_data.get("strong_careers", []):
                        try:
                            majors = [
                                MajorWithSchools(**major) if isinstance(major, dict) else major
                                for major in career.get("majors", [])
                            ]
                            strong_careers.append(
                                CareerWithMajors(
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
