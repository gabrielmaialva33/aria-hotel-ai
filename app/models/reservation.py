"""Reservation models for ARIA Hotel AI."""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ReservationStatus(str, Enum):
    """Reservation status states."""
    QUOTE = "quote"
    PENDING_PAYMENT = "pending_payment"
    CONFIRMED = "confirmed"
    CHECKED_IN = "checked_in"
    CHECKED_OUT = "checked_out"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class RoomType(str, Enum):
    """Available room types."""
    TERREO = "terreo"
    SUPERIOR = "superior"
    SUITE = "suite"
    FAMILY = "family"


class MealPlan(str, Enum):
    """Meal plan options."""
    ROOM_ONLY = "room_only"
    BREAKFAST = "breakfast"
    HALF_BOARD = "half_board"
    FULL_BOARD = "full_board"


class PaymentMethod(str, Enum):
    """Payment methods."""
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    PIX = "pix"
    BANK_TRANSFER = "bank_transfer"
    CASH = "cash"
    INVOICE = "invoice"


class PaymentStatus(str, Enum):
    """Payment status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    PARTIALLY_REFUNDED = "partially_refunded"


class RoomRate(BaseModel):
    """Room pricing model."""
    room_type: RoomType
    meal_plan: MealPlan
    base_rate: Decimal
    adult_rate: Decimal
    child_rate: Optional[Decimal] = None
    extra_bed_rate: Optional[Decimal] = None

    def calculate_total(
            self,
            nights: int,
            adults: int,
            children: int = 0,
            extra_beds: int = 0
    ) -> Decimal:
        """Calculate total price for the stay."""
        # Base rate for the room
        total = self.base_rate * nights

        # Additional adults (usually first 2 are included)
        if adults > 2:
            total += self.adult_rate * (adults - 2) * nights

        # Children
        if children > 0 and self.child_rate:
            total += self.child_rate * children * nights

        # Extra beds
        if extra_beds > 0 and self.extra_bed_rate:
            total += self.extra_bed_rate * extra_beds * nights

        return total


class RoomAssignment(BaseModel):
    """Room assignment details."""
    room_number: str
    room_type: RoomType
    floor: int
    features: List[str] = Field(default_factory=list)


class Payment(BaseModel):
    """Payment for a reservation."""
    id: UUID = Field(default_factory=uuid4)
    reservation_id: UUID
    amount: Decimal
    method: PaymentMethod
    status: PaymentStatus = PaymentStatus.PENDING
    transaction_id: Optional[str] = None
    processed_at: Optional[datetime] = None
    metadata: Dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)


class ReservationExtra(BaseModel):
    """Extra service or product added to reservation."""
    id: UUID = Field(default_factory=uuid4)
    reservation_id: UUID
    service_type: str  # spa, minibar, laundry, etc
    description: str
    quantity: int
    unit_price: Decimal
    date: date
    created_at: datetime = Field(default_factory=datetime.now)

    @property
    def total_price(self) -> Decimal:
        """Calculate total price."""
        return self.unit_price * self.quantity


class ReservationNote(BaseModel):
    """Note about a reservation."""
    id: UUID = Field(default_factory=uuid4)
    reservation_id: UUID
    author_id: Optional[UUID] = None
    content: str
    category: str = "general"  # general, housekeeping, front_desk, etc
    is_internal: bool = True
    created_at: datetime = Field(default_factory=datetime.now)


class Reservation(BaseModel):
    """Reservation model."""
    id: UUID = Field(default_factory=uuid4)
    guest_id: UUID
    booking_reference: Optional[str] = None
    status: ReservationStatus = ReservationStatus.QUOTE
    check_in: date
    check_out: date
    room_type: RoomType
    meal_plan: MealPlan = MealPlan.BREAKFAST
    adults: int = 2
    children: int = 0
    children_ages: List[int] = Field(default_factory=list)
    room_rate: Optional[RoomRate] = None
    special_requests: Optional[str] = None
    source: str = "direct"  # direct, ota, phone, etc
    channel_reference: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    confirmed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    cancellation_reason: Optional[str] = None

    # Related data
    room_assignments: List[RoomAssignment] = Field(default_factory=list)
    payments: List[Payment] = Field(default_factory=list)
    extras: List[ReservationExtra] = Field(default_factory=list)
    notes: List[ReservationNote] = Field(default_factory=list)

    def model_post_init(self, __context):
        """Initialize booking reference after model creation."""
        if not self.booking_reference:
            self.booking_reference = self._generate_reference()

    def _generate_reference(self) -> str:
        """Generate booking reference."""
        import random
        import string

        # Format: RES-YYYYMMDD-XXXX
        date_part = datetime.now().strftime("%Y%m%d")
        random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        return f"RES-{date_part}-{random_part}"

    @property
    def nights(self) -> int:
        """Get number of nights."""
        return (self.check_out - self.check_in).days

    @property
    def total_guests(self) -> int:
        """Get total number of guests."""
        return self.adults + self.children

    @property
    def total_amount(self) -> Decimal:
        """Calculate total reservation amount."""
        if not self.room_rate:
            return Decimal("0")

        # Base accommodation cost
        total = self.room_rate.calculate_total(
            nights=self.nights,
            adults=self.adults,
            children=self.children
        )

        # Add extras
        for extra in self.extras:
            total += extra.total_price

        return total

    @property
    def balance_due(self) -> Decimal:
        """Calculate balance due."""
        total_paid = Decimal("0")
        for payment in self.payments:
            if payment.status == PaymentStatus.COMPLETED:
                total_paid += payment.amount

        return self.total_amount - total_paid

    @property
    def is_fully_paid(self) -> bool:
        """Check if reservation is fully paid."""
        return self.balance_due <= 0

    def can_cancel(self) -> bool:
        """Check if reservation can be cancelled."""
        return self.status in [
            ReservationStatus.QUOTE,
            ReservationStatus.PENDING_PAYMENT,
            ReservationStatus.CONFIRMED
        ]

    def can_modify(self) -> bool:
        """Check if reservation can be modified."""
        return self.status in [
            ReservationStatus.QUOTE,
            ReservationStatus.PENDING_PAYMENT,
            ReservationStatus.CONFIRMED
        ] and self.check_in > date.today()

    def calculate_cancellation_fee(self) -> Decimal:
        """Calculate cancellation fee based on policy."""
        days_until_checkin = (self.check_in - date.today()).days

        if days_until_checkin >= 7:
            # Free cancellation
            return Decimal("0")
        elif days_until_checkin >= 3:
            # 50% fee
            return self.total_amount * Decimal("0.5")
        else:
            # 100% fee
            return self.total_amount


class ReservationCreate(BaseModel):
    """Model for creating a reservation."""
    guest_id: UUID
    check_in: date
    check_out: date
    room_type: RoomType
    meal_plan: MealPlan = MealPlan.BREAKFAST
    adults: int = 2
    children: int = 0
    children_ages: List[int] = Field(default_factory=list)
    special_requests: Optional[str] = None
    source: str = "direct"


class ReservationUpdate(BaseModel):
    """Model for updating a reservation."""
    check_in: Optional[date] = None
    check_out: Optional[date] = None
    room_type: Optional[RoomType] = None
    meal_plan: Optional[MealPlan] = None
    adults: Optional[int] = None
    children: Optional[int] = None
    children_ages: Optional[List[int]] = None
    special_requests: Optional[str] = None
