"""Guest models for ARIA Hotel AI."""

from datetime import date, datetime
from enum import Enum
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, EmailStr


class GuestStatus(str, Enum):
    """Guest status in the system."""
    PROSPECT = "prospect"
    ACTIVE = "active"
    INACTIVE = "inactive"
    VIP = "vip"
    BLOCKED = "blocked"


class LoyaltyTier(str, Enum):
    """Guest loyalty program tiers."""
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"


class GuestPreferences(BaseModel):
    """Guest preferences model."""
    room_type: Optional[str] = None
    floor: Optional[str] = None
    bed_type: Optional[str] = None
    meal_plan: Optional[str] = None
    dietary_restrictions: List[str] = Field(default_factory=list)
    special_requests: List[str] = Field(default_factory=list)
    amenities: List[str] = Field(default_factory=list)


class LoyaltyProgram(BaseModel):
    """Loyalty program information."""
    tier: LoyaltyTier = LoyaltyTier.BRONZE
    points: int = 0
    member_since: date
    nights_stayed: int = 0
    total_spent: float = 0.0


class Guest(BaseModel):
    """Guest model."""
    id: UUID = Field(default_factory=uuid4)
    name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    document: Optional[str] = None
    birthdate: Optional[date] = None
    nationality: Optional[str] = None
    language: str = "pt"
    preferences: GuestPreferences = Field(default_factory=GuestPreferences)
    loyalty_program: Optional[LoyaltyProgram] = None
    status: GuestStatus = GuestStatus.PROSPECT
    tags: List[str] = Field(default_factory=list)
    metadata: Dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

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


class GuestCreate(BaseModel):
    """Model for creating a guest."""
    name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    document: Optional[str] = None
    birthdate: Optional[date] = None
    nationality: Optional[str] = None
    language: str = "pt"


class GuestUpdate(BaseModel):
    """Model for updating a guest."""
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    document: Optional[str] = None
    birthdate: Optional[date] = None
    nationality: Optional[str] = None
    language: Optional[str] = None
    preferences: Optional[GuestPreferences] = None
    tags: Optional[List[str]] = None


class GuestNote(BaseModel):
    """Note about a guest."""
    id: UUID = Field(default_factory=uuid4)
    guest_id: UUID
    author_id: Optional[UUID] = None
    content: str
    category: str = "general"
    is_private: bool = False
    created_at: datetime = Field(default_factory=datetime.now)


class GuestInteraction(BaseModel):
    """Record of interaction with guest."""
    id: UUID = Field(default_factory=uuid4)
    guest_id: UUID
    channel: str  # whatsapp, email, phone, in_person
    interaction_type: str  # inquiry, complaint, feedback, etc
    summary: str
    sentiment: Optional[str] = None
    handled_by: Optional[str] = None  # ai or staff member id
    metadata: Dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
