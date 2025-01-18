import uuid
import logging
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy import or_
from app.models.user import User
from app.models.message import Message
from app.exceptions.formatters import format_http_exception


logger = logging.getLogger(__name__)


async def fetch_users_with_last_message(
    current_user_uuid: str,
    db: AsyncSession,
):
    try:
        stmt = (
            select(
                User.uuid.label("user_uuid"),
                User.username.label("username"),
                User.avatar.label("avatar"),
                Message.content.label("last_message"),
                Message.created_at.label("created_at"),
            )
            .join(Message, or_(Message.sender_id == User.id, Message.receiver_id == User.id))
            .where(
                or_(
                    Message.sender.has(uuid=current_user_uuid),
                    Message.receiver.has(uuid=current_user_uuid),
                ),
                User.uuid != current_user_uuid,
                Message.is_deleted == False,
            )
            .distinct(User.uuid)
            .order_by(User.uuid, Message.created_at.desc())
        )

        result = await db.execute(stmt)
        users_with_messages = result.fetchall()

        return [
            {
                "user_uuid": row.user_uuid,
                "username": row.username,
                "avatar": row.avatar,
                "last_message": row.last_message,
                "created_at": row.created_at,
            }
            for row in users_with_messages
        ]
    except Exception as e:
        raise format_http_exception(
            status_code=500,
            message="💥 Failed to fetch users with last messages.",
            details=str(e),
        )


async def unsend_message_service(message_uuid: str, db: AsyncSession, user_uuid: str) -> dict:
    try:
        # Fetch the message
        result = await db.execute(
            select(Message)
            .options(joinedload(Message.sender))
            .where(Message.uuid == message_uuid)
        )
        message = result.scalars().first()

        if not message:
            raise format_http_exception(
                status_code=404,
                message="Message not found.",
                details={"message_uuid": message_uuid},
            )

        if message.sender.uuid != user_uuid:
            raise format_http_exception(
                status_code=403,
                message="You do not have permission to unsend this message.",
            )

        # Mark as deleted
        message.is_deleted = True
        await db.commit()
        await db.refresh(message)

        return {"status": "success", "message": "Message successfully unsent."}

    except Exception as e:
        await db.rollback()
        raise format_http_exception(
            status_code=500,
            message="Failed to unsend the message.",
            details=str(e),
        )


async def edit_message_service(
    message_uuid: str,
    new_content: str,
    user_uuid: str,
    db: AsyncSession,
) -> dict:
    try:
        # Fetch the message to validate ownership
        stmt = select(Message).where(Message.uuid == message_uuid, Message.is_deleted == False)
        result = await db.execute(stmt)
        message = result.scalars().first()

        if not message:
            raise format_http_exception(
                status_code=404,
                message="Message not found.",
                details={"message_uuid": message_uuid},
            )

        # Ensure the user is the sender of the message
        if message.sender.uuid != user_uuid:
            raise format_http_exception(
                status_code=403,
                message="You are not allowed to edit this message.",
                details={"message_uuid": message_uuid},
            )

        # Update the message content
        message.content = new_content
        message.updated_at = datetime.utcnow()

        await db.commit()
        await db.refresh(message)

        return {
            "uuid": message.uuid,
            "content": message.content,
            "updated_at": message.updated_at,
        }

    except Exception as e:
        await db.rollback()
        raise format_http_exception(
            status_code=500,
            message="Failed to edit the message.",
            details=str(e),
        )


async def fetch_chats_with_user(
    current_user_uuid: str,
    other_user_uuid: str,
    db: AsyncSession,
):
    try:
        # Query messages between the two users
        stmt = (
            select(Message)
            .options(
                joinedload(Message.sender),
                joinedload(Message.receiver),
            )
            .where(
                or_(
                    (Message.sender.has(uuid=current_user_uuid) & Message.receiver.has(uuid=other_user_uuid)),
                    (Message.sender.has(uuid=other_user_uuid) & Message.receiver.has(uuid=current_user_uuid)),
                ),
                Message.is_deleted == False
            )
            .order_by(Message.created_at.asc())
        )

        result = await db.execute(stmt)
        messages = result.scalars().all()

        return [
            {
                "uuid": message.uuid,
                "sender_uuid": message.sender.uuid,
                "receiver_uuid": message.receiver.uuid,
                "content": message.content,
                "is_read": message.is_read,
                "created_at": message.created_at,
                "updated_at": message.updated_at,
            }
            for message in messages
        ]
    except Exception as e:
        raise format_http_exception(
            status_code=500,
            message="💥 Failed to fetch chats between users.",
            details=str(e),
        )


