<h1 align="center">
  <img src=".github/assets/images/aria-logo.png" height="200" alt="ARIA Hotel AI">
</h1>

<p align="center">
  <img src="https://img.shields.io/github/license/gabrielmaia/aria-hotel-ai?color=00b8d3?style=flat&logo=appveyor" alt="License" />
  <img src="https://img.shields.io/github/languages/top/gabrielmaia/aria-hotel-ai?style=flat&logo=appveyor" alt="GitHub top language" >
  <img src="https://img.shields.io/github/languages/count/gabrielmaia/aria-hotel-ai?style=flat&logo=appveyor" alt="GitHub language count" >
  <img src="https://img.shields.io/github/repo-size/gabrielmaia/aria-hotel-ai?style=flat&logo=appveyor" alt="Repository size" >
  <img src="https://img.shields.io/badge/python-3.11+-blue.svg?style=flat&logo=appveyor" alt="Python 3.11+" >
  <a href="https://github.com/gabrielmaia/aria-hotel-ai/commits/main">
    <img src="https://img.shields.io/github/last-commit/gabrielmaia/aria-hotel-ai?style=flat&logo=appveyor" alt="GitHub last commit" >
    <img src="https://img.shields.io/badge/made%20by-Gabriel%20Maia-15c3d6?style=flat&logo=appveyor" alt="Gabriel Maia" >  
  </a>
</p>

<br>

<p align="center">
    <a href="README.md">English</a>
    ·
    <a href="README-pt.md">Portuguese</a>
</p>

<p align="center">
  <a href="#bookmark-about">About</a>&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;
  <a href="#computer-technologies">Technologies</a>&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;
  <a href="#wrench-tools">Tools</a>&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;
  <a href="#package-installation">Installation</a>&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;
  <a href="#twisted_rightwards_arrows-api-routes">API Routes</a>&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;
  <a href="#memo-license">License</a>
</p>

<br>

## :bookmark: About

**ARIA Hotel AI** is a comprehensive AI-powered multimodal concierge system for hotels, built with the **Agno Framework** and advanced AI models. The system provides automated customer service via WhatsApp, digital check-in, service management, and much more, revolutionizing the hospitality experience.

### 🏗️ Architecture Overview

```mermaid
graph TB
    subgraph "Client Layer"
        WA[WhatsApp Users]
        WEB[Web Dashboard]
        MOB[Mobile Apps]
        VOICE[Voice Calls]
    end

    subgraph "API Gateway"
        FASTAPI[FastAPI Server<br/>Port 8000]
        WEBHOOKS[Webhook Handlers]
        MIDDLEWARE[Middleware Stack]
    end

    subgraph "AI Agents"
        ANA[Ana Agent<br/>Agno Framework]
        GEMINI[Google Gemini 2.0]
        VISION[Vision Processor<br/>OCR & Image Analysis]
        NLP[NLP Processor<br/>Multi-language]
    end

    subgraph "Core Services"
        SESSION[Session Manager<br/>Redis]
        CALC[Pricing Calculator]
        PAYMENT[Payment Gateway<br/>PIX & Cards]
        ANALYTICS[Analytics Dashboard]
        PROACTIVE[Proactive Messaging]
    end

    subgraph "Integrations"
        TWILIO[Twilio WhatsApp API]
        PMS[Hotel PMS System]
        OMNIBEES[Omnibees Booking]
        PDV[Restaurant POS]
    end

    subgraph "Data Layer"
        POSTGRES[(PostgreSQL<br/>Main Database)]
        REDIS[(Redis<br/>Sessions & Cache)]
        PROMETHEUS[(Prometheus<br/>Metrics)]
    end

    WA --> TWILIO
    WEB --> FASTAPI
    MOB --> FASTAPI
    VOICE --> TWILIO

    TWILIO --> WEBHOOKS
    WEBHOOKS --> FASTAPI
    FASTAPI --> MIDDLEWARE
    MIDDLEWARE --> ANA

    ANA --> GEMINI
    ANA --> VISION
    ANA --> NLP
    ANA --> SESSION
    ANA --> CALC
    ANA --> PAYMENT
    ANA --> ANALYTICS

    SESSION --> REDIS
    CALC --> POSTGRES
    PAYMENT --> PMS
    ANALYTICS --> PROMETHEUS

    ANA --> PMS
    ANA --> OMNIBEES
    ANA --> PDV

    style FASTAPI fill:#4A90E2
    style ANA fill:#FF6B6B
    style POSTGRES fill:#336791
    style REDIS fill:#DC382D
    style TWILIO fill:#F22F46
```

