"""Utility functions for ARIA Hotel AI."""

import re
from datetime import date, datetime, timedelta
from typing import List, Optional, Tuple

from aria.core.logging import get_logger

logger = get_logger(__name__)


def parse_date_pt(date_str: str) -> Optional[date]:
    """
    Parse date from Portuguese text.
    
    Handles formats like:
    - "10/02/2025" or "10-02-2025"
    - "10 de fevereiro"
    - "amanhã", "depois de amanhã"
    - "próxima sexta-feira"
    """
    date_str = date_str.lower().strip()
    today = date.today()
    
    # Direct date formats
    for fmt in ["%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%d/%m/%y", "%d-%m-%y"]:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    
    # Relative dates
    if date_str in ["hoje", "hj"]:
        return today
    elif date_str in ["amanhã", "amanha"]:
        return today + timedelta(days=1)
    elif date_str in ["depois de amanhã", "depois de amanha"]:
        return today + timedelta(days=2)
    
    # Month names in Portuguese
    months_pt = {
        "janeiro": 1, "jan": 1,
        "fevereiro": 2, "fev": 2,
        "março": 3, "mar": 3,
        "abril": 4, "abr": 4,
        "maio": 5, "mai": 5,
        "junho": 6, "jun": 6,
        "julho": 7, "jul": 7,
        "agosto": 8, "ago": 8,
        "setembro": 9, "set": 9,
        "outubro": 10, "out": 10,
        "novembro": 11, "nov": 11,
        "dezembro": 12, "dez": 12
    }
    
    # Try "DD de MONTH" format
    match = re.match(r"(\d{1,2})\s*de\s*(\w+)", date_str)
    if match:
        day = int(match.group(1))
        month_name = match.group(2)
        if month_name in months_pt:
            month = months_pt[month_name]
            year = today.year
            # If date is in the past, assume next year
            try:
                result = date(year, month, day)
                if result < today:
                    result = date(year + 1, month, day)
                return result
            except ValueError:
                pass
    
    # Weekday names
    weekdays_pt = {
        "segunda": 0, "segunda-feira": 0,
        "terça": 1, "terca": 1, "terça-feira": 1, "terca-feira": 1,
        "quarta": 2, "quarta-feira": 2,
        "quinta": 3, "quinta-feira": 3,
        "sexta": 4, "sexta-feira": 4,
        "sábado": 5, "sabado": 5,
        "domingo": 6
    }
    
    # Next weekday
    for weekday_name, weekday_num in weekdays_pt.items():
        if f"próxima {weekday_name}" in date_str or f"proxima {weekday_name}" in date_str:
            days_ahead = weekday_num - today.weekday()
            if days_ahead <= 0:  # Target day already happened this week
                days_ahead += 7
            return today + timedelta(days_ahead + 7)  # Next week
        elif weekday_name in date_str:
            days_ahead = weekday_num - today.weekday()
            if days_ahead <= 0:  # Target day already happened this week
                days_ahead += 7
            return today + timedelta(days_ahead)
    
    return None


def extract_phone_number(text: str) -> Optional[str]:
    """
    Extract Brazilian phone number from text.
    
    Returns cleaned phone number or None.
    """
    # Remove all non-numeric characters
    numbers = re.sub(r'\D', '', text)
    
    # Brazilian phone patterns
    # Mobile: 11 digits (with area code)
    # Landline: 10 digits (with area code)
    
    if len(numbers) == 11 and numbers[2] == '9':
        # Valid mobile
        return f"+55{numbers}"
    elif len(numbers) == 10:
        # Valid landline
        return f"+55{numbers}"
    elif len(numbers) == 13 and numbers.startswith('55'):
        # Already has country code
        return f"+{numbers}"
    elif len(numbers) == 9 and numbers[0] == '9':
        # Mobile without area code - assume São Paulo (11)
        return f"+5511{numbers}"
    elif len(numbers) == 8:
        # Landline without area code - assume São Paulo (11)
        return f"+5511{numbers}"
    
    return None


