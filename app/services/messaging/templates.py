"""Message template system for consistent communication."""

import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from app.domain.shared.value_objects import Money
from jinja2 import Environment, Template, select_autoescape, TemplateError

from app.core.logging import get_logger

logger = get_logger(__name__)


class TemplateCategory(Enum):
    """Template categories."""
    GREETING = "greeting"
    RESERVATION = "reservation"
    PAYMENT = "payment"
    CHECK_IN = "check_in"
    CHECK_OUT = "check_out"
    INFORMATION = "information"
    MARKETING = "marketing"
    FEEDBACK = "feedback"
    ERROR = "error"
    NOTIFICATION = "notification"


class TemplateChannel(Enum):
    """Communication channels."""
    WHATSAPP = "whatsapp"
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    WEB = "web"


@dataclass
class MessageTemplate:
    """Message template definition."""
    id: str
    name: str
    category: TemplateCategory
    channels: List[TemplateChannel]
    subject: Optional[str] = None  # For email
    body: str = ""
    media_urls: List[str] = field(default_factory=list)
    buttons: List[Dict[str, str]] = field(default_factory=list)
    variables: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    is_active: bool = True

    def __post_init__(self):
        """Extract variables from template."""
        if not self.variables:
            self.variables = self._extract_variables()

    def _extract_variables(self) -> List[str]:
        """Extract Jinja2 variables from template."""
        # Pattern to match {{ variable }} or {% ... %}
        pattern = r'\{\{[\s]*(\w+)[\s]*\}\}'
        variables = re.findall(pattern, self.body)

        if self.subject:
            variables.extend(re.findall(pattern, self.subject))

        return list(set(variables))


