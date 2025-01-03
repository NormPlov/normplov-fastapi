import logging
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.models import AssessmentType
from app.schemas.final_assessment import AllAssessmentsInput, AllAssessmentsResponse
from app.services.learning_style_assessment import predict_learning_style
from app.services.skill_assessment import predict_skills
from app.services.personality_assessment import process_personality_assessment
from app.services.interest_assessment import process_interest_assessment
from app.services.value_assessment import process_value_assessment
from app.services.test import create_user_test
from sqlalchemy.future import select

logger = logging.getLogger(__name__)


async def get_assessment_type_id(name: str, db: AsyncSession) -> int:
    stmt = select(AssessmentType.id).where(AssessmentType.name == name)
    result = await db.execute(stmt)
    assessment_type_id = result.scalars().first()
    if not assessment_type_id:
        raise HTTPException(status_code=404, detail=f"Assessment type '{name}' not found.")
    return assessment_type_id


async def process_final_assessment_service(
    input_data: AllAssessmentsInput,
    db: AsyncSession,
    current_user
) -> AllAssessmentsResponse:
    try:
        final_assessment_type_id = await get_assessment_type_id("Final Assessment", db)
        final_user_test = await create_user_test(db, current_user.id, final_assessment_type_id)

        learning_style_result = await predict_learning_style(
            data=input_data.learning_style.responses,
            db=db,
            current_user=current_user,
            final_user_test=final_user_test
        )
        skill_result = await predict_skills(
            responses=input_data.skill.responses,
            db=db,
            current_user=current_user,
            final_user_test=final_user_test
        )
        personality_result = await process_personality_assessment(
            input_data=input_data.personality.responses,
            db=db,
            current_user=current_user,
            final_user_test=final_user_test
        )
        interest_result = await process_interest_assessment(
            responses=input_data.interest.responses,
            db=db,
            current_user=current_user,
            final_user_test=final_user_test
        )
        value_result = await process_value_assessment(
            responses=input_data.value.responses,
            db=db,
            current_user=current_user,
            final_user_test=final_user_test
        )

        return AllAssessmentsResponse(
            learning_style=learning_style_result,
            skill=skill_result,
            personality=personality_result,
            interest=interest_result,
            value=value_result
        )

    except Exception as e:
        logger.exception("Error processing final assessment")
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
