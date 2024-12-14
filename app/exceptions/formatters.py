from fastapi import HTTPException


def format_http_exception(status_code: int, message: str, details: any = None) -> HTTPException:

    return HTTPException(
        status_code=status_code,
        detail={
            "error": True,
            "message": message,
            "details": details,
        },
    )
