from app.exceptions.formatters import format_http_exception
from app.models.user import User


def validate_authentication(current_user: User):
    if not current_user or not current_user.id:
        raise format_http_exception(
            status_code=401,
            message="Authentication required.",
            details="The user is not authenticated or the authentication token is invalid.",
        )
