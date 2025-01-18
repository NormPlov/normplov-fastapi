from pydantic import BaseModel
from uuid import UUID


class EditMessageRequest(BaseModel):
    message_uuid: str
    new_content: str


class ReplyToMessageRequest(BaseModel):
    reply_to_uuid: str
    content: str


class SendMessageRequest(BaseModel):
    receiver_uuid: UUID
    content: str
