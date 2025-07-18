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
from app.agents.ana.proactive_concierge import ProactiveConcierge
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
from app.core.utils import parse_meal_plan
from app.core.reservations import get_reservation_manager
from app.core.reservations import get_reservation_manager

logger = get_logger(__name__)


class AnaAgent:
    """Ana - Virtual assistant for Hotel Passarim using Agno framework."""
    
    def __init__(self):
        """Initialize Ana agent with Agno framework and tools."""
        self.name = "Ana"
        self.calculator = PricingCalculator()
        self.proactive_concierge = ProactiveConcierge()
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
                api_key=api_key,  # Pass API key explicitly
                temperature=0.7,
                vertexai=settings.google_genai_use_vertexai,
                project_id=settings.google_cloud_project,
                location=settings.google_cloud_location,
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
                self.get_proactive_suggestions,
                self.create_reservation,
                self.get_reservation_details,
                self.generate_payment_pix,
                self.confirm_guest_data,
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
        
        # First message - send greeting only if it's not a direct query
        is_direct_query = any(keyword in message.lower() for keyword in [
            "diaria", "diária", "preço", "valor", "quanto custa", "reserva", 
            "hospedagem", "quarto", "hoje", "amanhã", "disponibilidade"
        ])
        
        # Also check if message contains date references
        has_date_reference = any(keyword in message.lower() for keyword in [
            "hoje", "amanhã", "amanha", "semana", "fim de semana", "janeiro", "fevereiro"
        ])
        
        if len(conv_context.history) == 1 and conv_context.state == "initial" and not (is_direct_query or has_date_reference):
            conv_context.state = "greeting_sent"
            response = AnaResponse(text=ANA_GREETING)
            conv_context.add_message("assistant", response.text)
            # Save context to persist state
            self.contexts[phone] = conv_context
            return response
        
        try:
            # Check for simple acknowledgments
            simple_acks = ["ok", "sim", "certo", "entendi", "beleza", "blz", "ta", "tá"]
            if message.lower().strip() in simple_acks:
                # Create an appropriate response based on context
                if conv_context.current_request:
                    response_text = (
                        "Perfeito! 🎉 Sua reserva está quase pronta!\n\n"
                        "Para finalizar, você pode:\n"
                        "1. Me enviar seus dados pessoais para o cadastro\n"
                        "2. Fazer a reserva online em nosso site\n"
                        "3. Ligar para nossa recepção: (15) 3542-0000\n\n"
                        "Como prefere prosseguir? 😊"
                    )
                else:
                    response_text = "Legal! 😊 Posso ajudar com mais alguma coisa? Temos informações sobre o hotel, restaurante, lazer e muito mais!"
                
                response = AnaResponse(text=response_text)
                conv_context.add_message("assistant", response.text)
                self.contexts[phone] = conv_context
                return response
            
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
        # Ensure we have a valid response text
        if not response_text or not str(response_text).strip():
            response_text = "Entendi! Como posso ajudar você?"
        
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
        
        if "[[QUICK_REPLIES:" in response_text:
            # Extract quick replies
            start = response_text.find("[[QUICK_REPLIES:") + len("[[QUICK_REPLIES:")
            end = response_text.find("]]", start)
            if end > start:
                options_str = response_text[start:end]
                response.quick_replies = [opt.strip() for opt in options_str.split(",")]
                response.text = response_text[:response_text.find("[[QUICK_REPLIES:")] + response_text[end + 2:]

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
            parsed_meal_plan = parse_meal_plan(meal_plan) if meal_plan else None
            request = ReservationRequest(
                check_in=check_in_date,
                check_out=check_out_date,
                adults=adults,
                children=children or [],
                room_type=RoomType(room_type) if room_type else None,
                meal_plan=parsed_meal_plan,
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

    async def get_proactive_suggestions(self, guest_phone: str) -> str:
        """
        Get proactive suggestions for the guest.

        Args:
            guest_phone: Guest's phone number

        Returns:
            Formatted message with suggestions
        """
        context = self._get_conversation_context(guest_phone)
        suggestions = await self.proactive_concierge.get_suggestions(context)

        if not suggestions:
            return ""

        message = "Vi que você pode se interessar por:\n\n"
        for suggestion in suggestions:
            message += f"*{suggestion['title']}*\n"
            message += f"{suggestion['text']}\n"
            if suggestion.get('quick_replies'):
                message += "[[QUICK_REPLIES:"
                message += ", ".join(suggestion['quick_replies'])
                message += "]]\n"
            message += "\n"

        return message.strip()

    async def create_reservation(
        self,
        check_in: str,
        check_out: str,
        adults: int,
        children: List[int] = None,
        room_type: str = None,
        meal_plan: str = None,
        guest_name: str = None,
        guest_phone: str = None,
    ) -> str:
        """
        Cria uma reserva real no sistema e retorna o código de confirmação.

        Args:
            check_in: Data de check-in (YYYY-MM-DD)
            check_out: Data de check-out (YYYY-MM-DD)
            adults: Número de adultos
            children: Lista de idades das crianças
            room_type: Tipo de quarto preferido
            meal_plan: Plano de refeições
            guest_name: Nome do hóspede
            guest_phone: Telefone do hóspede

        Returns:
            Mensagem de confirmação com detalhes da reserva
        """
        try:
            # Parse das datas
            check_in_date = self._parse_flexible_date(check_in)
            check_out_date = self._parse_flexible_date(check_out)
            
            # Gera código único de reserva
            reservation_code = f"HP-{datetime.now().strftime('%Y%m%d')}-{datetime.now().strftime('%H%M%S')}"
            
            # Calcula o total da reserva
            parsed_meal_plan = parse_meal_plan(meal_plan) if meal_plan else MealPlan.CAFE_DA_MANHA
            request = ReservationRequest(
                check_in=check_in_date,
                check_out=check_out_date,
                adults=adults,
                children=children or [],
                room_type=RoomType(room_type) if room_type else RoomType.TERREO,
                meal_plan=parsed_meal_plan,
                is_holiday=bool(is_holiday_period(check_in_date, check_out_date))
            )
            
            prices = self.calculator.calculate(request)
            selected_price = next(
                (p for p in prices if p.room_type.value == (room_type or "terreo") 
                 and p.meal_plan == parsed_meal_plan), 
                prices[0]
            )
            
            # Salva no sistema de reservas
            reservation_manager = get_reservation_manager()
            reservation = reservation_manager.create_reservation(
                code=reservation_code,
                guest_name=guest_name or "A definir",
                guest_phone=guest_phone or "A definir",
                guest_document="A definir",
                check_in=check_in_date,
                check_out=check_out_date,
                adults=adults,
                children=children or [],
                room_type=room_type or "terreo",
                meal_plan=meal_plan or "cafe_da_manha",
                total_amount=float(selected_price.total)
            )
            
            # Salva também no contexto da conversa
            context = self._get_conversation_context(guest_phone or "unknown")
            context.current_request = request
            context.metadata["reservation_code"] = reservation_code
            context.metadata["total_amount"] = float(selected_price.total)
            context.metadata["confirmation_status"] = "confirmed"
            context.metadata["created_at"] = datetime.now().isoformat()
            context.metadata["guest_name"] = guest_name
            context.metadata["guest_phone"] = guest_phone
            
            # Formata os nomes para exibição
            room_display = "Térreo" if room_type == "terreo" else "Superior"
            meal_display = {
                "cafe_da_manha": "Apenas café da manhã",
                "meia_pensao": "Meia pensão", 
                "pensao_completa": "Pensão completa"
            }.get(meal_plan, "Apenas café da manhã")
            
            nights = (check_out_date - check_in_date).days
            
            return (
                f"✅ *Reserva Confirmada!* 🎉\n\n"
                f"📋 *Código:* {reservation_code}\n"
                f"👤 *Hóspede:* {guest_name or 'A definir'}\n"
                f"📅 *Check-in:* {check_in_date.strftime('%d/%m/%Y')}\n"
                f"📅 *Check-out:* {check_out_date.strftime('%d/%m/%Y')}\n"
                f"🌙 *Noites:* {nights}\n"
                f"👥 *Hóspedes:* {adults} adulto(s)" + 
                (f" + {len(children)} criança(s)" if children else "") + "\n"
                f"🏠 *Quarto:* {room_display}\n"
                f"🍽️ *Refeições:* {meal_display}\n"
                f"💰 *Total:* {selected_price.format_price()}\n\n"
                f"📱 *Próximos passos:*\n"
                f"1️⃣ Anote seu código: *{reservation_code}*\n"
                f"2️⃣ Para finalizar, envie seus dados:\n"
                f"   • Nome completo\n"
                f"   • CPF\n"
                f"   • Telefone\n\n"
                f"💳 *Pagamento:*\n"
                f"Você pode pagar na chegada ou solicitar link PIX agora mesmo!\n\n"
                f"🏨 Obrigado por escolher o Hotel Passarim! 🙏"
            )
            
        except Exception as e:
            logger.error("Erro ao criar reserva", error=str(e))
            return (
                "❌ Ops! Houve um problema ao criar sua reserva.\n\n"
                "Por favor, tente novamente ou ligue para nossa recepção:\n"
                "📞 (15) 3542-0000\n\n"
                "Estamos aqui para ajudar! 😊"
            )

    async def get_reservation_details(
        self,
        reservation_code: str,
        guest_phone: str = None
    ) -> str:
        """
        Consulta detalhes de uma reserva pelo código.
        
        Args:
            reservation_code: Código da reserva
            guest_phone: Telefone do hóspede (opcional)
            
        Returns:
            Detalhes da reserva ou mensagem de erro
        """
        try:
            # Busca no contexto se for o mesmo telefone
            if guest_phone and guest_phone in self.contexts:
                context = self.contexts[guest_phone]
                if context.metadata.get("reservation_code") == reservation_code:
                    request = context.current_request
                    if request:
                        room_display = "Térreo" if request.room_type == RoomType.TERREO else "Superior"
                        meal_display = {
                            MealPlan.CAFE_DA_MANHA: "Apenas café da manhã",
                            MealPlan.MEIA_PENSAO: "Meia pensão",
                            MealPlan.PENSAO_COMPLETA: "Pensão completa"
                        }.get(request.meal_plan, "Apenas café da manhã")
                        
                        total_amount = context.metadata.get("total_amount", 0)
                        guest_name = context.metadata.get("guest_name", "A definir")
                        status = context.metadata.get("confirmation_status", "pendente")
                        created_at = context.metadata.get("created_at")
                        
                        nights = request.nights
                        
                        return (
                            f"📋 *Detalhes da Reserva {reservation_code}*\n\n"
                            f"✅ *Status:* {status.capitalize()}\n"
                            f"👤 *Hóspede:* {guest_name}\n"
                            f"📅 *Check-in:* {request.check_in.strftime('%d/%m/%Y')}\n"
                            f"📅 *Check-out:* {request.check_out.strftime('%d/%m/%Y')}\n"
                            f"🌙 *Noites:* {nights}\n"
                            f"👥 *Hóspedes:* {request.adults} adulto(s)" +
                            (f" + {len(request.children)} criança(s)" if request.children else "") + "\n"
                            f"🏠 *Quarto:* {room_display}\n"
                            f"🍽️ *Refeições:* {meal_display}\n"
                            f"💰 *Total:* R$ {total_amount:,.2f}\n\n"
                            f"📱 *Informações de contato:*\n"
                            f"📞 Hotel: (15) 3542-0000\n"
                            f"💬 WhatsApp: Este chat\n\n"
                            f"Precisa de alguma alteração? 😊"
                        )
            
            # Se não encontrou, informa que precisa mais dados
            return (
                f"🔍 *Consulta de Reserva*\n\n"
                f"Não encontrei a reserva *{reservation_code}* em nosso sistema.\n\n"
                f"📝 *Verifique se:*\n"
                f"• O código está correto\n"
                f"• A reserva foi feita neste WhatsApp\n\n"
                f"📞 *Contato direto:*\n"
                f"Ligue para (15) 3542-0000 para mais informações.\n\n"
                f"Como posso ajudar? 😊"
            )
            
        except Exception as e:
            logger.error("Erro ao consultar reserva", error=str(e))
            return (
                "❌ Erro ao consultar reserva.\n\n"
                "Tente novamente ou ligue:\n"
                "📞 (15) 3542-0000"
            )

    async def generate_payment_pix(
        self,
        reservation_code: str,
        guest_phone: str = None
    ) -> str:
        """
        Gera link de pagamento PIX para uma reserva.
        
        Args:
            reservation_code: Código da reserva
            guest_phone: Telefone do hóspede
            
        Returns:
            Instruções de pagamento PIX
        """
        try:
            # Busca a reserva no contexto
            if guest_phone and guest_phone in self.contexts:
                context = self.contexts[guest_phone]
                if context.metadata.get("reservation_code") == reservation_code:
                    total_amount = context.metadata.get("total_amount", 0)
                    guest_name = context.metadata.get("guest_name", "Hóspede")
                    
                    # Gera chave PIX do hotel (simulado)
                    pix_key = "hotel.passarim@gmail.com"
                    
                    return (
                        f"💳 *Pagamento PIX - Reserva {reservation_code}*\n\n"
                        f"💰 *Valor:* R$ {total_amount:,.2f}\n"
                        f"👤 *Beneficiário:* Hotel Passarim\n"
                        f"🔑 *Chave PIX:* {pix_key}\n\n"
                        f"📱 *Como pagar:*\n"
                        f"1️⃣ Abra seu banco/carteira digital\n"
                        f"2️⃣ Escolha \"PIX\"\n"
                        f"3️⃣ Cole a chave: {pix_key}\n"
                        f"4️⃣ Informe o valor: R$ {total_amount:,.2f}\n"
                        f"5️⃣ Na descrição coloque: {reservation_code}\n\n"
                        f"⚡ *Pagamento instantâneo!*\n"
                        f"Assim que recebermos, sua reserva será confirmada.\n\n"
                        f"🎯 *Desconto de 5%* para pagamento à vista via PIX!\n"
                        f"Valor com desconto: R$ {total_amount * 0.95:,.2f}\n\n"
                        f"Dúvidas? Estou aqui para ajudar! 😊"
                    )
            
            return (
                f"❌ Reserva {reservation_code} não encontrada.\n\n"
                f"Confirme o código ou ligue:\n"
                f"📞 (15) 3542-0000"
            )
            
        except Exception as e:
            logger.error("Erro ao gerar PIX", error=str(e))
            return "❌ Erro ao gerar pagamento PIX. Tente novamente."

    async def confirm_guest_data(
        self,
        guest_phone: str,
        guest_name: str,
        guest_document: str,
        reservation_code: str = None
    ) -> str:
        """
        Confirma e salva os dados do hóspede para finalizar a reserva.
        
        Args:
            guest_phone: Telefone do hóspede
            guest_name: Nome completo
            guest_document: CPF ou documento
            reservation_code: Código da reserva (opcional)
            
        Returns:
            Confirmação dos dados e próximos passos
        """
        try:
            # Busca o contexto da conversa
            context = self._get_conversation_context(guest_phone)
            
            # Se não foi informado código, usa o do contexto
            if not reservation_code:
                reservation_code = context.metadata.get("reservation_code")
            
            if not reservation_code:
                return (
                    "❌ Não encontrei uma reserva ativa.\n\n"
                    "Faça uma nova reserva ou informe o código existente."
                )
            
            # Salva os dados no contexto
            context.metadata.update({
                "guest_name": guest_name,
                "guest_document": guest_document,
                "data_confirmed": True,
                "data_confirmed_at": datetime.now().isoformat()
            })
            
            # Atualiza o nome no contexto da conversa
            context.guest_name = guest_name.split()[0]  # Primeiro nome
            
            total_amount = context.metadata.get("total_amount", 0)
            
            return (
                f"✅ *Dados Confirmados!*\n\n"
                f"📋 *Reserva:* {reservation_code}\n"
                f"👤 *Nome:* {guest_name}\n"
                f"📄 *Documento:* {guest_document}\n"
                f"📱 *Telefone:* {guest_phone}\n\n"
                f"🎉 *Sua reserva está confirmada!*\n\n"
                f"💳 *Opções de pagamento:*\n"
                f"1️⃣ PIX (5% desconto) - R$ {total_amount * 0.95:,.2f}\n"
                f"2️⃣ Cartão na chegada - R$ {total_amount:,.2f}\n"
                f"3️⃣ Dinheiro na chegada - R$ {total_amount:,.2f}\n\n"
                f"📧 Em breve você receberá:\n"
                f"• Voucher de confirmação\n"
                f"• Instruções de chegada\n"
                f"• Link para check-in antecipado\n\n"
                f"🏨 *Hotel Passarim*\n"
                f"📍 Endereço será enviado em breve\n"
                f"📞 (15) 3542-0000\n\n"
                f"Aguardamos você! 🙏✨"
            )
            
        except Exception as e:
            logger.error("Erro ao confirmar dados", error=str(e))
            return "❌ Erro ao confirmar dados. Tente novamente."
