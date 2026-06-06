from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_conversation_store
from app.schemas.conversation import (
    Conversation,
    ConversationCreateRequest,
    ConversationListResponse,
    ConversationMessagesResponse,
)
from app.storage.base import ConversationStore

router = APIRouter(prefix="/v1/conversations", tags=["conversations"])


@router.post("", response_model=Conversation, status_code=201)
async def create_conversation(
    body: ConversationCreateRequest,
    store: ConversationStore = Depends(get_conversation_store),
) -> Conversation:
    conversation_id = body.conversation_id or f"conv-{uuid.uuid4().hex}"
    return await store.create_conversation(
        conversation_id=conversation_id,
        user_id=body.user_id,
        title=body.title,
    )


@router.get("", response_model=ConversationListResponse)
async def list_conversations(
    user_id: str | None = None,
    store: ConversationStore = Depends(get_conversation_store),
) -> ConversationListResponse:
    conversations = await store.list_conversations(user_id=user_id)
    return ConversationListResponse(conversations=conversations)


@router.get("/{conversation_id}", response_model=Conversation)
async def get_conversation(
    conversation_id: str,
    store: ConversationStore = Depends(get_conversation_store),
) -> Conversation:
    conversation = await store.get_conversation(conversation_id=conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return conversation


@router.get(
    "/{conversation_id}/messages",
    response_model=ConversationMessagesResponse,
)
async def get_conversation_messages(
    conversation_id: str,
    store: ConversationStore = Depends(get_conversation_store),
) -> ConversationMessagesResponse:
    conversation = await store.get_conversation(conversation_id=conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    messages = await store.get_messages(conversation_id=conversation_id)
    return ConversationMessagesResponse(
        conversation_id=conversation_id, messages=messages
    )


@router.delete("/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: str,
    store: ConversationStore = Depends(get_conversation_store),
) -> None:
    deleted = await store.delete_conversation(conversation_id=conversation_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found.")