### 🤖 Ana Agent Flow

```mermaid
sequenceDiagram
    participant User as WhatsApp User
    participant Twilio as Twilio API
    participant API as FastAPI Server
    participant Ana as Ana Agent
    participant AI as Gemini AI
    participant Services as Hotel Services
    participant DB as Database

    User->>Twilio: Send WhatsApp message
    Twilio->>API: Webhook notification
    API->>Ana: Process message
    Ana->>AI: Generate response with tools

    alt Booking Request
        AI->>Services: Check availability
        Services->>DB: Query rooms
        DB-->>Services: Available rooms
        Services-->>AI: Room options
    else Payment Request
        AI->>Services: Generate payment link
        Services-->>AI: PIX/Card link
    else Service Request
        AI->>Services: Create service order
        Services-->>AI: Order confirmation
    end

    AI-->>Ana: Response with actions
    Ana-->>API: Formatted response
    API->>Twilio: Send reply
    Twilio-->>User: WhatsApp message
```

### 📁 Module Structure

```mermaid
graph TD
    subgraph "Application Structure"
        APP[app/]

        subgraph "AI Agents"
            AGENTS[agents/]
            ANA_AGENT[ana/]
        end

        subgraph "API Layer"
            API_LAYER[api/]
            WEBHOOKS[webhooks/]
        end

        subgraph "Core Systems"
            CORE[core/]
            CONFIG[config.py]
            SESSIONS[sessions.py]
            LOGGING[logging.py]
        end

        subgraph "Integrations"
            INTEGRATIONS[integrations/]
            WHATSAPP[whatsapp/]
            OMNIBEES_INT[omnibees/]
        end

        subgraph "Services"
            SERVICES[services/]
            ANALYTICS_SVC[analytics/]
            PAYMENTS[payments/]
            VISION_SVC[vision/]
        end
    end

    APP --> AGENTS
    APP --> API_LAYER
    APP --> CORE
    APP --> INTEGRATIONS
    APP --> SERVICES

    AGENTS --> ANA_AGENT
    API_LAYER --> WEBHOOKS
    CORE --> CONFIG
    CORE --> SESSIONS
    CORE --> LOGGING
    INTEGRATIONS --> WHATSAPP
    INTEGRATIONS --> OMNIBEES_INT
    SERVICES --> ANALYTICS_SVC
    SERVICES --> PAYMENTS
    SERVICES --> VISION_SVC
```

## 🌟 Key Features

### Core Features

- **🤖 Ana AI Agent**: Intelligent assistant powered by Agno Framework and Google Gemini 2.0
- **📱 WhatsApp Integration**: 24/7 automated customer service via Twilio
- **🏨 Hotel Management**: Complete booking, check-in/out, and service management
- **💳 Payment Processing**: Integrated PIX and credit card payments with discounts
- **📊 Analytics Dashboard**: Real-time insights and performance metrics
- **🔍 Vision Analysis**: OCR and image processing for documents and requests
- **🌐 Multi-language Support**: Portuguese and English with NLP processing
- **⚡ Real-time Processing**: Fast response times with Redis caching
- **📈 Proactive Messaging**: Automated marketing and service notifications
- **🔒 Security First**: Secure webhook handling and data protection

### Advanced AI Features

- **🎯 Context-Aware Responses**: Maintains conversation context across sessions
- **🧮 Smart Pricing Calculator**: Dynamic pricing based on dates, occupancy, and preferences
- **📋 Service Orchestration**: Coordinates multiple hotel services seamlessly
- **🔄 Multi-modal Processing**: Handles text, images, and voice inputs
- **📱 Rich Media Support**: Sends images, documents, and interactive messages
- **🎨 Personalized Marketing**: Tailored offers based on guest preferences
- **📊 Sentiment Analysis**: Monitors guest satisfaction in real-time
- **🔍 Intelligent Search**: Natural language queries for hotel information

