import json
import logging
import uuid
from uuid import UUID

from typing import List, Dict, Any, Optional, Tuple

from pydantic import UUID4
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy.sql import text
from datetime import date
from app.models import UserResponse, UserTest, User
from datetime import datetime
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
from sqlalchemy import cast
from app.schemas.payload import BaseResponse
from app.schemas.test import UserTestResponseSchema, PaginationMetadata
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
                UserTest.user_id == current_user.id,  # Use the current user's ID
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
                    if not response.is_deleted and response.response_data  # Only include valid responses
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
    test_uuid: str, user_id: int, base_url: str, db: AsyncSession
) -> BaseResponse:
    try:

        stmt = select(UserTest).where(
            UserTest.uuid == test_uuid,
            UserTest.user_id == user_id,
            UserTest.is_deleted == False
        )
        result = await db.execute(stmt)
        user_test = result.scalars().first()

        if not user_test:
            raise HTTPException(status_code=404, detail="Test not found or already deleted.")

        shareable_link = f"{base_url}/shared-tests/{test_uuid}"

        return BaseResponse(
            date=date.today(),
            status=200,
            payload={"shareable_link": shareable_link},
            message="Shareable link generated successfully."
        )

    except SQLAlchemyError as e:
        logger.error(f"Database error during test fetch: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail="There was a problem with the database query. Please check the data types or parameters."
        )
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while generating the shareable link."
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
    assessment_type_id: int
) -> UserTest:
    try:
        stmt = text(
            """
            SELECT name
            FROM user_tests
            WHERE user_id = :user_id
            ORDER BY created_at DESC
            LIMIT 1
            """
        )
        result = await db.execute(stmt, {"user_id": user_id})
        latest_test = result.scalar()

        if latest_test and latest_test.startswith("Test "):
            try:
                latest_index = int(latest_test.replace("Test ", "").strip())
                next_index = latest_index + 1
            except ValueError:
                next_index = 1
        else:
            next_index = 1

        test_name = f"Test {next_index}"

        while True:
            generated_uuid = str(uuid.uuid4())
            validated_uuid = validate_uuid(generated_uuid)
            existing_test = await db.execute(
                select(UserTest).where(UserTest.uuid == validated_uuid)
            )
            if not existing_test.scalars().first():
                break

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

    except Exception as e:
        logger.error(f"Failed to create user test: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred while creating the user test.")
