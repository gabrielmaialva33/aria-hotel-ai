"""Shared value objects for domain entities."""

import re
from typing import Optional
from dataclasses import dataclass
from decimal import Decimal


class Email:
    """Email value object with validation."""
    
    def __init__(self, value: str):
        if not self._is_valid(value):
            raise ValueError(f"Invalid email: {value}")
        self.value = value.lower()
    
    @staticmethod
    def _is_valid(email: str) -> bool:
        """Validate email format."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    def __str__(self) -> str:
        return self.value
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, Email):
            return False
        return self.value == other.value
    
    def __hash__(self) -> int:
        return hash(self.value)
    
    @property
    def domain(self) -> str:
        """Get email domain."""
        return self.value.split('@')[1]
    
    @property
    def username(self) -> str:
        """Get email username."""
        return self.value.split('@')[0]


class Phone:
    """Phone number value object with Brazilian format validation."""
    
    def __init__(self, value: str, country_code: str = "+55"):
        cleaned = self._clean_number(value)
        if not self._is_valid(cleaned):
            raise ValueError(f"Invalid phone number: {value}")
        
        self.country_code = country_code
        self.number = cleaned
    
    @staticmethod
    def _clean_number(phone: str) -> str:
        """Clean phone number, keeping only digits."""
        return re.sub(r'[^\d]', '', phone)
    
    @staticmethod
    def _is_valid(phone: str) -> bool:
        """Validate Brazilian phone number."""
        # Brazilian mobile: 11 digits (with area code)
        # Brazilian landline: 10 digits (with area code)
        return len(phone) in [10, 11] and phone[:2].isdigit()
    
    def __str__(self) -> str:
        """Format as +55 11 99999-9999."""
        if len(self.number) == 11:
            return f"{self.country_code} {self.number[:2]} {self.number[2:7]}-{self.number[7:]}"
        else:
            return f"{self.country_code} {self.number[:2]} {self.number[2:6]}-{self.number[6:]}"
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, Phone):
            return False
        return self.number == other.number and self.country_code == other.country_code
    
    def __hash__(self) -> int:
        return hash((self.country_code, self.number))
    
    @property
    def area_code(self) -> str:
        """Get area code."""
        return self.number[:2]
    
    @property
    def is_mobile(self) -> bool:
        """Check if it's a mobile number."""
        return len(self.number) == 11 and self.number[2] == '9'
    
    def to_whatsapp(self) -> str:
        """Format for WhatsApp."""
        return f"{self.country_code}{self.number}"


