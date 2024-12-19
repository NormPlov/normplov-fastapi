import logging

from typing import Optional, List, Dict, Any
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from sqlalchemy.sql import func, text
from app.models import User, UserFeedback, UserTest, UserResponse


logger = logging.getLogger(__name__)


async def get_admin_user_responses(
    db: AsyncSession,
    test_uuid: str,
    user_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    try:
        query = select(UserResponse).options(
            joinedload(UserResponse.user_test),
            joinedload(UserResponse.assessment_type),
            joinedload(UserResponse.user),
        ).where(
            UserResponse.is_deleted == False,
            UserResponse.user_test.has(UserTest.uuid == test_uuid),
        )

        if user_id:
            query = query.where(UserResponse.user_id == user_id)

        result = await db.execute(query)
        responses = result.scalars().all()

        if not responses:
            logger.info(f"No responses found for test UUID {test_uuid}")
            return []

        return [
            {
                "test_uuid": str(response.user_test.uuid),
                "test_name": response.user_test.name,
                "user_id": response.user.id if response.user else None,
                "user_username": response.user.username if response.user else "Unknown",
                "assessment_type_name": response.assessment_type.name if response.assessment_type else "Unknown",
                "user_response_data": response.response_data,
                "created_at": response.created_at.strftime("%Y-%m-%d %H:%M:%S") if response.created_at else None,
                "is_deleted": response.is_deleted,
            }
            for response in responses
        ]

    except AttributeError as attr_err:
        logger.error(f"AttributeError while processing responses for test {test_uuid}: {attr_err}")
        raise HTTPException(
            status_code=500,
            detail="An internal error occurred while processing user responses.",
        )
    except Exception as e:
        logger.error(f"Unexpected error while fetching user responses for test {test_uuid}: {e}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred while fetching user responses.",
        )


async def fetch_metrics(db: AsyncSession):
    # Total counts
    total_users = await db.scalar(select(func.count(User.id)))
    total_feedbacks = await db.scalar(select(func.count(UserFeedback.id)))
    total_tests = await db.scalar(select(func.count(UserTest.id)))
    total_active_users = await db.scalar(select(func.count(User.id)).where(User.is_active == True))

    # Line chart data: Visits by country
    line_chart_query = text("""
        SELECT COALESCE(country, 'Unknown') AS country,  -- Replace NULL with 'Unknown'
            SUM(CASE WHEN DATE_TRUNC('month', created_at) = DATE_TRUNC('month', NOW()) THEN 1 ELSE 0 END) AS this_month_visits,
            SUM(CASE WHEN DATE_TRUNC('month', created_at) = DATE_TRUNC('month', NOW()) - INTERVAL '1 month' THEN 1 ELSE 0 END) AS last_month_visits
        FROM users
        GROUP BY country
        ORDER BY country;
    """)

    line_chart_result = await db.execute(line_chart_query)
    line_chart_data = [
        {
            "country": row["country"] if row["country"] is not None else "Unknown",
            "this_month_visits": row["this_month_visits"],
            "last_month_visits": row["last_month_visits"]
        }
        for row in line_chart_result.mappings()
    ]

    # Bar chart data: Test counts by day for this week and last week
    bar_chart_query = text("""
        SELECT TO_CHAR(created_at, 'Day') AS day,
            SUM(CASE WHEN created_at >= DATE_TRUNC('week', NOW()) THEN 1 ELSE 0 END) AS this_week_tests,
            SUM(CASE WHEN created_at >= DATE_TRUNC('week', NOW()) - INTERVAL '1 week' AND created_at < DATE_TRUNC('week', NOW()) THEN 1 ELSE 0 END) AS last_week_tests
        FROM user_tests
        WHERE created_at >= DATE_TRUNC('week', NOW()) - INTERVAL '2 weeks'
        GROUP BY TO_CHAR(created_at, 'Day')
        ORDER BY MIN(created_at);
    """)
    bar_chart_result = await db.execute(bar_chart_query)
    bar_chart_data = [
        {"day": row["day"].strip(), "this_week_tests": row["this_week_tests"], "last_week_tests": row["last_week_tests"]}
        for row in bar_chart_result.mappings()
    ]

    return {
        "total_users": total_users,
        "total_feedbacks": total_feedbacks,
        "total_tests": total_tests,
        "total_active_users": total_active_users,
        "line_chart_data": line_chart_data,
        "bar_chart_data": bar_chart_data,
    }
