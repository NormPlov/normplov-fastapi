import logging

from fastapi import APIRouter, Depends, status, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_db
from app.exceptions.formatters import format_http_exception
from app.services.message import send_message_service, reply_to_message_service, fetch_chats_with_user, \
    unsend_message_service, edit_message_service, fetch_users_with_last_message
from app.schemas.message import SendMessageRequest, ReplyToMessageRequest, EditMessageRequest
from app.schemas.payload import BaseResponse
from app.dependencies import get_current_user_data
from datetime import datetime

message_router = APIRouter()

logger = logging.getLogger(__name__)


@message_router.get(
    "/chats/users",
    summary="Get users with last messages",
    response_model=BaseResponse,
    status_code=200,
)
async def get_users_with_last_message_route(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user_data),
):
    try:
        users_with_last_message = await fetch_users_with_last_message(
            current_user_uuid=current_user.uuid,
            db=db,
        )

        return BaseResponse(
            date=datetime.utcnow().strftime("%d-%B-%Y"),
            status=200,
            message="Users with last messages retrieved successfully!",
            payload=users_with_last_message,
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error in get_users_with_last_message_route: {str(e)}")
        raise format_http_exception(
            status_code=400,
            message="Failed to fetch users with last messages.",
            details=str(e),
        )


@message_router.put(
    "/edit",
    summary="Edit a sent message",
    response_model=BaseResponse,
    status_code=status.HTTP_200_OK,
)
async def edit_message_route(
    request: EditMessageRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user_data),
):
    try:
        updated_message = await edit_message_service(
            message_uuid=request.message_uuid,
            new_content=request.new_content,
            user_uuid=current_user.uuid,
            db=db,
        )

        return BaseResponse(
            date=datetime.utcnow().strftime("%d-%B-%Y"),
            status=200,
            message="Message edited successfully! ✅",
            payload=updated_message,
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error in edit_message_route: {str(e)}")
        raise format_http_exception(
            status_code=400,
            message="Failed to edit the message.",
            details=str(e),
        )


@message_router.delete(
    "/unsend",
    summary="Unsend (delete) a sent message",
    response_model=BaseResponse,
    status_code=status.HTTP_200_OK,
)
async def unsend_message_route(
    message_uuid: str = Query(..., description="UUID of the message to unsend"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user_data),
):
    try:
        deleted_message = await unsend_message_service(
            message_uuid=message_uuid,
            user_uuid=current_user.uuid,
            db=db,
        )

        return BaseResponse(
            date=datetime.utcnow().strftime("%d-%B-%Y"),
            status=200,
            message="Message unsent successfully! ✅",
            payload=deleted_message,
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error in unsend_message_route: {str(e)}")
        raise format_http_exception(
            status_code=400,
            message="Failed to unsend the message.",
            details=str(e),
        )


@message_router.get(
    "/chat",
    summary="Get all chats between the current user and another user",
    response_model=BaseResponse,
)
async def get_chat_with_user(
    other_user_uuid: str = Query(..., description="UUID of the other user"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user_data),
):
    try:
        chats = await fetch_chats_with_user(
            current_user_uuid=current_user.uuid,
            other_user_uuid=other_user_uuid,
            db=db,
        )

        return BaseResponse(
            date=datetime.utcnow().strftime("%d-%B-%Y"),
            status=200,
            message="Chats retrieved successfully! ✅",
            payload=chats,
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error in get_chat_with_user: {str(e)}")
        raise format_http_exception(
            status_code=400,
            message="Failed to fetch chats.",
            details=str(e),
        )


@message_router.post(
    "/reply",
    summary="Reply to a message",
    response_model=BaseResponse,
    status_code=status.HTTP_201_CREATED,
)
async def reply_to_message_route(
    request: ReplyToMessageRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user_data),
):
    try:
        reply_message = await reply_to_message_service(
            reply_to_uuid=request.reply_to_uuid,
            receiver_uuid=current_user.uuid,
            content=request.content,
            db=db,
        )

        return BaseResponse(
            date=datetime.utcnow().strftime("%d-%B-%Y"),
            status=status.HTTP_201_CREATED,
            message="Reply sent successfully! ✅",
            payload=reply_message,
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error in reply_to_message_route: {str(e)}")
        raise format_http_exception(
            status_code=400,
            message="Failed to send the reply.",
            details=str(e),
        )


@message_router.post(
    "/send",
    summary="Send a message to a mentor",
    response_model=BaseResponse,
    status_code=status.HTTP_201_CREATED,
)
async def send_message_route(
    request: SendMessageRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user_data),
):
    try:
        message = await send_message_service(
            sender_uuid=current_user.uuid,
            receiver_uuid=request.receiver_uuid,
            content=request.content,
            db=db,
        )

        return BaseResponse(
            date=datetime.utcnow().strftime("%d-%B-%Y"),
            status=status.HTTP_201_CREATED,
            message="Message sent successfully! ✅",
            payload=message,
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error in send_message_route: {str(e)}")
        raise format_http_exception(
            status_code=400,
            message="Failed to send the message.",
            details=str(e),
        )