class TemplateEngine:
    """Template rendering engine with Jinja2."""

    def __init__(self):
        """Initialize template engine."""
        self.env = Environment(
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True
        )

        # Add custom filters
        self.env.filters['currency'] = self._format_currency
        self.env.filters['date'] = self._format_date
        self.env.filters['phone'] = self._format_phone
        self.env.filters['title_case'] = lambda s: s.title() if s else ""

        # Template storage (in production, use database)
        self.templates: Dict[str, MessageTemplate] = {}

        # Load default templates
        self._load_default_templates()

    def _load_default_templates(self):
        """Load default message templates."""
        # Welcome message
        self.add_template(MessageTemplate(
            id="welcome_guest",
            name="Mensagem de Boas-vindas",
            category=TemplateCategory.GREETING,
            channels=[TemplateChannel.WHATSAPP],
            body="""Olá {{ guest_name }}! 🌟

Seja muito bem-vindo(a) ao Hotel Passarim! 🏨

Sou a Ana, sua assistente virtual, e estou aqui para tornar sua experiência conosco ainda mais especial.

Como posso ajudar você hoje?
• 📅 Fazer uma reserva
• 💰 Consultar valores
• 🏊 Conhecer nossa estrutura
• 🍝 Reservar nosso rodízio de massas

É só me enviar uma mensagem! 😊"""
        ))

        # Reservation confirmation
        self.add_template(MessageTemplate(
            id="reservation_confirmed",
            name="Confirmação de Reserva",
            category=TemplateCategory.RESERVATION,
            channels=[TemplateChannel.WHATSAPP, TemplateChannel.EMAIL],
            subject="Reserva Confirmada - Hotel Passarim #{{ booking_reference }}",
            body="""✅ *Reserva Confirmada!*

Olá {{ guest_name }},

Sua reserva foi confirmada com sucesso! 🎉

📋 *Detalhes da Reserva:*
• Código: {{ booking_reference }}
• Check-in: {{ check_in | date }}
• Check-out: {{ check_out | date }}
• Acomodação: {{ room_type }}
• Hóspedes: {{ adults }} adulto(s){% if children %} e {{ children }} criança(s){% endif %}

💰 *Valor Total:* {{ total_amount | currency }}
{% if balance_due %}💳 *Saldo a pagar:* {{ balance_due | currency }}{% endif %}

📍 *Endereço:*
{{ hotel_address }}

ℹ️ *Informações importantes:*
• Check-in a partir das 14h
• Check-out até as 12h
• Estacionamento gratuito
• WiFi em todas as áreas

Qualquer dúvida, é só me chamar! 

Estamos ansiosos para recebê-lo(a)! 🏨✨"""
        ))

        # Pre-arrival reminder
        self.add_template(MessageTemplate(
            id="pre_arrival",
            name="Lembrete Pré-Chegada",
            category=TemplateCategory.NOTIFICATION,
            channels=[TemplateChannel.WHATSAPP],
            body="""Olá {{ guest_name }}! 👋

Amanhã é o grande dia da sua chegada! 🎊

*Algumas informações úteis:*

📍 *Como chegar:*
{{ hotel_address }}
📱 GPS: {{ gps_coordinates }}

🚗 *Estacionamento:*
Gratuito para hóspedes

⏰ *Check-in:*
A partir das 14h
Quer adiantar? Me avise!

🌤️ *Previsão do tempo:*
{{ weather_forecast }}

💡 *Dica:*
{{ personalized_tip }}

Precisa de algo antes da chegada? É só me chamar!

Até amanhã! 😊"""
        ))

        # Check-in digital
        self.add_template(MessageTemplate(
            id="digital_checkin",
            name="Check-in Digital",
            category=TemplateCategory.CHECK_IN,
            channels=[TemplateChannel.WHATSAPP],
            body="""📱 *Check-in Digital Disponível!*

Olá {{ guest_name }},

Agilize sua chegada fazendo o check-in digital! 

✅ *É rápido e fácil:*
1. Clique no link abaixo
2. Confirme seus dados
3. Envie uma foto do documento
4. Pronto! 

🔗 {{ checkin_link }}

*Vantagens:*
• 🚀 Chegada mais rápida
• 🎁 Welcome drink de cortesia
• 🗝️ Chave do quarto pronta na chegada

O link expira em 24 horas.

Dúvidas? Me chame! 💬""",
            buttons=[
                {"type": "url", "text": "Fazer Check-in", "url": "{{ checkin_link }}"}
            ]
        ))

        # Payment PIX
        self.add_template(MessageTemplate(
            id="payment_pix",
            name="Pagamento PIX",
            category=TemplateCategory.PAYMENT,
            channels=[TemplateChannel.WHATSAPP],
            body="""💰 *Pagamento via PIX*

{{ guest_name }}, seu PIX foi gerado!

*Valor:* {{ amount | currency }}
*Vencimento:* {{ expiration }}

📱 *Chave PIX (copia e cola):*
```
{{ pix_key }}
```

*QR Code:*
{{ qr_code_url }}

✅ Após o pagamento:
• Confirmação automática
• Recibo por e-mail
• Reserva garantida

⚠️ Importante: O QR Code expira em {{ expiration_minutes }} minutos.""",
            media_urls=["{{ qr_code_url }}"]
        ))

        # Room upgrade offer
        self.add_template(MessageTemplate(
            id="room_upgrade_offer",
            name="Oferta de Upgrade",
            category=TemplateCategory.MARKETING,
            channels=[TemplateChannel.WHATSAPP],
            body="""🌟 *Oferta Especial para Você!*

{{ guest_name }}, que tal tornar sua estadia ainda mais especial?

🏨 *Upgrade disponível:*
De: {{ current_room }}
Para: {{ upgrade_room }}

✨ *Vantagens:*
{{ upgrade_benefits }}

💰 *Investimento:*
Apenas {{ upgrade_price | currency }} por diária
({{ discount_percentage }}% de desconto!)

🎁 *Bônus:* {{ bonus_offer }}

Oferta válida por 24h ou até acabar a disponibilidade.

Aceita? Responda com:
1️⃣ Sim, quero o upgrade!
2️⃣ Não, obrigado
3️⃣ Quero saber mais"""
        ))

        # Feedback request
        self.add_template(MessageTemplate(
            id="feedback_request",
            name="Solicitação de Feedback",
            category=TemplateCategory.FEEDBACK,
            channels=[TemplateChannel.WHATSAPP, TemplateChannel.EMAIL],
            subject="Como foi sua experiência no Hotel Passarim?",
            body="""Olá {{ guest_name }}! 👋

Espero que tenha tido uma excelente estadia conosco! 

Sua opinião é muito importante para continuarmos melhorando. Poderia dedicar 2 minutinhos para nos avaliar?

⭐ *Avalie sua experiência:*
{{ feedback_link }}

Como agradecimento, você ganhará:
🎁 10% de desconto na próxima reserva
🎁 Prioridade no check-in
🎁 Welcome drink especial

Se preferir, pode responder aqui mesmo:

*Como você avalia sua estadia de 0 a 10?*
*O que mais gostou?*
*O que podemos melhorar?*

Muito obrigado! 💚

{{ hotel_signature }}""",
            buttons=[
                {"type": "url", "text": "Avaliar Agora", "url": "{{ feedback_link }}"}
            ]
        ))

        # Error message
        self.add_template(MessageTemplate(
            id="error_generic",
            name="Mensagem de Erro",
            category=TemplateCategory.ERROR,
            channels=[TemplateChannel.WHATSAPP],
            body="""😔 Ops! Algo não saiu como esperado...

{{ guest_name }}, encontrei um probleminha ao processar sua solicitação.

{% if error_details %}
*Detalhes:* {{ error_details }}
{% endif %}

*O que você pode fazer:*
• Tentar novamente em alguns instantes
• Verificar se todos os dados estão corretos
• Me enviar a mensagem de outra forma

Se o problema persistir, vou transferir você para nossa equipe. 

Desculpe pelo transtorno! 🙏"""
        ))

        # Restaurant reservation
        self.add_template(MessageTemplate(
            id="restaurant_reservation",
            name="Reserva de Restaurante",
            category=TemplateCategory.RESERVATION,
            channels=[TemplateChannel.WHATSAPP],
            body="""🍽️ *Reserva no Restaurante Confirmada!*

{{ guest_name }}, sua mesa está reservada!

📅 *Data:* {{ reservation_date | date }}
⏰ *Horário:* {{ reservation_time }}
👥 *Pessoas:* {{ party_size }}
{% if special_occasion %}🎉 *Ocasião:* {{ special_occasion }}{% endif %}

{% if is_pasta_night %}
🍝 *Rodízio de Massas*
• Adultos: {{ adults }} x {{ adult_price | currency }}
• Crianças: {{ children }} x {{ child_price | currency }}
• Total: {{ total_price | currency }}

⚠️ *Lembre-se:* 
• Entrada até 30min após o horário
• Pagamento antecipado via PIX
• Cancelamento até 4h antes
{% endif %}

📍 *Local:* {{ restaurant_location }}

Alguma restrição alimentar ou pedido especial? Me avise!

Bom apetite! 🍴"""
        ))

        # Weather alert
        self.add_template(MessageTemplate(
            id="weather_alert",
            name="Alerta de Clima",
            category=TemplateCategory.NOTIFICATION,
            channels=[TemplateChannel.WHATSAPP],
            body="""☔ *Alerta de Tempo!*

{{ guest_name }}, 

{{ weather_condition }} previsto para hoje!

*Sugestões para aproveitar seu dia:*
{{ weather_suggestions }}

*Atividades indoor disponíveis:*
{{ indoor_activities }}

{% if special_offer %}
🎁 *Oferta especial de dia chuvoso:*
{{ special_offer }}
{% endif %}

Precisa de guarda-chuva? Temos na recepção! ☂️

Qualquer coisa, é só chamar! 😊"""
        ))

    def add_template(self, template: MessageTemplate) -> bool:
        """Add or update a template."""
        try:
            # Validate template syntax
            self._validate_template(template)

            # Store template
            self.templates[template.id] = template

            logger.info(
                "Template added/updated",
                template_id=template.id,
                name=template.name
            )
            return True

        except Exception as e:
            logger.error(
                "Failed to add template",
                template_id=template.id,
                error=str(e)
            )
            return False

    def _validate_template(self, template: MessageTemplate):
        """Validate template syntax."""
        try:
            # Test render with dummy data
            dummy_context = {var: f"test_{var}" for var in template.variables}

            # Validate body
            Template(template.body).render(**dummy_context)

            # Validate subject if present
            if template.subject:
                Template(template.subject).render(**dummy_context)

        except TemplateError as e:
            raise ValueError(f"Invalid template syntax: {e}")

    def render(
            self,
            template_id: str,
            context: Dict[str, Any],
            channel: Optional[TemplateChannel] = None
    ) -> Dict[str, Any]:
        """
        Render a template with context.
        
        Args:
            template_id: Template identifier
            context: Variables to render
            channel: Target channel (for channel-specific formatting)
            
        Returns:
            Rendered message with all components
        """
        template = self.templates.get(template_id)
        if not template:
            raise ValueError(f"Template not found: {template_id}")

        if not template.is_active:
            raise ValueError(f"Template is inactive: {template_id}")

        # Check channel compatibility
        if channel and channel not in template.channels:
            raise ValueError(
                f"Template {template_id} doesn't support channel {channel.value}"
            )

        try:
            # Create Jinja2 template
            body_template = self.env.from_string(template.body)

            # Render body
            rendered_body = body_template.render(**context)

            # Apply channel-specific formatting
            if channel:
                rendered_body = self._format_for_channel(rendered_body, channel)

            # Build response
            result = {
                "body": rendered_body,
                "media_urls": [],
                "buttons": template.buttons.copy()
            }

            # Render subject if present
            if template.subject:
                subject_template = self.env.from_string(template.subject)
                result["subject"] = subject_template.render(**context)

            # Render media URLs
            for media_url in template.media_urls:
                if "{{" in media_url:
                    media_template = self.env.from_string(media_url)
                    rendered_url = media_template.render(**context)
                    result["media_urls"].append(rendered_url)
                else:
                    result["media_urls"].append(media_url)

            # Render button URLs
            for button in result["buttons"]:
                if "url" in button and "{{" in button["url"]:
                    url_template = self.env.from_string(button["url"])
                    button["url"] = url_template.render(**context)

            return result

        except Exception as e:
            logger.error(
                "Template rendering failed",
                template_id=template_id,
                error=str(e)
            )
            raise

    def _format_for_channel(self, text: str, channel: TemplateChannel) -> str:
        """Apply channel-specific formatting."""
        if channel == TemplateChannel.WHATSAPP:
            # WhatsApp uses * for bold, _ for italic
            # Already in the templates
            return text

        elif channel == TemplateChannel.EMAIL:
            # Convert WhatsApp formatting to HTML
            text = re.sub(r'\*([^*]+)\*', r'<strong>\1</strong>', text)
            text = re.sub(r'_([^_]+)_', r'<em>\1</em>', text)
            text = text.replace('\n', '<br>\n')
            return text

        elif channel == TemplateChannel.SMS:
            # Remove formatting for SMS
            text = re.sub(r'\*([^*]+)\*', r'\1', text)
            text = re.sub(r'_([^_]+)_', r'\1', text)
            # Shorten if needed (SMS limit)
            if len(text) > 160:
                text = text[:157] + "..."
            return text

        return text

    def _format_currency(self, value: Union[float, str, Money]) -> str:
        """Format currency for display."""
        if isinstance(value, Money):
            return str(value)

        try:
            amount = float(value)
            return f"R$ {amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        except (ValueError, TypeError):
            return str(value)

    def _format_date(self, value: Union[str, date, datetime]) -> str:
        """Format date for display."""
        if isinstance(value, str):
            try:
                # Try to parse ISO format
                if "T" in value:
                    value = datetime.fromisoformat(value.replace("Z", "+00:00"))
                else:
                    value = date.fromisoformat(value)
            except ValueError:
                return value

        if isinstance(value, datetime):
            return value.strftime("%d/%m/%Y às %H:%M")
        elif isinstance(value, date):
            return value.strftime("%d/%m/%Y")

        return str(value)

    def _format_phone(self, value: str) -> str:
        """Format phone number for display."""
        # Remove non-digits
        digits = re.sub(r'[^\d]', '', value)

        if len(digits) == 11:
            # Brazilian mobile
            return f"({digits[:2]}) {digits[2:7]}-{digits[7:]}"
        elif len(digits) == 10:
            # Brazilian landline
            return f"({digits[:2]}) {digits[2:6]}-{digits[6:]}"

        return value

    def get_template(self, template_id: str) -> Optional[MessageTemplate]:
        """Get template by ID."""
        return self.templates.get(template_id)

    def list_templates(
            self,
            category: Optional[TemplateCategory] = None,
            channel: Optional[TemplateChannel] = None,
            active_only: bool = True
    ) -> List[MessageTemplate]:
        """List templates with optional filters."""
        templates = list(self.templates.values())

        if category:
            templates = [t for t in templates if t.category == category]

        if channel:
            templates = [t for t in templates if channel in t.channels]

        if active_only:
            templates = [t for t in templates if t.is_active]

        return templates

    def get_required_variables(self, template_id: str) -> List[str]:
        """Get required variables for a template."""
        template = self.templates.get(template_id)
        if not template:
            return []

        return template.variables

    def validate_context(
            self,
            template_id: str,
            context: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        """
        Validate if context has all required variables.
        
        Returns:
            Tuple of (is_valid, missing_variables)
        """
        template = self.templates.get(template_id)
        if not template:
            return False, ["template_not_found"]

        missing = []
        for var in template.variables:
            if var not in context:
                missing.append(var)

        return len(missing) == 0, missing

    def clone_template(
            self,
            template_id: str,
            new_id: str,
            new_name: str,
            modifications: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Clone an existing template with modifications."""
        original = self.templates.get(template_id)
        if not original:
            return False

        # Create copy
        new_template = MessageTemplate(
            id=new_id,
            name=new_name,
            category=original.category,
            channels=original.channels.copy(),
            subject=original.subject,
            body=original.body,
            media_urls=original.media_urls.copy(),
            buttons=[b.copy() for b in original.buttons],
            metadata=original.metadata.copy()
        )

        # Apply modifications
        if modifications:
            for key, value in modifications.items():
                if hasattr(new_template, key):
                    setattr(new_template, key, value)

        return self.add_template(new_template)

    def export_templates(self) -> str:
        """Export all templates as JSON."""
        export_data = []

        for template in self.templates.values():
            export_data.append({
                "id": template.id,
                "name": template.name,
                "category": template.category.value,
                "channels": [c.value for c in template.channels],
                "subject": template.subject,
                "body": template.body,
                "media_urls": template.media_urls,
                "buttons": template.buttons,
                "variables": template.variables,
                "metadata": template.metadata,
                "is_active": template.is_active
            })

        return json.dumps(export_data, indent=2, ensure_ascii=False)

    def import_templates(self, json_data: str) -> Tuple[int, List[str]]:
        """
        Import templates from JSON.
        
        Returns:
            Tuple of (success_count, error_messages)
        """
        success_count = 0
        errors = []

        try:
            data = json.loads(json_data)

            for item in data:
                try:
                    template = MessageTemplate(
                        id=item["id"],
                        name=item["name"],
                        category=TemplateCategory(item["category"]),
                        channels=[TemplateChannel(c) for c in item["channels"]],
                        subject=item.get("subject"),
                        body=item["body"],
                        media_urls=item.get("media_urls", []),
                        buttons=item.get("buttons", []),
                        metadata=item.get("metadata", {}),
                        is_active=item.get("is_active", True)
                    )

                    if self.add_template(template):
                        success_count += 1
                    else:
                        errors.append(f"Failed to add template: {item['id']}")

                except Exception as e:
                    errors.append(f"Error in template {item.get('id', 'unknown')}: {e}")

        except json.JSONDecodeError as e:
            errors.append(f"Invalid JSON: {e}")

        return success_count, errors


# Singleton instance
_template_engine = None


def get_template_engine() -> TemplateEngine:
    """Get or create template engine instance."""
    global _template_engine

    if _template_engine is None:
        _template_engine = TemplateEngine()

    return _template_engine


# Convenience functions
def render_template(
        template_id: str,
        context: Dict[str, Any],
        channel: Optional[TemplateChannel] = None
) -> Dict[str, Any]:
    """Render a template with context."""
    engine = get_template_engine()
    return engine.render(template_id, context, channel)


def send_templated_message(
        phone: str,
        template_id: str,
        context: Dict[str, Any]
) -> str:
    """Send a templated message via WhatsApp."""
    from app.integrations.whatsapp import WhatsAppClient

    # Render template
    engine = get_template_engine()
    rendered = engine.render(template_id, context, TemplateChannel.WHATSAPP)

    # Send message
    client = WhatsAppClient()
    return asyncio.run(
        client.send_message(
            to=phone,
            body=rendered["body"],
            media_urls=rendered.get("media_urls")
        )
    )
