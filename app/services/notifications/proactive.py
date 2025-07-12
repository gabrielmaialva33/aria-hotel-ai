"""Proactive notification system for guest engagement."""

import asyncio
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Callable

from app.core.database.models import Reservation, Guest, Message
from app.core.database.session import get_db
from celery import Celery
from sqlalchemy import select

from app.agents.ana.improved_agent import ImprovedAnaAgent
from app.core.logging import get_logger
from app.core.memory.vector_store import get_memory_store
from app.integrations.whatsapp import WhatsAppClient

logger = get_logger(__name__)


class TriggerType(Enum):
    """Types of notification triggers."""
    PRE_ARRIVAL = "pre_arrival"  # X days before check-in
    DAY_OF_ARRIVAL = "day_of_arrival"  # Day of check-in
    WELCOME = "welcome"  # Upon check-in
    DURING_STAY = "during_stay"  # During the stay
    PRE_DEPARTURE = "pre_departure"  # Day before checkout
    POST_DEPARTURE = "post_departure"  # After checkout
    BIRTHDAY = "birthday"  # Guest birthday
    SPECIAL_OFFER = "special_offer"  # Promotional offers
    WEATHER_BASED = "weather_based"  # Weather-related
    EVENT_BASED = "event_based"  # Local events
    FEEDBACK_REQUEST = "feedback_request"  # Request reviews
    LOYALTY = "loyalty"  # Loyalty program updates


@dataclass
class NotificationRule:
    """Rule for triggering notifications."""
    name: str
    trigger_type: TriggerType
    condition: Callable  # Function that returns True if should trigger
    template: str
    priority: int = 5  # 1-10, higher is more important
    enabled: bool = True
    metadata: Dict = None


@dataclass
class ScheduledNotification:
    """A notification scheduled to be sent."""
    id: str
    guest_id: str
    rule_name: str
    scheduled_time: datetime
    message: str
    metadata: Dict
    status: str = "pending"  # pending, sent, failed, cancelled


