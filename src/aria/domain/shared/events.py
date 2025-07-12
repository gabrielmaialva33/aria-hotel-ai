"""Domain events for event-driven architecture."""

from abc import ABC
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4


@dataclass
class DomainEvent(ABC):
    """Base class for all domain events."""
    
    event_id: UUID = field(default_factory=uuid4)
    aggregate_id: Optional[UUID] = None
    occurred_at: Optional[datetime] = None
    metadata: dict = field(default_factory=dict)
    
    @property
    def event_name(self) -> str:
        """Get event name from class name."""
        return self.__class__.__name__
