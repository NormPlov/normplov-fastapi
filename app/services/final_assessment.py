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
from app.schemas.learning_style_assessment import LearningStyleResponse
from app.schemas.personality_assessment import PersonalityTypeDetails, PersonalityAssessmentResponse, PersonalityTraits
from app.schemas.skill_assessment import SkillAssessmentResponse
from app.schemas.value_assessment import ValueAssessmentResponse

logger = logging.getLogger(__name__)


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

            elif user_test.assessment_type.name.lower() == "learningstyle" and response_data:
                learning_style = LearningStyleResponse(
                    learning_style=response_data.get("learning_style", "")
                )

            elif user_test.assessment_type.name.lower() == "interest" and response_data:
                interest = InterestAssessmentResponse(
                    type_name=response_data.get("type_name", "")
                )

            elif user_test.assessment_type.name.lower() == "skill" and response_data:
                skill = SkillAssessmentResponse(
                    top_category=response_data.get("top_category", "")
                )

            elif user_test.assessment_type.name.lower() == "value" and response_data:
                value = ValueAssessmentResponse(
                    chart_data=response_data.get("chart_data", {"labels": [], "values": []})
                )

        # Return the aggregated response
        return AllAssessmentsResponse(
            learning_style=learning_style,
            skill=skill,
            personality=personality,
            interest=interest,
            value=value
        )

    except Exception as e:
        logger.exception("Error retrieving tests")
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
