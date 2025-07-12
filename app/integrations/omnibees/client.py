"""Omnibees integration client for hotel reservations."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional

import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class ReservationStatus(Enum):
    """Reservation status in Omnibees."""
    CONFIRMED = "confirmed"
    PENDING = "pending"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"
    CHECKED_IN = "checked_in"
    CHECKED_OUT = "checked_out"


class RoomStatus(Enum):
    """Room availability status."""
    AVAILABLE = "available"
    OCCUPIED = "occupied"
    BLOCKED = "blocked"
    MAINTENANCE = "maintenance"


@dataclass
class Room:
    """Room information from Omnibees."""
    id: str
    type: str
    name: str
    max_occupancy: int
    base_rate: Decimal
    amenities: List[str]
    images: List[str]
    status: RoomStatus


@dataclass
class Availability:
    """Room availability for a date range."""
    room_type: str
    available_count: int
    total_count: int
    dates: Dict[str, int]  # date -> available count
    min_rate: Decimal
    max_rate: Decimal


@dataclass
class Guest:
    """Guest information."""
    name: str
    email: Optional[str]
    phone: str
    document: str
    document_type: str = "cpf"
    birthdate: Optional[date] = None
    address: Optional[Dict] = None


@dataclass
class Reservation:
    """Complete reservation details."""
    id: str
    hotel_id: str
    status: ReservationStatus
    check_in: date
    check_out: date
    rooms: List[Dict]
    guests: List[Guest]
    total_amount: Decimal
    paid_amount: Decimal
    notes: Optional[str]
    created_at: datetime
    source: str = "whatsapp"


class OmnibeesClient:
    """Client for Omnibees Channel Manager integration."""

    def __init__(self):
        """Initialize Omnibees client."""
        self.base_url = settings.get("OMNIBEES_API_URL", "https://api.omnibees.com/v2")
        self.api_key = settings.get("OMNIBEES_API_KEY")
        self.hotel_id = settings.get("OMNIBEES_HOTEL_ID", "passarim-hotel")

        if not self.api_key:
            logger.warning("Omnibees API key not configured")

        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            timeout=30.0
        )

    async def check_availability(
            self,
            check_in: date,
            check_out: date,
            guests: int,
            room_type: Optional[str] = None
    ) -> List[Availability]:
        """
        Check room availability for date range.
        
        Args:
            check_in: Check-in date
            check_out: Check-out date
            guests: Number of guests
            room_type: Specific room type (optional)
            
        Returns:
            List of available room types with counts
        """
        try:
            # In production, this would call the real API
            # For now, return mock data

            if settings.app_env == "development":
                return self._mock_availability(check_in, check_out, guests, room_type)

            # Real API call
            response = await self.client.get(
                f"/hotels/{self.hotel_id}/availability",
                params={
                    "check_in": check_in.isoformat(),
                    "check_out": check_out.isoformat(),
                    "guests": guests,
                    "room_type": room_type
                }
            )

            response.raise_for_status()
            data = response.json()

            return [
                Availability(
                    room_type=item["room_type"],
                    available_count=item["available"],
                    total_count=item["total"],
                    dates=item["availability_by_date"],
                    min_rate=Decimal(str(item["min_rate"])),
                    max_rate=Decimal(str(item["max_rate"]))
                )
                for item in data["availability"]
            ]

        except Exception as e:
            logger.error(
                "Error checking availability",
                error=str(e),
                check_in=check_in,
                check_out=check_out
            )
            # Return mock data on error
            return self._mock_availability(check_in, check_out, guests, room_type)

    async def create_reservation(
            self,
            check_in: date,
            check_out: date,
            room_type: str,
            guests: List[Guest],
            meal_plan: Optional[str] = None,
            special_requests: Optional[str] = None,
            source_channel: str = "whatsapp"
    ) -> Reservation:
        """
        Create a new reservation.
        
        Args:
            check_in: Check-in date
            check_out: Check-out date
            room_type: Type of room
            guests: List of guests
            meal_plan: Meal plan code
            special_requests: Special requests
            source_channel: Booking source
            
        Returns:
            Created reservation
        """
        try:
            if settings.app_env == "development":
                return self._mock_create_reservation(
                    check_in, check_out, room_type, guests
                )

            # Prepare reservation data
            reservation_data = {
                "hotel_id": self.hotel_id,
                "check_in": check_in.isoformat(),
                "check_out": check_out.isoformat(),
                "rooms": [{
                    "room_type": room_type,
                    "guests": len(guests),
                    "meal_plan": meal_plan
                }],
                "guests": [
                    {
                        "name": guest.name,
                        "email": guest.email,
                        "phone": guest.phone,
                        "document": guest.document,
                        "document_type": guest.document_type
                    }
                    for guest in guests
                ],
                "special_requests": special_requests,
                "source": source_channel
            }

            # Create reservation
            response = await self.client.post(
                f"/hotels/{self.hotel_id}/reservations",
                json=reservation_data
            )

            response.raise_for_status()
            data = response.json()

            return Reservation(
                id=data["reservation_id"],
                hotel_id=self.hotel_id,
                status=ReservationStatus(data["status"]),
                check_in=check_in,
                check_out=check_out,
                rooms=data["rooms"],
                guests=guests,
                total_amount=Decimal(str(data["total_amount"])),
                paid_amount=Decimal("0"),
                notes=special_requests,
                created_at=datetime.now()
            )

        except Exception as e:
            logger.error("Error creating reservation", error=str(e))
            raise

    async def get_reservation(self, reservation_id: str) -> Optional[Reservation]:
        """Get reservation details by ID."""
        try:
            if settings.app_env == "development":
                return self._mock_get_reservation(reservation_id)

            response = await self.client.get(
                f"/hotels/{self.hotel_id}/reservations/{reservation_id}"
            )

            if response.status_code == 404:
                return None

            response.raise_for_status()
            data = response.json()

            return self._parse_reservation(data)

        except Exception as e:
            logger.error(
                "Error fetching reservation",
                error=str(e),
                reservation_id=reservation_id
            )
            return None

    async def update_reservation(
            self,
            reservation_id: str,
            updates: Dict
    ) -> Optional[Reservation]:
        """Update existing reservation."""
        try:
            if settings.app_env == "development":
                # Return mock updated reservation
                reservation = self._mock_get_reservation(reservation_id)
                if reservation:
                    for key, value in updates.items():
                        if hasattr(reservation, key):
                            setattr(reservation, key, value)
                return reservation

            response = await self.client.patch(
                f"/hotels/{self.hotel_id}/reservations/{reservation_id}",
                json=updates
            )

            response.raise_for_status()
            data = response.json()

            return self._parse_reservation(data)

        except Exception as e:
            logger.error(
                "Error updating reservation",
                error=str(e),
                reservation_id=reservation_id
            )
            return None

    async def cancel_reservation(
            self,
            reservation_id: str,
            reason: str
    ) -> bool:
        """Cancel a reservation."""
        try:
            if settings.app_env == "development":
                return True

            response = await self.client.post(
                f"/hotels/{self.hotel_id}/reservations/{reservation_id}/cancel",
                json={"reason": reason}
            )

            return response.status_code == 200

        except Exception as e:
            logger.error(
                "Error cancelling reservation",
                error=str(e),
                reservation_id=reservation_id
            )
            return False

    async def get_room_types(self) -> List[Dict]:
        """Get all room types for the hotel."""
        try:
            if settings.app_env == "development":
                return [
                    {
                        "code": "TERREO",
                        "name": "Quarto Térreo",
                        "max_occupancy": 4,
                        "base_rate": 290.00,
                        "amenities": ["ar-condicionado", "tv", "frigobar", "wifi"]
                    },
                    {
                        "code": "SUPERIOR",
                        "name": "Quarto Superior",
                        "max_occupancy": 4,
                        "base_rate": 320.00,
                        "amenities": ["ar-condicionado", "tv", "frigobar", "wifi", "varanda"]
                    }
                ]

            response = await self.client.get(f"/hotels/{self.hotel_id}/room-types")
            response.raise_for_status()

            return response.json()["room_types"]

        except Exception as e:
            logger.error("Error fetching room types", error=str(e))
            return []

    def generate_booking_link(
            self,
            check_in: date,
            check_out: date,
            adults: int,
            children: int = 0,
            room_type: Optional[str] = None,
            promo_code: Optional[str] = None
    ) -> str:
        """Generate direct booking link for Omnibees."""
        base_url = f"https://booking.omnibees.com/chain"

        params = {
            "c": self.hotel_id,
            "checkin": check_in.strftime("%d/%m/%Y"),
            "checkout": check_out.strftime("%d/%m/%Y"),
            "ad": adults,
            "ch": children
        }

        if room_type:
            params["room"] = room_type

        if promo_code:
            params["promo"] = promo_code

        # Build query string
        query = "&".join(f"{k}={v}" for k, v in params.items())

        return f"{base_url}?{query}"

    # Mock methods for development

    def _mock_availability(
            self,
            check_in: date,
            check_out: date,
            guests: int,
            room_type: Optional[str]
    ) -> List[Availability]:
        """Mock availability data for development."""
        # Calculate number of nights
        nights = (check_out - check_in).days

        # Mock availability data
        availabilities = []

        if not room_type or room_type == "TERREO":
            availabilities.append(
                Availability(
                    room_type="TERREO",
                    available_count=3,
                    total_count=5,
                    dates={
                        (check_in + timedelta(days=i)).isoformat(): 3
                        for i in range(nights)
                    },
                    min_rate=Decimal("290.00"),
                    max_rate=Decimal("350.00")
                )
            )

        if not room_type or room_type == "SUPERIOR":
            availabilities.append(
                Availability(
                    room_type="SUPERIOR",
                    available_count=2,
                    total_count=3,
                    dates={
                        (check_in + timedelta(days=i)).isoformat(): 2
                        for i in range(nights)
                    },
                    min_rate=Decimal("320.00"),
                    max_rate=Decimal("380.00")
                )
            )

        return availabilities

    def _mock_create_reservation(
            self,
            check_in: date,
            check_out: date,
            room_type: str,
            guests: List[Guest]
    ) -> Reservation:
        """Mock reservation creation for development."""
        import uuid

        nights = (check_out - check_in).days
        rate = Decimal("290.00") if room_type == "TERREO" else Decimal("320.00")
        total = rate * nights

        return Reservation(
            id=f"RES{uuid.uuid4().hex[:8].upper()}",
            hotel_id=self.hotel_id,
            status=ReservationStatus.CONFIRMED,
            check_in=check_in,
            check_out=check_out,
            rooms=[{
                "room_type": room_type,
                "guests": len(guests),
                "rate": float(rate)
            }],
            guests=guests,
            total_amount=total,
            paid_amount=Decimal("0"),
            notes=None,
            created_at=datetime.now()
        )

    def _mock_get_reservation(self, reservation_id: str) -> Optional[Reservation]:
        """Mock get reservation for development."""
        if not reservation_id.startswith("RES"):
            return None

        # Return mock reservation
        return Reservation(
            id=reservation_id,
            hotel_id=self.hotel_id,
            status=ReservationStatus.CONFIRMED,
            check_in=date.today() + timedelta(days=7),
            check_out=date.today() + timedelta(days=9),
            rooms=[{
                "room_type": "TERREO",
                "guests": 2,
                "rate": 290.00
            }],
            guests=[
                Guest(
                    name="João Silva",
                    email="joao@example.com",
                    phone="+5511999999999",
                    document="123.456.789-00"
                )
            ],
            total_amount=Decimal("580.00"),
            paid_amount=Decimal("0"),
            notes="Chegada após 20h",
            created_at=datetime.now()
        )

    def _parse_reservation(self, data: Dict) -> Reservation:
        """Parse reservation data from API response."""
        return Reservation(
            id=data["id"],
            hotel_id=data["hotel_id"],
            status=ReservationStatus(data["status"]),
            check_in=date.fromisoformat(data["check_in"]),
            check_out=date.fromisoformat(data["check_out"]),
            rooms=data["rooms"],
            guests=[
                Guest(
                    name=g["name"],
                    email=g.get("email"),
                    phone=g["phone"],
                    document=g["document"],
                    document_type=g.get("document_type", "cpf")
                )
                for g in data["guests"]
            ],
            total_amount=Decimal(str(data["total_amount"])),
            paid_amount=Decimal(str(data.get("paid_amount", 0))),
            notes=data.get("notes"),
            created_at=datetime.fromisoformat(data["created_at"])
        )

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.client.aclose()


# Convenience functions for quick access

async def check_hotel_availability(
        check_in: date,
        check_out: date,
        guests: int
) -> List[Availability]:
    """Quick function to check availability."""
    async with OmnibeesClient() as client:
        return await client.check_availability(check_in, check_out, guests)


async def create_booking(
        check_in: date,
        check_out: date,
        room_type: str,
        guest_name: str,
        guest_phone: str,
        guest_document: str
) -> Reservation:
    """Quick function to create a booking."""
    async with OmnibeesClient() as client:
        guest = Guest(
            name=guest_name,
            phone=guest_phone,
            document=guest_document
        )
        return await client.create_reservation(
            check_in=check_in,
            check_out=check_out,
            room_type=room_type,
            guests=[guest]
        )


def get_booking_link(
        check_in: date,
        check_out: date,
        adults: int,
        children: int = 0
) -> str:
    """Get direct booking link."""
    client = OmnibeesClient()
    return client.generate_booking_link(check_in, check_out, adults, children)
