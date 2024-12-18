from pydantic import BaseModel
from typing import List, Optional


class LineChartData(BaseModel):
    country: Optional[str]
    this_month_visits: int
    last_month_visits: int


class BarChartData(BaseModel):
    day: str
    this_week_tests: int
    last_week_tests: int


class MetricsResponse(BaseModel):
    total_users: int
    total_feedbacks: int
    total_tests: int
    total_active_users: int
    line_chart_data: List[LineChartData]
    bar_chart_data: List[BarChartData]
