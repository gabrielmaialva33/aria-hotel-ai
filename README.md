# ARIA Hotel AI 🏨🤖

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Agno Framework](https://img.shields.io/badge/Agno-0.1.42+-green.svg)](https://agno.dev)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109.0+-teal.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

ARIA Hotel AI é um sistema completo de assistente virtual para hotéis, alimentado pelo framework **Agno** e modelos de IA avançados. O sistema oferece atendimento automatizado via WhatsApp, check-in digital, gestão de serviços e muito mais.

## 🌟 Principais Funcionalidades

### 🤖 Ana - Assistente Virtual Inteligente (Powered by Agno)
- **Atendimento 24/7** via WhatsApp usando Agno Framework
- **Cálculo automático** de tarifas e disponibilidade
- **Check-in digital** sem filas
- **Extrato de conta** em tempo real
- **Pagamentos integrados** com geração de links
- **Marketing personalizado** baseado em preferências
- **Análise de imagens** para documentos e solicitações visuais
- **Suporte multilíngue** (Português e Inglês)

### 📱 Recursos para Hóspedes
- ✅ Reservas instantâneas via WhatsApp
- ✅ Check-in/check-out automático
- ✅ Solicitação de serviços (room service, limpeza, etc)
- ✅ Informações do hotel (WiFi, restaurante, lazer)
- ✅ Pagamento facilitado (PIX com desconto, cartão)
- ✅ Histórico de preferências e personalização

### 🏨 Benefícios para o Hotel
- 📊 Redução de 70% nas chamadas para recepção
- 💰 Aumento de 25% em upselling via marketing direcionado
- ⚡ Check-in 3x mais rápido
- 📈 Analytics e insights em tempo real
- 🔄 Integração com sistemas existentes (PMS, PDV)
- 🎯 Pesquisa de satisfação automatizada

## 🚀 Quick Start

### Pré-requisitos
- Python 3.11+
- Redis
- PostgreSQL
- Conta Twilio (para WhatsApp)
- API Key do Google Gemini

### Instalação

1. **Clone o repositório:**
```bash
git clone https://github.com/gabrielmaia/aria-hotel-ai.git
cd aria-hotel-ai
```

2. **Configure o ambiente:**
```bash
# Copie o arquivo de exemplo
cp .env.example .env

# Edite com suas credenciais
nano .env
```

3. **Instale as dependências:**
```bash
# Criar ambiente virtual
python -m venv venv
source venv/bin/activate  # No Windows: venv\Scripts\activate

# Instalar dependências
pip install -r requirements.txt
# ou via pip install -e .
```

4. **Inicialize o banco de dados:**
```bash
# Subir containers Docker
docker-compose up -d postgres redis

# Rodar migrations (se aplicável)
python -m app.cli db init
```

5. **Execute o sistema:**
```bash
# Modo desenvolvimento
python main.py

# Ou usando o CLI
aria serve
```

## 🏗️ Arquitetura

```
aria-hotel-ai/
├── app/                    # Application code
│   ├── agents/            # AI agents
│   │   └── ana/           # Ana assistant agent (Agno-powered)
│   │       ├── agent.py   # Main agent implementation
│   │       ├── models.py  # Data models
│   │       ├── calculator.py # Pricing logic
│   │       └── prompts.py # System prompts
│   ├── api/               # FastAPI endpoints and webhooks
│   │   ├── webhooks/      # WhatsApp, voice, etc.
│   │   └── main.py        # Main FastAPI app
│   ├── core/              # Core functionality
│   │   ├── config.py      # Configuration management
│   │   ├── logging.py     # Structured logging
│   │   └── sessions.py    # Session management
│   ├── integrations/      # External integrations
│   │   ├── whatsapp/      # WhatsApp/Twilio
│   │   └── omnibees/      # PMS integration
│   ├── models/            # Data models (Pydantic)
│   └── services/          # Business logic
├── tests/                 # Test suite
├── examples/              # Usage examples
├── docs/                  # Documentation
└── main.py               # Entry point
```

## 🔧 Configuração do Agno

O Ana Agent usa o Agno Framework para processamento inteligente:

```python
from agno.agent import Agent
from agno.models.google import Gemini

# Configuração do agente
self.agent = Agent(
    model=Gemini(id="gemini-2.0-flash"),
    system_prompt=ANA_SYSTEM_PROMPT,
    tools=[
        self.calculate_pricing,
        self.check_availability,
        self.process_check_in,
        self.generate_payment_link,
        # ... outras ferramentas
    ],
    markdown=True,
    temperature=0.7,
)
```

## 📡 Webhooks e Integrações

### WhatsApp (Twilio)
```
POST /webhooks/whatsapp
```

### Sistemas do Hotel
- **PMS**: Integração para reservas e check-in
- **PDV**: Consumer/Sischef para restaurante  
- **Pagamentos**: Gateway com PIX e cartões
- **Omnibees**: Sistema de reservas online

## 🧪 Testing

### Executar testes unitários:
```bash
pytest tests/
# Com coverage
pytest --cov=app
```

### Testar o agente Ana:
```bash
python examples/test_ana_agno.py
```

### Teste via CLI:
```bash
# Test WhatsApp
aria test-whatsapp +5511999999999

# Test Ana agent
aria test-ana "Olá, quais quartos disponíveis?"

# Calculate pricing
aria calculate-price 2024-07-20 2024-07-25 2 --children 5,8
```

## 📊 Monitoramento

O sistema inclui:
- **Prometheus** para métricas
- **Grafana** para dashboards
- **Logs estruturados** com structlog
- **Health checks** em `/health`

Acesse:
- API Docs: http://localhost:8000/docs
- Grafana: http://localhost:3000
- Prometheus: http://localhost:9090

## 🚢 Deploy

### Usando Docker:
```bash
# Build e run completo
docker-compose up --build
```

### Deploy em produção:
```bash
# Build para produção
docker build -t aria-hotel-ai:latest .

# Run com variáveis de produção
docker run --env-file .env.prod aria-hotel-ai:latest
```

## 🔑 Variáveis de Ambiente

```env
# AI Services
GEMINI_API_KEY=your-gemini-key
OPENAI_API_KEY=your-openai-key  # opcional
GROQ_API_KEY=your-groq-key      # opcional

# Twilio
TWILIO_ACCOUNT_SID=your-sid
TWILIO_AUTH_TOKEN=your-token
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886

# Database
DATABASE_URL=postgresql://user:pass@localhost/aria
REDIS_URL=redis://localhost:6379/0

# Application
APP_ENV=development
LOG_LEVEL=INFO
WEBHOOK_BASE_URL=https://your-domain.com
```

## 📚 Documentação Completa

- [Guia de Implementação](docs/implementation-guide.md)
- [Implementação Agno](docs/agno-implementation.md)
- [Status do Projeto](docs/implementation-status.md)
- [API Reference](docs/api-reference.md)

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 👥 Team

- Gabriel Maia - Lead Developer - [gabrielmaialva33@gmail.com](mailto:gabrielmaialva33@gmail.com)

## 🙏 Acknowledgments

- [Agno Framework](https://agno.dev) - AI Agent Framework
- [FastAPI](https://fastapi.tiangolo.com/) - Web Framework
- [Twilio](https://www.twilio.com/) - WhatsApp API
- [Google Gemini](https://deepmind.google/technologies/gemini/) - AI Model
- Hotel Passarim team for domain expertise

---

<p align="center">
  Feito com ❤️ para revolucionar a hospitalidade
</p>
