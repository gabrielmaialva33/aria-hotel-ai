# 📚 Guia Completo de Implementação - ARIA Hotel AI v2.0

## 🌟 Visão Geral

O ARIA Hotel AI é um sistema completo de concierge com IA multimodal para hotéis, oferecendo:

- **IA Conversacional Avançada** com processamento de linguagem natural
- **Processamento Multimodal** (texto, voz, imagem, documentos)
- **Sistema de Pagamentos** integrado (Stripe, MercadoPago/PIX)
- **Autenticação e Autorização** robusta com RBAC
- **Observabilidade Completa** com OpenTelemetry e Prometheus
- **Templates de Mensagens** personalizáveis
- **Notificações Proativas** baseadas em eventos
- **Analytics em Tempo Real** com dashboards

## 📦 Componentes Implementados

### 1. **Core AI System**

#### NLP Avançado (`nlp_processor.py`)
```python
from aria.agents.ana.nlp_processor import NLPProcessor

# Processa mensagens com detecção de intenção e entidades
nlp = NLPProcessor()
result = await nlp.process("Quero reservar para páscoa, 2 adultos")

# Resultado inclui:
# - intent: RESERVATION_INQUIRY
# - entities: [date: "2025-04-20", adults: 2]
# - sentiment: positive
# - language: pt
```

#### Vision Processing (`vision_processor.py`)
```python
from aria.tools.vision_processor import VisionProcessor

# Processa documentos para check-in digital
vision = VisionProcessor()
result = await vision.process_image("https://example.com/cpf.jpg")

# Extrai e valida:
# - CPF, RG, Passaporte
# - QR codes (PIX, reservas)
# - Análise de fotos
```

#### Agent Melhorado (`improved_agent.py`)
```python
from aria.agents.ana.improved_agent import ImprovedAnaAgent

agent = ImprovedAnaAgent()
response = await agent.process_message(
    phone="+5511999999999",
    message="Estou insatisfeito com o serviço",
    context={"name": "João"}
)

# Features:
# - Quick replies automáticas
# - Detecção de sentimento negativo
# - Transferência inteligente
# - Contexto persistente
```

### 2. **Payment System** 💳

#### Gateway Unificado (`payments/gateway.py`)
```python
from aria.payments.gateway import get_payment_gateway, PaymentRequest

gateway = get_payment_gateway()

# Processo de pagamento PIX
response = await gateway.create_pix_payment(
    amount=Money(Decimal("580.00"), "BRL"),
    customer_id="guest_123",
    order_id="RES-20250120-ABCD",
    description="Reserva Hotel Passarim"
)

# Retorna:
# - QR Code para pagamento
# - Chave PIX copia e cola
# - Status em tempo real
```

**Providers Suportados:**
- **Stripe**: Cartões internacionais
- **MercadoPago**: PIX, cartões nacionais, boleto

### 3. **Security & Auth** 🔐

#### Sistema de Autenticação (`auth/security.py`)
```python
from aria.auth.security import AuthService, require_permissions, UserRole

# Criar token JWT
auth = AuthService()
token = auth.create_access_token(user)

# Proteger endpoints
@router.post("/refund")
async def issue_refund(
    user = Depends(require_permissions(Permission.ISSUE_REFUNDS))
):
    # Apenas usuários com permissão podem acessar
    pass

# Rate limiting
@router.get("/api/data", dependencies=[Depends(RateLimiter(max_requests=100))])
async def protected_endpoint():
    pass
```

**Features:**
- JWT com refresh tokens
- RBAC (Role-Based Access Control)
- API Keys para integrações
- Rate limiting por usuário
- Session management com Redis

### 4. **Observability** 📊

#### Monitoramento Completo (`observability/monitoring.py`)
```python
from aria.observability.monitoring import (
    monitor_async,
    setup_monitoring,
    metrics_collector
)

# Decorador para monitorar funções
@monitor_async(name="process_reservation")
async def process_reservation(data):
    # Automaticamente:
    # - Cria spans de tracing
    # - Registra métricas
    # - Captura erros
    pass

# Métricas customizadas
metrics_collector.record_payment(
    provider="mercadopago",
    method="pix",
    status="success"
)
```

**Integrações:**
- **OpenTelemetry**: Distributed tracing
- **Prometheus**: Métricas
- **Sentry**: Error tracking
- **Health checks**: Database, Redis, AI

### 5. **Message Templates** 📝

#### Sistema de Templates (`messaging/templates.py`)
```python
from aria.messaging.templates import get_template_engine, TemplateChannel

engine = get_template_engine()

# Renderizar template
result = engine.render(
    template_id="reservation_confirmed",
    context={
        "guest_name": "João",
        "booking_reference": "RES-123",
        "check_in": date(2025, 3, 20),
        "total_amount": Money(Decimal("580.00"))
    },
    channel=TemplateChannel.WHATSAPP
)

# Resultado formatado para WhatsApp com:
# - Texto com formatação (*bold*, _italic_)
# - Botões interativos
# - Imagens/documentos anexos
```