### Hotel Operations

```mermaid
graph LR
    subgraph "Guest Journey"
        INQUIRY[Initial Inquiry]
        BOOKING[Room Booking]
        CHECKIN[Digital Check-in]
        SERVICES[Service Requests]
        CHECKOUT[Check-out & Payment]
        FEEDBACK[Feedback Collection]
    end

    subgraph "Ana Capabilities"
        AVAILABILITY[Check Availability]
        PRICING[Calculate Pricing]
        RESERVATION[Make Reservation]
        ROOM_SERVICE[Room Service]
        HOUSEKEEPING[Housekeeping]
        CONCIERGE[Concierge Services]
        BILLING[Generate Bills]
        PAYMENT_LINK[Payment Links]
    end

    INQUIRY --> AVAILABILITY
    BOOKING --> PRICING
    BOOKING --> RESERVATION
    CHECKIN --> ROOM_SERVICE
    SERVICES --> HOUSEKEEPING
    SERVICES --> CONCIERGE
    CHECKOUT --> BILLING
    CHECKOUT --> PAYMENT_LINK
    FEEDBACK --> CONCIERGE

    style INQUIRY fill:#90EE90
    style BOOKING fill:#87CEEB
    style CHECKIN fill:#DDA0DD
    style SERVICES fill:#F0E68C
    style CHECKOUT fill:#FFA07A
    style FEEDBACK fill:#98FB98
```

<br>

## :computer: Technologies

