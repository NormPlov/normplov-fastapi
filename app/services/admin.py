import logging

from typing import Optional, List, Dict, Any
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from sqlalchemy.sql import func, text
from app.models import User, UserFeedback, UserTest, UserResponse
from collections import defaultdict

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


async def fetch_metrics(db: AsyncSession, year: int = None, month: int = None):
    total_users = await db.scalar(select(func.count(User.id)))
    total_feedbacks = await db.scalar(select(func.count(UserFeedback.id)))
    total_tests = await db.scalar(select(func.count(UserTest.id)))
    total_active_users = await db.scalar(select(func.count(User.id)).where(User.is_active == True))

    job_filters = "WHERE is_deleted = FALSE AND is_active = TRUE"
    params = {}

    if year:
        job_filters += " AND EXTRACT(YEAR FROM created_at) = :year"
        params["year"] = year
    if month:
        job_filters += " AND EXTRACT(MONTH FROM created_at) = :month"
        params["month"] = month

    bar_chart_jobs_query = text(f"""
        SELECT category, COUNT(*) AS count
        FROM jobs
        {job_filters}
        GROUP BY category
        ORDER BY count DESC
    """)
    bar_chart_jobs_result = await db.execute(bar_chart_jobs_query, params)
    bar_chart_jobs_data = [
        {"category": row["category"], "count": row["count"]} for row in bar_chart_jobs_result.mappings()
    ]

    pie_chart_query = text("""
        SELECT type, COUNT(*) AS count
        FROM schools
        WHERE is_deleted = FALSE
        GROUP BY type
    """)
    pie_chart_result = await db.execute(pie_chart_query)
    pie_chart_data = [
        {"type": row["type"], "count": row["count"]} for row in pie_chart_result.mappings()
    ]

    # Bar Chart: Count jobs by category
    bar_chart_jobs_query = text("""
            SELECT category, COUNT(*) AS count
            FROM jobs
            WHERE is_deleted = FALSE AND is_active = TRUE
            GROUP BY category
            ORDER BY count DESC
        """)
    bar_chart_jobs_result = await db.execute(bar_chart_jobs_query)
    bar_chart_jobs_data = [
        {"category": row["category"], "count": row["count"]} for row in bar_chart_jobs_result.mappings()
    ]

    filters = "WHERE ur.is_deleted = FALSE"
    params = {}

    if year:
        filters += " AND EXTRACT(YEAR FROM ur.created_at) = :year"
        params["year"] = year
    if month:
        filters += " AND EXTRACT(MONTH FROM ur.created_at) = :month"
        params["month"] = month

    bar_chart_assessments_query = text(f"""
            SELECT at.name AS assessment_type, COUNT(ur.id) AS count
            FROM user_responses ur
            JOIN assessment_types at ON ur.assessment_type_id = at.id
            {filters}
            GROUP BY at.name
            ORDER BY count DESC
        """)
    bar_chart_assessments_result = await db.execute(bar_chart_assessments_query, params)
    bar_chart_assessments_data = [
        {"assessment_type": row["assessment_type"], "count": row["count"]} for row in
        bar_chart_assessments_result.mappings()
    ]

    line_chart_query = text("""
        SELECT country, COUNT(*) AS user_count
        FROM users
        WHERE is_deleted = FALSE
        GROUP BY country
        ORDER BY user_count DESC;
    """)
    line_chart_result = await db.execute(line_chart_query)
    line_chart_data_raw = [
        {"country": row["country"], "user_count": row["user_count"]} for row in line_chart_result.mappings()
    ]

    line_chart_data = defaultdict(int)
    for row in line_chart_data_raw:
        normalized_country = row["country"].strip() if row["country"] else "Unknown"
        line_chart_data[normalized_country] += row["user_count"]

    line_chart_data = [{"country": k, "user_count": v} for k, v in line_chart_data.items()]

    return {
        "total_users": total_users,
        "total_feedbacks": total_feedbacks,
        "total_tests": total_tests,
        "total_active_users": total_active_users,
        "pie_chart_data": pie_chart_data,
        "bar_chart_jobs_data": bar_chart_jobs_data,
        "bar_chart_assessments_data": bar_chart_assessments_data,
        "line_chart_data": line_chart_data,
    }
