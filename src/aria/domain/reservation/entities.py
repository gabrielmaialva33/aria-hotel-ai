"""Reservation domain entities following DDD principles."""

from datetime import date, datetime, timedelta
from typing import Dict, List, Optional
from uuid import UUID
from dataclasses import dataclass
from enum import Enum
from decimal import Decimal

from aria.domain.shared.entity import Entity, AggregateRoot
from aria.domain.shared.value_objects import Money, DateRange, Email, Phone
from aria.domain.shared.events import DomainEvent
from aria.domain.guest.entities import Guest


class ReservationStatus(Enum):
    """Reservation status states."""
    QUOTE = "quote"  # Initial quote, not confirmed
    PENDING_PAYMENT = "pending_payment"  # Awaiting payment
    CONFIRMED = "confirmed"  # Paid and confirmed
    CHECKED_IN = "checked_in"  # Guest has checked in
    CHECKED_OUT = "checked_out"  # Guest has checked out
    CANCELLED = "cancelled"  # Cancelled by guest or hotel
    NO_SHOW = "no_show"  # Guest didn't show up


class RoomType(Enum):
    """Available room types."""
    TERREO = "terreo"
    SUPERIOR = "superior"
    SUITE = "suite"
    FAMILY = "family"


class MealPlan(Enum):
    """Meal plan options."""
    ROOM_ONLY = "room_only"
    BREAKFAST = "breakfast"
    HALF_BOARD = "half_board"  # Breakfast + lunch or dinner
    FULL_BOARD = "full_board"  # All meals


class PaymentMethod(Enum):
    """Payment methods."""
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    PIX = "pix"
    BANK_TRANSFER = "bank_transfer"
    CASH = "cash"
    INVOICE = "invoice"


# Domain Events
@dataclass
class ReservationCreated(DomainEvent):
    """Event raised when a reservation is created."""
    reservation_id: UUID
    guest_id: UUID
    check_in: date
    check_out: date
    room_type: str
    total_amount: float


@dataclass
class ReservationConfirmed(DomainEvent):
    """Event raised when a reservation is confirmed."""
    reservation_id: UUID
    confirmed_at: datetime
    payment_method: str


@dataclass
class ReservationCancelled(DomainEvent):
    """Event raised when a reservation is cancelled."""
    reservation_id: UUID
    cancelled_at: datetime
    reason: str
    cancellation_fee: Optional[float] = None


@dataclass
class GuestCheckedIn(DomainEvent):
    """Event raised when guest checks in."""
    reservation_id: UUID
    room_number: str
    checked_in_at: datetime


@dataclass
class GuestCheckedOut(DomainEvent):
    """Event raised when guest checks out."""
    reservation_id: UUID
    checked_out_at: datetime
    final_amount: float


@dataclass
class RoomRate:
    """Value object for room pricing."""
    
    room_type: RoomType
    meal_plan: MealPlan
    base_rate: Money
    adult_rate: Money
    child_rate: Optional[Money] = None
    extra_bed_rate: Optional[Money] = None
    
    def calculate_total(
        self,
        nights: int,
        adults: int,
        children: int = 0,
        extra_beds: int = 0
    ) -> Money:
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


@dataclass
class RoomAssignment:
    """Room assignment details."""
    
    room_number: str
    room_type: RoomType
    floor: int
    features: List[str] = None  # view, balcony, etc
    
    def __post_init__(self):
        if self.features is None:
            self.features = []


