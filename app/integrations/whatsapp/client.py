"""WhatsApp client for sending and receiving messages via Twilio."""

from typing import Dict, List, Optional

from twilio.rest import Client as TwilioClient
from twilio.twiml.messaging_response import MessagingResponse

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class WhatsAppClient:
    """Client for WhatsApp messaging via Twilio."""
    
    def __init__(self):
        """Initialize WhatsApp client with Twilio credentials."""
        self.client = TwilioClient(
            settings.twilio_account_sid,
            settings.twilio_auth_token
        )
        self.from_number = settings.twilio_whatsapp_number
        
        # Validate configuration
        if not self.from_number:
            raise ValueError("TWILIO_WHATSAPP_NUMBER not configured")
        
        logger.info("WhatsApp client initialized", from_number=self.from_number)
    
    async def send_message(
        self,
        to: str,
        body: str,
        media_urls: Optional[List[str]] = None,
        callback_url: Optional[str] = None
    ) -> str:
        """
        Send WhatsApp message.
        
        Args:
            to: Recipient phone number (without whatsapp: prefix)
            body: Message text
            media_urls: List of media URLs to attach
            callback_url: Webhook URL for status callbacks
            
        Returns:
            Message SID
        """
        # Ensure phone has whatsapp: prefix
        if not to.startswith("whatsapp:"):
            to = f"whatsapp:{to}"
        
        try:
            # Build message parameters
            params = {
                "body": body,
                "from_": self.from_number,
                "to": to
            }
            
            # Add media if provided
            if media_urls:
                params["media_url"] = media_urls[:10]  # Twilio limit
            
            # Add callback URL if provided
            if callback_url:
                params["status_callback"] = callback_url
            
            # Send message
            message = self.client.messages.create(**params)
            
            logger.info(
                "WhatsApp message sent",
                message_sid=message.sid,
                to=to,
                body_length=len(body),
                media_count=len(media_urls) if media_urls else 0
            )
            
            return message.sid
            
        except Exception as e:
            logger.error(
                "Failed to send WhatsApp message",
                error=str(e),
                to=to,
                body_preview=body[:100]
            )
            raise
    
    async def send_template_message(
        self,
        to: str,
        template_name: str,
        template_params: Optional[Dict] = None
    ) -> str:
        """
        Send WhatsApp template message.
        
        Args:
            to: Recipient phone number
            template_name: Name of approved template
            template_params: Parameters for template
            
        Returns:
            Message SID
        """
        # TODO: Implement template messaging when configured
        # For now, fall back to regular message
        body = self._format_template(template_name, template_params)
        return await self.send_message(to, body)
    
    def parse_webhook(self, form_data: Dict) -> Dict:
        """
        Parse incoming webhook from Twilio.
        
        Args:
            form_data: Form data from webhook request
            
        Returns:
            Parsed message data
        """
        # Extract relevant fields
        from_number = form_data.get("From", "").replace("whatsapp:", "")
        to_number = form_data.get("To", "").replace("whatsapp:", "")
        body = form_data.get("Body", "")
        message_sid = form_data.get("MessageSid", "")
        
        # Extract media if present
        media_urls = []
        num_media = int(form_data.get("NumMedia", 0))
        for i in range(num_media):
            media_url = form_data.get(f"MediaUrl{i}")
            media_type = form_data.get(f"MediaContentType{i}")
            if media_url:
                media_urls.append({
                    "url": media_url,
                    "content_type": media_type
                })
        
        # Extract location if present
        location = None
        if form_data.get("Latitude") and form_data.get("Longitude"):
            location = {
                "latitude": float(form_data.get("Latitude")),
                "longitude": float(form_data.get("Longitude")),
                "label": form_data.get("LocationLabel"),
                "address": form_data.get("LocationAddress")
            }
        
        return {
            "message_sid": message_sid,
            "from": from_number,
            "to": to_number,
            "body": body,
            "media": media_urls,
            "location": location,
            "raw_data": form_data
        }
    
    def create_response(self) -> MessagingResponse:
        """Create a new Twilio messaging response."""
        return MessagingResponse()
    
    def _format_template(
        self,
        template_name: str,
        params: Optional[Dict] = None
    ) -> str:
        """Format a template with parameters."""
        templates = {
            "welcome": "Bem-vindo ao Hotel Passarim! {name}",
            "reservation_confirmed": "Sua reserva foi confirmada! Check-in: {check_in}",
            "check_in_reminder": "Olá {name}! Lembramos que seu check-in é amanhã às {time}.",
            "feedback_request": "Como foi sua estadia no Hotel Passarim? Adoraríamos ouvir sua opinião!"
        }
        
        template = templates.get(template_name, "")
        if params:
            template = template.format(**params)
        
        return template
    
    async def send_quick_replies(
        self,
        to: str,
        body: str,
        options: List[str]
    ) -> str:
        """
        Send message with quick reply options.
        
        Note: WhatsApp Business API supports quick replies,
        but Twilio's implementation may vary.
        """
        # Format options as numbered list
        formatted_body = f"{body}\n\n"
        for i, option in enumerate(options, 1):
            formatted_body += f"{i}. {option}\n"
        
        formatted_body += "\nResponda com o número da opção desejada."
        
        return await self.send_message(to, formatted_body)
    
    async def send_location(
        self,
        to: str,
        latitude: float,
        longitude: float,
        name: str,
        address: str
    ) -> str:
        """Send location message."""
        # Twilio supports location sharing via specific parameters
        body = f"📍 {name}\n{address}"
        
        # TODO: Implement proper location sharing when Twilio supports it
        # For now, send Google Maps link
        maps_url = f"https://maps.google.com/?q={latitude},{longitude}"
        
        return await self.send_message(
            to,
            f"{body}\n\n🗺️ Ver no mapa: {maps_url}"
        )
    
    async def mark_as_read(self, message_sid: str) -> bool:
        """Mark a message as read (if supported)."""
        # TODO: Implement when Twilio supports read receipts
        logger.debug("Mark as read not implemented", message_sid=message_sid)
        return True