def format_phone_display(phone: str) -> str:
    """Format phone number for display."""
    # Remove + and country code for display
    if phone.startswith("+55"):
        phone = phone[3:]
    elif phone.startswith("55"):
        phone = phone[2:]
    
    # Format as (XX) XXXXX-XXXX or (XX) XXXX-XXXX
    if len(phone) == 11:
        return f"({phone[:2]}) {phone[2:7]}-{phone[7:]}"
    elif len(phone) == 10:
        return f"({phone[:2]}) {phone[2:6]}-{phone[6:]}"
    
    return phone


def format_currency_brl(amount: float) -> str:
    """Format amount as Brazilian Real."""
    return f"R$ {amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def calculate_age(birth_date: date) -> int:
    """Calculate age from birth date."""
    today = date.today()
    age = today.year - birth_date.year
    
    # Adjust if birthday hasn't occurred this year
    if (today.month, today.day) < (birth_date.month, birth_date.day):
        age -= 1
    
    return age


def parse_children_ages(text: str) -> List[int]:
    """
    Parse children ages from text.
    
    Examples:
    - "5 e 8 anos"
    - "uma de 3 e outra de 7"
    - "3, 5, 10"
    """
    # Find all numbers in the text
    numbers = re.findall(r'\d+', text)
    
    # Convert to integers and filter reasonable ages (0-17)
    ages = []
    for num in numbers:
        age = int(num)
        if 0 <= age <= 17:
            ages.append(age)
    
    return ages


def is_business_hours() -> bool:
    """Check if current time is within business hours (8 AM - 10 PM)."""
    now = datetime.now()
    return 8 <= now.hour < 22


def get_greeting() -> str:
    """Get appropriate greeting based on time of day."""
    hour = datetime.now().hour
    
    if 5 <= hour < 12:
        return "Bom dia"
    elif 12 <= hour < 18:
        return "Boa tarde"
    else:
        return "Boa noite"


def sanitize_message(text: str) -> str:
    """Sanitize message text for storage/display."""
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove control characters
    text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\r\t')
    
    # Trim
    text = text.strip()
    
    return text


def split_message_for_whatsapp(text: str, max_length: int = 1600) -> List[str]:
    """
    Split long message into chunks for WhatsApp.
    
    WhatsApp has a limit of ~1600 characters per message.
    """
    if len(text) <= max_length:
        return [text]
    
    messages = []
    current = ""
    
    # Split by paragraphs first
    paragraphs = text.split('\n\n')
    
    for paragraph in paragraphs:
        if len(current) + len(paragraph) + 2 <= max_length:
            if current:
                current += "\n\n"
            current += paragraph
        else:
            if current:
                messages.append(current)
            
            # If paragraph itself is too long, split by sentences
            if len(paragraph) > max_length:
                sentences = re.split(r'(?<=[.!?])\s+', paragraph)
                current = ""
                for sentence in sentences:
                    if len(current) + len(sentence) + 1 <= max_length:
                        if current:
                            current += " "
                        current += sentence
                    else:
                        if current:
                            messages.append(current)
                        current = sentence
            else:
                current = paragraph
    
    if current:
        messages.append(current)
    
    return messages


def generate_booking_reference() -> str:
    """Generate a unique booking reference."""
    import random
    import string
    
    # Format: HP-YYYYMMDD-XXXX
    today = date.today()
    date_str = today.strftime("%Y%m%d")
    random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    
    return f"HP-{date_str}-{random_str}"


def parse_meal_preference(text: str) -> Optional[str]:
    """Parse meal plan preference from text."""
    text = text.lower()
    
    if any(word in text for word in ["completa", "completo", "todas as refeições", "todas refeições"]):
        return "pensao_completa"
    elif any(word in text for word in ["meia pensão", "meia pensao", "meia-pensão"]):
        return "meia_pensao"
    elif any(word in text for word in ["café", "cafe", "apenas café", "so cafe"]):
        return "cafe_da_manha"
    
    return None


def extract_email(text: str) -> Optional[str]:
    """Extract email address from text."""
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    match = re.search(email_pattern, text)
    return match.group(0) if match else None
