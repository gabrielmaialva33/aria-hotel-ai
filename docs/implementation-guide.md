# Guia de Implementação ARIA Hotel AI

## Fase 1: Implementação do MVP

### 1. Configuração da Ana (Agente Principal)

Primeiro, vamos implementar a Ana seguindo o prompt do Hotel Passarim.

#### 1.1 Estrutura de Dados da Ana

```python
# src/aria/agents/ana/models.py
from enum import Enum
from datetime import date
from typing import Optional, List, Dict
from pydantic import BaseModel

class RoomType(str, Enum):
    TERREO = "terreo"
    SUPERIOR = "superior"

class MealPlan(str, Enum):
    CAFE_DA_MANHA = "cafe_da_manha"
    MEIA_PENSAO = "meia_pensao"
    PENSAO_COMPLETA = "pensao_completa"

class ReservationRequest(BaseModel):
    check_in: date
    check_out: date
    adults: int
    children: List[int] = []  # Lista com as idades
    room_type: Optional[RoomType] = None
    meal_plan: Optional[MealPlan] = None
    
class Pricing(BaseModel):
    room_type: RoomType
    meal_plan: MealPlan
    adults: int
    children: List[int]
    nights: int
    total: float
    breakdown: Dict[str, float]
```

#### 1.2 Base de Conhecimento

```python
# src/aria/agents/ana/knowledge_base.py
HOTEL_INFO = {
    "name": "Hotel Passarim",
    "location": "Capão Bonito",
    "check_in_time": "14:00",
    "check_out_time": "12:00",
    "wifi_password": "passarim2025",
    "restaurant_hours": {
        "breakfast": "07:00-11:00",
        "lunch": "12:00-15:00",
        "dinner": "19:30-22:00"
    }
}

PRICING_TABLE = {
    "normal": {
        "terreo": {
            1: {"cafe": 199, "meia": 279, "completa": 359},
            2: {"cafe": 290, "meia": 460, "completa": 610},
            3: {"cafe": 350, "meia": 590, "completa": 830},
            4: {"cafe": 420, "meia": 740, "completa": 1060}
        },
        "superior": {
            1: {"cafe": 239, "meia": 319, "completa": 399},
            2: {"cafe": 350, "meia": 520, "completa": 670},
            3: {"cafe": 420, "meia": 660, "completa": 900},
            4: {"cafe": 490, "meia": 840, "completa": 1130}
        }
    }
}

HOLIDAYS = {
    "pascoa_2025": {
        "start": date(2025, 4, 17),
        "end": date(2025, 4, 21),
        "min_nights": 3,
        "packages": {...}
    }
}
```

### 2. Integração WhatsApp com Twilio

#### 2.1 Cliente WhatsApp

```python
# src/aria/integrations/whatsapp/client.py
from twilio.rest import Client
from aria.core.config import settings
from aria.core.logging import get_logger

logger = get_logger(__name__)

class WhatsAppClient:
    def __init__(self):
        self.client = Client(
            settings.twilio_account_sid,
            settings.twilio_auth_token
        )
        self.from_number = settings.twilio_whatsapp_number
        
    async def send_message(
        self, 
        to: str, 
        body: str,
        media_urls: List[str] = None
    ):
        """Envia mensagem WhatsApp"""
        try:
            message = self.client.messages.create(
                body=body,
                from_=self.from_number,
                to=f"whatsapp:{to}",
                media_url=media_urls or []
            )
            logger.info("WhatsApp message sent", 
                       message_sid=message.sid,
                       to=to)
            return message.sid
        except Exception as e:
            logger.error("Failed to send WhatsApp", 
                        error=str(e), to=to)
            raise
```

#### 2.2 Webhook Handler

```python
# src/aria/api/webhooks/whatsapp.py
from fastapi import APIRouter, Request, HTTPException
from aria.agents.ana import AnaAgent
from aria.integrations.whatsapp import WhatsAppClient

router = APIRouter()
whatsapp = WhatsAppClient()
ana = AnaAgent()

@router.post("/webhooks/whatsapp")
async def handle_whatsapp_message(request: Request):
    """Processa mensagens recebidas do WhatsApp"""
    data = await request.form()
    
    # Extrai dados da mensagem
    from_number = data.get("From", "").replace("whatsapp:", "")
    message_body = data.get("Body", "")
    media_url = data.get("MediaUrl0")  # Primeira imagem, se houver
    
    # Processa com a Ana
    response = await ana.process_message(
        phone=from_number,
        message=message_body,
        media_url=media_url
    )
    
    # Envia resposta
    await whatsapp.send_message(
        to=from_number,
        body=response.text,
        media_urls=response.media_urls
    )
    
    return {"status": "ok"}
```

### 3. Implementação da Ana com Agno

#### 3.1 Agente Ana

