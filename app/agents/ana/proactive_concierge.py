"""Proactive concierge for Ana agent."""

from datetime import datetime
from typing import Dict, Any, List, Optional

from app.agents.ana.models import ConversationContext
from app.core.logging import get_logger

logger = get_logger(__name__)


class ProactiveConcierge:
    """Proactive concierge to provide personalized suggestions."""

    def __init__(self):
        """Initialize proactive concierge."""
        pass

    async def get_suggestions(
        self,
        context: ConversationContext,
        weather: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get personalized suggestions for a guest.

        Args:
            context: Conversation context
            weather: Optional weather information

        Returns:
            List of suggestions
        """
        suggestions = []

        # Example: Suggest spa on a rainy day
        if weather and weather.get("condition") == "rain":
            suggestions.append({
                "type": "spa_offer",
                "title": "Dia de Chuva, Dia de Spa!",
                "text": "Que tal aproveitar o dia chuvoso para relaxar em nosso spa? Temos pacotes especiais com massagem e ofurô.",
                "quick_replies": ["Ver pacotes de spa", "Agora não"]
            })

        # Example: Suggest dinner reservation based on preferences
        if context.preferences.get("likes_italian_food"):
            suggestions.append({
                "type": "dinner_reservation",
                "title": "Noite Italiana no Hotel Passarim",
                "text": "Vimos que você gosta de comida italiana! Que tal uma reserva para o nosso rodízio de massas hoje à noite?",
                "quick_replies": ["Reservar massa", "Ver cardápio"]
            })

        # Example: Suggest late check-out on the day of departure
        if context.current_request and context.current_request.check_out == datetime.now().date():
            suggestions.append({
                "type": "late_checkout",
                "title": "Aproveite um Pouco Mais!",
                "text": "Não quer que o dia acabe? Oferecemos late check-out até as 15h por uma pequena taxa.",
                "quick_replies": ["Saber mais", "Não, obrigado"]
            })

        logger.info(
            "Generated proactive suggestions",
            guest_phone=context.guest_phone,
            num_suggestions=len(suggestions)
        )

        return suggestions
