# ARIA Hotel AI 🏨🤖

AI-powered multimodal concierge system for hotels, built with [Agno](https://agno.dev) and integrated with
WhatsApp/Voice via Twilio.

## 🌟 Features

- **Multimodal Processing**: Handle text, voice, images, and video inputs
- **Multi-Agent Architecture**: Specialized agents for different tasks (concierge, booking, wellness, etc.)
- **Real-time Communication**: WhatsApp and voice call integration via Twilio
- **Persistent Memory**: Remember guest preferences across interactions
- **Proactive Engagement**: Anticipate guest needs based on patterns
- **Emotion Detection**: Adjust responses based on guest emotional state

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Redis
- PostgreSQL (optional, for production)
- Twilio account
- OpenAI/Groq API keys

### Installation

```bash
# Clone the repository
git clone https://github.com/gabrielmaia/aria-hotel-ai.git
cd aria-hotel-ai

# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e .

# Copy environment variables
cp .env.example .env
# Edit .env with your credentials
```

### Running Locally

```bash
# Start the API server
uv run aria serve

# Or with hot reload for development
uv run uvicorn aria.api.main:app --reload
```

### Testing

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov

# Run specific test file
uv run pytest tests/unit/test_agents.py
```

## 📁 Project Structure

```
aria-hotel-ai/
├── src/aria/           # Main application code
│   ├── agents/         # AI agents (orchestrator, concierge, etc.)
│   ├── tools/          # Agent tools (hotel, vision, emotion)
│   ├── integrations/   # External integrations (Twilio, PMS)
│   ├── core/           # Core functionality (config, models)
│   └── api/            # FastAPI application
├── tests/              # Test suite
├── docs/               # Documentation
├── scripts/            # Utility scripts
└── config/             # Configuration files
```

## 🔧 Configuration

### Environment Variables

See `.env.example` for all available configuration options. Key variables:

- `OPENAI_API_KEY`: OpenAI API key for GPT models
- `GROQ_API_KEY`: Groq API key (free tier available)
- `TWILIO_*`: Twilio credentials for WhatsApp/Voice
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string

### WhatsApp Setup

1. Configure Twilio WhatsApp sandbox or production number
2. Set webhook URL to `https://your-domain.com/webhooks/whatsapp`
3. Test with sandbox by sending "join [keyword]" to the Twilio number

## 🧪 Development

### Code Style

We use `ruff` for linting and `black` for formatting:

```bash
# Format code
uv run ruff format .

# Lint code
uv run ruff check . --fix

# Type checking
uv run mypy src/aria
```

### Pre-commit Hooks

```bash
# Install pre-commit hooks
uv run pre-commit install

# Run manually
uv run pre-commit run --all-files
```

## 📚 Documentation

Full documentation is available at [https://aria-hotel-ai.readthedocs.io](https://aria-hotel-ai.readthedocs.io)

### Building Docs Locally

```bash
uv run mkdocs serve
# Visit http://localhost:8000
```

## 🚀 Deployment

### Docker

```bash
# Build image
docker build -t aria-hotel-ai .

# Run container
docker run -p 8000:8000 --env-file .env aria-hotel-ai
```

### Docker Compose

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f aria
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Agno](https://agno.dev) - Multi-agent framework
- [Twilio](https://twilio.com) - Communication APIs
- [OpenAI](https://openai.com) - AI models
- [Groq](https://groq.com) - Fast inference

## 📞 Support

- Documentation: [https://aria-hotel-ai.readthedocs.io](https://aria-hotel-ai.readthedocs.io)
- Issues: [GitHub Issues](https://github.com/gabrielmaia/aria-hotel-ai/issues)
- Email: support@aria-hotel-ai.com