@dataclass
class Document:
    """Document value object (CPF, RG, Passport, etc)."""
    
    type: str  # cpf, rg, passport, cnh
    number: str
    issuer: Optional[str] = None
    issue_date: Optional[str] = None
    
    def __post_init__(self):
        """Validate document after initialization."""
        if self.type == "cpf":
            if not self._validate_cpf(self.number):
                raise ValueError(f"Invalid CPF: {self.number}")
        elif self.type == "passport":
            if not self._validate_passport(self.number):
                raise ValueError(f"Invalid passport: {self.number}")
    
    @staticmethod
    def _validate_cpf(cpf: str) -> bool:
        """Validate Brazilian CPF."""
        # Remove non-digits
        cpf = re.sub(r'[^\d]', '', cpf)
        
        if len(cpf) != 11:
            return False
        
        # Check for repeated digits
        if len(set(cpf)) == 1:
            return False
        
        # Validate check digits
        nums = [int(d) for d in cpf]
        
        # First digit
        sum1 = sum(nums[i] * (10 - i) for i in range(9))
        digit1 = (sum1 * 10) % 11
        if digit1 == 10:
            digit1 = 0
        
        if digit1 != nums[9]:
            return False
        
        # Second digit
        sum2 = sum(nums[i] * (11 - i) for i in range(10))
        digit2 = (sum2 * 10) % 11
        if digit2 == 10:
            digit2 = 0
        
        return digit2 == nums[10]
    
    @staticmethod
    def _validate_passport(passport: str) -> bool:
        """Basic passport validation."""
        # Most passports are 6-9 alphanumeric characters
        cleaned = re.sub(r'[^A-Z0-9]', '', passport.upper())
        return 6 <= len(cleaned) <= 9
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "type": self.type,
            "number": self.number,
            "issuer": self.issuer,
            "issue_date": self.issue_date
        }
    
    @property
    def masked(self) -> str:
        """Get masked document number for display."""
        if self.type == "cpf":
            # Show only first 3 and last 2 digits
            clean = re.sub(r'[^\d]', '', self.number)
            return f"{clean[:3]}.***.***-{clean[-2:]}"
        elif self.type == "passport":
            # Show only first 2 and last 2 characters
            return f"{self.number[:2]}****{self.number[-2:]}"
        else:
            # Generic masking
            visible = max(2, len(self.number) // 4)
            return f"{self.number[:visible]}{'*' * (len(self.number) - 2 * visible)}{self.number[-visible:]}"


@dataclass
class Money:
    """Money value object with currency."""
    
    amount: Decimal
    currency: str = "BRL"
    
    def __post_init__(self):
        """Ensure amount is Decimal."""
        if not isinstance(self.amount, Decimal):
            self.amount = Decimal(str(self.amount))
        
        # Round to 2 decimal places
        self.amount = self.amount.quantize(Decimal('0.01'))
    
    def __str__(self) -> str:
        """Format as currency string."""
        if self.currency == "BRL":
            return f"R$ {self.amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        else:
            return f"{self.currency} {self.amount:,.2f}"
    
    def __add__(self, other):
        """Add two money values."""
        if isinstance(other, Money):
            if self.currency != other.currency:
                raise ValueError("Cannot add different currencies")
            return Money(self.amount + other.amount, self.currency)
        return NotImplemented
    
    def __sub__(self, other):
        """Subtract two money values."""
        if isinstance(other, Money):
            if self.currency != other.currency:
                raise ValueError("Cannot subtract different currencies")
            return Money(self.amount - other.amount, self.currency)
        return NotImplemented
    
    def __mul__(self, other):
        """Multiply money by a number."""
        if isinstance(other, (int, float, Decimal)):
            return Money(self.amount * Decimal(str(other)), self.currency)
        return NotImplemented
    
    def __truediv__(self, other):
        """Divide money by a number."""
        if isinstance(other, (int, float, Decimal)):
            return Money(self.amount / Decimal(str(other)), self.currency)
        return NotImplemented
    
    def __eq__(self, other) -> bool:
        """Check equality."""
        if not isinstance(other, Money):
            return False
        return self.amount == other.amount and self.currency == other.currency
    
    def __lt__(self, other) -> bool:
        """Less than comparison."""
        if not isinstance(other, Money):
            return NotImplemented
        if self.currency != other.currency:
            raise ValueError("Cannot compare different currencies")
        return self.amount < other.amount
    
    def __le__(self, other) -> bool:
        """Less than or equal comparison."""
        return self == other or self < other
    
    def __gt__(self, other) -> bool:
        """Greater than comparison."""
        if not isinstance(other, Money):
            return NotImplemented
        if self.currency != other.currency:
            raise ValueError("Cannot compare different currencies")
        return self.amount > other.amount
    
    def __ge__(self, other) -> bool:
        """Greater than or equal comparison."""
        return self == other or self > other
    
    def is_zero(self) -> bool:
        """Check if amount is zero."""
        return self.amount == Decimal('0')
    
    def is_positive(self) -> bool:
        """Check if amount is positive."""
        return self.amount > Decimal('0')
    
    def is_negative(self) -> bool:
        """Check if amount is negative."""
        return self.amount < Decimal('0')


@dataclass
class DateRange:
    """Date range value object."""
    
    start_date: date
    end_date: date
    
    def __post_init__(self):
        """Validate date range."""
        if self.end_date < self.start_date:
            raise ValueError("End date must be after or equal to start date")
    
    @property
    def nights(self) -> int:
        """Calculate number of nights."""
        return (self.end_date - self.start_date).days
    
    @property
    def days(self) -> int:
        """Calculate number of days (inclusive)."""
        return self.nights + 1
    
    def contains(self, date: date) -> bool:
        """Check if date is within range."""
        return self.start_date <= date <= self.end_date
    
    def overlaps(self, other: "DateRange") -> bool:
        """Check if ranges overlap."""
        return not (self.end_date < other.start_date or self.start_date > other.end_date)
    
    def merge(self, other: "DateRange") -> Optional["DateRange"]:
        """Merge overlapping ranges."""
        if not self.overlaps(other):
            return None
        
        return DateRange(
            min(self.start_date, other.start_date),
            max(self.end_date, other.end_date)
        )
    
    def __str__(self) -> str:
        """String representation."""
        return f"{self.start_date.strftime('%d/%m/%Y')} - {self.end_date.strftime('%d/%m/%Y')}"


@dataclass
class Address:
    """Address value object."""
    
    street: str
    number: str
    complement: Optional[str] = None
    neighborhood: str = None
    city: str = None
    state: str = None
    country: str = "Brasil"
    postal_code: Optional[str] = None
    
    def __str__(self) -> str:
        """Format as full address."""
        parts = [f"{self.street}, {self.number}"]
        
        if self.complement:
            parts.append(self.complement)
        
        if self.neighborhood:
            parts.append(self.neighborhood)
        
        if self.city and self.state:
            parts.append(f"{self.city}/{self.state}")
        elif self.city:
            parts.append(self.city)
        
        if self.postal_code:
            parts.append(f"CEP: {self.format_postal_code()}")
        
        if self.country != "Brasil":
            parts.append(self.country)
        
        return ", ".join(parts)
    
    def format_postal_code(self) -> str:
        """Format Brazilian postal code."""
        if not self.postal_code:
            return ""
        
        clean = re.sub(r'[^\d]', '', self.postal_code)
        if len(clean) == 8:
            return f"{clean[:5]}-{clean[5:]}"
        return self.postal_code
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "street": self.street,
            "number": self.number,
            "complement": self.complement,
            "neighborhood": self.neighborhood,
            "city": self.city,
            "state": self.state,
            "country": self.country,
            "postal_code": self.postal_code
        }