async def reply_to_message_service(
    reply_to_uuid: str,
    receiver_uuid: str,
    content: str,
    db: AsyncSession,
) -> dict:
    try:
        # Validate the original message
        original_message_query = (
            select(Message)
            .options(selectinload(Message.sender))
            .where(Message.uuid == reply_to_uuid)
        )
        original_message_result = await db.execute(original_message_query)
        original_message = original_message_result.scalars().first()

        if not original_message:
            raise format_http_exception(
                status_code=404,
                message="❌ The message you're replying to does not exist.",
                details={"reply_to_uuid": reply_to_uuid},
            )

        # Validate the receiver exists
        receiver_query = select(User).where(User.uuid == receiver_uuid, User.is_active == True, User.is_deleted == False)
        receiver_result = await db.execute(receiver_query)
        receiver = receiver_result.scalars().first()

        if not receiver:
            raise format_http_exception(
                status_code=400,
                message="❌ Receiver does not exist or is inactive.",
                details={"receiver_uuid": receiver_uuid},
            )

        # Create the reply message
        reply_message = Message(
            uuid=str(uuid.uuid4()),
            sender_id=receiver.id,
            receiver_id=original_message.sender_id,  # Reply to the original sender
            content=content,
            is_read=False,
        )

        db.add(reply_message)
        await db.commit()
        await db.refresh(reply_message)

        # Convert SQLAlchemy object to dictionary for response
        return {
            "uuid": reply_message.uuid,
            "sender_uuid": receiver.uuid,
            "receiver_uuid": original_message.sender.uuid,
            "content": reply_message.content,
            "is_read": reply_message.is_read,
            "created_at": reply_message.created_at,
            "updated_at": reply_message.updated_at,
        }

    except Exception as e:
        await db.rollback()
        raise format_http_exception(
            status_code=500,
            message="💥 Failed to send the reply message.",
            details=str(e),
        )


async def send_message_service(
    sender_uuid: str,
    receiver_uuid: str,
    content: str,
    db: AsyncSession,
) -> dict:
    try:
        # Validate sender exists and is active
        sender_query = select(User).where(
            User.uuid == sender_uuid, User.is_active == True, User.is_deleted == False
        )
        sender_result = await db.execute(sender_query)
        sender = sender_result.scalars().first()

        if not sender:
            raise format_http_exception(
                status_code=400,
                message="❌ Sender does not exist or is inactive.",
                details={"sender_uuid": sender_uuid},
            )

        # Validate receiver exists and is active
        receiver_query = select(User).where(
            User.uuid == str(receiver_uuid), User.is_active == True, User.is_deleted == False
        )
        receiver_result = await db.execute(receiver_query)
        receiver = receiver_result.scalars().first()

        if not receiver:
            raise format_http_exception(
                status_code=400,
                message="❌ Receiver does not exist or is inactive.",
                details={"receiver_uuid": receiver_uuid},
            )

        # Create the message
        new_message = Message(
            uuid=str(uuid.uuid4()),
            sender_id=sender.id,
            receiver_id=receiver.id,
            content=content,
            is_read=False,
        )

        db.add(new_message)
        await db.commit()
        await db.refresh(new_message)

        # Convert SQLAlchemy object to dictionary
        return {
            "uuid": new_message.uuid,
            "sender_uuid": sender.uuid,
            "receiver_uuid": receiver.uuid,
            "content": new_message.content,
            "is_read": new_message.is_read,
            "created_at": new_message.created_at,
            "updated_at": new_message.updated_at,
        }

    except Exception as e:
        await db.rollback()
        raise format_http_exception(
            status_code=500,
            message="💥 Failed to send the message.",
            details=str(e),
        )

