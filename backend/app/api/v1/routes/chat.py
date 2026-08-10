from fastapi import APIRouter, Depends

from app.api.v1.deps import get_chat_service, get_current_user
from app.api.v1.schemas.chat import ChatRequest, ChatResponse, MessageResponse
from app.api.v1.schemas.conversation import ConversationResponse
from app.domain.entities.user import User
from app.services.rag.chat_service import ChatService

router = APIRouter(tags=["chat"])


@router.post("/subjects/{subject_id}/chat", response_model=ChatResponse)
async def send_chat_message(
    subject_id: str,
    body: ChatRequest,
    current_user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
) -> ChatResponse:
    result = await service.send_message(
        user_id=current_user.id,
        subject_id=subject_id,
        conversation_id=body.conversation_id,
        question=body.question,
        document_id=body.document_id,
    )
    return ChatResponse(
        conversation_id=result.conversation.id,
        user_message=MessageResponse.from_entity(result.user_message),
        assistant_message=MessageResponse.from_entity(result.assistant_message),
    )


@router.get("/subjects/{subject_id}/conversations", response_model=list[ConversationResponse])
async def list_conversations(
    subject_id: str,
    current_user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
) -> list[ConversationResponse]:
    conversations = await service.list_conversations(user_id=current_user.id, subject_id=subject_id)
    return [ConversationResponse.from_entity(c) for c in conversations]


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageResponse])
async def list_messages(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
) -> list[MessageResponse]:
    messages = await service.list_messages(user_id=current_user.id, conversation_id=conversation_id)
    return [MessageResponse.from_entity(m) for m in messages]
