import logging
from datetime import datetime

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


async def fetch_metrics(db: AsyncSession, year: int = None, month: int = None, week: int = None):
    total_users = await db.scalar(select(func.count(User.id)))
    total_feedbacks = await db.scalar(select(func.count(UserFeedback.id)))
    total_tests = await db.scalar(select(func.count(UserTest.id)))
    total_active_users = await db.scalar(select(func.count(User.id)).where(User.is_active == True))

    pie_chart_query = text("""
        SELECT type, COUNT(*) AS count
        FROM schools
        WHERE is_deleted = FALSE
        GROUP BY type
    """)
    pie_chart_result = await db.execute(pie_chart_query)
    pie_chart_raw_data = [
        {"type": row["type"], "count": row["count"]} for row in pie_chart_result.mappings()
    ]
    total_schools = sum(item["count"] for item in pie_chart_raw_data)
    pie_chart_data = [
        {"type": item["type"], "percentage": round((item["count"] / total_schools) * 100, 2)}
        for item in pie_chart_raw_data
    ]

    current_date = datetime.utcnow()
    current_year = current_date.year
    current_month = current_date.month
    current_week = current_date.isocalendar()[1]

    # Modified bar_chart_jobs_query: Trending Jobs per month (Jan to Dec) using job category instead of title
    bar_chart_jobs_query = text("""
        WITH job_counts AS (
            SELECT 
                EXTRACT(MONTH FROM jobs.posted_at) AS month,
                jobs.category AS label,
                COUNT(jobs.id) AS count
            FROM jobs
            WHERE jobs.is_deleted = FALSE 
              AND jobs.is_active = TRUE 
              AND jobs.category IS NOT NULL 
              AND EXTRACT(YEAR FROM jobs.posted_at) = :current_year
            GROUP BY EXTRACT(MONTH FROM jobs.posted_at), jobs.category
        )
        SELECT 
            month, 
            label, 
            count
        FROM job_counts
        ORDER BY month, count DESC
    """)

    bar_chart_jobs_result = await db.execute(bar_chart_jobs_query, {
        'current_year': current_year
    })

    # Short month names
    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    # Organizing job data by month, and getting top 5 job categories for each month
    bar_chart_jobs_data = {month_name: [] for month_name in month_names}  # Initialize a list for each month

    for row in bar_chart_jobs_result.mappings():
        month = int(row["month"])  # month as integer
        job_category = row["label"]
        job_count = row["count"]

        # Append job category data to the respective month, but limit to top 5 categories
        if len(bar_chart_jobs_data[month_names[month - 1]]) < 5:
            bar_chart_jobs_data[month_names[month - 1]].append({"label": job_category, "count": job_count})

    # Remove months that have no data (i.e., empty lists)
    bar_chart_jobs_data = {month: data for month, data in bar_chart_jobs_data.items() if data}

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
        SELECT EXTRACT(MONTH FROM created_at) AS month, 
               COUNT(*) AS user_count, 
               EXTRACT(YEAR FROM created_at) AS year
        FROM users
        WHERE is_deleted = FALSE AND EXTRACT(YEAR FROM created_at) IN (EXTRACT(YEAR FROM NOW()), EXTRACT(YEAR FROM NOW()) - 1)
        GROUP BY EXTRACT(MONTH FROM created_at), EXTRACT(YEAR FROM created_at)
        ORDER BY month
    """)
    line_chart_result = await db.execute(line_chart_query)

    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    line_chart_data = [{"month": month,
                        str(datetime.utcnow().year - 1): 0,
                        str(datetime.utcnow().year): 0} for month in months]

    for row in line_chart_result.mappings():
        month_index = int(row["month"]) - 1
        year = int(row["year"])

        if year == datetime.utcnow().year - 1:
            line_chart_data[month_index][str(datetime.utcnow().year - 1)] = row["user_count"]
        elif year == datetime.utcnow().year:
            line_chart_data[month_index][str(datetime.utcnow().year)] = row["user_count"]

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
