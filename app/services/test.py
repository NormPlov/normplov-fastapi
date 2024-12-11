import logging
import uuid

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql import text
from datetime import date
from sqlalchemy.orm import joinedload
from app.models import UserResponse, UserTest
from app.schemas.assessment import AssessmentResponseData
from datetime import datetime
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
from sqlalchemy import cast
from sqlalchemy.dialects.postgresql import UUID
from app.schemas.payload import BaseResponse
from app.utils.pagination import paginate_results

logger = logging.getLogger(__name__)


async def get_shared_test(test_uuid: str, db: AsyncSession) -> BaseResponse:
    try:
        stmt = select(UserTest).where(
            cast(UserTest.uuid, UUID) == cast(test_uuid, UUID),
            UserTest.is_deleted == False
        )
        result = await db.execute(stmt)
        user_test = result.scalars().first()

        if not user_test:
            raise HTTPException(status_code=404, detail="Test not found or deleted.")

        response_stmt = select(UserResponse).where(
            UserResponse.user_test_id == user_test.id,
            UserResponse.is_deleted == False
        )
        response_result = await db.execute(response_stmt)
        user_response = response_result.scalars().first()

        if not user_response:
            raise HTTPException(status_code=404, detail="No response found for the test.")

        response_payload = {
            "response_uuid": user_response.uuid,
            "uuid": user_response.uuid,
            "response_data": user_response.response_data,
            "is_draft": user_response.is_draft,
            "created_at": user_response.created_at.strftime("%d-%B-%Y %H:%M:%S"),
            "updated_at": user_response.updated_at.strftime("%d-%B-%Y %H:%M:%S") if user_response.updated_at else None
        }

        return BaseResponse(
            date=date.today(),
            status=200,
            payload={
                "test_uuid": user_test.uuid,
                "test_name": user_test.name,
                "response": response_payload
            },
            message="User response retrieved successfully."
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")


async def generate_shareable_link(
    test_uuid: str, user_id: int, base_url: str, db: AsyncSession
) -> BaseResponse:
    try:
        stmt = select(UserTest).where(
            cast(UserTest.uuid, UUID) == cast(test_uuid, UUID),
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
        # Fetch the test
        stmt = select(UserTest).where(
            UserTest.uuid == test_uuid,
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
            payload={"test_uuid": test_uuid},
            message="Test deleted successfully."
        )
        return response

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")


async def get_tests_by_user(
    user_id: int,
    db: AsyncSession,
    search: str = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    filter_by: dict = None,
    page: int = 1,
    page_size: int = 10,
):
    try:
        query = select(UserTest).where(
            UserTest.user_id == user_id,
            UserTest.is_deleted == False,
            UserTest.user_responses.any(is_draft=False)
        )

        if search:
            query = query.where(UserTest.name.ilike(f"%{search}%"))

        if filter_by:
            for key, value in filter_by.items():
                if hasattr(UserTest, key):
                    query = query.where(getattr(UserTest, key) == value)

        if hasattr(UserTest, sort_by):
            sort_column = getattr(UserTest, sort_by)
            if sort_order.lower() == "asc":
                query = query.order_by(sort_column.asc())
            else:
                query = query.order_by(sort_column.desc())

        result = await db.execute(query)
        tests = result.scalars().all()

        if not tests:
            raise HTTPException(status_code=404, detail="No tests found for this user.")

        formatted_tests = [
            {
                "test_uuid": str(test.uuid),
                "test_name": test.name,
                "is_completed": test.is_completed,
                "is_deleted": test.is_deleted,
                "created_at": test.created_at.strftime("%d-%B-%Y"),
                "updated_at": test.updated_at.strftime("%d-%B-%Y") if test.updated_at else None,
            }
            for test in tests
        ]

        # Paginate results
        paginated_results = paginate_results(formatted_tests, page, page_size)

        return paginated_results

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")


async def create_user_test(
    db: AsyncSession,
    user_id: int,
    test_name_prefix: str,
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

        # Determine the next test index
        if latest_test and latest_test.startswith(test_name_prefix):
            try:
                latest_index = int(latest_test.split(" ")[-1])
                next_index = latest_index + 1
            except ValueError:
                next_index = 1
        else:
            next_index = 1

        test_name = f"{test_name_prefix} Test {next_index}"

        new_test = UserTest(
            uuid=str(uuid.uuid4()),
            user_id=user_id,
            name=test_name,
            assessment_type_id=assessment_type_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            is_completed=False,
            is_deleted=False,
        )
        db.add(new_test)
        await db.commit()
        await db.refresh(new_test)

        return new_test

    except Exception as e:
        raise RuntimeError(f"Failed to create user test: {e}")


async def get_assessment_responses_by_test(
    test_uuid: str,
    db: AsyncSession,
    user_id: int
) -> list[AssessmentResponseData]:
    try:
        # Ensure explicit casting of test_uuid to UUID for compatibility
        stmt = (
            select(UserResponse)
            .options(joinedload(UserResponse.assessment_type))
            .where(
                UserResponse.user_test.has(
                    cast(UserTest.uuid, UUID) == cast(test_uuid, UUID)
                ),
                UserResponse.user_id == user_id,
                UserResponse.is_deleted == False
            )
        )
        result = await db.execute(stmt)
        user_responses = result.scalars().all()

        if not user_responses:
            raise HTTPException(
                status_code=404,
                detail=f"No assessment responses found for test UUID: {test_uuid}"
            )

        # Map responses to schema and format
        response_data = [
            AssessmentResponseData(
                assessment_type=response.assessment_type.name,
                response_data=response.response_data,
                created_at=response.created_at.strftime("%A, %d, %Y")
            )
            for response in user_responses
        ]

        return response_data

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")