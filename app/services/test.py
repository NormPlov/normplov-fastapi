import json
import uuid
from sqlalchemy.sql import text
from datetime import date
from sqlalchemy.orm import joinedload
from app.models import UserResponse, UserTest, AssessmentType
from app.schemas.assessment import AssessmentResponseData
from datetime import datetime
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.schemas.payload import BaseResponse


async def get_shared_test(test_uuid: str, db: AsyncSession) -> BaseResponse:
    try:
        stmt = select(UserTest).where(
            UserTest.uuid == test_uuid,
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
            "response_id": user_response.id,
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
        # Validate the test
        stmt = select(UserTest).where(
            UserTest.uuid == test_uuid,
            UserTest.user_id == user_id,
            UserTest.is_deleted == False
        )
        result = await db.execute(stmt)
        user_test = result.scalars().first()

        if not user_test:
            raise HTTPException(status_code=404, detail="Test not found or already deleted.")

        # Construct the shareable link
        shareable_link = f"{base_url}/shared-tests/{test_uuid}"

        # Prepare and return the response
        return BaseResponse(
            date=date.today(),
            status=200,
            payload={"shareable_link": shareable_link},
            message="Shareable link generated successfully."
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")


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


async def get_tests_by_user(user_id: int, db: AsyncSession):
    try:
        stmt = select(UserTest).where(
            UserTest.user_id == user_id,
            UserTest.is_deleted == False
        ).order_by(UserTest.created_at.desc())

        result = await db.execute(stmt)
        tests = result.scalars().all()

        if not tests:
            raise HTTPException(status_code=404, detail="No tests found for this user.")

        return [
            {
                "test_uuid": test.uuid,
                "test_name": test.name,
                "is_completed": test.is_completed,
                "is_deleted": test.is_deleted,
                "created_at": test.created_at,
            }
            for test in tests
        ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")


async def get_test_details(test_uuid: str, user_id: int, db: AsyncSession):
    try:
        # Validate test_uuid and fetch UserTest
        stmt = select(UserTest).where(
            UserTest.uuid == test_uuid,
            UserTest.user_id == user_id,
            UserTest.is_deleted == False
        )
        result = await db.execute(stmt)
        user_test = result.scalars().first()

        if not user_test:
            raise HTTPException(status_code=404, detail="Test not found.")

        # Fetch all assessment types
        assessment_types_stmt = select(AssessmentType).where(
            AssessmentType.is_deleted == False
        )
        assessment_types_result = await db.execute(assessment_types_stmt)
        assessment_types = assessment_types_result.scalars().all()

        if not assessment_types:
            raise HTTPException(status_code=404, detail="No assessment types found.")

        assessments_data = []

        for assessment_type in assessment_types:
            # Check if a draft exists for this assessment type
            draft_stmt = select(UserResponse).where(
                UserResponse.user_test_id == user_test.id,
                UserResponse.assessment_type_id == assessment_type.id,
                UserResponse.is_draft == True,
                UserResponse.is_deleted == False
            )
            draft_result = await db.execute(draft_stmt)
            draft = draft_result.scalars().first()

            # Determine completion status
            if draft:
                completion_status = "in_progress"
            else:
                response_stmt = select(UserResponse).where(
                    UserResponse.user_test_id == user_test.id,
                    UserResponse.assessment_type_id == assessment_type.id,
                    UserResponse.is_draft == False,
                    UserResponse.is_deleted == False
                )
                response_result = await db.execute(response_stmt)
                response = response_result.scalars().first()
                completion_status = "completed" if response else "not_started"

            # Parse draft response data if available
            draft_data = None
            if draft and draft.response_data:
                try:
                    if isinstance(draft.response_data, str):
                        draft_data = json.loads(draft.response_data)
                    else:
                        draft_data = draft.response_data

                    if isinstance(draft_data, dict) and not draft_data.get("responses"):
                        draft_data = {"responses": draft_data}
                except json.JSONDecodeError as e:
                    print("JSON Decode Error:", str(e))
                    draft_data = {"responses": {}}

            assessments_data.append({
                "assessment_type_uuid": assessment_type.uuid,
                "assessment_type_name": assessment_type.name,
                "is_draft": bool(draft),
                "draft_data": draft_data,
                "completion_status": completion_status
            })

        return {
            "test_uuid": user_test.uuid,
            "test_name": user_test.name,
            "assessments": assessments_data
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")


async def create_user_test(db: AsyncSession, user_id: int, test_name_prefix: str) -> UserTest:
    try:
        # Query the latest test name to determine the next index
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

        # Create and save the new test
        new_test = UserTest(
            uuid=str(uuid.uuid4()),
            user_id=user_id,
            name=test_name,
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
        stmt = (
            select(UserResponse)
            .options(joinedload(UserResponse.assessment_type))
            .where(
                UserResponse.user_test.has(uuid=test_uuid),
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
