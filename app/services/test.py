import logging
import traceback
import uuid
import json
import os

from fastapi import Request
from uuid import UUID
from typing import List, Dict, Any, Optional, Tuple
from io import BytesIO
import pandas as pd
from pydantic import UUID4
from html2image import Html2Image
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
from app.schemas.test_career import CareerData, CategoryWithResponsibilities, MajorData
from app.utils.pagination import paginate_results
from fastapi.templating import Jinja2Templates

logger = logging.getLogger(__name__)


# Configure Jinja2 templates
templates = Jinja2Templates(directory="app/templates")


async def fetch_all_tests_with_users(db: AsyncSession, page: int = 1, page_size: int = 1000) -> list:

    try:
        if page < 1:
            raise format_http_exception(
                status_code=400,
                message="Invalid page number.",
                details="Page number must be greater than or equal to 1.",
            )

        if page_size < 1 or page_size > 1000:
            raise format_http_exception(
                status_code=400,
                message="Invalid page size.",
                details="Page size must be between 1 and 1000.",
            )

        stmt = (
            select(UserTest)
            .options(joinedload(UserTest.user))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await db.execute(stmt)
        tests = result.scalars().all()

        if not tests:
            raise format_http_exception(
                status_code=404,
                message="No tests found.",
                details="The database contains no tests for the specified criteria.",
            )

        return tests

    except Exception as e:
        raise format_http_exception(
            status_code=500,
            message="An error occurred while fetching tests.",
            details=str(e),
        )


async def generate_excel_for_tests(tests: list) -> BytesIO:

    try:
        if not tests:
            raise format_http_exception(
                status_code=404,
                message="No tests available for Excel export.",
                details="The provided test data is empty.",
            )

        test_data = [
            {
                "Test UUID": test.uuid,
                "Test Name": test.name,
                "User": test.user.username if test.user else "Unknown",
                "Email": test.user.email if test.user else "Unknown",
                "Created At": test.created_at.strftime("%Y-%m-%d"),
                "Is Completed": test.is_completed,
            }
            for test in tests
        ]
        df = pd.DataFrame(test_data)

        # Create Excel in memory
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Tests")
        output.seek(0)

        return output

    except Exception as e:
        raise format_http_exception(
            status_code=500,
            message="Failed to generate Excel file.",
            details=str(e),
        )


async def fetch_specific_career_from_user_response_by_test_uuid(
    db: AsyncSession,
    test_uuid: str,
) -> Optional[CareerData]:
    stmt = (
        select(UserResponse)
        .join(UserTest, UserResponse.user_test_id == UserTest.id)
        .where(UserTest.uuid == test_uuid)
        .where(UserResponse.is_deleted == False)
        .where(UserResponse.is_completed == True)
    )
    result = await db.execute(stmt)
    user_response: Optional[UserResponse] = result.scalars().first()

    if not user_response:
        raise format_http_exception(
            status_code=404,
            message=f"No UserResponse found for test_uuid '{test_uuid}'.",
        )

    try:
        response_data = user_response.response_data
        logger.debug("Response data from API: %s", response_data)

        if isinstance(response_data, str):
            response_data = json.loads(response_data)

    except (json.JSONDecodeError, TypeError) as e:
        logger.exception("Failed to parse JSON response_data")
        raise format_http_exception(
            status_code=400,
            message="Invalid or malformed JSON in user_response.response_data.",
            details=str(e),
        )

    # Look for career-related data in potential keys
    career_keys = ["career_path", "career_recommendations", "related_careers", "strong_careers", "recommendations"]
    career_recommendations = None

    for key in career_keys:
        if key in response_data:
            career_recommendations = response_data[key]
            logger.debug("career_recommendations: %s", career_recommendations)
            if isinstance(career_recommendations, dict) and "recommendations" in career_recommendations:
                career_recommendations = career_recommendations["recommendations"]
            break

    if not career_recommendations or not isinstance(career_recommendations, list):
        raise format_http_exception(
            status_code=404,
            message=f"No career data found for test_uuid '{test_uuid}'.",
        )

    # Default to the first career if multiple are available
    specific_career_json = career_recommendations[0]

    # Convert to CareerData
    categories_json = specific_career_json.get("categories", [])
    categories_list: List[CategoryWithResponsibilities] = [
        CategoryWithResponsibilities(
            category_name=cat.get("category_name", ""),
            responsibilities=cat.get("responsibilities", []),
        )
        for cat in categories_json
    ]

    majors_json = specific_career_json.get("majors", [])
    majors_list: List[MajorData] = [
        MajorData(
            major_name=major.get("major_name", ""),
            schools=major.get("schools", []),
        )
        for major in majors_json
    ]

    return CareerData(
        career_uuid=specific_career_json.get("career_uuid"),
        career_name=specific_career_json.get("career_name", ""),
        description=specific_career_json.get("description", ""),
        categories=categories_list,
        majors=majors_list,
    )


async def get_public_responses(
    db: AsyncSession,
    test_uuid: Optional[str] = None
) -> List[Dict[str, Any]]:
    try:
        query = select(UserResponse).options(
            joinedload(UserResponse.user_test),
            joinedload(UserResponse.assessment_type)
        ).where(
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
        logger.error(f"Error fetching public responses: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while fetching public responses.")


def format_response_data(response_data: Any) -> List[Dict[str, Any]]:
    try:
        if isinstance(response_data, str):
            response_data = json.loads(response_data)

        if isinstance(response_data, list) and all(isinstance(item, dict) for item in response_data):
            return response_data

        if isinstance(response_data, dict):
            return [response_data]

        if isinstance(response_data, list):
            return [{"data": item} for item in response_data]

        return [{"data": response_data}]
    except Exception as e:
        logger.error(f"Error formatting response_data: {e}")
        return [{"data": str(response_data)}]


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

        formatted_tests = []
        for test in paginated_data["items"]:
            formatted_responses = [
                format_response_data(response.response_data)
                for response in test.user_responses
                if not response.is_deleted and response.response_data
            ]
            flattened_responses = [item for sublist in formatted_responses for item in sublist]

            formatted_tests.append(
                UserTestResponseSchema(
                    test_uuid=str(test.uuid),
                    test_name=test.name,
                    assessment_type_name=(
                        test.assessment_type.name if test.assessment_type else None
                    ),
                    response_data=flattened_responses,
                    created_at=test.created_at
                )
            )

        formatted_tests.sort(key=lambda x: x.created_at, reverse=True)

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
    test_uuid: Optional[str] = None,
) -> List[Dict[str, Any]]:
    try:
        query = select(UserResponse).options(
            joinedload(UserResponse.user_test),
            joinedload(UserResponse.assessment_type)
        ).where(UserResponse.is_deleted == False)

        if test_uuid:
            query = query.where(UserResponse.user_test.has(UserTest.uuid == test_uuid))

        result = await db.execute(query)
        responses = result.scalars().all()

        # Deserialize response_data if it's a string
        return [
            {
                "test_uuid": str(response.user_test.uuid),
                "test_name": response.user_test.name,
                "assessment_type_name": response.assessment_type.name,
                "user_response_data": json.loads(response.response_data)
                if isinstance(response.response_data, str) else response.response_data,
                "created_at": response.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "is_deleted": response.is_deleted,
            }
            for response in responses
        ]

    except Exception as e:
        logger.error(f"Error fetching user responses: {e}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred while fetching user responses.",
        )


async def render_html_for_test(request: Request, test_name: str, test_data: dict) -> str:
    try:
        # Ensure `test_data` contains the required fields
        if not isinstance(test_data, dict):
            raise ValueError(f"test_data must be a dictionary, got {type(test_data)}")

        # Map templates for each assessment type
        template_map = {
            "Personality Test": "assessments/personality_test.html",
            "Skill Test": "assessments/skill_test.html",
            "Interest Test": "assessments/interest_test.html",
            "Learning Style Test": "assessments/learning_style_test.html",
            "Value Test": "assessments/value_test.html",
            "All Test": "assessments/all_tests.html",
        }

        # Select the template based on the test name
        template_file = template_map.get(test_name)
        if not template_file:
            raise ValueError(f"No template found for test_name: {test_name}")

        # Extract user response data
        user_response_data = test_data.get("user_response_data", {})
        if not user_response_data:
            raise ValueError("Missing 'user_response_data' in test_data.")

        # log the response from each test
        logger.debug(f"user_response_data: {user_response_data}")

        # Render the template with the required context
        html_content = templates.TemplateResponse(
            template_file,
            {
                "request": request,
                "user_response_data": user_response_data,
                "test_name": test_data.get("test_name", "Unknown Test"),
                "test_uuid": test_data.get("test_uuid", "Unknown UUID"),
            }
        ).body.decode("utf-8")

        logger.debug(f"Generated HTML content: {html_content}")
        return html_content

    except Exception as e:
        logger.error(f"Error rendering template: {traceback.format_exc()}")
        raise Exception(f"Error rendering template: {traceback.format_exc()}")


async def html_to_image(html_content: str) -> BytesIO:

    try:
        hti = Html2Image()

        temp_image_path = "temp_rendered_image.png"
        temp_html_path = "temp_rendered_html.html"

        with open(temp_html_path, "w", encoding="utf-8") as file:
            file.write(html_content)

        # Here is the way we set the size of the image
        hti.screenshot(
            html_file=temp_html_path,
            save_as=temp_image_path,
            size=(1200, 630)
        )

        with open(temp_image_path, "rb") as image_file:
            image_stream = BytesIO(image_file.read())

        os.remove(temp_image_path)
        os.remove(temp_html_path)

        return image_stream

    except Exception as e:
        raise Exception(f"Error while generating image: {traceback.format_exc()}")


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
            "LearningStyle": "learningStyle",
            "Interests": "interest",
            "Skill": "skill",
            "AllTests": "all"
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
) -> UserTest:
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

        if assessment_type == "All Tests":
            test_name = assessment_type
        else:
            test_name = f"{assessment_type} Test"

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

    except HTTPException as e:
        raise
    except Exception as e:
        await db.rollback()
        raise format_http_exception(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="An error occurred while creating the user test.",
            details=str(e),
        )
