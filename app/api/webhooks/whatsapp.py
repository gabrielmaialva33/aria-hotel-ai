"""WhatsApp webhook handlers."""

from typing import Dict

from fastapi import APIRouter, Form, HTTPException, Request, Response
from fastapi.responses import PlainTextResponse

from app.agents.ana.agent import AnaAgent  # Use the new Agno-powered agent
from app.core.logging import get_logger
from app.core.sessions import SessionManager
from app.integrations.whatsapp import MediaHandler, WhatsAppClient

logger = get_logger(__name__)

# Initialize components
router = APIRouter(prefix="/webhooks/whatsapp", tags=["webhooks"])
whatsapp_client = WhatsAppClient()
media_handler = MediaHandler()
session_manager = SessionManager()
ana_agent = AnaAgent()  # Now using Agno Framework


@router.post("")
async def handle_whatsapp_webhook(request: Request):
    """
    Handle incoming WhatsApp messages from Twilio.
    
    Twilio sends form-encoded data for WhatsApp webhooks.
    """
    try:
        # Parse form data
        form_data = await request.form()
        form_dict = dict(form_data)

        # Log incoming webhook
        logger.info(
            "WhatsApp webhook received",
            message_sid=form_dict.get("MessageSid"),
            from_number=form_dict.get("From")
        )

        # Parse webhook data
        message_data = whatsapp_client.parse_webhook(form_dict)

        # Get phone number
        phone = message_data["from"]

        # Get or restore session
        session = await session_manager.get_session(phone)

        # Process message with Ana
        response = await ana_agent.process_message(
            phone=phone,
            message=message_data["body"],
            media_url=message_data["media"][0]["url"] if message_data["media"] else None,
            context=session
        )

        # Send response
        await whatsapp_client.send_message(
            to=phone,
            body=response.text,
            media_urls=response.media_urls if response.media_urls else None
        )

        # Handle special actions
        if response.action == "transfer_to_reception":
            await _notify_reception(phone, session, message_data)
        elif response.action == "generate_link":
            # TODO: Integrate with Omnibees
            pass

        # Update session
        session["last_message"] = message_data["body"]
        await session_manager.save_session(phone, session)

        # Return empty response (Twilio doesn't expect content)
        return Response(content="", media_type="text/plain")

    except Exception as e:
        logger.error(
            "Error processing WhatsApp webhook",
            error=str(e),
            error_type=type(e).__name__
        )
        # Return error but don't raise to avoid Twilio retries
        return PlainTextResponse(content="Error", status_code=200)


@router.post("/status")
async def handle_status_webhook(request: Request):
    """Handle message status updates from Twilio."""
    try:
        form_data = await request.form()

        message_sid = form_data.get("MessageSid")
        status = form_data.get("MessageStatus")

        logger.info(
            "WhatsApp status update",
            message_sid=message_sid,
            status=status
        )

        # TODO: Update message status in database

        return Response(content="", media_type="text/plain")

    except Exception as e:
        logger.error("Error processing status webhook", error=str(e))
        return PlainTextResponse(content="Error", status_code=200)


@router.get("/health")
async def webhook_health():
    """Health check for WhatsApp webhook."""
    return {"status": "healthy", "webhook": "whatsapp"}


async def _notify_reception(phone: str, session: Dict, message_data: Dict):
    """Notify reception about transfer request."""
    # TODO: Implement notification system
    logger.info(
        "Transfer to reception requested",
        phone=phone,
        reason=session.get("transfer_reason", "Customer request")
    )

    # Send notification to reception
    # This could be:
    # - Internal notification system
    # - Email to reception
    # - Message to reception WhatsApp group
    # - Update in reception dashboard
    pass


@router.post("/test")
async def test_webhook(
        From: str = Form(...),
        Body: str = Form(...),
        MessageSid: str = Form(...)
):
    """Test endpoint for WhatsApp webhook."""
    try:
        # Create test message data
        message_data = {
            "From": From,
            "Body": Body,
            "MessageSid": MessageSid
        }

        # Process with Ana
        phone = From.replace("whatsapp:", "")
        response = await ana_agent.process_message(
            phone=phone,
            message=Body
        )

        # Return response for testing
        return {
            "status": "success",
            "request": message_data,
            "response": {
                "text": response.text,
                "media_urls": response.media_urls,
                "action": response.action
            }
        }

    except Exception as e:
        logger.error("Test webhook error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
