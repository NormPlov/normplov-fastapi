import logging
import uuid

from typing import List, Dict, Any, Optional
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload
from sqlalchemy.sql import text
from datetime import date
from app.models import UserResponse, UserTest, User, AssessmentType
from datetime import datetime
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
from sqlalchemy import cast
from sqlalchemy.dialects.postgresql import UUID
from app.schemas.payload import BaseResponse
from app.utils.pagination import paginate_results
from sqlalchemy.types import String

logger = logging.getLogger(__name__)


async def get_all_tests(
    db: AsyncSession,
    search: Optional[str] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    filter_by: Optional[str] = None,
    page: int = 1,
    page_size: int = 10,
) -> Dict[str, Any]:
    try:
        # Base query
        query = (
            select(UserTest)
            .join(User)
            .join(AssessmentType, UserTest.assessment_type_id == AssessmentType.id)
            .options(
                joinedload(UserTest.user),
                joinedload(UserTest.user_responses),
                joinedload(UserTest.assessment_type),  # Load assessment type
            )
            .where(UserTest.is_deleted == False)
        )

        # Apply search
        if search:
            query = query.where(
                UserTest.name.ilike(f"%{search}%")
                | User.username.ilike(f"%{search}%")
                | AssessmentType.name.ilike(f"%{search}%")  # Search in assessment type
                | UserResponse.response_data.cast(String).ilike(f"%{search}%")
            )

        # Apply filters
        if filter_by:
            try:
                import json
                filters = json.loads(filter_by)
                if not isinstance(filters, dict):
                    raise ValueError("Filter must be a JSON object.")
                for key, value in filters.items():
                    if hasattr(UserTest, key):
                        query = query.where(getattr(UserTest, key) == value)
            except (ValueError, TypeError) as e:
                raise HTTPException(status_code=400, detail=f"Invalid filter format: {e}")

        # Apply sorting
        if hasattr(UserTest, sort_by):
            sort_column = getattr(UserTest, sort_by)
            query = query.order_by(sort_column.asc() if sort_order == "asc" else sort_column.desc())
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid sort_by field. Choose a valid field from UserTest or User.",
            )

        # Execute query
        result = await db.execute(query)
        tests = result.unique().scalars().all()

        # Format response
        formatted_tests = [
            {
                "test_uuid": str(test.uuid),
                "test_name": test.name,
                "assessment_type_name": test.assessment_type.name if test.assessment_type else None,  # Include assessment type name
                "is_completed": test.is_completed,
                "is_deleted": test.is_deleted,
                "created_at": test.created_at.strftime("%d-%B-%Y"),
                "user": {
                    "username": test.user.username,
                    "avatar": test.user.avatar,
                    "email": test.user.email,
                },
                "responses": [
                    {
                        "response_uuid": str(response.uuid),
                        "response_data": response.response_data,
                        "is_draft": response.is_draft,
                        "is_completed": response.is_completed,
                    }
                    for response in test.user_responses
                ],
            }
            for test in tests
        ]

        # Paginate results
        paginated_results = paginate_results(formatted_tests, page, page_size)

        return paginated_results

    except Exception as e:
        logger.error(f"Error fetching all tests: {e}")
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")


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


async def get_user_tests(
    db: AsyncSession,
    user_id: int,
    search: Optional[str] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    filter_by: Optional[str] = None,
    page: int = 1,
    page_size: int = 10,
) -> Dict[str, Any]:
    try:
        query = select(UserTest).options(
            joinedload(UserTest.user), joinedload(UserTest.assessment_type)
        ).where(
            UserTest.user_id == user_id,
            UserTest.is_deleted == False
        )

        if search:
            query = query.where(UserTest.name.ilike(f"%{search}%"))

        if filter_by:
            try:
                import json
                filters = json.loads(filter_by)
                if not isinstance(filters, dict):
                    raise ValueError("Filter must be a JSON object.")
                for key, value in filters.items():
                    if hasattr(UserTest, key):
                        query = query.where(getattr(UserTest, key) == value)
            except (ValueError, TypeError) as e:
                raise HTTPException(status_code=400, detail=f"Invalid filter format: {e}")

        if hasattr(UserTest, sort_by):
            sort_column = getattr(UserTest, sort_by)
            query = query.order_by(sort_column.asc() if sort_order == "asc" else sort_column.desc())
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid sort_by field. Choose a valid field from UserTest.",
            )

        result = await db.execute(query)
        tests = result.scalars().all()

        formatted_tests = [
            {
                "test_uuid": str(test.uuid),
                "test_name": test.name,
                "assessment_type_name": test.assessment_type.name if test.assessment_type else None,
                "is_completed": test.is_completed,
                "is_deleted": test.is_deleted,
                "created_at": test.created_at.strftime("%d-%B-%Y"),
            }
            for test in tests
        ]

        paginated_results = paginate_results(formatted_tests, page, page_size)

        return paginated_results

    except Exception as e:
        logger.error(f"Error fetching user tests: {e}")
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")


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


async def delete_test(test_uuid: str, user_id: int, db: AsyncSession):
    try:
        stmt = select(UserTest).where(
            UserTest.uuid == cast(test_uuid, UUID),
            UserTest.user_id == user_id,
            UserTest.is_deleted == False
        )
        result = await db.execute(stmt)
        user_test = result.scalars().first()

        if not user_test:
            raise HTTPException(status_code=404, detail="Test not found or already deleted.")

        # Soft delete the test
        user_test.is_deleted = True
        await db.commit()

        # Prepare the response
        response = BaseResponse(
            date=date.today(),
            status=200,
            payload={"test_uuid": str(test_uuid)},
            message="Test deleted successfully."
        )
        return response

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")


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

        new_test = UserTest(
            uuid=uuid.uuid4(),
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
        raise RuntimeError(f"Failed to create user test: {e}")

