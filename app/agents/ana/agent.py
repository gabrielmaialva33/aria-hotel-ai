"""Ana Agent - Main implementation using Agno framework."""

import json
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

# Agno imports
from agno.agent import Agent
from agno.models.google import Gemini
from agno.tools.reasoning import ReasoningTools

# Local imports
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
from app.agents.ana.prompts import (
    ANA_GREETING,
    ANA_SYSTEM_PROMPT,
    AMENITIES_INFO,
    OMNIBEES_LINK_MESSAGE,
    REQUEST_INFO_TEMPLATE,
    RESTAURANT_INFO,
    TRANSFER_TO_RECEPTION,
    WIFI_INFO,
)
from app.core.logging import get_logger
from app.core.config import settings

logger = get_logger(__name__)


class AnaAgent:
    """Ana - Virtual assistant for Hotel Passarim using Agno framework."""
    
    def __init__(self):
        """Initialize Ana agent with Agno framework and tools."""
        self.name = "Ana"
        self.calculator = PricingCalculator()
        self.contexts: Dict[str, ConversationContext] = {}
        
        # Get API key (try both GEMINI_API_KEY and GOOGLE_API_KEY)
        api_key = settings.gemini_api_key or settings.google_api_key
        if not api_key:
            logger.error("No Google/Gemini API key found in settings")
            raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY must be set")
        
        logger.info(
            "Initializing Ana Agent with Agno Framework",
            model="gemini-2.0-flash",
            has_api_key=bool(api_key),
            using_vertexai=False
        )
        
        # Initialize Agno agent with Gemini Flash and reasoning
        self.agent = Agent(
            model=Gemini(
                id="gemini-2.0-flash",  # Recommended for most use-cases
                api_key=api_key,
                temperature=0.7,
                vertexai=False,  # Force Google AI Studio instead of Vertex AI
            ),
            reasoning=True,  # Enable reasoning for better responses
            instructions=ANA_SYSTEM_PROMPT + f"\n\nData atual: {datetime.now().strftime('%d/%m/%Y')} ({datetime.now().strftime('%A')})",
            tools=[
                # Reasoning tools for better problem solving
                ReasoningTools(add_instructions=True),
                # Hotel specific tools
                self.calculate_pricing,
                self.check_availability,
                self.generate_omnibees_link,
                self.transfer_to_reception,
                self.provide_hotel_info,
                self.handle_pasta_reservation,
                self.process_check_in,
                self.get_guest_account_statement,
                self.generate_payment_link,
                self.schedule_satisfaction_survey,
                self.send_marketing_campaign,
                self.update_guest_preferences,
                self.route_service_request,
                self.check_payment_status,
            ],
            # Chat history configuration
            add_history_to_messages=True,
            num_history_responses=3,
            read_chat_history=True,
            # Display configuration
            show_tool_calls=True,
            markdown=True,
        )
    
    async def process_message(
        self,
        phone: str,
        message: str,
        media_url: Optional[str] = None,
        context: Optional[Dict] = None
    ) -> AnaResponse:
        """
        Process incoming message from guest using Agno.
        
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
        
        # First message - send greeting only if it's really the first interaction
        if len(conv_context.history) == 1 and conv_context.state == "initial":
            conv_context.state = "greeting_sent"
            response = AnaResponse(text=ANA_GREETING)
            conv_context.add_message("assistant", response.text)
            # Save context to persist state
            self.contexts[phone] = conv_context
            return response
        
        try:
            # Build context for Agno
            agno_context = {
                "guest_phone": phone,
                "guest_name": conv_context.guest_name,
                "conversation_state": conv_context.state,
                "current_reservation": conv_context.current_request.model_dump() if conv_context.current_request else None,
                "preferences": conv_context.preferences,
                "media_url": media_url,
                "history": conv_context.history[-5:],  # Last 5 messages for context
                "current_date": datetime.now().strftime("%Y-%m-%d"),
                "current_datetime": datetime.now().isoformat()
            }
            
            # Process with Agno agent
            agent_response = await self.agent.arun(
                message,
                context=agno_context
            )
            
            # Extract text from RunResponse if needed
            if hasattr(agent_response, 'content'):
                response_text = agent_response.content
            elif isinstance(agent_response, str):
                response_text = agent_response
            else:
                response_text = str(agent_response)
            
            # Parse any structured actions from response
            response = self._parse_agent_response(response_text)
            
            # Update context
            conv_context.add_message("assistant", response.text)
            conv_context.state = "active"  # Update state after successful interaction
            
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
    
    def _parse_agent_response(self, response_text: str) -> AnaResponse:
        """Parse agent response for structured actions."""
        # Default response
        response = AnaResponse(text=response_text)
        
        # Check for special markers in response
        if "[[TRANSFER_TO_RECEPTION]]" in response_text:
            response.needs_human = True
            response.action = "transfer_to_reception"
            response.text = response_text.replace("[[TRANSFER_TO_RECEPTION]]", "").strip()
        
        if "[[OMNIBEES_LINK:" in response_text:
            # Extract link
            start = response_text.find("[[OMNIBEES_LINK:") + len("[[OMNIBEES_LINK:")
            end = response_text.find("]]", start)
            if end > start:
                link = response_text[start:end]
                response.metadata["omnibees_link"] = link
                response.text = response_text[:response_text.find("[[OMNIBEES_LINK:")] + response_text[end + 2:]
        
        if "[[PAYMENT_LINK:" in response_text:
            # Extract payment link
            start = response_text.find("[[PAYMENT_LINK:") + len("[[PAYMENT_LINK:")
            end = response_text.find("]]", start)
            if end > start:
                link = response_text[start:end]
                response.metadata["payment_link"] = link
                response.text = response_text[:response_text.find("[[PAYMENT_LINK:")] + response_text[end + 2:]
        
        return response
    
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
    
    # Tool implementations for Agno
    
    async def calculate_pricing(
        self,
        check_in: str,
        check_out: str, 
        adults: int,
        children: List[int] = None,
        room_type: str = None,
        meal_plan: str = None
    ) -> str:
        """
        Calculate and present pricing options for hotel stay.
        
        Args:
            check_in: Check-in date (YYYY-MM-DD or DD/MM/YYYY or "hoje" or "amanhã")
            check_out: Check-out date (YYYY-MM-DD or DD/MM/YYYY or "hoje" or "amanhã")
            adults: Number of adults
            children: List of children ages
            room_type: Optional room type preference (terreo or superior)
            meal_plan: Optional meal plan preference
            
        Returns:
            Formatted pricing message with all options
        """
        try:
            # Parse dates - handle different formats
            check_in_date = self._parse_flexible_date(check_in)
            check_out_date = self._parse_flexible_date(check_out)
            
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
                    "[[TRANSFER_TO_RECEPTION]] Vou transferir para a recepção finalizar sua reserva!"
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
        """
        Check room availability for given dates.
        
        Args:
            check_in: Check-in date (YYYY-MM-DD)
            check_out: Check-out date (YYYY-MM-DD)
            room_type: Optional specific room type
            
        Returns:
            Availability status message
        """
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
        """
        Generate personalized Omnibees link for reservation.
        
        Args:
            check_in: Check-in date
            check_out: Check-out date
            adults: Number of adults
            children: Number of children
            
        Returns:
            Message with Omnibees link
        """
        # TODO: Integrate with Omnibees API
        # For now, generate a mock link
        base_url = "https://booking.omnibees.com/hotelpassarim"
        params = f"?checkin={check_in}&checkout={check_out}&adults={adults}&children={children}"
        
        link = base_url + params
        
        return f"[[OMNIBEES_LINK:{link}]] " + OMNIBEES_LINK_MESSAGE.format(link=link)
    
    async def transfer_to_reception(self, reason: str) -> str:
        """
        Transfer conversation to human reception staff.
        
        Args:
            reason: Reason for transfer
            
        Returns:
            Transfer message
        """
        return "[[TRANSFER_TO_RECEPTION]] " + TRANSFER_TO_RECEPTION.format(reason=reason)
    
    async def provide_hotel_info(self, info_type: str) -> str:
        """
        Provide specific hotel information.
        
        Args:
            info_type: Type of information requested (wifi, restaurant, amenities, etc)
            
        Returns:
            Requested hotel information
        """
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
        """
        Handle reservation for pasta rotation dinner.
        
        Args:
            date: Reservation date
            adults: Number of adults
            children: Number of children
            
        Returns:
            Pasta rotation reservation details
        """
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
    
    # New tools for additional features
    
    async def process_check_in(
        self,
        guest_phone: str,
        reservation_code: str,
        arrival_time: Optional[str] = None
    ) -> str:
        """
        Process digital check-in for guest.
        
        Args:
            guest_phone: Guest's phone number
            reservation_code: Reservation confirmation code
            arrival_time: Expected arrival time
            
        Returns:
            Check-in confirmation or form link
        """
        # TODO: Integrate with PMS to validate reservation
        # For now, return check-in form link
        check_in_link = f"{settings.webhook_base_url}/check-in/{reservation_code}"
        
        return (
            f"📋 *Check-in Digital*\n\n"
            f"Para agilizar sua chegada, complete o check-in online:\n"
            f"🔗 {check_in_link}\n\n"
            f"✅ Benefícios:\n"
            f"• Chegada mais rápida\n"
            f"• Escolha de quarto (sujeito à disponibilidade)\n"
            f"• Documentação digital\n\n"
            f"Horário previsto de chegada: {arrival_time or 'A definir'}"
        )
    
    async def get_guest_account_statement(
        self,
        guest_phone: str,
        room_number: Optional[str] = None
    ) -> str:
        """
        Get current account statement for guest.
        
        Args:
            guest_phone: Guest's phone number
            room_number: Optional room number
            
        Returns:
            Account statement details
        """
        # TODO: Integrate with PMS for real data
        # Mock data for now
        return (
            f"📊 *Extrato da Conta - Quarto {room_number or '101'}*\n\n"
            f"📅 Período: 10/01 a 12/01/2025\n\n"
            f"*Lançamentos:*\n"
            f"• Diárias (2x): R$ 580,00\n"
            f"• Restaurante: R$ 127,50\n"
            f"• Frigobar: R$ 45,00\n"
            f"• Lavanderia: R$ 35,00\n\n"
            f"💰 *Total: R$ 787,50*\n\n"
            f"💳 Pagamentos realizados: R$ 580,00\n"
            f"📍 Saldo a pagar: R$ 207,50"
        )
    
    async def generate_payment_link(
        self,
        amount: float,
        description: str,
        guest_phone: str
    ) -> str:
        """
        Generate payment link for services or reservations.
        
        Args:
            amount: Payment amount
            description: Payment description
            guest_phone: Guest's phone number
            
        Returns:
            Payment link and instructions
        """
        # TODO: Integrate with payment gateway
        # Mock payment link for now
        payment_id = f"PAY{datetime.now().strftime('%Y%m%d%H%M%S')}"
        payment_link = f"{settings.webhook_base_url}/payment/{payment_id}"
        
        return (
            f"💳 *Link de Pagamento*\n\n"
            f"📝 Descrição: {description}\n"
            f"💰 Valor: R$ {amount:.2f}\n\n"
            f"🔗 Link para pagamento:\n"
            f"{payment_link}\n\n"
            f"[[PAYMENT_LINK:{payment_link}]] "
            f"✅ Aceitamos:\n"
            f"• PIX (desconto de 5%)\n"
            f"• Cartão de crédito/débito\n"
            f"• Transferência bancária"
        )
    
    async def schedule_satisfaction_survey(
        self,
        guest_phone: str,
        checkout_date: str
    ) -> str:
        """
        Schedule post-stay satisfaction survey.
        
        Args:
            guest_phone: Guest's phone number
            checkout_date: Guest's checkout date
            
        Returns:
            Survey scheduling confirmation
        """
        # TODO: Integrate with survey system
        survey_date = datetime.strptime(checkout_date, "%Y-%m-%d") + timedelta(days=1)
        
        return (
            f"📋 *Pesquisa de Satisfação Agendada*\n\n"
            f"Valorizamos sua opinião! 💝\n\n"
            f"Enviaremos uma breve pesquisa no dia {survey_date.strftime('%d/%m/%Y')} "
            f"para conhecer sua experiência conosco.\n\n"
            f"Sua avaliação nos ajuda a melhorar continuamente! ⭐"
        )
    
    async def send_marketing_campaign(
        self,
        campaign_type: str,
        target_audience: Optional[str] = None
    ) -> str:
        """
        Send marketing campaign to guests.
        
        Args:
            campaign_type: Type of campaign (seasonal, promotional, etc)
            target_audience: Optional audience filter
            
        Returns:
            Campaign details
        """
        # TODO: Integrate with marketing automation
        return (
            f"📣 *Campanha de Marketing: {campaign_type}*\n\n"
            f"🎯 Público-alvo: {target_audience or 'Todos os hóspedes'}\n\n"
            f"📱 Canais:\n"
            f"• WhatsApp\n"
            f"• Email\n"
            f"• SMS\n\n"
            f"✅ Campanha configurada com sucesso!"
        )
    
    async def update_guest_preferences(
        self,
        guest_phone: str,
        preferences: Dict[str, Any]
    ) -> str:
        """
        Update guest preferences for personalization.
        
        Args:
            guest_phone: Guest's phone number
            preferences: Dictionary of preferences
            
        Returns:
            Confirmation message
        """
        # Update context preferences
        if guest_phone in self.contexts:
            self.contexts[guest_phone].preferences.update(preferences)
        
        pref_list = "\n".join([f"• {k}: {v}" for k, v in preferences.items()])
        
        return (
            f"✅ *Preferências Atualizadas*\n\n"
            f"Registramos suas preferências:\n"
            f"{pref_list}\n\n"
            f"Isso nos ajuda a personalizar sua experiência! 🌟"
        )
    
    async def route_service_request(
        self,
        service_type: str,
        details: str,
        room_number: str
    ) -> str:
        """
        Route service requests to appropriate department.
        
        Args:
            service_type: Type of service (housekeeping, maintenance, etc)
            details: Request details
            room_number: Guest's room number
            
        Returns:
            Service request confirmation
        """
        # Map service types to departments
        department_map = {
            "limpeza": "Governança",
            "manutenção": "Manutenção",
            "restaurante": "Restaurante",
            "lavanderia": "Lavanderia",
            "recepção": "Recepção"
        }
        
        department = department_map.get(service_type.lower(), "Recepção")
        request_id = f"SR{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        return (
            f"📋 *Solicitação de Serviço #{request_id}*\n\n"
            f"🏨 Quarto: {room_number}\n"
            f"🔧 Tipo: {service_type}\n"
            f"📝 Detalhes: {details}\n\n"
            f"✅ Encaminhado para: {department}\n"
            f"⏱️ Tempo estimado: 15-30 minutos\n\n"
            f"Acompanhe o status enviando: STATUS {request_id}"
        )
    
    async def check_payment_status(
        self,
        payment_id: str
    ) -> str:
        """
        Check status of a payment.
        
        Args:
            payment_id: Payment identifier
            
        Returns:
            Payment status details
        """
        # TODO: Integrate with payment gateway
        # Mock status for now
        return (
            f"💳 *Status do Pagamento {payment_id}*\n\n"
            f"✅ Status: Aprovado\n"
            f"💰 Valor: R$ 787,50\n"
            f"📅 Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
            f"🏦 Forma: PIX\n\n"
            f"Obrigado pelo pagamento! 😊"
        )

    # Utility methods
    
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
    
    def _parse_flexible_date(self, date_str: str) -> date:
        """Parse date from various formats including 'hoje' and 'amanhã'."""
        date_str = date_str.strip().lower()
        
        # Handle special keywords
        if date_str in ["hoje", "today"]:
            return datetime.now().date()
        elif date_str in ["amanhã", "amanha", "tomorrow"]:
            return datetime.now().date() + timedelta(days=1)
        
        # Try parsing as YYYY-MM-DD
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            pass
        
        # Try parsing as DD/MM/YYYY
        try:
            return datetime.strptime(date_str, "%d/%m/%Y").date()
        except ValueError:
            pass
        
        # Try parsing as DD-MM-YYYY
        try:
            return datetime.strptime(date_str, "%d-%m-%Y").date()
        except ValueError:
            pass
        
        # Try the original parse_date method
        return self._parse_date(date_str)