**Templates Incluídos:**
- Boas-vindas e saudações
- Confirmação de reserva
- Check-in digital
- Pagamento PIX
- Solicitação de feedback
- Ofertas personalizadas
- Alertas meteorológicos

### 6. **Proactive Notifications** 🔔

#### Sistema de Notificações (`notifications/proactive.py`)
```python
from aria.core.notifications.proactive import NotificationEngine

engine = NotificationEngine()

# Verifica e agenda notificações
await engine.check_and_schedule_notifications()

# Triggers automáticos:
# - 1 dia antes do check-in
# - Dia da chegada
# - Durante a estadia
# - Pós checkout
# - Aniversários
# - Ofertas especiais
```

### 7. **Domain-Driven Design** 🏛️

#### Value Objects
```python
from aria.domain.shared.value_objects import Email, Phone, Money, Document

# Email com validação
email = Email("joao@example.com")

# Telefone brasileiro
phone = Phone("+5511999999999")

# Dinheiro com operações
price = Money(Decimal("290.00"), "BRL")
total = price * 2  # R$ 580,00

# Documento com validação
cpf = Document(type="cpf", number="123.456.789-00")
```

#### Entities & Aggregates
```python
from aria.domain.guest.entities import Guest
from aria.domain.reservation.entities import Reservation

# Guest com eventos de domínio
guest = Guest(
    name="João Silva",
    email=Email("joao@example.com"),
    phone=Phone("+5511999999999")
)

# Eventos são disparados automaticamente
guest.join_loyalty_program()  # Dispara LoyaltyProgramJoined
guest.earn_loyalty_points(100, "reservation")  # Dispara PointsEarned
```

### 8. **Analytics Dashboard** 📈

#### Real-time Analytics (`analytics/dashboard.py`)
```python
from aria.analytics.dashboard import AnalyticsDashboard

dashboard = AnalyticsDashboard()
metrics = await dashboard.get_dashboard_metrics()

# Métricas incluem:
# - Taxa de ocupação
# - ADR e RevPAR
# - Taxa de resolução da IA
# - NPS e sentimento
# - Tendências e alertas
```

### 9. **Memory System** 🧠

#### Vector Store (`memory/vector_store.py`)
```python
from aria.core.memory.vector_store import get_memory_store

store = await get_memory_store()

# Adicionar memória
await store.add_memory(
    guest_id="guest_123",
    content="Prefere quarto no andar superior",
    metadata={"type": "preference"}
)

# Busca semântica
results = await store.search_memories(
    query="preferências de quarto",
    guest_id="guest_123"
)

# Perfil do hóspede
profile = await store.get_guest_profile("guest_123")
```

## 🚀 Como Implantar em Produção

### 1. **Configuração de Ambiente**

```bash
# .env para produção
APP_ENV=production
APP_DEBUG=false
LOG_LEVEL=INFO

# APIs
OPENAI_API_KEY=sk-...
GROQ_API_KEY=gsk-...
GEMINI_API_KEY=AIza...

# Pagamentos
STRIPE_API_KEY=sk_live_...
MERCADOPAGO_ACCESS_TOKEN=APP_USR-...

# Segurança
JWT_SECRET_KEY=$(openssl rand -hex 32)
PAYMENT_ENCRYPTION_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

# Observabilidade
SENTRY_DSN=https://...@sentry.io/...
OTLP_ENDPOINT=https://otel-collector:4317
```

### 2. **Deploy com Docker**

```yaml
# docker-compose.production.yml
version: '3.8'

services:
  aria-api:
    image: aria-hotel-ai:latest
    environment:
      - APP_ENV=production
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '2'
          memory: 4G
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3

  nginx:
    image: nginx:alpine
    volumes:
      - ./config/nginx.prod.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    ports:
      - "443:443"
      - "80:80"

  postgres:
    image: postgres:16
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_PASSWORD_FILE=/run/secrets/db_password
    secrets:
      - db_password

  redis-sentinel:
    image: redis:7-alpine
    command: redis-sentinel /etc/redis-sentinel.conf
    volumes:
      - ./config/sentinel.conf:/etc/redis-sentinel.conf

volumes:
  postgres_data:
    driver: local

secrets:
  db_password:
    external: true
```

