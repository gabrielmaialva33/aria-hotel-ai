"""WhatsApp integration via Twilio."""

from app.integrations.whatsapp.client import WhatsAppClient
from app.integrations.whatsapp.media import MediaHandler

__all__ = ["WhatsAppClient", "MediaHandler"]
