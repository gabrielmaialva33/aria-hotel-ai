"""Ana Agent implementation using Google Gemini."""

import json
from datetime import datetime
from typing import Dict, List, Optional

import google.generativeai as genai

from app.agents.ana.calculator import PricingCalculator
from app.agents.ana.knowledge_base import (
    HOTEL_INFO,
    PASTA_ROTATION,
    is_holiday_period,
)
from app.agents.ana.models import (
    AnaResponse,
    ConversationContext,
    MealPlan,
    ReservationRequest,
    RoomType,
)
from app.agents.ana.prompts import ANA_GREETING, ANA_SYSTEM_PROMPT
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class AnaGeminiAgent:
    """Ana agent using Google Gemini."""
    
    def __init__(self):
        """Initialize Ana agent with Gemini."""
        # Configure Gemini
        if settings.gemini_api_key:
            genai.configure(api_key=settings.gemini_api_key)
            self.model = genai.GenerativeModel(
                'gemini-1.5-flash',
                system_instruction=ANA_SYSTEM_PROMPT
            )
        else:
            logger.warning("Gemini API key not configured")
            self.model = None
            
        self.calculator = PricingCalculator()
        self.contexts: Dict[str, ConversationContext] = {}
        
        logger.info("Ana Gemini Agent initialized")
    
    async def process_message(
        self,
        phone: str,
        message: str,
        media_url: Optional[str] = None,
        context: Optional[Dict] = None
    ) -> AnaResponse:
        """Process incoming message from guest."""
        # Get or create conversation context
        conv_context = self._get_conversation_context(phone, context)
        
        # Add message to history
        conv_context.add_message("user", message)
        
        # First message - send greeting
        if len(conv_context.history) == 1:
            conv_context.state = "greeting"
            response = AnaResponse(text=ANA_GREETING)
            conv_context.add_message("assistant", response.text)
            return response
        
        # Process with Gemini if available
        if self.model:
            try:
                response_text = await self._process_with_gemini(conv_context, message)
                response = self._parse_response(response_text, conv_context)
                
                # Update context
                conv_context.add_message("assistant", response.text)
                self.contexts[phone] = conv_context
                
                return response
                
            except Exception as e:
                logger.error(
                    "Error processing with Gemini",
                    phone=phone,
                    error=str(e)
                )
        
        # Fallback response
        return AnaResponse(
            text="Desculpe, estou com dificuldades técnicas. "
                 "Por favor, ligue para nossa recepção: (15) 3542-0000",
            needs_human=True
        )
    
    async def _process_with_gemini(
        self,
        context: ConversationContext,
        message: str
    ) -> str:
        """Process message with Gemini model."""
        # Build conversation history
        history = []
        for msg in context.history[:-1]:  # Exclude the last user message
            history.append({
                "role": "user" if msg["role"] == "user" else "model",
                "parts": [msg["content"]]
            })
        
        # Start chat with history
        chat = self.model.start_chat(history=history)
        
        # Add context about current state
        context_prompt = f"""
        Contexto atual:
        - Estado da conversa: {context.state}
        - Nome do hóspede: {context.guest_name or 'Não informado'}
        - Telefone: {context.guest_phone}
        
        Informações do Hotel:
        - Check-in: {HOTEL_INFO['check_in_time']}
        - Check-out: {HOTEL_INFO['check_out_time']}
        - WhatsApp: {HOTEL_INFO['whatsapp']}
        
        Mensagem do hóspede: {message}
        
        Lembre-se de seguir as diretrizes de atendimento e ser sempre acolhedora!
        """
        
        # Get response
        response = chat.send_message(context_prompt)
        return response.text
    
    def _parse_response(self, response_text: str, context: ConversationContext) -> AnaResponse:
        """Parse Gemini response into AnaResponse."""
        response = AnaResponse(text=response_text)
        
        # Check for specific keywords/actions in response
        lower_text = response_text.lower()
        
        if "transferir" in lower_text and "recepção" in lower_text:
            response.needs_human = True
            response.action = "transfer_to_reception"
        elif "gerar link" in lower_text or "link para reserva" in lower_text:
            response.action = "generate_link"
        elif any(word in lower_text for word in ["valor", "preço", "custo", "diária"]):
            context.state = "pricing"
        elif any(word in lower_text for word in ["reserva", "disponibilidade"]):
            context.state = "booking"
        
        return response
    
    def _get_conversation_context(
        self,
        phone: str,
        context: Optional[Dict] = None
    ) -> ConversationContext:
        """Get or create conversation context."""
        if phone in self.contexts:
            return self.contexts[phone]
        
        # Create new context
        conv_context = ConversationContext(
            guest_phone=phone,
            guest_name=context.get("name") if context else None,
            preferences=context.get("preferences", {}) if context else {}
        )
        
        self.contexts[phone] = conv_context
        return conv_context
    
    # Tool-like methods for Gemini to use via prompting
    
    def calculate_pricing(
        self,
        check_in: str,
        check_out: str,
        adults: int,
        children: List[int] = None
    ) -> str:
        """Calculate accommodation pricing."""
        try:
            # Parse dates
            from datetime import datetime
            check_in_date = datetime.strptime(check_in, "%Y-%m-%d").date()
            check_out_date = datetime.strptime(check_out, "%Y-%m-%d").date()
            
            # Create request
            request = ReservationRequest(
                check_in=check_in_date,
                check_out=check_out_date,
                adults=adults,
                children=children or [],
                is_holiday=bool(is_holiday_period(check_in_date, check_out_date))
            )
            
            # Calculate
            prices = self.calculator.calculate(request)
            
            # Format response
            return self.calculator.format_pricing_message(prices)
            
        except Exception as e:
            logger.error("Error calculating pricing", error=str(e))
            return "Desculpe, não consegui calcular os valores. Por favor, tente novamente."
