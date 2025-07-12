"""Ana Agent - Main implementation using Agno framework."""

import json
from datetime import date, datetime
from typing import Dict, List, Optional

from agno import Agent, Tool
from pydantic import BaseModel

from aria.agents.ana.calculator import PricingCalculator
from aria.agents.ana.knowledge_base import (
    HOTEL_INFO,
    PASTA_ROTATION,
    is_holiday_period,
)
from aria.agents.ana.models import (
    AnaResponse,
    ConversationContext,
    MealPlan,
    ReservationRequest,
    RoomType,
)
from aria.agents.ana.prompts import (
    ANA_GREETING,
    ANA_SYSTEM_PROMPT,
    AMENITIES_INFO,
    OMNIBEES_LINK_MESSAGE,
    REQUEST_INFO_TEMPLATE,
    RESTAURANT_INFO,
    TRANSFER_TO_RECEPTION,
    WIFI_INFO,
)
from aria.core.logging import get_logger

logger = get_logger(__name__)


class AnaAgent(Agent):
    """Ana - Virtual assistant for Hotel Passarim."""
    
    def __init__(self):
        """Initialize Ana agent with tools and configuration."""
        super().__init__(
            name="Ana",
            system_prompt=ANA_SYSTEM_PROMPT,
            model="gpt-4-turbo",
            temperature=0.7,
            tools=[
                self.calculate_pricing,
                self.check_availability,
                self.generate_omnibees_link,
                self.transfer_to_reception,
                self.provide_hotel_info,
                self.handle_pasta_reservation,
            ]
        )
        self.calculator = PricingCalculator()
        self.contexts: Dict[str, ConversationContext] = {}
    
    async def process_message(
        self,
        phone: str,
        message: str,
        media_url: Optional[str] = None,
        context: Optional[Dict] = None
    ) -> AnaResponse:
        """
        Process incoming message from guest.
        
        Args:
            phone: Guest's phone number
            message: Text message content
            media_url: URL of attached media (if any)
            context: Additional context from session
            
        Returns:
            AnaResponse with text and optional media/actions
        """
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
        
        # Process with LLM
        try:
            # Build messages for LLM
            messages = self._build_messages(conv_context)
            
            # Get response from LLM with tools
            llm_response = await self.complete(
                messages=messages,
                context={
                    "phone": phone,
                    "conversation_context": conv_context.model_dump()
                }
            )
            
            # Parse response
            response = self._parse_llm_response(llm_response)
            
            # Update context
            conv_context.add_message("assistant", response.text)
            
            # Save context
            self.contexts[phone] = conv_context
            
            return response
            
        except Exception as e:
            logger.error(
                "Error processing message",
                phone=phone,
                error=str(e)
            )
            return AnaResponse(
                text="Desculpe, tive um problema ao processar sua mensagem. "
                     "Vou transferir você para nossa recepção. Um momento! 😊",
                needs_human=True,
                action="transfer_to_reception"
            )
    
    def _get_conversation_context(
        self,
        phone: str,
        context: Optional[Dict] = None
    ) -> ConversationContext:
        """Get or create conversation context for a phone number."""
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
    
    def _build_messages(self, context: ConversationContext) -> List[Dict]:
        """Build messages array for LLM from conversation history."""
        messages = []
        
        # Add conversation history
        for msg in context.history:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        return messages
    
    def _parse_llm_response(self, llm_response: Dict) -> AnaResponse:
        """Parse LLM response into AnaResponse object."""
        # Extract content and tool calls
        content = llm_response.get("content", "")
        tool_calls = llm_response.get("tool_calls", [])
        
        response = AnaResponse(text=content)
        
        # Process tool calls
        for tool_call in tool_calls:
            tool_name = tool_call.get("name")
            
            if tool_name == "transfer_to_reception":
                response.needs_human = True
                response.action = "transfer_to_reception"
            elif tool_name == "generate_omnibees_link":
                response.action = "generate_link"
                response.metadata = tool_call.get("arguments", {})
            
        return response
    
    # Tool implementations
    
    @Tool(description="Calculate accommodation pricing based on dates and guests")
    async def calculate_pricing(
        self,
        check_in: str,
        check_out: str, 
        adults: int,
        children: List[int] = None,
        room_type: str = None,
        meal_plan: str = None
    ) -> str:
        """Calculate and present pricing options."""
        try:
            # Parse dates
            check_in_date = datetime.strptime(check_in, "%Y-%m-%d").date()
            check_out_date = datetime.strptime(check_out, "%Y-%m-%d").date()
            
            # Create reservation request
            request = ReservationRequest(
                check_in=check_in_date,
                check_out=check_out_date,
                adults=adults,
                children=children or [],
                room_type=RoomType(room_type) if room_type else None,
                meal_plan=MealPlan(meal_plan) if meal_plan else None,
                is_holiday=bool(is_holiday_period(check_in_date, check_out_date))
            )
            
            # Check if needs reception
            if request.requires_reception():
                return (
                    "Esta reserva precisa ser finalizada pela recepção devido a:\n"
                    "- Mais de 4 pessoas no mesmo quarto\n"
                    "- Crianças acima de 5 anos (precisam cama extra)\n"
                    "- Pacotes com refeições incluídas\n\n"
                    "Vou transferir para a recepção finalizar sua reserva!"
                )
            
            # Calculate pricing
            prices = self.calculator.calculate(request)
            
            # Format response
            return self.calculator.format_pricing_message(prices)
            
        except Exception as e:
            logger.error("Error calculating pricing", error=str(e))
            return "Desculpe, não consegui calcular os valores. Por favor, tente novamente."
    
    @Tool(description="Check room availability for given dates")
    async def check_availability(
        self,
        check_in: str,
        check_out: str,
        room_type: Optional[str] = None
    ) -> str:
        """Check room availability."""
        # TODO: Integrate with PMS or local database
        # For now, return mock availability
        return (
            f"✅ Temos disponibilidade para o período de {check_in} a {check_out}!\n\n"
            "Posso calcular os valores para sua hospedagem?"
        )
    
    @Tool(description="Generate Omnibees reservation link")
    async def generate_omnibees_link(
        self,
        check_in: str,
        check_out: str,
        adults: int,
        children: int = 0
    ) -> str:
        """Generate personalized Omnibees link for reservation."""
        # TODO: Integrate with Omnibees API
        # For now, generate a mock link
        base_url = "https://booking.omnibees.com/hotelpassarim"
        params = f"?checkin={check_in}&checkout={check_out}&adults={adults}&children={children}"
        
        link = base_url + params
        
        return OMNIBEES_LINK_MESSAGE.format(link=link)
    
    @Tool(description="Transfer conversation to human reception staff")
    async def transfer_to_reception(self, reason: str) -> str:
        """Transfer to reception with specific reason."""
        return TRANSFER_TO_RECEPTION.format(reason=reason)
    
    @Tool(description="Provide hotel information like WiFi, restaurant hours, amenities")
    async def provide_hotel_info(self, info_type: str) -> str:
        """Provide specific hotel information."""
        info_type = info_type.lower()
        
        if "wifi" in info_type or "internet" in info_type:
            return WIFI_INFO
        elif "restaurante" in info_type or "refeição" in info_type:
            return RESTAURANT_INFO
        elif "lazer" in info_type or "estrutura" in info_type:
            return AMENITIES_INFO
        elif "check" in info_type:
            return (
                f"🕐 *Horários:*\n"
                f"Check-in: a partir das {HOTEL_INFO['check_in_time']}\n"
                f"Check-out: até às {HOTEL_INFO['check_out_time']}"
            )
        else:
            return (
                f"📍 *{HOTEL_INFO['name']}*\n"
                f"📍 Localização: {HOTEL_INFO['location']}\n"
                f"📞 WhatsApp: {HOTEL_INFO['whatsapp']}\n"
                f"🌐 Site: {HOTEL_INFO['website']}"
            )
    
    @Tool(description="Handle pasta rotation reservation")
    async def handle_pasta_reservation(
        self,
        date: str,
        adults: int,
        children: int = 0
    ) -> str:
        """Handle reservation for pasta rotation."""
        pasta_info = PASTA_ROTATION["friday_saturday"]
        
        total_people = adults + children
        adult_price = adults * pasta_info["price_adult"]
        child_price = children * pasta_info["price_child"]
        total_price = adult_price + child_price
        prepayment = total_people * pasta_info["prepayment"]
        
        return (
            f"🍝 *Rodízio de Massas - {date}*\n\n"
            f"👥 {adults} adulto(s) e {children} criança(s)\n"
            f"💰 Valor total: R$ {total_price:.2f}\n\n"
            f"⚠️ *Importante:*\n"
            f"1. Faça sua reserva em: www.hotelpassarim.com.br/reservas\n"
            f"2. Após a reserva, envie R$ {prepayment:.2f} via PIX para garantir sua mesa\n"
            f"3. Chave PIX: {HOTEL_INFO['phone']}\n\n"
            f"O rodízio inclui antepastos, 4 tipos de ravioli, 2 tipos de rondelli "
            f"e massas com molhos artesanais! 😋"
        )
