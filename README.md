# ARIA Hotel AI 🏨🤖

AI-powered multimodal concierge system for hotels, providing intelligent guest services through WhatsApp, voice calls, and other channels.

## 🚀 Features

- **Multimodal AI Assistant**: Text, voice, and image processing capabilities
- **WhatsApp Integration**: Full conversational AI through WhatsApp Business
- **Intelligent Pricing**: Dynamic room rate calculations
- **Guest Management**: Complete guest profiles and preferences
- **Reservation System**: Booking management with real-time availability
- **Multilingual Support**: Portuguese and English (expandable)
- **Proactive Messaging**: Automated guest communications
- **Analytics Dashboard**: Real-time insights and metrics

## 📁 Project Structure

```
aria-hotel-ai/
├── app/                    # Application code
│   ├── api/               # FastAPI endpoints and webhooks
│   │   ├── webhooks/      # WhatsApp, voice, etc.
│   │   └── main.py        # Main FastAPI app
│   ├── agents/            # AI agents
│   │   └── ana/           # Ana assistant agent
│   ├── core/              # Core functionality
│   │   ├── config.py      # Configuration management
│   │   ├── logging.py     # Structured logging
│   │   └── sessions.py    # Session management
│   ├── integrations/      # External integrations
│   │   ├── whatsapp/      # WhatsApp/Twilio
│   │   └── omnibees/      # PMS integration
│   ├── models/            # Data models (Pydantic)
│   │   ├── guest.py       # Guest models
│   │   ├── reservation.py # Reservation models
│   │   └── conversation.py # Chat models
│   └── services/          # Business logic
│       ├── messaging/     # Message templates
│       ├── analytics/     # Analytics service
│       ├── payments/      # Payment processing
│       └── vision/        # Image analysis
├── tests/                 # Test suite
├── scripts/               # Utility scripts
├── docs/                  # Documentation
├── config/                # Configuration files
└── main.py               # Entry point
```

## 🛠️ Tech Stack

- **Framework**: FastAPI
- **AI/ML**: OpenAI, Google Gemini, Groq
- **Database**: PostgreSQL + Redis
- **Messaging**: Twilio (WhatsApp/Voice)
- **Container**: Docker + Docker Compose
- **Monitoring**: Prometheus + Grafana

## 📋 Prerequisites

- Python 3.11+
- Docker & Docker Compose
- Redis
- PostgreSQL (optional, can use SQLite for development)
- Twilio Account (for WhatsApp/Voice)
- AI API Keys (OpenAI/Gemini/Groq)

## 🚀 Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/gabrielmaia/aria-hotel-ai.git
   cd aria-hotel-ai
   ```

2. **Set up environment**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and configuration
   ```

3. **Install dependencies**
   ```bash
   pip install -e .
   # or for development
   pip install -e ".[dev]"
   ```

4. **Run with Docker**
   ```bash
   docker-compose up -d
   ```

5. **Or run locally**
   ```bash
   # Start Redis first
   redis-server
   
   # Run the application
   python main.py
   # or use the CLI
   aria serve
   ```

## 🔧 Configuration

Key environment variables:

```env
# AI Services
OPENAI_API_KEY=your-key
GEMINI_API_KEY=your-key
GROQ_API_KEY=your-key

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
```

## 📱 WhatsApp Setup

1. Configure webhook URL in Twilio Console:
   ```
   https://your-domain.com/webhooks/whatsapp
   ```

2. Test the integration:
   ```bash
   aria test-whatsapp +5511999999999
   ```

## 🧪 Testing

Run tests:
```bash
pytest
# With coverage
pytest --cov=app
```

## 📚 API Documentation

Once running, access:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 🛠️ CLI Commands

```bash
# Start server
aria serve

# Show configuration
aria info

# Test WhatsApp
aria test-whatsapp +5511999999999

# Test Ana agent
aria test-ana "Olá, quais quartos disponíveis?"

# Calculate pricing
aria calculate-price 2024-07-20 2024-07-25 2 --children 5,8
```

## 📊 Architecture

The system follows a clean architecture pattern:

- **API Layer**: FastAPI handles HTTP requests and webhooks
- **Service Layer**: Business logic and orchestration
- **Agent Layer**: AI agents for different capabilities
- **Integration Layer**: External service connections
- **Model Layer**: Data models and validation

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

- Hotel Passarim team for domain expertise
- Anthropic, OpenAI, and Google for AI capabilities
- Twilio for communication infrastructure