### 3. **Kubernetes Deployment**

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: aria-hotel-ai
spec:
  replicas: 3
  selector:
    matchLabels:
      app: aria-hotel-ai
  template:
    metadata:
      labels:
        app: aria-hotel-ai
    spec:
      containers:
      - name: aria
        image: aria-hotel-ai:latest
        ports:
        - containerPort: 8000
        env:
        - name: APP_ENV
          value: "production"
        envFrom:
        - secretRef:
            name: aria-secrets
        resources:
          requests:
            memory: "2Gi"
            cpu: "1"
          limits:
            memory: "4Gi"
            cpu: "2"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: aria-service
spec:
  selector:
    app: aria-hotel-ai
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
```

### 4. **CI/CD Pipeline**

```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Run tests
      run: |
        docker-compose -f docker-compose.test.yml up --abort-on-container-exit
        
    - name: Security scan
      uses: snyk/actions/python@master
      with:
        args: --severity-threshold=high

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
    - name: Build and push Docker image
      env:
        DOCKER_REGISTRY: ${{ secrets.DOCKER_REGISTRY }}
      run: |
        docker build -t $DOCKER_REGISTRY/aria-hotel-ai:${{ github.sha }} .
        docker push $DOCKER_REGISTRY/aria-hotel-ai:${{ github.sha }}

  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
    - name: Deploy to Kubernetes
      run: |
        kubectl set image deployment/aria-hotel-ai \
          aria=$DOCKER_REGISTRY/aria-hotel-ai:${{ github.sha }}
        kubectl rollout status deployment/aria-hotel-ai
```

## 📊 Monitoramento em Produção

### Dashboards Grafana

```json
{
  "dashboard": {
    "title": "ARIA Hotel AI - Production",
    "panels": [
      {
        "title": "Request Rate",
        "targets": [{
          "expr": "rate(aria_http_requests_total[5m])"
        }]
      },
      {
        "title": "AI Resolution Rate",
        "targets": [{
          "expr": "aria_messages_processed_total{status='success'} / aria_messages_processed_total"
        }]
      },
      {
        "title": "Payment Success Rate",
        "targets": [{
          "expr": "aria_payment_transactions_total{status='captured'} / aria_payment_transactions_total"
        }]
      }
    ]
  }
}
```

### Alertas Prometheus

```yaml
# prometheus/alerts.yml
groups:
- name: aria_alerts
  rules:
  - alert: HighErrorRate
    expr: rate(aria_http_requests_total{status_code=~"5.."}[5m]) > 0.05
    for: 5m
    annotations:
      summary: "High error rate detected"
      
  - alert: LowAIResolution
    expr: aria_ai_resolution_rate < 0.7
    for: 10m
    annotations:
      summary: "AI resolution rate below 70%"
      
  - alert: PaymentFailures
    expr: rate(aria_payment_transactions_total{status="failed"}[5m]) > 0.1
    for: 5m
    annotations:
      summary: "High payment failure rate"
```

## 🔒 Checklist de Segurança

- [x] **Autenticação**: JWT com refresh tokens
- [x] **Autorização**: RBAC com permissões granulares
- [x] **Rate Limiting**: Por usuário e endpoint
- [x] **Encriptação**: Dados sensíveis encriptados
- [x] **Validação**: Input validation em todos os endpoints
- [x] **CORS**: Configurado para domínios autorizados
- [x] **Headers de Segurança**: CSP, HSTS, X-Frame-Options
- [x] **Secrets Management**: Variáveis de ambiente e vault
- [x] **Audit Logging**: Todas as ações críticas
- [x] **LGPD Compliance**: Anonimização e direito ao esquecimento

## 📈 Métricas de Sucesso

### KPIs Técnicos
- **Uptime**: > 99.95%
- **Latência P95**: < 500ms
- **Taxa de Erro**: < 0.1%
- **Resolução por IA**: > 85%

### KPIs de Negócio
- **Taxa de Conversão**: +25%
- **NPS**: > 70
- **Tempo de Resposta**: < 30s
- **Economia Operacional**: 40%

## 🚨 Troubleshooting

### Problemas Comuns

#### 1. Rate Limit Exceeded
```python
# Aumentar limite para usuário específico
await auth_service.redis_client.delete(f"rate_limit:{user_id}")
```

#### 2. Memory Store Lento
```python
# Rebuild índice FAISS
await memory_store._rebuild_index()
```

#### 3. Pagamento PIX Não Aparece
```bash
# Verificar webhook MercadoPago
curl -X POST https://api.mercadopago.com/v1/webhooks/test \
  -H "Authorization: Bearer $MP_ACCESS_TOKEN"
```

## 📞 Suporte e Contato

- **Documentação**: https://aria-hotel-ai.readthedocs.io
- **Issues**: https://github.com/gabrielmaia/aria-hotel-ai/issues
- **Email**: support@aria-hotel-ai.com
- **Discord**: https://discord.gg/aria-hotel-ai

---

**ARIA Hotel AI v2.0** - Transformando a hospitalidade com inteligência artificial 🚀
