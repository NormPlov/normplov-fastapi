import json
import logging
import uuid

from uuid import UUID
from typing import List, Dict, Any, Optional, Tuple
from pydantic import UUID4
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload, selectinload
from datetime import date
from app.exceptions.formatters import format_http_exception
from app.models import UserResponse, UserTest, User, AssessmentType
from datetime import datetime
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from app.schemas.payload import BaseResponse
from app.schemas.test import UserTestResponseSchema, PaginationMetadata, UserTestResponse
from app.utils.pagination import paginate_results

logger = logging.getLogger(__name__)


async def fetch_user_tests_for_current_user(
    db: AsyncSession,
    current_user: User,
    page: int,
    page_size: int
) -> Tuple[List[UserTestResponseSchema], PaginationMetadata]:
    try:
        query = (
            select(UserTest)
            .options(
                selectinload(UserTest.assessment_type),
                selectinload(UserTest.user_responses)
            )
            .where(
                UserTest.user_id == current_user.id,
                UserTest.is_deleted == False
            )
            .order_by(UserTest.created_at.desc())
        )

        result = await db.execute(query)
        user_tests = result.scalars().all()

        paginated_data = paginate_results(user_tests, page, page_size)

        formatted_tests = [
            UserTestResponseSchema(
                test_uuid=str(test.uuid),
                test_name=test.name,
                assessment_type_name=(
                    test.assessment_type.name if test.assessment_type else None
                ),
                response_data=[
                    json.loads(response.response_data) if isinstance(response.response_data, str) else response.response_data
                    for response in test.user_responses
                    if not response.is_deleted and response.response_data
                ],
                created_at=test.created_at
            )
            for test in paginated_data["items"]
        ]

        metadata = PaginationMetadata(
            page=paginated_data["metadata"]["page"],
            page_size=paginated_data["metadata"]["page_size"],
            total_items=paginated_data["metadata"]["total_items"],
            total_pages=paginated_data["metadata"]["total_pages"],
        )

        return formatted_tests, metadata

    except SQLAlchemyError as e:
        logger.error(f"Database error: {e}")
        raise Exception("Error retrieving user tests.")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise Exception("An unexpected error occurred.")


async def get_user_responses(
    db: AsyncSession,
    user_id: int,
    test_uuid: Optional[str] = None
) -> List[Dict[str, Any]]:
    try:
        query = select(UserResponse).options(
            joinedload(UserResponse.user_test),
            joinedload(UserResponse.assessment_type)
        ).where(
            UserResponse.user_id == user_id,
            UserResponse.is_deleted == False
        )

        if test_uuid:
            query = query.where(UserResponse.user_test.has(UserTest.uuid == test_uuid))

        result = await db.execute(query)
        responses = result.scalars().all()

        return [
            {
                "test_uuid": str(response.user_test.uuid),
                "test_name": response.user_test.name,
                "assessment_type_name": response.assessment_type.name,
                "user_response_data": response.response_data,
                "created_at": response.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "is_deleted": response.is_deleted,
            }
            for response in responses
        ]

    except Exception as e:
        logger.error(f"Error fetching user responses: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while fetching user responses.")


async def generate_shareable_link(
    test_uuid: str, base_url: str, db: AsyncSession
) -> BaseResponse:
    try:
        stmt = (
            select(UserTest)
            .options(selectinload(UserTest.assessment_type))
            .where(
                UserTest.uuid == test_uuid,
                UserTest.is_deleted == False
            )
        )
        result = await db.execute(stmt)
        user_test = result.scalars().first()

        if not user_test:
            raise HTTPException(
                status_code=404,
                detail="Test not found or already deleted."
            )

        assessment_type_mapping: Dict[str, str] = {
            "Values": "value",
            "Personality": "personality",
            "Learning Style": "learningStyle",
            "Interests": "interest",
            "Skill": "skill",
        }

        assessment_type_key = user_test.assessment_type.name.replace(" ", "")
        specific_path = assessment_type_mapping.get(assessment_type_key)

        if not specific_path:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown assessment type: {user_test.assessment_type.name}"
            )

        shareable_link = f"{base_url}/share-tests/{specific_path}/{test_uuid}"

        test_response = UserTestResponse(
            test_uuid=str(user_test.uuid),
            test_name=user_test.name,
            assessment_type_name=user_test.assessment_type.name.replace(" ", "")
        )

        return BaseResponse(
            date=date.today(),
            status=200,
            payload={
                "shareable_link": shareable_link,
                "test_details": test_response
            },
            message="Shareable link generated successfully."
        )

    except SQLAlchemyError as e:
        logger.error(f"Database error while generating shareable link: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail="Database query error. Please check the parameters."
        )
    except Exception as e:
        logger.error(f"Unexpected error while generating shareable link: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred. Please try again later."
        )


async def delete_test(test_uuid: UUID4, user_id: int, db: AsyncSession):
    try:
        stmt = select(UserTest).where(
            UserTest.uuid == test_uuid,
            UserTest.user_id == user_id,
            UserTest.is_deleted == False,
        )
        result = await db.execute(stmt)
        user_test = result.scalars().first()

        if not user_test:
            raise HTTPException(status_code=404, detail="Test not found or already deleted.")

        user_test.is_deleted = True
        await db.commit()

        response = BaseResponse(
            date=date.today(),
            status=200,
            payload={"test_uuid": str(test_uuid)},
            message="Test deleted successfully.",
        )
        return response

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")


def validate_uuid(value: str) -> str:
    try:
        return str(UUID(value))
    except ValueError:
        raise ValueError(f"Invalid UUID format: {value}")


async def create_user_test(
    db: AsyncSession,
    user_id: int,
    assessment_type_id: int,
    final_user_test: UserTest = None
) -> UserTest:
    if final_user_test:
        return final_user_test
    try:
        assessment_type = (
            await db.execute(
                select(AssessmentType.name).where(AssessmentType.id == assessment_type_id)
            )
        ).scalar_one_or_none()

        if not assessment_type:
            logger.error(f"Assessment type with id={assessment_type_id} not found.")
            raise format_http_exception(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Assessment type not found."
            )

        test_name = f"{assessment_type} Test"
        while True:
            generated_uuid = str(uuid.uuid4())
            validated_uuid = validate_uuid(generated_uuid)
            existing_test = await db.execute(
                select(UserTest).where(UserTest.uuid == validated_uuid)
            )
            if not existing_test.scalars().first():
                break

        # Create new test
        new_test = UserTest(
            uuid=validated_uuid,
            user_id=user_id,
            name=test_name,
            assessment_type_id=assessment_type_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            is_completed=True,
            is_deleted=False,
        )

        db.add(new_test)
        await db.commit()
        await db.refresh(new_test)

        return new_test

    except HTTPException as e:
        raise
    except Exception as e:
        await db.rollback()
        raise format_http_exception(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="An error occurred while creating the user test.",
            details=str(e),
        )
