from datetime import datetime


def format_date(date: datetime) -> str:
    if date:
        return date.strftime("%d-%B-%Y")
    return None