```python
# src/aria/agents/ana/agent.py
from agno import Agent, Tool
from aria.agents.ana.knowledge_base import HOTEL_INFO, PRICING_TABLE
from aria.agents.ana.calculator import PricingCalculator
from aria.agents.ana.prompts import ANA_SYSTEM_PROMPT

class AnaAgent(Agent):
    def __init__(self):
        super().__init__(
            name="Ana",
            system_prompt=ANA_SYSTEM_PROMPT,
            model="gpt-4-turbo",
            tools=[
                self.calculate_pricing,
                self.check_availability,
                self.generate_omnibees_link,
                self.transfer_to_reception
            ]
        )
        self.calculator = PricingCalculator()
        
    @Tool(description="Calcula valores de hospedagem")
    async def calculate_pricing(
        self,
        check_in: str,
        check_out: str,
        adults: int,
        children: List[int] = []
    ):
        """Calcula valores seguindo as regras do Hotel Passarim"""
        # Implementação do cálculo
        pass
        
    @Tool(description="Verifica disponibilidade")
    async def check_availability(
        self,
        check_in: str,
        check_out: str,
        room_type: str = None
    ):
        """Verifica disponibilidade de quartos"""
        # Integração com PMS ou banco local
        pass
```

### 4. Banco de Dados e Cache

#### 4.1 Modelos SQLAlchemy

```python
# src/aria/core/database/models.py
from sqlalchemy import Column, String, JSON, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
import uuid

Base = declarative_base()

class Guest(Base):
    __tablename__ = "guests"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255))
    phone = Column(String(50), unique=True, index=True)
    email = Column(String(255))
    preferences = Column(JSON, default={})
    created_at = Column(DateTime, server_default="now()")
    
class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    guest_id = Column(UUID(as_uuid=True), ForeignKey("guests.id"))
    channel = Column(String(50))  # whatsapp, voice, web
    thread_id = Column(String(255))
    context = Column(JSON, default={})
    created_at = Column(DateTime, server_default="now()")
```

#### 4.2 Redis Session Manager

```python
# src/aria/core/sessions.py
import json
from datetime import datetime, timedelta
import redis.asyncio as redis
from aria.core.config import settings

class SessionManager:
    def __init__(self):
        self.redis = redis.from_url(
            str(settings.redis_url),
            decode_responses=True
        )
        self.ttl = timedelta(hours=24)
        
    async def get_session(self, phone: str) -> dict:
        """Recupera sessão do usuário"""
        key = f"session:whatsapp:{phone}"
        data = await self.redis.get(key)
        return json.loads(data) if data else {}
        
    async def save_session(self, phone: str, data: dict):
        """Salva sessão do usuário"""
        key = f"session:whatsapp:{phone}"
        data["last_activity"] = datetime.now().isoformat()
        await self.redis.setex(
            key,
            self.ttl,
            json.dumps(data)
        )
```

### 5. Sistema de Filas para Processamento

```python
# src/aria/core/queue.py
from celery import Celery
from aria.core.config import settings

celery_app = Celery(
    "aria",
    broker=str(settings.redis_url),
    backend=str(settings.redis_url)
)

@celery_app.task
def process_check_in(reservation_id: str):
    """Processa check-in em background"""
    pass

@celery_app.task
def send_marketing_message(guest_id: str, template: str):
    """Envia mensagem de marketing"""
    pass
```

### 6. API Principal

```python
# src/aria/api/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from aria.api.webhooks import whatsapp, voice
from aria.api.routes import reservations, services, payments
from aria.core.config import settings

app = FastAPI(
    title="ARIA Hotel AI",
    version="0.1.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rotas
app.include_router(whatsapp.router, tags=["webhooks"])
app.include_router(voice.router, tags=["webhooks"]) 
app.include_router(reservations.router, prefix="/api/v1")
app.include_router(services.router, prefix="/api/v1")
app.include_router(payments.router, prefix="/api/v1")

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
```

## Próximos Passos

1. **Configurar ambiente Twilio**:
   - Criar conta e obter credenciais
   - Configurar sandbox WhatsApp
   - Apontar webhooks para sua aplicação

2. **Implementar testes**:
   - Testes unitários para cálculo de preços
   - Testes de integração para WhatsApp
   - Testes e2e para fluxos completos

3. **Deploy inicial**:
   - Dockerizar aplicação
   - Deploy em cloud (AWS/GCP/Azure)
   - Configurar domínio e SSL

4. **Iteração e melhorias**:
   - Coletar feedback
   - Implementar novas features
   - Otimizar performance

## Estrutura de Diretórios Recomendada

```
src/aria/
├── agents/
│   ├── ana/
│   │   ├── __init__.py
│   │   ├── agent.py
│   │   ├── calculator.py
│   │   ├── knowledge_base.py
│   │   ├── models.py
│   │   └── prompts.py
│   ├── checkin/
│   ├── services/
│   └── marketing/
├── api/
│   ├── __init__.py
│   ├── main.py
│   ├── webhooks/
│   │   ├── whatsapp.py
│   │   └── voice.py
│   └── routes/
│       ├── reservations.py
│       ├── services.py
│       └── payments.py
├── integrations/
│   ├── whatsapp/
│   │   ├── client.py
│   │   └── templates.py
│   ├── twilio/
│   ├── omnibees/
│   └── payment/
├── modules/
│   ├── booking/
│   ├── checkin/
│   └── services/
└── core/
    ├── database/
    ├── cache/
    └── queue/
```