class Reservation(AggregateRoot):
    """Reservation aggregate root."""
    
    def __init__(
        self,
        id: Optional[UUID] = None,
        guest_id: UUID = None,
        booking_reference: Optional[str] = None,
        status: ReservationStatus = ReservationStatus.QUOTE,
        date_range: DateRange = None,
        room_type: RoomType = None,
        meal_plan: MealPlan = MealPlan.BREAKFAST,
        adults: int = 2,
        children: int = 0,
        children_ages: Optional[List[int]] = None,
        room_rate: Optional[RoomRate] = None,
        special_requests: Optional[str] = None,
        source: str = "direct",  # direct, ota, phone, etc
        channel_reference: Optional[str] = None,
        created_at: Optional[datetime] = None,
        confirmed_at: Optional[datetime] = None,
        cancelled_at: Optional[datetime] = None,
        cancellation_reason: Optional[str] = None
    ):
        super().__init__(id)
        self.guest_id = guest_id
        self.booking_reference = booking_reference or self._generate_reference()
        self.status = status
        self.date_range = date_range
        self.room_type = room_type
        self.meal_plan = meal_plan
        self.adults = adults
        self.children = children
        self.children_ages = children_ages or []
        self.room_rate = room_rate
        self.special_requests = special_requests
        self.source = source
        self.channel_reference = channel_reference
        self.created_at = created_at or datetime.now()
        self.confirmed_at = confirmed_at
        self.cancelled_at = cancelled_at
        self.cancellation_reason = cancellation_reason
        
        # Additional properties
        self.room_assignments: List[RoomAssignment] = []
        self.payments: List["Payment"] = []
        self.extras: List["ReservationExtra"] = []
        self.notes: List["ReservationNote"] = []
        
        # Calculate initial total
        self._total_amount = self._calculate_total()
        
        # Raise creation event if new
        if not created_at:
            self.raise_event(ReservationCreated(
                reservation_id=self.id,
                guest_id=self.guest_id,
                check_in=self.date_range.start_date,
                check_out=self.date_range.end_date,
                room_type=self.room_type.value,
                total_amount=float(self._total_amount.amount)
            ))
    
    def _generate_reference(self) -> str:
        """Generate booking reference."""
        import random
        import string
        
        # Format: RES-YYYYMMDD-XXXX
        date_part = datetime.now().strftime("%Y%m%d")
        random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        return f"RES-{date_part}-{random_part}"
    
    def _calculate_total(self) -> Money:
        """Calculate total reservation amount."""
        if not self.room_rate or not self.date_range:
            return Money(Decimal("0"))
        
        # Base accommodation cost
        total = self.room_rate.calculate_total(
            nights=self.date_range.nights,
            adults=self.adults,
            children=self.children
        )
        
        # Add extras
        for extra in self.extras:
            total += extra.total_price
        
        return total
    
    @property
    def total_amount(self) -> Money:
        """Get total reservation amount."""
        return self._total_amount
    
    @property
    def balance_due(self) -> Money:
        """Calculate balance due."""
        total_paid = Money(Decimal("0"))
        for payment in self.payments:
            if payment.status == PaymentStatus.COMPLETED:
                total_paid += payment.amount
        
        return self.total_amount - total_paid
    
    @property
    def is_fully_paid(self) -> bool:
        """Check if reservation is fully paid."""
        return self.balance_due.is_zero() or self.balance_due.is_negative()
    
    @property
    def check_in_date(self) -> date:
        """Get check-in date."""
        return self.date_range.start_date
    
    @property
    def check_out_date(self) -> date:
        """Get check-out date."""
        return self.date_range.end_date
    
    @property
    def nights(self) -> int:
        """Get number of nights."""
        return self.date_range.nights
    
    @property
    def total_guests(self) -> int:
        """Get total number of guests."""
        return self.adults + self.children
    
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
        ] and self.check_in_date > date.today()
    
    def confirm(self, payment_method: PaymentMethod):
        """Confirm the reservation."""
        if self.status != ReservationStatus.PENDING_PAYMENT:
            raise ValueError(f"Cannot confirm reservation in status {self.status}")
        
        if not self.is_fully_paid:
            raise ValueError("Cannot confirm reservation without full payment")
        
        self.status = ReservationStatus.CONFIRMED
        self.confirmed_at = datetime.now()
        
        self.raise_event(ReservationConfirmed(
            reservation_id=self.id,
            confirmed_at=self.confirmed_at,
            payment_method=payment_method.value
        ))
    
    def cancel(self, reason: str, cancellation_fee: Optional[Money] = None):
        """Cancel the reservation."""
        if not self.can_cancel():
            raise ValueError(f"Cannot cancel reservation in status {self.status}")
        
        self.status = ReservationStatus.CANCELLED
        self.cancelled_at = datetime.now()
        self.cancellation_reason = reason
        
        self.raise_event(ReservationCancelled(
            reservation_id=self.id,
            cancelled_at=self.cancelled_at,
            reason=reason,
            cancellation_fee=float(cancellation_fee.amount) if cancellation_fee else None
        ))
    
    def check_in(self, room_number: str):
        """Check in the guest."""
        if self.status != ReservationStatus.CONFIRMED:
            raise ValueError(f"Cannot check in reservation in status {self.status}")
        
        if self.check_in_date > date.today():
            raise ValueError("Cannot check in before check-in date")
        
        # Find room assignment or create new one
        assignment = next(
            (a for a in self.room_assignments if a.room_number == room_number),
            None
        )
        
        if not assignment:
            assignment = RoomAssignment(
                room_number=room_number,
                room_type=self.room_type,
                floor=int(room_number[0])  # Assuming first digit is floor
            )
            self.room_assignments.append(assignment)
        
        self.status = ReservationStatus.CHECKED_IN
        
        self.raise_event(GuestCheckedIn(
            reservation_id=self.id,
            room_number=room_number,
            checked_in_at=datetime.now()
        ))
    
    def check_out(self):
        """Check out the guest."""
        if self.status != ReservationStatus.CHECKED_IN:
            raise ValueError(f"Cannot check out reservation in status {self.status}")
        
        # Calculate final amount (including any additional charges)
        final_amount = self._calculate_total()
        
        self.status = ReservationStatus.CHECKED_OUT
        
        self.raise_event(GuestCheckedOut(
            reservation_id=self.id,
            checked_out_at=datetime.now(),
            final_amount=float(final_amount.amount)
        ))
    
    def add_extra(self, extra: "ReservationExtra"):
        """Add an extra service/product to the reservation."""
        self.extras.append(extra)
        self._total_amount = self._calculate_total()
    
    def add_payment(self, payment: "Payment"):
        """Add a payment to the reservation."""
        self.payments.append(payment)
    
    def add_note(self, note: "ReservationNote"):
        """Add a note to the reservation."""
        self.notes.append(note)
    
    def assign_room(self, room_assignment: RoomAssignment):
        """Assign a room to the reservation."""
        # Remove any existing assignment for the same room
        self.room_assignments = [
            a for a in self.room_assignments 
            if a.room_number != room_assignment.room_number
        ]
        self.room_assignments.append(room_assignment)
    
    def calculate_cancellation_fee(self) -> Money:
        """Calculate cancellation fee based on policy."""
        days_until_checkin = (self.check_in_date - date.today()).days
        
        if days_until_checkin >= 7:
            # Free cancellation
            return Money(Decimal("0"))
        elif days_until_checkin >= 3:
            # 50% fee
            return self.total_amount * 0.5
        else:
            # 100% fee
            return self.total_amount
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "id": str(self.id),
            "guest_id": str(self.guest_id),
            "booking_reference": self.booking_reference,
            "status": self.status.value,
            "check_in": self.check_in_date.isoformat(),
            "check_out": self.check_out_date.isoformat(),
            "nights": self.nights,
            "room_type": self.room_type.value,
            "meal_plan": self.meal_plan.value,
            "adults": self.adults,
            "children": self.children,
            "children_ages": self.children_ages,
            "total_amount": str(self.total_amount),
            "balance_due": str(self.balance_due),
            "is_fully_paid": self.is_fully_paid,
            "special_requests": self.special_requests,
            "source": self.source,
            "created_at": self.created_at.isoformat(),
            "confirmed_at": self.confirmed_at.isoformat() if self.confirmed_at else None,
            "room_assignments": [
                {
                    "room_number": a.room_number,
                    "room_type": a.room_type.value,
                    "floor": a.floor,
                    "features": a.features
                }
                for a in self.room_assignments
            ]
        }


class PaymentStatus(Enum):
    """Payment status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    PARTIALLY_REFUNDED = "partially_refunded"


@dataclass
class Payment(Entity):
    """Payment for a reservation."""
    
    reservation_id: UUID
    amount: Money
    method: PaymentMethod
    status: PaymentStatus = PaymentStatus.PENDING
    transaction_id: Optional[str] = None
    processed_at: Optional[datetime] = None
    metadata: Dict = None
    
    def __post_init__(self):
        super().__init__()
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ReservationExtra(Entity):
    """Extra service or product added to reservation."""
    
    reservation_id: UUID
    type: str  # spa, minibar, laundry, etc
    description: str
    quantity: int
    unit_price: Money
    date: date
    
    def __post_init__(self):
        super().__init__()
    
    @property
    def total_price(self) -> Money:
        """Calculate total price."""
        return self.unit_price * self.quantity


@dataclass
class ReservationNote(Entity):
    """Note about a reservation."""
    
    reservation_id: UUID
    author_id: UUID
    content: str
    category: str = "general"  # general, housekeeping, front_desk, etc
    is_internal: bool = True
    created_at: datetime = None
    
    def __post_init__(self):
        super().__init__()
        if self.created_at is None:
            self.created_at = datetime.now()
