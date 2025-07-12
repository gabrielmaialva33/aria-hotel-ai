"""Conversation and message models for ARIA Hotel AI."""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class MessageRole(str, Enum):
    """Message sender role."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class MessageType(str, Enum):
    """Type of message content."""
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    DOCUMENT = "document"
    LOCATION = "location"


class ConversationStatus(str, Enum):
    """Conversation status."""
    ACTIVE = "active"
    WAITING = "waiting"  # Waiting for user response
    RESOLVED = "resolved"
    ABANDONED = "abandoned"


class ConversationChannel(str, Enum):
    """Communication channel."""
    WHATSAPP = "whatsapp"
    WEB_CHAT = "web_chat"
    VOICE = "voice"
    EMAIL = "email"
    SMS = "sms"


class Message(BaseModel):
    """Message in a conversation."""
    id: UUID = Field(default_factory=uuid4)
    conversation_id: UUID
    role: MessageRole
    content: str
    message_type: MessageType = MessageType.TEXT
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)

    # For media messages
    media_url: Optional[str] = None
    media_mime_type: Optional[str] = None

    # For AI messages
    confidence_score: Optional[float] = None
    intent: Optional[str] = None
    entities: Dict[str, Any] = Field(default_factory=dict)


class Conversation(BaseModel):
    """Conversation/chat session model."""
    id: UUID = Field(default_factory=uuid4)
    guest_id: Optional[UUID] = None
    channel: ConversationChannel
    status: ConversationStatus = ConversationStatus.ACTIVE
    language: str = "pt"

    # Contact info for non-registered guests
    phone_number: Optional[str] = None
    email: Optional[str] = None
    name: Optional[str] = None

    # Conversation context
    context: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    last_message_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None

    # Messages
    messages: List[Message] = Field(default_factory=list)

    # Analytics
    message_count: int = 0
    ai_message_count: int = 0
    user_message_count: int = 0

    def add_message(self, message: Message) -> None:
        """Add a message to the conversation."""
        self.messages.append(message)
        self.last_message_at = message.created_at
        self.updated_at = datetime.now()
        self.message_count += 1

        if message.role == MessageRole.ASSISTANT:
            self.ai_message_count += 1
        elif message.role == MessageRole.USER:
            self.user_message_count += 1

    def get_context_summary(self) -> str:
        """Get a summary of the conversation context."""
        # This could be enhanced with AI summarization
        recent_messages = self.messages[-10:]  # Last 10 messages
        return "\n".join([
            f"{msg.role.value}: {msg.content[:100]}..."
            for msg in recent_messages
        ])

    def mark_resolved(self) -> None:
        """Mark conversation as resolved."""
        self.status = ConversationStatus.RESOLVED
        self.resolved_at = datetime.now()
        self.updated_at = datetime.now()


class ConversationSummary(BaseModel):
    """Summary of a conversation for listing/search."""
    id: UUID
    guest_name: Optional[str]
    channel: ConversationChannel
    status: ConversationStatus
    last_message: Optional[str]
    last_message_at: Optional[datetime]
    message_count: int
    created_at: datetime
    tags: List[str]