class NotificationEngine:
    """Engine for managing proactive notifications."""

    def __init__(self):
        """Initialize notification engine."""
        self.rules: List[NotificationRule] = []
        self.whatsapp_client = WhatsAppClient()
        self.ana_agent = ImprovedAnaAgent()
        self.memory_store = None
        self._initialized = False

        # Register default rules
        self._register_default_rules()

    async def initialize(self):
        """Initialize connections and load rules."""
        if self._initialized:
            return

        try:
            self.memory_store = await get_memory_store()
            self._initialized = True
            logger.info("Notification engine initialized", rules_count=len(self.rules))

        except Exception as e:
            logger.error("Failed to initialize notification engine", error=str(e))

    def _register_default_rules(self):
        """Register default notification rules."""
        # Pre-arrival (1 day before)
        self.add_rule(NotificationRule(
            name="pre_arrival_reminder",
            trigger_type=TriggerType.PRE_ARRIVAL,
            condition=lambda r: (r.check_in - date.today()).days == 1,
            template=(
                "Olá {name}! 🌟\n\n"
                "Amanhã é o grande dia da sua chegada ao Hotel Passarim!\n\n"
                "📍 Endereço: {address}\n"
                "🕐 Check-in: a partir das 14h\n"
                "🚗 Temos estacionamento gratuito\n\n"
                "Quer adiantar seu check-in digital? É super rápido! "
                "Clique aqui: {checkin_link}\n\n"
                "Qualquer dúvida, é só me chamar! 😊"
            ),
            priority=8
        ))

        # Day of arrival
        self.add_rule(NotificationRule(
            name="arrival_day_welcome",
            trigger_type=TriggerType.DAY_OF_ARRIVAL,
            condition=lambda r: r.check_in == date.today(),
            template=(
                "Bom dia {name}! ☀️\n\n"
                "Hoje é o dia da sua chegada! Estamos ansiosos para recebê-los.\n\n"
                "🌡️ Tempo hoje: {weather}\n"
                "💡 Dica: {tip}\n\n"
                "Seu quarto já está sendo preparado com todo carinho. "
                "Previsão de chegada? Me avise para agilizarmos tudo! 🏨"
            ),
            priority=7
        ))

        # Welcome upon check-in
        self.add_rule(NotificationRule(
            name="welcome_message",
            trigger_type=TriggerType.WELCOME,
            condition=lambda r: r.status == "checked_in" and r.check_in == date.today(),
            template=(
                "Bem-vindo ao Hotel Passarim, {name}! 🎉\n\n"
                "Espero que aproveite cada momento da sua estadia.\n\n"
                "📶 WiFi: HotelPassarim_Guest\n"
                "🔐 Senha: passarim2025\n\n"
                "☕ Café da manhã: 7h às 10h\n"
                "🏊 Piscina: até 22h\n\n"
                "Precisa de algo? É só me chamar aqui pelo WhatsApp!"
            ),
            priority=9
        ))

        # During stay - suggest activities
        self.add_rule(NotificationRule(
            name="activity_suggestion",
            trigger_type=TriggerType.DURING_STAY,
            condition=lambda r: r.check_in < date.today() < r.check_out,
            template=(
                "Oi {name}! Como está sendo sua estadia? 😊\n\n"
                "{suggestion}\n\n"
                "Posso fazer alguma reserva para você?"
            ),
            priority=5,
            metadata={"time_of_day": "morning"}
        ))

        # Pre-departure
        self.add_rule(NotificationRule(
            name="checkout_reminder",
            trigger_type=TriggerType.PRE_DEPARTURE,
            condition=lambda r: (r.check_out - date.today()).days == 1,
            template=(
                "Olá {name}! 👋\n\n"
                "Amanhã é seu dia de check-out (até 12h).\n\n"
                "🧳 Precisa de late check-out? Posso verificar!\n"
                "🚕 Quer que chame um táxi?\n"
                "📦 Esqueceu algo? Me avise!\n\n"
                "Foi um prazer ter vocês conosco! 💚"
            ),
            priority=7
        ))

        # Post-departure feedback
        self.add_rule(NotificationRule(
            name="feedback_request",
            trigger_type=TriggerType.FEEDBACK_REQUEST,
            condition=lambda r: (date.today() - r.check_out).days == 2,
            template=(
                "Oi {name}! Espero que tenham chegado bem em casa 🏠\n\n"
                "Sua opinião é muito importante para nós! "
                "Poderia dedicar 2 minutinhos para avaliar sua experiência?\n\n"
                "👉 {feedback_link}\n\n"
                "Como agradecimento, você ganhará 10% de desconto "
                "na próxima reserva! 🎁"
            ),
            priority=6
        ))

        # Birthday greetings
        self.add_rule(NotificationRule(
            name="birthday_greeting",
            trigger_type=TriggerType.BIRTHDAY,
            condition=lambda
                g: g.birthdate and g.birthdate.month == date.today().month and g.birthdate.day == date.today().day,
            template=(
                "🎂 Feliz Aniversário, {name}! 🎉\n\n"
                "O Hotel Passarim deseja um dia repleto de alegrias!\n\n"
                "Que tal comemorar com a gente? Preparamos uma "
                "oferta especial de aniversário:\n\n"
                "🎁 20% de desconto na hospedagem\n"
                "🍰 Bolo de cortesia\n"
                "🥂 Upgrade de quarto (sujeito a disponibilidade)\n\n"
                "Válido para reservas este mês. Vamos celebrar juntos? 🎊"
            ),
            priority=8
        ))

        # Weather-based suggestions
        self.add_rule(NotificationRule(
            name="rainy_day_activity",
            trigger_type=TriggerType.WEATHER_BASED,
            condition=lambda r, weather: r.check_in <= date.today() <= r.check_out and weather.get("rain", False),
            template=(
                "Oi {name}! 🌧️\n\n"
                "Vi que está chovendo hoje. Que tal aproveitar:\n\n"
                "🎮 Nossa sala de jogos\n"
                "📚 Biblioteca com lareira\n"
                "☕ Café especial no restaurante\n"
                "🧖 Desconto de 20% na massagem\n\n"
                "Posso reservar algo para você?"
            ),
            priority=4
        ))

        # Special offers for returning guests
        self.add_rule(NotificationRule(
            name="returning_guest_offer",
            trigger_type=TriggerType.SPECIAL_OFFER,
            condition=lambda g: g.total_stays > 2 and (date.today() - g.last_stay).days > 60,
            template=(
                "Olá {name}! Sentimos sua falta! 💚\n\n"
                "Já faz {days_since} dias desde sua última visita. "
                "Preparamos uma oferta especial para você:\n\n"
                "✨ 15% de desconto na hospedagem\n"
                "✨ Early check-in garantido\n"
                "✨ Welcome drink de cortesia\n\n"
                "Código: VOLTEI15\n"
                "Válido por 30 dias. Esperamos ver você em breve! 🏨"
            ),
            priority=6
        ))

    def add_rule(self, rule: NotificationRule):
        """Add a notification rule."""
        self.rules.append(rule)
        logger.info("Notification rule added", rule_name=rule.name)

    async def check_and_schedule_notifications(self):
        """Check all rules and schedule notifications as needed."""
        logger.info("Checking notification rules")

        scheduled_count = 0

        async with get_db() as db:
            # Check pre-arrival and arrival rules
            await self._check_reservation_rules(db)

            # Check guest-based rules (birthdays, loyalty)
            await self._check_guest_rules(db)

            # Check weather-based rules
            await self._check_weather_rules(db)

            # Check special offers
            await self._check_special_offer_rules(db)

        logger.info("Notification check complete", scheduled=scheduled_count)

    async def _check_reservation_rules(self, db):
        """Check rules related to reservations."""
        # Get relevant reservations
        result = await db.execute(
            select(Reservation)
            .where(Reservation.status.in_(["confirmed", "checked_in"]))
            .where(Reservation.check_in >= date.today() - timedelta(days=1))
            .where(Reservation.check_in <= date.today() + timedelta(days=7))
        )

        reservations = result.scalars().all()

        for reservation in reservations:
            # Get guest info
            guest_result = await db.execute(
                select(Guest).where(Guest.id == reservation.guest_id)
            )
            guest = guest_result.scalar_one_or_none()

            if not guest:
                continue

            # Check each reservation-based rule
            for rule in self.rules:
                if rule.trigger_type in [
                    TriggerType.PRE_ARRIVAL,
                    TriggerType.DAY_OF_ARRIVAL,
                    TriggerType.WELCOME,
                    TriggerType.DURING_STAY,
                    TriggerType.PRE_DEPARTURE,
                    TriggerType.FEEDBACK_REQUEST
                ]:
                    if rule.enabled and rule.condition(reservation):
                        await self._schedule_notification(
                            guest=guest,
                            reservation=reservation,
                            rule=rule
                        )

    async def _check_guest_rules(self, db):
        """Check rules related to guest attributes."""
        # Get guests with birthdays this week
        today = date.today()
        week_later = today + timedelta(days=7)

        # This query would need to be adjusted for birthday checking
        result = await db.execute(
            select(Guest)
            .where(Guest.metadata["birthdate"].isnot(None))
        )

        guests = result.scalars().all()

        for guest in guests:
            for rule in self.rules:
                if rule.trigger_type == TriggerType.BIRTHDAY:
                    if rule.enabled and rule.condition(guest):
                        await self._schedule_notification(
                            guest=guest,
                            reservation=None,
                            rule=rule
                        )

    async def _check_weather_rules(self, db):
        """Check weather-based rules."""
        # Get current weather (mock for now)
        weather = await self._get_weather()

        if weather.get("rain") or weather.get("cold"):
            # Get current guests
            result = await db.execute(
                select(Reservation)
                .where(Reservation.status == "checked_in")
                .where(Reservation.check_in <= date.today())
                .where(Reservation.check_out >= date.today())
            )

            current_stays = result.scalars().all()

            for reservation in current_stays:
                guest_result = await db.execute(
                    select(Guest).where(Guest.id == reservation.guest_id)
                )
                guest = guest_result.scalar_one_or_none()

                if guest:
                    for rule in self.rules:
                        if rule.trigger_type == TriggerType.WEATHER_BASED:
                            if rule.enabled and rule.condition(reservation, weather):
                                await self._schedule_notification(
                                    guest=guest,
                                    reservation=reservation,
                                    rule=rule,
                                    additional_context={"weather": weather}
                                )

    async def _check_special_offer_rules(self, db):
        """Check special offer rules."""
        # Get guests for special offers
        result = await db.execute(
            select(Guest)
            .where(Guest.metadata["total_stays"].astext.cast(Integer) > 1)
        )

        eligible_guests = result.scalars().all()

        for guest in eligible_guests:
            # Get guest profile from memory store
            if self.memory_store:
                profile = await self.memory_store.get_guest_profile(str(guest.id))

                for rule in self.rules:
                    if rule.trigger_type == TriggerType.SPECIAL_OFFER:
                        # Add profile data to guest object for condition check
                        guest.total_stays = profile["total_interactions"]
                        # Calculate last stay (would need proper implementation)
                        guest.last_stay = date.today() - timedelta(days=90)

                        if rule.enabled and rule.condition(guest):
                            await self._schedule_notification(
                                guest=guest,
                                reservation=None,
                                rule=rule
                            )

    async def _schedule_notification(
            self,
            guest: Guest,
            reservation: Optional[Reservation],
            rule: NotificationRule,
            additional_context: Optional[Dict] = None
    ):
        """Schedule a notification to be sent."""
        # Check if already scheduled
        if await self._is_already_scheduled(guest.id, rule.name):
            return

        # Prepare context for template
        context = {
            "name": guest.name.split()[0],  # First name
            "address": "Rua Example, 123, Cidade/SP",
            "checkin_link": f"https://hotelpassarim.com.br/checkin/{reservation.id if reservation else ''}",
            "feedback_link": "https://hotelpassarim.com.br/feedback",
            "weather": "Ensolarado, 25°C",
            "tip": "A piscina está com temperatura perfeita!",
            "suggestion": self._get_activity_suggestion(guest, reservation),
            "days_since": 90  # Would calculate properly
        }

        if additional_context:
            context.update(additional_context)

        # Format message
        message = rule.template.format(**context)

        # Determine send time
        send_time = self._determine_send_time(rule, guest)

        # Create scheduled notification
        notification = ScheduledNotification(
            id=f"{guest.id}_{rule.name}_{date.today()}",
            guest_id=str(guest.id),
            rule_name=rule.name,
            scheduled_time=send_time,
            message=message,
            metadata={
                "rule_type": rule.trigger_type.value,
                "priority": rule.priority,
                "reservation_id": str(reservation.id) if reservation else None
            }
        )

        # Save to database/queue
        await self._save_scheduled_notification(notification)

        logger.info(
            "Notification scheduled",
            guest_id=guest.id,
            rule=rule.name,
            send_time=send_time
        )

    async def send_scheduled_notifications(self):
        """Send all pending scheduled notifications."""
        # Get pending notifications
        pending = await self._get_pending_notifications()

        for notification in pending:
            if notification.scheduled_time <= datetime.now():
                await self._send_notification(notification)

    async def _send_notification(self, notification: ScheduledNotification):
        """Send a single notification."""
        try:
            # Get guest phone
            async with get_db() as db:
                result = await db.execute(
                    select(Guest).where(Guest.id == notification.guest_id)
                )
                guest = result.scalar_one_or_none()

                if not guest or not guest.phone:
                    logger.warning(
                        "Cannot send notification - no phone",
                        guest_id=notification.guest_id
                    )
                    notification.status = "failed"
                    await self._update_notification_status(notification)
                    return

            # Send via WhatsApp
            message_sid = await self.whatsapp_client.send_message(
                to=guest.phone,
                body=notification.message
            )

            # Record in memory store
            if self.memory_store:
                await self.memory_store.add_memory(
                    guest_id=notification.guest_id,
                    content=f"Proactive notification sent: {notification.rule_name}",
                    metadata={
                        "type": "proactive_notification",
                        "rule": notification.rule_name,
                        "message_sid": message_sid
                    }
                )

            # Update status
            notification.status = "sent"
            await self._update_notification_status(notification)

            logger.info(
                "Notification sent",
                guest_id=notification.guest_id,
                rule=notification.rule_name
            )

        except Exception as e:
            logger.error(
                "Failed to send notification",
                error=str(e),
                notification_id=notification.id
            )
            notification.status = "failed"
            await self._update_notification_status(notification)

    def _determine_send_time(self, rule: NotificationRule, guest: Guest) -> datetime:
        """Determine optimal send time based on rule and guest preferences."""
        now = datetime.now()

        # Default send times by rule type
        default_times = {
            TriggerType.PRE_ARRIVAL: now.replace(hour=10, minute=0),
            TriggerType.DAY_OF_ARRIVAL: now.replace(hour=8, minute=0),
            TriggerType.WELCOME: now,  # Immediate
            TriggerType.DURING_STAY: now.replace(hour=9, minute=0),
            TriggerType.PRE_DEPARTURE: now.replace(hour=16, minute=0),
            TriggerType.FEEDBACK_REQUEST: now.replace(hour=14, minute=0),
            TriggerType.BIRTHDAY: now.replace(hour=9, minute=0),
            TriggerType.SPECIAL_OFFER: now.replace(hour=11, minute=0),
            TriggerType.WEATHER_BASED: now.replace(hour=8, minute=30)
        }

        send_time = default_times.get(rule.trigger_type, now)

        # Adjust based on guest timezone if available
        # TODO: Implement timezone handling

        # Don't send too early or too late
        if send_time.hour < 8:
            send_time = send_time.replace(hour=8)
        elif send_time.hour > 20:
            send_time = send_time.replace(hour=20)

        # If time has passed today, send tomorrow
        if send_time < now and rule.trigger_type != TriggerType.WELCOME:
            send_time += timedelta(days=1)

        return send_time

    def _get_activity_suggestion(self, guest: Guest, reservation: Optional[Reservation]) -> str:
        """Get personalized activity suggestion."""
        suggestions = [
            "🍝 Hoje é sexta! Que tal nosso famoso Rodízio de Massas às 19h?",
            "☀️ Dia lindo! A piscina está perfeita para um mergulho.",
            "🎮 Temos torneio de sinuca hoje às 18h. Participe!",
            "🚶 Trilha ecológica saindo às 8h30. Quer participar?",
            "🧘 Aula de yoga no jardim às 7h. Começe o dia com energia!"
        ]

        # TODO: Personalize based on guest preferences from memory store
        import random
        return random.choice(suggestions)

    async def _get_weather(self) -> Dict:
        """Get current weather (mock for now)."""
        # TODO: Integrate with weather API
        import random
        return {
            "temperature": random.randint(20, 30),
            "condition": random.choice(["sunny", "cloudy", "rainy"]),
            "rain": random.random() > 0.7
        }

    async def _is_already_scheduled(self, guest_id: str, rule_name: str) -> bool:
        """Check if notification is already scheduled."""
        # TODO: Implement database check
        return False

    async def _save_scheduled_notification(self, notification: ScheduledNotification):
        """Save scheduled notification to database."""
        # TODO: Implement database save
        pass

    async def _get_pending_notifications(self) -> List[ScheduledNotification]:
        """Get pending notifications from database."""
        # TODO: Implement database query
        return []

    async def _update_notification_status(self, notification: ScheduledNotification):
        """Update notification status in database."""
        # TODO: Implement database update
        pass


# Celery tasks for scheduled execution
app = Celery('aria.notifications')


@app.task
def check_notifications():
    """Celery task to check and schedule notifications."""

    async def run():
        engine = NotificationEngine()
        await engine.initialize()
        await engine.check_and_schedule_notifications()

    asyncio.run(run())


@app.task
def send_notifications():
    """Celery task to send scheduled notifications."""

    async def run():
        engine = NotificationEngine()
        await engine.initialize()
        await engine.send_scheduled_notifications()

    asyncio.run(run())


# Schedule tasks to run periodically
app.conf.beat_schedule = {
    'check-notifications': {
        'task': 'aria.core.notifications.proactive.check_notifications',
        'schedule': timedelta(hours=1),  # Check every hour
    },
    'send-notifications': {
        'task': 'aria.core.notifications.proactive.send_notifications',
        'schedule': timedelta(minutes=5),  # Send every 5 minutes
    },
}
