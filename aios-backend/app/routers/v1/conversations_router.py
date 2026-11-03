from fastapi import APIRouter, Depends, status

from app.dependencies.auth_dependencies import get_current_principal
from app.dependencies.service_dependencies import get_conversation_service
from app.schemas.conversation import (
    ConversationRead,
    ConversationStartRequest,
    MessageCreateRequest,
    MessageRead,
)
from app.security.principal import Principal
from app.services.conversation_service import ConversationService

router = APIRouter(prefix="/conversations", tags=["Conversations"])


@router.post("", response_model=ConversationRead, status_code=status.HTTP_201_CREATED)
async def start_conversation(
    payload: ConversationStartRequest,
    service: ConversationService = Depends(get_conversation_service),
    principal: Principal = Depends(get_current_principal),
):
    return await service.start(payload.workspace_id, principal.id, payload.agent_id, payload.title)


@router.post("/{conversation_id}/messages", response_model=MessageRead, status_code=status.HTTP_201_CREATED)
async def add_message(
    conversation_id: str,
    payload: MessageCreateRequest,
    service: ConversationService = Depends(get_conversation_service),
):
    return await service.add_message(conversation_id, payload.role, payload.content)


@router.get("/{conversation_id}/messages", response_model=list[MessageRead])
async def get_history(conversation_id: str, service: ConversationService = Depends(get_conversation_service)):
    return await service.get_history(conversation_id)
