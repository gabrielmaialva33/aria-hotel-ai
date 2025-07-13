"""Data models for Ana agent."""

from datetime import date
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class RoomType(str, Enum):
    """Available room types."""

    TERREO = "terreo"
    SUPERIOR = "superior"


class MealPlan(str, Enum):
    """Available meal plans."""

    CAFE_DA_MANHA = "cafe_da_manha"
    MEIA_PENSAO = "meia_pensao"
    PENSAO_COMPLETA = "pensao_completa"


class ReservationRequest(BaseModel):
    """Model for reservation requests."""

    check_in: date
    check_out: date
    adults: int = Field(ge=1, le=4)
    children: List[int] = Field(default_factory=list, description="Ages of children")
    room_type: Optional[RoomType] = None
    meal_plan: Optional[MealPlan] = None
    is_holiday: bool = False
    promo_code: Optional[str] = None

    @field_validator("children")
    @classmethod
    def validate_children(cls, v: List[int]) -> List[int]:
        """Validate children ages."""
        for age in v:
            if age < 0 or age > 17:
                raise ValueError(f"Invalid child age: {age}")
        return v

    @property
    def nights(self) -> int:
        """Calculate number of nights."""
        return (self.check_out - self.check_in).days

    @property
    def total_guests(self) -> int:
        """Total number of guests."""
        return self.adults + len(self.children)

    def requires_reception(self) -> bool:
        """Check if reservation requires reception handling."""
        # More than 4 people needs multiple rooms
        if self.total_guests > 4:
            return True
        # Children over 5 need extra beds
        if any(age > 5 for age in self.children):
            return True
        # Holiday packages or meal plans need reception
        if self.is_holiday or self.meal_plan in [MealPlan.MEIA_PENSAO, MealPlan.PENSAO_COMPLETA]:
            return True
        return False


class PricingBreakdown(BaseModel):
    """Breakdown of pricing components."""

    base_rate: float = Field(description="Base room rate")
    children_rate: float = Field(default=0.0, description="Additional rate for children")
    meal_supplement: float = Field(default=0.0, description="Meal plan supplement")
    discount_amount: float = Field(default=0.0, description="Discount amount")
    discount_percentage: float = Field(default=0.0, description="Discount percentage")


class Pricing(BaseModel):
    """Pricing information for a reservation."""

    room_type: RoomType
    meal_plan: MealPlan
    adults: int
    children: List[int]
    nights: int
    total: float = Field(ge=0)
    total_per_night: float = Field(ge=0)
    breakdown: PricingBreakdown
    currency: str = "BRL"

    def format_price(self) -> str:
        """Format price in Brazilian currency."""
        return f"R$ {self.total:,.2f}"


class ConversationContext(BaseModel):
    """Context for ongoing conversation."""

    guest_phone: str
    guest_name: Optional[str] = None
    current_request: Optional[ReservationRequest] = None
    state: str = "initial"  # initial, greeting_sent, collecting_info, presenting_options, etc.
    history: List[Dict[str, str]] = Field(default_factory=list)
    preferences: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)  # For storing reservation data, etc
    language: str = "pt_BR"

    def add_message(self, role: str, content: str):
        """Add message to conversation history."""
        self.history.append({
            "role": role,
            "content": content,
            "timestamp": date.today().isoformat()
        })


class AnaResponse(BaseModel):
    """Response from Ana agent."""

    text: str
    media_urls: List[str] = Field(default_factory=list)
    quick_replies: List[str] = Field(default_factory=list)
    needs_human: bool = False
    action: Optional[str] = None  # generate_link, transfer_reception, etc.
    metadata: Dict[str, Any] = Field(default_factory=dict)
