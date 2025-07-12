"""Ana Agent - Main implementation."""

import json
from datetime import date, datetime
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass

# Try to import Google Generative AI
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logger = None

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
from aria.core.config import settings

logger = get_logger(__name__)


@dataclass
class Tool:
    """Simple tool definition."""
    name: str
    description: str
    function: Callable


class AnaAgent:
    """Ana - Virtual assistant for Hotel Passarim."""
    
    def __init__(self):
        """Initialize Ana agent with tools and configuration."""
        self.name = "Ana"
        self.system_prompt = ANA_SYSTEM_PROMPT
        self.calculator = PricingCalculator()
        self.contexts: Dict[str, ConversationContext] = {}
        
        # Register tools
        self.tools = {
            "calculate_pricing": Tool(
                name="calculate_pricing",
                description="Calculate accommodation pricing based on dates and guests",
                function=self.calculate_pricing
            ),
            "check_availability": Tool(
                name="check_availability", 
                description="Check room availability for given dates",
                function=self.check_availability
            ),
            "generate_omnibees_link": Tool(
                name="generate_omnibees_link",
                description="Generate Omnibees reservation link",
                function=self.generate_omnibees_link
            ),
            "transfer_to_reception": Tool(
                name="transfer_to_reception",
                description="Transfer conversation to human reception staff",
                function=self.transfer_to_reception
            ),
            "provide_hotel_info": Tool(
                name="provide_hotel_info",
                description="Provide hotel information like WiFi, restaurant hours, amenities",
                function=self.provide_hotel_info
            ),
            "handle_pasta_reservation": Tool(
                name="handle_pasta_reservation",
                description="Handle pasta rotation reservation",
                function=self.handle_pasta_reservation
            ),
        }
    
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
        
        # Process message with simple intent detection
        try:
            response = await self._process_with_intent(message, conv_context)
            
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
    
    async def _process_with_intent(
        self, 
        message: str, 
        context: ConversationContext
    ) -> AnaResponse:
        """Process message based on detected intent."""
        message_lower = message.lower()
        
        # Check for greetings
        if any(word in message_lower for word in ["olá", "oi", "bom dia", "boa tarde", "boa noite"]):
            return AnaResponse(text=ANA_GREETING)
        
        # Check for WiFi info
        if any(word in message_lower for word in ["wifi", "internet", "senha"]):
            return AnaResponse(text=WIFI_INFO)
        
        # Check for restaurant info
        if any(word in message_lower for word in ["restaurante", "almoço", "jantar", "café da manhã", "refeição"]):
            return AnaResponse(text=RESTAURANT_INFO)
        
        # Check for amenities info
        if any(word in message_lower for word in ["lazer", "piscina", "estrutura", "atividades"]):
            return AnaResponse(text=AMENITIES_INFO)
        
        # Check for reservation intent
        if any(word in message_lower for word in ["reserva", "reservar", "hospedagem", "quarto", "valores", "preço"]):
            # Check if we have dates in the message
            if any(char.isdigit() for char in message):
                # Try to extract dates and calculate
                return await self._handle_pricing_request(message, context)
            else:
                return AnaResponse(text=REQUEST_INFO_TEMPLATE)
        
        # Check for pasta rotation
        if any(word in message_lower for word in ["rodízio", "massa", "pasta"]):
            return AnaResponse(
                text="🍝 Nosso Rodízio de Massas acontece toda sexta e sábado, das 19h às 22h!\n\n"
                     "Adultos: R$ 74,90 | Crianças (5-12): R$ 35,90\n\n"
                     "Reserva obrigatória em: www.hotelpassarim.com.br/reservas"
            )
        
        # Default: Ask what they need
        return AnaResponse(
            text="Como posso ajudar você? Posso fornecer informações sobre:\n"
                 "• Valores de hospedagem\n"
                 "• Disponibilidade de quartos\n"
                 "• Estrutura e lazer\n"
                 "• Horários do restaurante\n"
                 "• Rodízio de massas\n"
                 "• WiFi e outras comodidades"
        )
    
    async def _handle_pricing_request(
        self, 
        message: str, 
        context: ConversationContext
    ) -> AnaResponse:
        """Handle pricing calculation request."""
        # Simple date extraction (this would be more sophisticated in production)
        import re
        
        # Try to find dates in format DD/MM/YYYY or DD-MM-YYYY
        date_pattern = r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})'
        dates = re.findall(date_pattern, message)
        
        # Try to find number of adults
        adults_pattern = r'(\d+)\s*(?:adult|pessoa|pax)'
        adults_match = re.search(adults_pattern, message.lower())
        adults = int(adults_match.group(1)) if adults_match else 2
        
        # Try to find children
        children_pattern = r'(\d+)\s*(?:criança|filho)'
        children_match = re.search(children_pattern, message.lower())
        children_count = int(children_match.group(1)) if children_match else 0
        
        if len(dates) >= 2:
            try:
                # Parse dates
                check_in = self._parse_date(dates[0])
                check_out = self._parse_date(dates[1])
                
                # Calculate pricing
                result = await self.calculate_pricing(
                    check_in=check_in.strftime("%Y-%m-%d"),
                    check_out=check_out.strftime("%Y-%m-%d"),
                    adults=adults,
                    children=[]  # Simplified for now
                )
                
                return AnaResponse(text=result)
                
            except Exception as e:
                logger.error("Error parsing dates", error=str(e))
                return AnaResponse(text=REQUEST_INFO_TEMPLATE)
        else:
            return AnaResponse(text=REQUEST_INFO_TEMPLATE)
    
    def _parse_date(self, date_str: str) -> date:
        """Parse date from string."""
        for sep in ['/', '-']:
            if sep in date_str:
                parts = date_str.split(sep)
                if len(parts) == 3:
                    day, month, year = parts
                    if len(year) == 2:
                        year = f"20{year}"
                    return date(int(year), int(month), int(day))
        raise ValueError(f"Could not parse date: {date_str}")
    
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
    
    # Tool implementations
    
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
                    "• Mais de 4 pessoas no mesmo quarto\n"
                    "• Crianças acima de 5 anos (precisam cama extra)\n"
                    "• Pacotes com refeições incluídas\n\n"
                    "Vou transferir para a recepção finalizar sua reserva!"
                )
            
            # Calculate pricing
            prices = self.calculator.calculate(request)
            
            # Format response
            return self.calculator.format_pricing_message(prices)
            
        except Exception as e:
            logger.error("Error calculating pricing", error=str(e))
            return "Desculpe, não consegui calcular os valores. Por favor, tente novamente."
    
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
    
    async def transfer_to_reception(self, reason: str) -> str:
        """Transfer to reception with specific reason."""
        return TRANSFER_TO_RECEPTION.format(reason=reason)
    
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
