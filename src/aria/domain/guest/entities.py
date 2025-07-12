"""Guest domain entities following DDD principles."""

from datetime import date, datetime
from typing import Dict, List, Optional
from uuid import UUID, uuid4
from dataclasses import dataclass, field
from enum import Enum

from aria.domain.shared.value_objects import Email, Phone, Document
from aria.domain.shared.entity import Entity, AggregateRoot
from aria.domain.shared.events import DomainEvent


class GuestStatus(Enum):
    """Guest status in the system."""
    PROSPECT = "prospect"  # Showed interest but never booked
    ACTIVE = "active"  # Has active or future bookings
    INACTIVE = "inactive"  # No recent activity
    VIP = "vip"  # High-value guest
    BLOCKED = "blocked"  # Blocked from booking


class GuestPreferences:
    """Value object for guest preferences."""
    
    def __init__(
        self,
        room_type: Optional[str] = None,
        floor: Optional[str] = None,
        bed_type: Optional[str] = None,
        meal_plan: Optional[str] = None,
        dietary_restrictions: Optional[List[str]] = None,
        special_requests: Optional[List[str]] = None,
        amenities: Optional[List[str]] = None
    ):
        self.room_type = room_type
        self.floor = floor
        self.bed_type = bed_type
        self.meal_plan = meal_plan
        self.dietary_restrictions = dietary_restrictions or []
        self.special_requests = special_requests or []
        self.amenities = amenities or []
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "room_type": self.room_type,
            "floor": self.floor,
            "bed_type": self.bed_type,
            "meal_plan": self.meal_plan,
            "dietary_restrictions": self.dietary_restrictions,
            "special_requests": self.special_requests,
            "amenities": self.amenities
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "GuestPreferences":
        """Create from dictionary."""
        return cls(**data)


class LoyaltyTier(Enum):
    """Guest loyalty program tiers."""
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"


@dataclass
class LoyaltyProgram:
    """Value object for loyalty program information."""
    tier: LoyaltyTier
    points: int
    member_since: date
    nights_stayed: int
    total_spent: float
    
    def add_points(self, points: int):
        """Add loyalty points."""
        self.points += points
        self._check_tier_upgrade()
    
    def _check_tier_upgrade(self):
        """Check if guest qualifies for tier upgrade."""
        if self.points >= 10000 and self.tier != LoyaltyTier.PLATINUM:
            self.tier = LoyaltyTier.PLATINUM
        elif self.points >= 5000 and self.tier not in [LoyaltyTier.GOLD, LoyaltyTier.PLATINUM]:
            self.tier = LoyaltyTier.GOLD
        elif self.points >= 2000 and self.tier == LoyaltyTier.BRONZE:
            self.tier = LoyaltyTier.SILVER


# Domain Events
@dataclass
class GuestCreated(DomainEvent):
    """Event raised when a guest is created."""
    guest_id: UUID
    name: str
    email: Optional[str]
    phone: str


@dataclass
class GuestProfileUpdated(DomainEvent):
    """Event raised when guest profile is updated."""
    guest_id: UUID
    changes: Dict


@dataclass
class GuestPreferencesUpdated(DomainEvent):
    """Event raised when guest preferences are updated."""
    guest_id: UUID
    preferences: Dict


@dataclass
class GuestStatusChanged(DomainEvent):
    """Event raised when guest status changes."""
    guest_id: UUID
    old_status: GuestStatus
    new_status: GuestStatus
    reason: Optional[str]


@dataclass
class LoyaltyPointsEarned(DomainEvent):
    """Event raised when guest earns loyalty points."""
    guest_id: UUID
    points: int
    source: str
    new_total: int


