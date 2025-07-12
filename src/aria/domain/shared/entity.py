"""Base classes for domain entities following DDD principles."""

from abc import ABC
from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4

from aria.domain.shared.events import DomainEvent


class Entity(ABC):
    """Base class for all domain entities."""
    
    def __init__(self, id: Optional[UUID] = None):
        """Initialize entity with unique identifier."""
        self.id = id or uuid4()
    
    def __eq__(self, other) -> bool:
        """Entities are equal if they have the same ID."""
        if not isinstance(other, Entity):
            return False
        return self.id == other.id
    
    def __hash__(self) -> int:
        """Hash based on ID."""
        return hash(self.id)


class AggregateRoot(Entity):
    """Base class for aggregate roots."""
    
    def __init__(self, id: Optional[UUID] = None):
        """Initialize aggregate root."""
        super().__init__(id)
        self._domain_events: List[DomainEvent] = []
        self._version = 0
    
    def raise_event(self, event: DomainEvent):
        """Raise a domain event."""
        event.aggregate_id = self.id
        event.occurred_at = datetime.now()
        self._domain_events.append(event)
    
    def clear_events(self):
        """Clear all pending domain events."""
        self._domain_events.clear()
    
    def get_events(self) -> List[DomainEvent]:
        """Get all pending domain events."""
        return self._domain_events.copy()
    
    def increment_version(self):
        """Increment aggregate version for optimistic locking."""
        self._version += 1
    
    @property
    def version(self) -> int:
        """Get current version."""
        return self._version