- **[Python 3.11+](https://www.python.org/)**
- **[Agno Framework](https://agno.dev/)** - AI Agent Framework
- **[FastAPI](https://fastapi.tiangolo.com/)** - Modern web framework
- **[Google Gemini 2.0](https://deepmind.google/technologies/gemini/)** - Advanced AI model
- **[Twilio](https://www.twilio.com/)** - WhatsApp Business API
- **[PostgreSQL](https://www.postgresql.org/)** - Primary database
- **[Redis](https://redis.io/)** - Session management and caching
- **[OpenCV](https://opencv.org/)** - Computer vision processing
- **[Prometheus](https://prometheus.io/)** - Metrics and monitoring
- **[Docker](https://www.docker.com/)** - Containerization

<br>

## :wrench: Tools

- **[PyCharm](https://www.jetbrains.com/pycharm/)** / **[VS Code](https://code.visualstudio.com/)**
- **[Postman](https://www.postman.com/)** / **[Insomnia](https://insomnia.rest/)**
- **[DataGrip](https://www.jetbrains.com/datagrip/)**
- **[Docker Desktop](https://www.docker.com/products/docker-desktop/)**
- **[Grafana](https://grafana.com/)** - Monitoring dashboards

<br>

## :package: Installation

### :heavy_check_mark: **Prerequisites**

The following software must be installed:

- **[Python 3.11+](https://www.python.org/downloads/)**
- **[Git](https://git-scm.com/)**
- **[Docker](https://www.docker.com/get-started/)** (recommended)
- **[Redis](https://redis.io/download/)** (or via Docker)
- **[PostgreSQL](https://www.postgresql.org/download/)** (or via Docker)

### API Keys Required:
- **Google Gemini API Key**
- **Twilio Account SID and Auth Token**
- **WhatsApp Business Number** (via Twilio)

<br>

### :arrow_down: **Cloning the repository**

```sh
git clone https://github.com/gabrielmaia/aria-hotel-ai.git
cd aria-hotel-ai
```

<br>

### :arrow_forward: **Running the application**

#### Option 1: Docker (Recommended)

```sh
# Copy environment file
cp .env.example .env

# Edit with your API keys
nano .env

# Start all services
docker-compose up --build

# The API will be available at http://localhost:8000
```

#### Option 2: Local Development

```sh
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
# or
pip install -e .

# Copy and configure environment
cp .env.example .env
nano .env

# Start Redis and PostgreSQL (via Docker)
docker-compose up -d postgres redis

# Run database migrations (if applicable)
python -m app.cli db init

# Start the application
python main.py
# or
aria serve

# The API will be available at http://localhost:8000
```

#### Option 3: Using the CLI

```sh
# Install the package
pip install -e .

# Start the server
aria serve --host 0.0.0.0 --port 8000 --reload

# Test the Ana agent
aria test-ana "Hello, what rooms are available?"

# Calculate pricing
aria calculate-price 2024-07-20 2024-07-25 2 --children 5,8

# Test WhatsApp integration
aria test-whatsapp +5511999999999
```

## :twisted_rightwards_arrows: API Routes

The API follows RESTful principles and all endpoints are well-documented with OpenAPI/Swagger.

### 🛣️ Route Organization

```mermaid
graph LR
    subgraph "Public Routes"
        ROOT[GET /]
        HEALTH[GET /health]
        METRICS[GET /metrics]
        DOCS[GET /docs]
    end

    subgraph "Webhook Routes"
        WA_WEBHOOK[POST /webhooks/whatsapp]
        VOICE_WEBHOOK[POST /webhooks/voice]
    end

    subgraph "API v1 Routes"
        STATS[GET /api/v1/stats]
        RESERVATIONS[/api/v1/reservations/*]
        SERVICES[/api/v1/services/*]
        PAYMENTS[/api/v1/payments/*]
        ANALYTICS[/api/v1/analytics/*]
    end

    style ROOT fill:#90EE90
    style HEALTH fill:#90EE90
    style METRICS fill:#90EE90
    style DOCS fill:#90EE90
    style WA_WEBHOOK fill:#FFB6C1
    style VOICE_WEBHOOK fill:#FFB6C1
```

### 📋 Route Details

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| **GET** | `/` | API information and available endpoints | ❌ |
| **GET** | `/health` | Health check with service status | ❌ |
| **GET** | `/metrics` | Prometheus metrics | ❌ |
| **GET** | `/docs` | Interactive API documentation | ❌ |
| **GET** | `/api/v1/stats` | Application statistics | ❌ |
| **POST** | `/webhooks/whatsapp` | WhatsApp message webhook | ✅ (Twilio) |
| **POST** | `/webhooks/voice` | Voice call webhook | ✅ (Twilio) |
| **GET** | `/api/v1/reservations` | List reservations | ✅ |
| **POST** | `/api/v1/reservations` | Create reservation | ✅ |
| **GET** | `/api/v1/services` | List hotel services | ✅ |
| **POST** | `/api/v1/services` | Request service | ✅ |
| **GET** | `/api/v1/payments` | List payments | ✅ |
| **POST** | `/api/v1/payments/pix` | Generate PIX payment | ✅ |
| **GET** | `/api/v1/analytics/dashboard` | Analytics dashboard | ✅ |

### 🔄 Request/Response Flow

```mermaid
sequenceDiagram
    participant Client
    participant FastAPI
    participant Middleware
    participant Ana
    participant Services
    participant Database

    Client->>FastAPI: HTTP Request
    FastAPI->>Middleware: Route Match

    alt Webhook Request
        Middleware->>Middleware: Verify Twilio Signature
    else API Request
        Middleware->>Middleware: Rate Limiting
    end

    Middleware->>Ana: Process Request
    Ana->>Services: Business Logic
    Services->>Database: Data Operations
    Database-->>Services: Query Results
    Services-->>Ana: Processed Data
    Ana-->>FastAPI: Response Data
    FastAPI-->>Client: HTTP Response
```

### 🔐 Ana Agent Capabilities

The Ana agent supports various tools and capabilities:

```mermaid
graph TD
    subgraph "Ana Agent Tools"
        CALC[calculate_pricing]
        AVAIL[check_availability]
        CHECKIN[process_check_in]
        PAYMENT[generate_payment_link]
        SERVICE[request_service]
        INFO[get_hotel_info]
        VISION[analyze_image]
        TRANSLATE[translate_text]
    end

    subgraph "Input Types"
        TEXT[Text Messages]
        IMAGE[Images/Documents]
        VOICE[Voice Messages]
        LOCATION[Location Data]
    end

    subgraph "Output Types"
        RESPONSE[Text Responses]
        MEDIA[Rich Media]
        LINKS[Payment Links]
        DOCS[Documents/PDFs]
    end

    TEXT --> CALC
    TEXT --> AVAIL
    TEXT --> CHECKIN
    IMAGE --> VISION
    VOICE --> TRANSLATE
    LOCATION --> INFO

    CALC --> RESPONSE
    AVAIL --> MEDIA
    PAYMENT --> LINKS
    SERVICE --> DOCS

    style CALC fill:#4A90E2
    style VISION fill:#FF6B6B
    style PAYMENT fill:#32CD32
```

### 📊 Analytics & Monitoring

Access the monitoring dashboards:

- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Metrics**: http://localhost:8000/metrics
- **Grafana Dashboard**: http://localhost:3000 (if using Docker Compose)
- **Prometheus**: http://localhost:9090 (if using Docker Compose)

### 🧪 Testing the API

```bash
# Test the main endpoint
curl http://localhost:8000/

# Check health status
curl http://localhost:8000/health

# Get application stats
curl http://localhost:8000/api/v1/stats

# Test Ana agent via CLI
aria test-ana "What rooms are available for tonight?"

# Test WhatsApp webhook (requires Twilio setup)
aria test-whatsapp +5511999999999
```

### 🔧 Agno Framework Configuration

The Ana Agent uses the Agno Framework for intelligent processing:

```python
from agno.agent import Agent
from agno.models.google import Gemini

# Agent configuration
self.agent = Agent(
    model=Gemini(id="gemini-2.0-flash"),
    system_prompt=ANA_SYSTEM_PROMPT,
    tools=[
        self.calculate_pricing,
        self.check_availability,
        self.process_check_in,
        self.generate_payment_link,
        self.request_service,
        self.analyze_image,
        # ... other tools
    ],
    markdown=True,
    temperature=0.7,
)
```

### 🔑 Environment Variables

```env
# AI Services
GEMINI_API_KEY=your-gemini-key
OPENAI_API_KEY=your-openai-key  # optional
GROQ_API_KEY=your-groq-key      # optional

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

### 🚢 Deployment

#### Using Docker:
```bash
# Build and run complete stack
docker-compose up --build
```

#### Production deployment:
```bash
# Build for production
docker build -t aria-hotel-ai:latest .

# Run with production variables
docker run --env-file .env.prod aria-hotel-ai:latest
```

### 📚 Documentation

- [Implementation Guide](docs/implementation-guide.md)
- [Agno Implementation](docs/agno-implementation.md)
- [Project Status](docs/implementation-status.md)
- [API Reference](docs/api-reference.md)
- [Complete Implementation Guide](docs/complete-implementation-guide.md)

## :memo: License

This project is under the **MIT** license. [MIT](./LICENSE) ❤️

Liked? Leave a little star to help the project ⭐

<br>

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 👥 Team

- **Gabriel Maia** - Lead Developer - [gabrielmaialva33@gmail.com](mailto:gabrielmaialva33@gmail.com)

## 🙏 Acknowledgments

- **[Agno Framework](https://agno.dev)** - AI Agent Framework
- **[FastAPI](https://fastapi.tiangolo.com/)** - Modern Web Framework
- **[Twilio](https://www.twilio.com/)** - WhatsApp Business API
- **[Google Gemini](https://deepmind.google/technologies/gemini/)** - Advanced AI Model
- **Hotel Passarim** team for domain expertise and real-world testing

<br>

<p align="center">
  <img src="https://raw.githubusercontent.com/gabrielmaialva33/gabrielmaialva33/master/assets/gray0_ctp_on_line.svg?sanitize=true" />
</p>

<p align="center">
  &copy; 2024-present <a href="https://github.com/gabrielmaia/" target="_blank">Gabriel Maia</a>
</p>