class Guest(AggregateRoot):
    """Guest aggregate root."""
    
    def __init__(
        self,
        id: Optional[UUID] = None,
        name: str = None,
        email: Optional[Email] = None,
        phone: Optional[Phone] = None,
        document: Optional[Document] = None,
        birthdate: Optional[date] = None,
        nationality: Optional[str] = None,
        language: str = "pt",
        preferences: Optional[GuestPreferences] = None,
        loyalty_program: Optional[LoyaltyProgram] = None,
        status: GuestStatus = GuestStatus.PROSPECT,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None
    ):
        super().__init__(id)
        self.name = name
        self.email = email
        self.phone = phone
        self.document = document
        self.birthdate = birthdate
        self.nationality = nationality
        self.language = language
        self.preferences = preferences or GuestPreferences()
        self.loyalty_program = loyalty_program
        self.status = status
        self.tags = tags or []
        self.metadata = metadata or {}
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()
        
        # Raise creation event if new
        if not created_at:
            self.raise_event(GuestCreated(
                guest_id=self.id,
                name=self.name,
                email=str(self.email) if self.email else None,
                phone=str(self.phone) if self.phone else None
            ))
    
    def update_profile(
        self,
        name: Optional[str] = None,
        email: Optional[Email] = None,
        phone: Optional[Phone] = None,
        document: Optional[Document] = None,
        birthdate: Optional[date] = None,
        nationality: Optional[str] = None,
        language: Optional[str] = None
    ):
        """Update guest profile information."""
        changes = {}
        
        if name and name != self.name:
            changes["name"] = {"old": self.name, "new": name}
            self.name = name
        
        if email and email != self.email:
            changes["email"] = {"old": str(self.email), "new": str(email)}
            self.email = email
        
        if phone and phone != self.phone:
            changes["phone"] = {"old": str(self.phone), "new": str(phone)}
            self.phone = phone
        
        if document and document != self.document:
            self.document = document
            changes["document"] = {"updated": True}
        
        if birthdate and birthdate != self.birthdate:
            self.birthdate = birthdate
            changes["birthdate"] = {"updated": True}
        
        if nationality and nationality != self.nationality:
            self.nationality = nationality
            changes["nationality"] = {"old": self.nationality, "new": nationality}
        
        if language and language != self.language:
            self.language = language
            changes["language"] = {"old": self.language, "new": language}
        
        if changes:
            self.updated_at = datetime.now()
            self.raise_event(GuestProfileUpdated(
                guest_id=self.id,
                changes=changes
            ))
    
    def update_preferences(self, preferences: GuestPreferences):
        """Update guest preferences."""
        self.preferences = preferences
        self.updated_at = datetime.now()
        
        self.raise_event(GuestPreferencesUpdated(
            guest_id=self.id,
            preferences=preferences.to_dict()
        ))
    
    def change_status(self, new_status: GuestStatus, reason: Optional[str] = None):
        """Change guest status."""
        if new_status == self.status:
            return
        
        old_status = self.status
        self.status = new_status
        self.updated_at = datetime.now()
        
        self.raise_event(GuestStatusChanged(
            guest_id=self.id,
            old_status=old_status,
            new_status=new_status,
            reason=reason
        ))
    
    def join_loyalty_program(self):
        """Join the loyalty program."""
        if self.loyalty_program:
            return
        
        self.loyalty_program = LoyaltyProgram(
            tier=LoyaltyTier.BRONZE,
            points=0,
            member_since=date.today(),
            nights_stayed=0,
            total_spent=0.0
        )
        
        self.updated_at = datetime.now()
    
    def earn_loyalty_points(self, points: int, source: str):
        """Earn loyalty points."""
        if not self.loyalty_program:
            self.join_loyalty_program()
        
        self.loyalty_program.add_points(points)
        
        self.raise_event(LoyaltyPointsEarned(
            guest_id=self.id,
            points=points,
            source=source,
            new_total=self.loyalty_program.points
        ))
    
    def add_tag(self, tag: str):
        """Add a tag to the guest."""
        if tag not in self.tags:
            self.tags.append(tag)
            self.updated_at = datetime.now()
    
    def remove_tag(self, tag: str):
        """Remove a tag from the guest."""
        if tag in self.tags:
            self.tags.remove(tag)
            self.updated_at = datetime.now()
    
    def is_vip(self) -> bool:
        """Check if guest is VIP."""
        return (
            self.status == GuestStatus.VIP or
            (self.loyalty_program and self.loyalty_program.tier in [LoyaltyTier.GOLD, LoyaltyTier.PLATINUM])
        )
    
    def can_book(self) -> bool:
        """Check if guest can make bookings."""
        return self.status != GuestStatus.BLOCKED
    
    def get_age(self) -> Optional[int]:
        """Calculate guest age."""
        if not self.birthdate:
            return None
        
        today = date.today()
        age = today.year - self.birthdate.year
        
        # Adjust if birthday hasn't occurred this year
        if (today.month, today.day) < (self.birthdate.month, self.birthdate.day):
            age -= 1
        
        return age
    
    def is_birthday_month(self) -> bool:
        """Check if current month is guest's birthday month."""
        if not self.birthdate:
            return False
        
        return self.birthdate.month == date.today().month
    
    def get_preferred_communication_time(self) -> str:
        """Get preferred time for communications."""
        # Could be enhanced with ML to learn patterns
        return self.metadata.get("preferred_contact_time", "morning")
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "id": str(self.id),
            "name": self.name,
            "email": str(self.email) if self.email else None,
            "phone": str(self.phone) if self.phone else None,
            "document": self.document.to_dict() if self.document else None,
            "birthdate": self.birthdate.isoformat() if self.birthdate else None,
            "nationality": self.nationality,
            "language": self.language,
            "preferences": self.preferences.to_dict(),
            "loyalty_program": {
                "tier": self.loyalty_program.tier.value,
                "points": self.loyalty_program.points,
                "member_since": self.loyalty_program.member_since.isoformat(),
                "nights_stayed": self.loyalty_program.nights_stayed,
                "total_spent": self.loyalty_program.total_spent
            } if self.loyalty_program else None,
            "status": self.status.value,
            "tags": self.tags,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


class GuestNote(Entity):
    """Note about a guest (for staff use)."""
    
    def __init__(
        self,
        id: Optional[UUID] = None,
        guest_id: UUID = None,
        author_id: UUID = None,
        content: str = None,
        category: str = "general",
        is_private: bool = False,
        created_at: Optional[datetime] = None
    ):
        super().__init__(id)
        self.guest_id = guest_id
        self.author_id = author_id
        self.content = content
        self.category = category
        self.is_private = is_private
        self.created_at = created_at or datetime.now()


class GuestInteraction(Entity):
    """Record of interaction with guest."""
    
    def __init__(
        self,
        id: Optional[UUID] = None,
        guest_id: UUID = None,
        channel: str = None,  # whatsapp, email, phone, in_person
        type: str = None,  # inquiry, complaint, feedback, etc
        summary: str = None,
        sentiment: Optional[str] = None,
        handled_by: Optional[str] = None,  # ai or staff member id
        metadata: Optional[Dict] = None,
        created_at: Optional[datetime] = None
    ):
        super().__init__(id)
        self.guest_id = guest_id
        self.channel = channel
        self.type = type
        self.summary = summary
        self.sentiment = sentiment
        self.handled_by = handled_by
        self.metadata = metadata or {}
        self.created_at = created_at or datetime.now()
