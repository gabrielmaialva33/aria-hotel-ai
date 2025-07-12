"""Improved Ana Agent with advanced NLP and multimodal capabilities."""

from datetime import datetime
from typing import Dict, Optional

from app.agents.ana.calculator import PricingCalculator
from app.agents.ana.models import AnaResponse, ConversationContext, ReservationRequest
from app.agents.ana.nlp_processor import NLPProcessor, Intent
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class ImprovedAnaAgent:
    """Enhanced Ana agent with semantic understanding and proactive features."""

    def __init__(self):
        """Initialize improved Ana agent."""
        self.name = "Ana"
        self.nlp = NLPProcessor()
        self.calculator = PricingCalculator()

        # In-memory context store (would be Redis/DB in production)
        self.contexts: Dict[str, ConversationContext] = {}

        # Response templates by intent
        self.response_templates = {
            Intent.GREETING: [
                "Olá! 😊 Sou a Ana, assistente virtual do Hotel Passarim. Como posso ajudar você hoje?",
                "Oi! Bem-vindo ao Hotel Passarim! 🏨 Em que posso ser útil?",
                "Bom dia! Sou a Ana e estou aqui para tornar sua experiência conosco ainda melhor. Como posso ajudar?"
            ],
            Intent.UNKNOWN: [
                "Desculpe, não entendi muito bem. Você poderia reformular sua pergunta?",
                "Hmm, não tenho certeza se entendi. Você está perguntando sobre:\n• Reservas e valores?\n• Estrutura do hotel?\n• Nosso restaurante?\n• Outra informação?"
            ]
        }

        # Quick reply suggestions by intent
        self.quick_replies = {
            Intent.GREETING: [
                "Ver valores de hospedagem",
                "Conhecer o hotel",
                "Fazer uma reserva",
                "Falar com a recepção"
            ],
            Intent.PRICING_REQUEST: [
                "Incluir crianças",
                "Pensão completa",
                "Ver fotos dos quartos",
                "Confirmar reserva"
            ],
            Intent.UNKNOWN: [
                "Valores e reservas",
                "Estrutura e lazer",
                "Restaurante",
                "Falar com alguém"
            ]
        }

    async def process_message(
            self,
            phone: str,
            message: str,
            media_url: Optional[str] = None,
            location: Optional[Dict] = None,
            context: Optional[Dict] = None
    ) -> AnaResponse:
        """
        Process incoming message with advanced NLP.
        
        Args:
            phone: Guest's phone number
            message: Text message content
            media_url: URL of attached media
            location: Location data if shared
            context: Additional context
            
        Returns:
            Enhanced AnaResponse
        """
        try:
            # Get or create conversation context
            conv_context = self._get_or_create_context(phone, context)

            # Add message to history
            conv_context.add_message("user", message)

            # Process with NLP
            nlp_result = await self.nlp.process(message)

            logger.info(
                "NLP processing complete",
                phone=phone,
                intent=nlp_result.intent.value,
                confidence=nlp_result.confidence,
                entities=[e.type for e in nlp_result.entities],
                sentiment=nlp_result.sentiment
            )

            # Route to appropriate handler
            response = await self._route_intent(
                nlp_result,
                conv_context,
                media_url,
                location
            )

            # Add quick replies if appropriate
            if nlp_result.intent in self.quick_replies:
                response.quick_replies = self.quick_replies[nlp_result.intent]

            # Check if sentiment is negative - might need human help
            if nlp_result.sentiment == "negative" and nlp_result.confidence > 0.7:
                response.needs_human = True
                response.metadata["transfer_reason"] = "negative_sentiment"

            # Save updated context
            conv_context.add_message("assistant", response.text)
            conv_context.metadata["last_intent"] = nlp_result.intent.value
            conv_context.metadata["last_sentiment"] = nlp_result.sentiment
            self.contexts[phone] = conv_context

            return response

        except Exception as e:
            logger.error(
                "Error processing message",
                phone=phone,
                error=str(e),
                error_type=type(e).__name__
            )
            return AnaResponse(
                text="Ops! Tive um probleminha ao processar sua mensagem. 😅 "
                     "Vou chamar alguém da nossa equipe para ajudar você melhor!",
                needs_human=True,
                action="transfer_to_reception"
            )

    async def _route_intent(
            self,
            nlp_result,
            context: ConversationContext,
            media_url: Optional[str] = None,
            location: Optional[Dict] = None
    ) -> AnaResponse:
        """Route to appropriate handler based on intent."""

        # Map intents to handlers
        handlers = {
            Intent.GREETING: self._handle_greeting,
            Intent.RESERVATION_INQUIRY: self._handle_reservation_inquiry,
            Intent.PRICING_REQUEST: self._handle_pricing_request,
            Intent.AVAILABILITY_CHECK: self._handle_availability_check,
            Intent.AMENITIES_INFO: self._handle_amenities_info,
            Intent.RESTAURANT_INFO: self._handle_restaurant_info,
            Intent.WIFI_INFO: self._handle_wifi_info,
            Intent.PASTA_ROTATION: self._handle_pasta_rotation,
            Intent.COMPLAINT: self._handle_complaint,
            Intent.THANKS: self._handle_thanks,
            Intent.UNKNOWN: self._handle_unknown
        }

        handler = handlers.get(nlp_result.intent, self._handle_unknown)
        return await handler(nlp_result, context, media_url, location)

    async def _handle_greeting(self, nlp_result, context, media_url, location) -> AnaResponse:
        """Handle greeting intent."""
        # Personalize if we know the guest
        if context.guest_name:
            text = f"Olá {context.guest_name}! 😊 Que bom ter você de volta! Como posso ajudar?"
        else:
            # Use template
            import random
            text = random.choice(self.response_templates[Intent.GREETING])

        return AnaResponse(
            text=text,
            metadata={"intent": "greeting"}
        )

    async def _handle_pricing_request(self, nlp_result, context, media_url, location) -> AnaResponse:
        """Handle pricing request with extracted entities."""
        # Extract relevant entities
        dates = [e for e in nlp_result.entities if e.type == "date"]
        adults = next((e for e in nlp_result.entities if e.type == "adults"), None)
        children = [e for e in nlp_result.entities if e.type == "children"]
        nights = next((e for e in nlp_result.entities if e.type == "nights"), None)

        # Check if we have enough information
        if len(dates) < 2 and not nights:
            return AnaResponse(
                text="Para calcular os valores, preciso saber:\n\n"
                     "📅 Datas de check-in e check-out\n"
                     "👥 Número de adultos\n"
                     "👶 Se há crianças (e suas idades)\n\n"
                     "Por exemplo: *'Valores para 2 adultos de 15 a 17 de março'*",
                metadata={"intent": "pricing_request", "missing_info": True}
            )

        try:
            # Determine check-in and check-out
            if len(dates) >= 2:
                check_in = datetime.fromisoformat(dates[0].value).date()
                check_out = datetime.fromisoformat(dates[1].value).date()
            elif len(dates) == 1 and nights:
                check_in = datetime.fromisoformat(dates[0].value).date()
                check_out = check_in + timedelta(days=int(nights.value))
            else:
                raise ValueError("Insufficient date information")

            # Get guest counts
            adult_count = int(adults.value) if adults else 2
            children_ages = [int(c.value) for c in children] if children else []

            # Create reservation request
            request = ReservationRequest(
                check_in=check_in,
                check_out=check_out,
                adults=adult_count,
                children=children_ages
            )

            # Calculate pricing
            prices = self.calculator.calculate(request)
            message = self.calculator.format_pricing_message(prices)

            # Add visual elements
            if settings.enable_vision_analysis:
                # Would generate room images here
                media_urls = [
                    "https://hotelpassarim.com.br/images/quarto-terreo.jpg",
                    "https://hotelpassarim.com.br/images/quarto-superior.jpg"
                ]
            else:
                media_urls = None

            return AnaResponse(
                text=message,
                media_urls=media_urls,
                action="show_pricing",
                metadata={
                    "intent": "pricing_request",
                    "check_in": check_in.isoformat(),
                    "check_out": check_out.isoformat(),
                    "adults": adult_count,
                    "children": children_ages
                }
            )

        except Exception as e:
            logger.error("Error calculating pricing", error=str(e))
            return AnaResponse(
                text="Desculpe, tive um problema ao calcular os valores. "
                     "Poderia me informar novamente as datas e número de pessoas?",
                metadata={"intent": "pricing_request", "error": True}
            )

    async def _handle_availability_check(self, nlp_result, context, media_url, location) -> AnaResponse:
        """Check availability for dates."""
        dates = [e for e in nlp_result.entities if e.type == "date"]

        if len(dates) < 2:
            return AnaResponse(
                text="Para verificar disponibilidade, preciso das datas de entrada e saída. "
                     "Por exemplo: *'Tem vaga de 10 a 12 de abril?'*",
                metadata={"intent": "availability_check", "missing_dates": True}
            )

        # TODO: Actually check availability in PMS
        # For now, mock response
        check_in = datetime.fromisoformat(dates[0].value).date()
        check_out = datetime.fromisoformat(dates[1].value).date()

        return AnaResponse(
            text=f"✅ Ótima notícia! Temos disponibilidade para o período "
                 f"de {check_in.strftime('%d/%m')} a {check_out.strftime('%d/%m')}!\n\n"
                 f"Gostaria de ver os valores para essa data?",
            action="availability_confirmed",
            metadata={
                "intent": "availability_check",
                "available": True,
                "check_in": check_in.isoformat(),
                "check_out": check_out.isoformat()
            }
        )

    async def _handle_amenities_info(self, nlp_result, context, media_url, location) -> AnaResponse:
        """Provide information about hotel amenities."""
        return AnaResponse(
            text="🏨 *Estrutura do Hotel Passarim:*\n\n"
                 "🏊 *Área de Lazer:*\n"
                 "• Piscina aquecida (28°C)\n"
                 "• Playground infantil\n"
                 "• Sala de jogos\n"
                 "• Churrasqueira\n\n"
                 "🛏️ *Acomodações:*\n"
                 "• Quartos térreos e superiores\n"
                 "• Ar condicionado\n"
                 "• TV a cabo\n"
                 "• Frigobar\n"
                 "• WiFi gratuito\n\n"
                 "🌳 *Outros:*\n"
                 "• Estacionamento gratuito\n"
                 "• Área verde de 5.000m²\n"
                 "• Pet friendly (consulte regras)\n"
                 "• Acessibilidade",
            media_urls=["https://hotelpassarim.com.br/tour-virtual"],
            metadata={"intent": "amenities_info"}
        )

    async def _handle_restaurant_info(self, nlp_result, context, media_url, location) -> AnaResponse:
        """Provide restaurant information."""
        return AnaResponse(
            text="🍽️ *Restaurante do Hotel:*\n\n"
                 "☕ *Café da Manhã:* 7h às 10h\n"
                 "Buffet colonial completo incluído na diária\n\n"
                 "🥘 *Almoço:* 12h às 15h\n"
                 "Buffet variado (não incluído)\n"
                 "Adultos: R$ 45,90 | Crianças: R$ 22,90\n\n"
                 "🍝 *Rodízio de Massas:*\n"
                 "Sextas e Sábados, 19h às 22h\n"
                 "Adultos: R$ 74,90 | Crianças: R$ 35,90\n"
                 "Reserva: hotelpassarim.com.br/reservas\n\n"
                 "🍕 *Room Service:* até 22h",
            metadata={"intent": "restaurant_info"}
        )

    async def _handle_wifi_info(self, nlp_result, context, media_url, location) -> AnaResponse:
        """Provide WiFi information."""
        return AnaResponse(
            text="📶 *WiFi do Hotel Passarim:*\n\n"
                 "🌐 *Rede:* HotelPassarim_Guest\n"
                 "🔐 *Senha:* passarim2025\n\n"
                 "✅ WiFi gratuito em todo o hotel\n"
                 "✅ Alta velocidade (100 Mbps)\n"
                 "✅ Ideal para trabalho remoto\n\n"
                 "Problemas para conectar? Estamos aqui para ajudar! 😊",
            metadata={"intent": "wifi_info"}
        )

    async def _handle_pasta_rotation(self, nlp_result, context, media_url, location) -> AnaResponse:
        """Handle pasta rotation inquiries."""
        # Check if they mentioned a date
        dates = [e for e in nlp_result.entities if e.type == "date"]

        if dates:
            date_obj = datetime.fromisoformat(dates[0].value).date()
            # Check if it's Friday or Saturday
            if date_obj.weekday() not in [4, 5]:  # Not Friday or Saturday
                return AnaResponse(
                    text=f"🍝 O Rodízio de Massas acontece apenas às *sextas e sábados*, das 19h às 22h.\n\n"
                         f"A data {date_obj.strftime('%d/%m')} é {self._get_weekday_name(date_obj.weekday())}. "
                         f"Que tal escolher uma sexta ou sábado?",
                    metadata={"intent": "pasta_rotation", "invalid_date": True}
                )

        return AnaResponse(
            text="🍝 *Rodízio de Massas Artesanais*\n\n"
                 "📅 Sextas e Sábados, 19h às 22h\n\n"
                 "💰 *Valores:*\n"
                 "• Adultos: R$ 74,90\n"
                 "• Crianças (5-12): R$ 35,90\n"
                 "• Menores de 5: Cortesia\n\n"
                 "🍴 *Incluído:*\n"
                 "• Antepastos variados\n"
                 "• 4 tipos de ravioli\n"
                 "• 2 tipos de rondelli\n"
                 "• Massas com molhos artesanais\n"
                 "• Sobremesa\n\n"
                 "📱 *Reserva obrigatória:*\n"
                 "hotelpassarim.com.br/reservas\n\n"
                 "Gostaria de fazer uma reserva?",
            metadata={"intent": "pasta_rotation"}
        )

    async def _handle_complaint(self, nlp_result, context, media_url, location) -> AnaResponse:
        """Handle complaints with care."""
        return AnaResponse(
            text="Sinto muito que você esteja tendo uma experiência negativa. 😔\n\n"
                 "Sua satisfação é muito importante para nós. Vou transferir você "
                 "imediatamente para nossa gerência para resolver isso da melhor forma possível.",
            needs_human=True,
            action="transfer_to_management",
            metadata={
                "intent": "complaint",
                "priority": "high",
                "sentiment": nlp_result.sentiment
            }
        )

    async def _handle_thanks(self, nlp_result, context, media_url, location) -> AnaResponse:
        """Handle thank you messages."""
        return AnaResponse(
            text="Por nada! 😊 Foi um prazer ajudar!\n\n"
                 "Se precisar de mais alguma coisa, é só chamar. "
                 "Estou sempre aqui para tornar sua experiência no Hotel Passarim ainda melhor! 🏨✨",
            metadata={"intent": "thanks"}
        )

    async def _handle_unknown(self, nlp_result, context, media_url, location) -> AnaResponse:
        """Handle unknown intents."""
        import random
        text = random.choice(self.response_templates[Intent.UNKNOWN])

        # If this is the second unknown in a row, offer human help
        if context.metadata.get("last_intent") == "unknown":
            text += "\n\nOu se preferir, posso chamar alguém da nossa equipe para ajudar! 😊"

        return AnaResponse(
            text=text,
            metadata={"intent": "unknown"}
        )

    def _get_or_create_context(self, phone: str, additional_context: Optional[Dict] = None) -> ConversationContext:
        """Get existing context or create new one."""
        if phone in self.contexts:
            return self.contexts[phone]

        context = ConversationContext(
            guest_phone=phone,
            guest_name=additional_context.get("name") if additional_context else None,
            preferences=additional_context.get("preferences", {}) if additional_context else {}
        )

        self.contexts[phone] = context
        return context

    def _get_weekday_name(self, weekday: int) -> str:
        """Get weekday name in Portuguese."""
        names = ["segunda-feira", "terça-feira", "quarta-feira",
                 "quinta-feira", "sexta-feira", "sábado", "domingo"]
        return names[weekday]

    async def handle_media(self, phone: str, media_url: str, media_type: str) -> AnaResponse:
        """Handle media messages (images, documents, etc)."""
        if media_type.startswith("image/"):
            # TODO: Implement image analysis
            # - Document OCR for check-in
            # - Room preference detection
            # - Damage reports
            return AnaResponse(
                text="Recebi sua imagem! 📸 Estou analisando...\n\n"
                     "Em breve terei recursos para processar documentos e imagens. "
                     "Por enquanto, pode me dizer como posso ajudar?",
                metadata={"media_received": True, "media_type": media_type}
            )

        elif media_type == "application/pdf":
            # TODO: Handle PDF documents
            return AnaResponse(
                text="Recebi seu documento PDF! 📄\n\n"
                     "Em breve poderei processar documentos automaticamente. "
                     "É um documento para check-in?",
                metadata={"media_received": True, "media_type": media_type}
            )

        else:
            return AnaResponse(
                text="Recebi seu arquivo! Por enquanto, trabalho melhor com textos. "
                     "Como posso ajudar você?",
                metadata={"media_received": True, "media_type": media_type}
            )

    async def get_proactive_message(self, phone: str, trigger: str) -> Optional[AnaResponse]:
        """Generate proactive messages based on triggers."""
        context = self.contexts.get(phone)
        if not context:
            return None

        if trigger == "pre_arrival":
            # 1 day before check-in
            return AnaResponse(
                text="Olá! 😊 Amanhã é o grande dia da sua chegada!\n\n"
                     "Algumas informações úteis:\n"
                     "📍 Endereço: Rua Example, 123\n"
                     "🕐 Check-in a partir das 14h\n"
                     "🚗 Estacionamento gratuito\n\n"
                     "Gostaria de adiantar seu check-in? É super rápido!",
                action="pre_arrival_reminder",
                metadata={"trigger": "pre_arrival"}
            )

        elif trigger == "post_checkout":
            # After checkout
            return AnaResponse(
                text="Espero que tenha aproveitado sua estadia! 🏨✨\n\n"
                     "Sua opinião é muito importante para nós. "
                     "Poderia dedicar 2 minutinhos para avaliar sua experiência?\n\n"
                     "👉 hotelpassarim.com.br/avaliacao",
                action="feedback_request",
                metadata={"trigger": "post_checkout"}
            )

        elif trigger == "special_offer":
            # Based on preferences
            if context.preferences.get("likes_pasta"):
                return AnaResponse(
                    text="🍝 Oi! Sexta-feira tem Rodízio de Massas!\n\n"
                         "Lembrei que você gostou da última vez. "
                         "Que tal garantir sua mesa?\n\n"
                         "Use o código VOLTOU10 para 10% de desconto!",
                    action="special_offer",
                    metadata={"trigger": "special_offer", "offer_type": "pasta"}
                )

        return None
