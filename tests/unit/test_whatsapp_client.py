"""Unit tests for WhatsApp client."""

from unittest.mock import MagicMock, patch

import pytest

from aria.integrations.whatsapp.client import WhatsAppClient


class TestWhatsAppClient:
    """Test WhatsApp client functionality."""
    
    @pytest.fixture
    def mock_settings(self):
        """Mock settings."""
        with patch("aria.integrations.whatsapp.client.settings") as mock:
            mock.twilio_account_sid = "ACtest123"
            mock.twilio_auth_token = "testtoken123"
            mock.twilio_whatsapp_number = "whatsapp:+14155238886"
            yield mock
    
    @pytest.fixture
    def mock_twilio_client(self):
        """Mock Twilio client."""
        with patch("aria.integrations.whatsapp.client.TwilioClient") as mock:
            yield mock
    
    @pytest.fixture
    def whatsapp_client(self, mock_settings, mock_twilio_client):
        """Create WhatsApp client with mocks."""
        return WhatsAppClient()
    
    @pytest.mark.asyncio
    async def test_send_message(self, whatsapp_client, mock_twilio_client):
        """Test sending a simple message."""
        # Setup mock
        mock_message = MagicMock()
        mock_message.sid = "SM123456"
        mock_twilio_client.return_value.messages.create.return_value = mock_message
        
        # Send message
        message_sid = await whatsapp_client.send_message(
            to="+5511999999999",
            body="Test message"
        )
        
        # Verify
        assert message_sid == "SM123456"
        mock_twilio_client.return_value.messages.create.assert_called_once()
        
        # Check call arguments
        call_args = mock_twilio_client.return_value.messages.create.call_args[1]
        assert call_args["to"] == "whatsapp:+5511999999999"
        assert call_args["body"] == "Test message"
        assert call_args["from_"] == "whatsapp:+14155238886"
    
    @pytest.mark.asyncio
    async def test_send_message_with_media(self, whatsapp_client, mock_twilio_client):
        """Test sending message with media."""
        # Setup mock
        mock_message = MagicMock()
        mock_message.sid = "SM123456"
        mock_twilio_client.return_value.messages.create.return_value = mock_message
        
        # Send message with media
        media_urls = ["https://example.com/image1.jpg", "https://example.com/image2.jpg"]
        message_sid = await whatsapp_client.send_message(
            to="+5511999999999",
            body="Check out these photos!",
            media_urls=media_urls
        )
        
        # Verify media was included
        call_args = mock_twilio_client.return_value.messages.create.call_args[1]
        assert call_args["media_url"] == media_urls
    
    def test_parse_webhook(self, whatsapp_client):
        """Test webhook parsing."""
        # Sample webhook data
        form_data = {
            "MessageSid": "SM123456",
            "From": "whatsapp:+5511999999999",
            "To": "whatsapp:+14155238886",
            "Body": "Hello, I need a room",
            "NumMedia": "1",
            "MediaUrl0": "https://api.twilio.com/2010-04-01/Accounts/AC123/Messages/MM123/Media/ME123",
            "MediaContentType0": "image/jpeg"
        }
        
        # Parse
        parsed = whatsapp_client.parse_webhook(form_data)
        
        # Verify
        assert parsed["message_sid"] == "SM123456"
        assert parsed["from"] == "+5511999999999"
        assert parsed["to"] == "+14155238886"
        assert parsed["body"] == "Hello, I need a room"
        assert len(parsed["media"]) == 1
        assert parsed["media"][0]["content_type"] == "image/jpeg"
    
    def test_parse_webhook_with_location(self, whatsapp_client):
        """Test webhook parsing with location data."""
        form_data = {
            "MessageSid": "SM123456",
            "From": "whatsapp:+5511999999999",
            "To": "whatsapp:+14155238886",
            "Body": "My location",
            "Latitude": "-23.550520",
            "Longitude": "-46.633308",
            "LocationLabel": "São Paulo",
            "LocationAddress": "São Paulo, SP, Brazil"
        }
        
        parsed = whatsapp_client.parse_webhook(form_data)
        
        assert parsed["location"] is not None
        assert parsed["location"]["latitude"] == -23.550520
        assert parsed["location"]["longitude"] == -46.633308
        assert parsed["location"]["label"] == "São Paulo"
    
    @pytest.mark.asyncio
    async def test_send_quick_replies(self, whatsapp_client, mock_twilio_client):
        """Test sending quick reply options."""
        # Setup mock
        mock_message = MagicMock()
        mock_message.sid = "SM123456"
        mock_twilio_client.return_value.messages.create.return_value = mock_message
        
        # Send quick replies
        await whatsapp_client.send_quick_replies(
            to="+5511999999999",
            body="What would you like to do?",
            options=["Make a reservation", "Check prices", "See photos"]
        )
        
        # Verify formatted message
        call_args = mock_twilio_client.return_value.messages.create.call_args[1]
        body = call_args["body"]
        
        assert "What would you like to do?" in body
        assert "1. Make a reservation" in body
        assert "2. Check prices" in body
        assert "3. See photos" in body
        assert "Responda com o número" in body
    
    def test_format_template(self, whatsapp_client):
        """Test template formatting."""
        # Test welcome template
        message = whatsapp_client._format_template(
            "welcome",
            {"name": "João Silva"}
        )
        assert message == "Bem-vindo ao Hotel Passarim! João Silva"
        
        # Test reservation confirmed template
        message = whatsapp_client._format_template(
            "reservation_confirmed",
            {"check_in": "15/02/2025"}
        )
        assert message == "Sua reserva foi confirmada! Check-in: 15/02/2025"
