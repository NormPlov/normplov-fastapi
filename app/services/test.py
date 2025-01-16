import logging
import traceback
import uuid
import json

from uuid import UUID
from typing import List, Dict, Any, Optional, Tuple
from io import BytesIO
from pydantic import UUID4
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
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
templates = Jinja2Templates(directory="templates")


async def fetch_specific_career_from_user_response_by_test_uuid(
    db: AsyncSession,
    test_uuid: str,
    career_name: Optional[str] = None,
    career_uuid: Optional[str] = None,
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
        raise HTTPException(
            status_code=404,
            detail=f"No UserResponse found for test_uuid '{test_uuid}'"
        )

    try:
        response_data = user_response.response_data
        logger.debug("Response data from API: %s", response_data)

        if isinstance(response_data, str):
            response_data = json.loads(response_data)

    except (json.JSONDecodeError, TypeError) as e:
        logger.exception("Failed to parse JSON response_data")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid or malformed JSON in user_response.response_data: {str(e)}"
        )

    # Look for career-related data in potential keys
    career_keys = ["career_path", "career_recommendations", "related_careers", "strong_careers", "recommendations"]
    career_recommendations = None

    for key in career_keys:
        if key in response_data:
            career_recommendations = response_data[key]
            logger.debug("career_recommendations: %s", career_recommendations)
            # If the key contains nested recommendations, extract them
            if isinstance(career_recommendations, dict) and "recommendations" in career_recommendations:
                career_recommendations = career_recommendations["recommendations"]
            break

    if not career_recommendations or not isinstance(career_recommendations, list):
        raise HTTPException(
            status_code=404,
            detail=f"No career data found for test_uuid '{test_uuid}' and specified filters."
        )

    # Find the specific career by name or UUID
    specific_career_json = None
    if career_uuid or career_name:
        specific_career_json = next(
            (career for career in career_recommendations
             if (career_uuid and career.get("career_uuid") == career_uuid)
             or (career_name and career.get("career_name") == career_name)),
            None
        )

    # If no specific filters, return the first career as default
    if not specific_career_json and not career_uuid and not career_name:
        specific_career_json = career_recommendations[0]  # Default to first career

    if not specific_career_json:
        raise HTTPException(
            status_code=404,
            detail=f"No career found for career_uuid='{career_uuid}' or career_name='{career_name}' in test_uuid '{test_uuid}'."
        )

    # Convert to CareerData
    categories_json = specific_career_json.get("categories", [])
    categories_list: List[CategoryWithResponsibilities] = [
        CategoryWithResponsibilities(
            category_name=cat.get("category_name", ""),
            responsibilities=cat.get("responsibilities", [])
        ) for cat in categories_json
    ]

    majors_json = specific_career_json.get("majors", [])
    majors_list: List[MajorData] = [
        MajorData(
            major_name=major.get("major_name", ""),
            schools=major.get("schools", [])
        ) for major in majors_json
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


async def render_html_for_test(test_name: str, test_data: dict) -> str:
    try:
        template_map = {
            "Personality Test": "personality_test.html",
            "Skill Test": "skill_test.html",
            "Interest Test": "interest_test.html",
            "Learning Style Test": "learning_style_test.html",
            "Value Test": "value_test.html",
            "All Tests": "all_test.html"
        }

        # Get the template file for the test
        template_file = template_map.get(test_name)
        if not template_file:
            raise ValueError(f"No template found for test_name: {test_name}")

        return templates.TemplateResponse(template_file, {"test_data": test_data}).body.decode("utf-8")
    except Exception as e:
        raise Exception(f"Error rendering template: {traceback.format_exc()}")


async def html_to_image(html_content: str) -> BytesIO:

    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1024x768')

    try:
        with webdriver.Chrome(options=options) as driver:
            driver.get("data:text/html;charset=utf-8," + html_content)
            driver.implicitly_wait(2)

            screenshot = driver.get_screenshot_as_png()

        return BytesIO(screenshot)
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
