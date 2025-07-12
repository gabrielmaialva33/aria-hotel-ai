"""Unit tests for utility functions."""

from datetime import date, timedelta

from aria.core.utils import (
    extract_email,
    extract_phone_number,
    format_currency_brl,
    format_phone_display,
    generate_booking_reference,
    get_greeting,
    parse_children_ages,
    parse_date_pt,
    parse_meal_preference,
    sanitize_message,
    split_message_for_whatsapp,
)


class TestDateParsing:
    """Test date parsing functions."""

    def test_parse_date_direct_formats(self):
        """Test parsing direct date formats."""
        # DD/MM/YYYY
        assert parse_date_pt("10/02/2025") == date(2025, 2, 10)
        assert parse_date_pt("31/12/2024") == date(2024, 12, 31)

        # DD-MM-YYYY
        assert parse_date_pt("10-02-2025") == date(2025, 2, 10)

        # DD.MM.YYYY
        assert parse_date_pt("10.02.2025") == date(2025, 2, 10)

    def test_parse_date_relative(self):
        """Test parsing relative dates."""
        today = date.today()

        assert parse_date_pt("hoje") == today
        assert parse_date_pt("amanhã") == today + timedelta(days=1)
        assert parse_date_pt("depois de amanhã") == today + timedelta(days=2)

    def test_parse_date_month_names(self):
        """Test parsing dates with month names."""
        today = date.today()
        year = today.year

        # Should handle "DD de MONTH" format
        result = parse_date_pt("10 de fevereiro")
        assert result.day == 10
        assert result.month == 2

        # If date is in past, should assume next year
        past_date = parse_date_pt("1 de janeiro")
        if today > date(year, 1, 1):
            assert past_date.year == year + 1
        else:
            assert past_date.year == year

    def test_parse_date_weekdays(self):
        """Test parsing weekday names."""
        today = date.today()

        # Test "próxima sexta-feira"
        result = parse_date_pt("próxima sexta-feira")
        assert result.weekday() == 4  # Friday
        assert result > today + timedelta(days=7)  # Next week

        # Test just "sexta-feira" (this week or next)
        result = parse_date_pt("sexta-feira")
        assert result.weekday() == 4
        assert result > today


class TestPhoneExtraction:
    """Test phone number extraction."""

    def test_extract_mobile_numbers(self):
        """Test extracting mobile numbers."""
        # With area code
        assert extract_phone_number("11 99999-8888") == "+5511999998888"
        assert extract_phone_number("(11) 99999-8888") == "+5511999998888"
        assert extract_phone_number("11999998888") == "+5511999998888"

        # Without area code (assumes São Paulo)
        assert extract_phone_number("99999-8888") == "+5511999998888"
        assert extract_phone_number("999998888") == "+5511999998888"

    def test_extract_landline_numbers(self):
        """Test extracting landline numbers."""
        # With area code
        assert extract_phone_number("11 3333-4444") == "+5511333344444"
        assert extract_phone_number("(11) 3333-4444") == "+5511333344444"

        # Without area code
        assert extract_phone_number("3333-4444") == "+5511333344444"

    def test_format_phone_display(self):
        """Test phone formatting for display."""
        assert format_phone_display("+5511999998888") == "(11) 99999-8888"
        assert format_phone_display("+5511333344444") == "(11) 3333-4444"
        assert format_phone_display("11999998888") == "(11) 99999-8888"


class TestCurrencyFormatting:
    """Test currency formatting."""

    def test_format_currency_brl(self):
        """Test Brazilian Real formatting."""
        assert format_currency_brl(1234.56) == "R$ 1.234,56"
        assert format_currency_brl(1000000.00) == "R$ 1.000.000,00"
        assert format_currency_brl(99.90) == "R$ 99,90"
        assert format_currency_brl(0.50) == "R$ 0,50"


class TestChildrenAgesParsing:
    """Test parsing children ages from text."""

    def test_parse_simple_ages(self):
        """Test parsing simple age lists."""
        assert parse_children_ages("5 e 8 anos") == [5, 8]
        assert parse_children_ages("3, 5, 10") == [3, 5, 10]
        assert parse_children_ages("uma de 3 e outra de 7") == [3, 7]

    def test_parse_complex_text(self):
        """Test parsing ages from complex text."""
        assert parse_children_ages("tenho 2 filhos, um de 4 anos e outro de 12") == [4, 12]
        assert parse_children_ages("crianças com 2, 5 e 9 anos") == [2, 5, 9]

    def test_filter_invalid_ages(self):
        """Test filtering out invalid ages."""
        assert parse_children_ages("25 e 5 anos") == [5]  # 25 is too old
        assert parse_children_ages("apartamento 301, criança 7 anos") == [7]  # Ignore 301


class TestMessageUtilities:
    """Test message handling utilities."""

    def test_sanitize_message(self):
        """Test message sanitization."""
        assert sanitize_message("  Hello   World  ") == "Hello World"
        assert sanitize_message("Line1\n\n\nLine2") == "Line1 Line2"
        assert sanitize_message("Test\x00\x01") == "Test"  # Remove control chars

    def test_split_long_message(self):
        """Test splitting long messages."""
        short_msg = "Hello, this is a short message."
        assert split_message_for_whatsapp(short_msg) == [short_msg]

        # Create a long message
        long_msg = "A" * 2000
        parts = split_message_for_whatsapp(long_msg)
        assert len(parts) > 1
        assert all(len(part) <= 1600 for part in parts)

    def test_get_greeting(self):
        """Test time-based greeting."""
        # Mock different times
        greeting = get_greeting()
        assert greeting in ["Bom dia", "Boa tarde", "Boa noite"]


class TestOtherUtilities:
    """Test other utility functions."""

    def test_generate_booking_reference(self):
        """Test booking reference generation."""
        ref1 = generate_booking_reference()
        ref2 = generate_booking_reference()

        assert ref1.startswith("HP-")
        assert len(ref1) == 17  # HP-YYYYMMDD-XXXX
        assert ref1 != ref2  # Should be unique

    def test_parse_meal_preference(self):
        """Test meal preference parsing."""
        assert parse_meal_preference("quero pensão completa") == "pensao_completa"
        assert parse_meal_preference("meia pensão por favor") == "meia_pensao"
        assert parse_meal_preference("só café da manhã") == "cafe_da_manha"
        assert parse_meal_preference("não sei") is None

    def test_extract_email(self):
        """Test email extraction."""
        assert extract_email("meu email é joao@example.com") == "joao@example.com"
        assert extract_email("Contact: user@domain.co.uk please") == "user@domain.co.uk"
        assert extract_email("no email here") is None
