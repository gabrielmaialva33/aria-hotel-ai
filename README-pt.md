<h1 align="center">
  <img src="https://raw.githubusercontent.com/gabrielmaialva33/aria-hotel-ai/refs/heads/main/.github/assets/hotel_2.png" height="200" alt="ARIA Hotel AI">
</h1>

<p align="center">
  <img src="https://img.shields.io/github/license/gabrielmaialv33/aria-hotel-ai?color=00b8d3?style=flat&logo=appveyor" alt="License" />
  <img src="https://img.shields.io/github/languages/top/gabrielmaialv33/aria-hotel-ai?style=flat&logo=appveyor" alt="GitHub top language" >
  <img src="https://img.shields.io/github/languages/count/gabrielmaialv33/aria-hotel-ai?style=flat&logo=appveyor" alt="GitHub language count" >
  <img src="https://img.shields.io/github/repo-size/gabrielmaialv33/aria-hotel-ai?style=flat&logo=appveyor" alt="Repository size" >
  <img src="https://img.shields.io/badge/python-3.11+-blue.svg?style=flat&logo=appveyor" alt="Python 3.11+" >
  <a href="https://github.com/gabrielmaialv33/aria-hotel-ai/commits/main">
    <img src="https://img.shields.io/github/last-commit/gabrielmaialv33/aria-hotel-ai?style=flat&logo=appveyor" alt="GitHub last commit" >
    <img src="https://img.shields.io/badge/feito%20por-Gabriel%20Maia-15c3d6?style=flat&logo=appveyor" alt="Gabriel Maia" >  
  </a>
</p>

<br>

<p align="center">
    <a href="README.md">English</a>
    ·
    <a href="README-pt.md">Portuguese</a>
</p>

<p align="center">
  <a href="#bookmark-sobre">Sobre</a>&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;
  <a href="#computer-tecnologias">Tecnologias</a>&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;
  <a href="#wrench-ferramentas">Ferramentas</a>&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;
  <a href="#package-instalação">Instalação</a>&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;
  <a href="#twisted_rightwards_arrows-rotas-da-api">Rotas da API</a>&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;
  <a href="#memo-licença">Licença</a>
</p>

<br>

## :bookmark: Sobre

**ARIA Hotel AI** é um sistema completo de concierge multimodal alimentado por IA para hotéis, construído com o **Agno Framework** e modelos de IA avançados. O sistema oferece atendimento automatizado via WhatsApp, check-in digital, gestão de serviços e muito mais, revolucionando a experiência de hospitalidade.

### 🏗️ Visão Geral da Arquitetura

```mermaid
graph TB
    subgraph "Camada Cliente"
        WA[Usuários WhatsApp]
        WEB[Dashboard Web]
        MOB[Apps Mobile]
        VOICE[Chamadas de Voz]
    end

    subgraph "Gateway API"
        FASTAPI[Servidor FastAPI<br/>Porta 8000]
        WEBHOOKS[Manipuladores Webhook]
        MIDDLEWARE[Stack de Middleware]
    end

    subgraph "Agentes IA"
        ANA[Agente Ana<br/>Agno Framework]
        GEMINI[Google Gemini 2.0]
        VISION[Processador Visão<br/>OCR & Análise Imagem]
        NLP[Processador NLP<br/>Multi-idioma]
    end

    subgraph "Serviços Core"
        SESSION[Gerenciador Sessão<br/>Redis]
        CALC[Calculadora Preços]
        PAYMENT[Gateway Pagamento<br/>PIX & Cartões]
        ANALYTICS[Dashboard Analytics]
        PROACTIVE[Mensagens Proativas]
    end

    subgraph "Integrações"
        TWILIO[API WhatsApp Twilio]
        PMS[Sistema PMS Hotel]
        OMNIBEES[Reservas Omnibees]
        PDV[POS Restaurante]
    end

    subgraph "Camada Dados"
        POSTGRES[(PostgreSQL<br/>Banco Principal)]
        REDIS[(Redis<br/>Sessões & Cache)]
        PROMETHEUS[(Prometheus<br/>Métricas)]
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

### 🤖 Fluxo do Agente Ana

```mermaid
sequenceDiagram
    participant User as Usuário WhatsApp
    participant Twilio as API Twilio
    participant API as Servidor FastAPI
    participant Ana as Agente Ana
    participant AI as IA Gemini
    participant Services as Serviços Hotel
    participant DB as Banco Dados

    User->>Twilio: Enviar mensagem WhatsApp
    Twilio->>API: Notificação webhook
    API->>Ana: Processar mensagem
    Ana->>AI: Gerar resposta com ferramentas
    
    alt Solicitação Reserva
        AI->>Services: Verificar disponibilidade
        Services->>DB: Consultar quartos
        DB-->>Services: Quartos disponíveis
        Services-->>AI: Opções de quartos
    else Solicitação Pagamento
        AI->>Services: Gerar link pagamento
        Services-->>AI: Link PIX/Cartão
    else Solicitação Serviço
        AI->>Services: Criar pedido serviço
        Services-->>AI: Confirmação pedido
    end

    AI-->>Ana: Resposta com ações
    Ana-->>API: Resposta formatada
    API->>Twilio: Enviar resposta
    Twilio-->>User: Mensagem WhatsApp
```

### 📁 Estrutura Modular

```mermaid
graph TD
    subgraph "Estrutura Aplicação"
        APP[app/]
        
        subgraph "Agentes IA"
            AGENTS[agents/]
            ANA_AGENT[ana/]
        end
        
        subgraph "Camada API"
            API_LAYER[api/]
            WEBHOOKS[webhooks/]
        end
        
        subgraph "Sistemas Core"
            CORE[core/]
            CONFIG[config.py]
            SESSIONS[sessions.py]
            LOGGING[logging.py]
        end
        
        subgraph "Integrações"
            INTEGRATIONS[integrations/]
            WHATSAPP[whatsapp/]
            OMNIBEES_INT[omnibees/]
        end
        
        subgraph "Serviços"
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

## 🌟 Principais Funcionalidades

### Funcionalidades Core

- **🤖 Agente Ana IA**: Assistente inteligente alimentado pelo Agno Framework e Google Gemini 2.0
- **📱 Integração WhatsApp**: Atendimento automatizado 24/7 via Twilio
- **🏨 Gestão Hoteleira**: Reservas completas, check-in/out e gestão de serviços
- **💳 Processamento Pagamentos**: PIX integrado e pagamentos com cartão com descontos
- **📊 Dashboard Analytics**: Insights e métricas de performance em tempo real
- **🔍 Análise Visão**: OCR e processamento de imagens para documentos e solicitações
- **🌐 Suporte Multi-idioma**: Português e Inglês com processamento NLP
- **⚡ Processamento Tempo Real**: Tempos de resposta rápidos com cache Redis
- **📈 Mensagens Proativas**: Marketing automatizado e notificações de serviços
- **🔒 Segurança Primeiro**: Manipulação segura de webhooks e proteção de dados

### Funcionalidades Avançadas IA

- **🎯 Respostas Contextuais**: Mantém contexto da conversa entre sessões
- **🧮 Calculadora Preços Inteligente**: Preços dinâmicos baseados em datas, ocupação e preferências
- **📋 Orquestração Serviços**: Coordena múltiplos serviços do hotel perfeitamente
- **🔄 Processamento Multi-modal**: Manipula entradas de texto, imagens e voz
- **📱 Suporte Mídia Rica**: Envia imagens, documentos e mensagens interativas
- **🎨 Marketing Personalizado**: Ofertas sob medida baseadas em preferências do hóspede
- **📊 Análise Sentimento**: Monitora satisfação do hóspede em tempo real
- **🔍 Busca Inteligente**: Consultas em linguagem natural para informações do hotel

### Operações Hoteleiras

```mermaid
graph LR
    subgraph "Jornada Hóspede"
        INQUIRY[Consulta Inicial]
        BOOKING[Reserva Quarto]
        CHECKIN[Check-in Digital]
        SERVICES[Solicitações Serviço]
        CHECKOUT[Check-out & Pagamento]
        FEEDBACK[Coleta Feedback]
    end

    subgraph "Capacidades Ana"
        AVAILABILITY[Verificar Disponibilidade]
        PRICING[Calcular Preços]
        RESERVATION[Fazer Reserva]
        ROOM_SERVICE[Serviço Quarto]
        HOUSEKEEPING[Limpeza]
        CONCIERGE[Serviços Concierge]
        BILLING[Gerar Contas]
        PAYMENT_LINK[Links Pagamento]
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

## :computer: Tecnologias

- **[Python 3.11+](https://www.python.org/)**
- **[Agno Framework](https://agno.dev/)** - Framework de Agentes IA
- **[FastAPI](https://fastapi.tiangolo.com/)** - Framework web moderno
- **[Google Gemini 2.0](https://deepmind.google/technologies/gemini/)** - Modelo IA avançado
- **[Twilio](https://www.twilio.com/)** - API WhatsApp Business
- **[PostgreSQL](https://www.postgresql.org/)** - Banco de dados principal
- **[Redis](https://redis.io/)** - Gerenciamento de sessões e cache
- **[OpenCV](https://opencv.org/)** - Processamento visão computacional
- **[Prometheus](https://prometheus.io/)** - Métricas e monitoramento
- **[Docker](https://www.docker.com/)** - Containerização

<br>

## :wrench: Ferramentas

- **[PyCharm](https://www.jetbrains.com/pycharm/)** / **[VS Code](https://code.visualstudio.com/)**
- **[Postman](https://www.postman.com/)** / **[Insomnia](https://insomnia.rest/)**
- **[DataGrip](https://www.jetbrains.com/datagrip/)**
- **[Docker Desktop](https://www.docker.com/products/docker-desktop/)**
- **[Grafana](https://grafana.com/)** - Dashboards de monitoramento

<br>

## :package: Instalação

### :heavy_check_mark: **Pré-requisitos**

Os seguintes softwares devem estar instalados:

- **[Python 3.11+](https://www.python.org/downloads/)**
- **[Git](https://git-scm.com/)**
- **[Docker](https://www.docker.com/get-started/)** (recomendado)
- **[Redis](https://redis.io/download/)** (ou via Docker)
- **[PostgreSQL](https://www.postgresql.org/download/)** (ou via Docker)

### Chaves API Necessárias:
- **Chave API Google Gemini**
- **SID da Conta Twilio e Token de Autenticação**
- **Número WhatsApp Business** (via Twilio)

<br>

### :arrow_down: **Clonando o repositório**

```sh
git clone https://github.com/gabrielmaialv33/aria-hotel-ai.git
cd aria-hotel-ai
```

<br>

### :arrow_forward: **Executando a aplicação**

#### Opção 1: Docker (Recomendado)

```sh
# Copiar arquivo de ambiente
cp .env.example .env

# Editar com suas chaves API
nano .env

# Iniciar todos os serviços
docker-compose up --build

# A API estará disponível em http://localhost:8000
```

#### Opção 2: Desenvolvimento Local

```sh
# Criar ambiente virtual
python -m venv venv
source venv/bin/activate  # No Windows: venv\Scripts\activate

# Instalar dependências
pip install -r requirements.txt
# ou
pip install -e .

# Copiar e configurar ambiente
cp .env.example .env
nano .env

# Iniciar Redis e PostgreSQL (via Docker)
docker-compose up -d postgres redis

# Executar migrações do banco (se aplicável)
python -m app.cli db init

# Iniciar a aplicação
python main.py
# ou
aria serve

# A API estará disponível em http://localhost:8000
```

#### Opção 3: Usando o CLI

```sh
# Instalar o pacote
pip install -e .

# Iniciar o servidor
aria serve --host 0.0.0.0 --port 8000 --reload

# Testar o agente Ana
aria test-ana "Olá, quais quartos estão disponíveis?"

# Calcular preços
aria calculate-price 2024-07-20 2024-07-25 2 --children 5,8

# Testar integração WhatsApp
aria test-whatsapp +5511999999999
```

<br>

## :twisted_rightwards_arrows: Rotas da API

A API segue princípios RESTful e todos os endpoints são bem documentados com OpenAPI/Swagger.

### 🛣️ Organização das Rotas

```mermaid
graph LR
    subgraph "Rotas Públicas"
        ROOT[GET /]
        HEALTH[GET /health]
        METRICS[GET /metrics]
        DOCS[GET /docs]
    end

    subgraph "Rotas Webhook"
        WA_WEBHOOK[POST /webhooks/whatsapp]
        VOICE_WEBHOOK[POST /webhooks/voice]
    end

    subgraph "Rotas API v1"
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

### 📋 Detalhes das Rotas

| Método | Endpoint | Descrição | Auth Necessária |
|--------|----------|-----------|-----------------|
| **GET** | `/` | Informações da API e endpoints disponíveis | ❌ |
| **GET** | `/health` | Verificação de saúde com status dos serviços | ❌ |
| **GET** | `/metrics` | Métricas Prometheus | ❌ |
| **GET** | `/docs` | Documentação interativa da API | ❌ |
| **GET** | `/api/v1/stats` | Estatísticas da aplicação | ❌ |
| **POST** | `/webhooks/whatsapp` | Webhook de mensagens WhatsApp | ✅ (Twilio) |
| **POST** | `/webhooks/voice` | Webhook de chamadas de voz | ✅ (Twilio) |
| **GET** | `/api/v1/reservations` | Listar reservas | ✅ |
| **POST** | `/api/v1/reservations` | Criar reserva | ✅ |
| **GET** | `/api/v1/services` | Listar serviços do hotel | ✅ |
| **POST** | `/api/v1/services` | Solicitar serviço | ✅ |
| **GET** | `/api/v1/payments` | Listar pagamentos | ✅ |
| **POST** | `/api/v1/payments/pix` | Gerar pagamento PIX | ✅ |
| **GET** | `/api/v1/analytics/dashboard` | Dashboard de analytics | ✅ |

### 🔄 Fluxo Requisição/Resposta

```mermaid
sequenceDiagram
    participant Cliente
    participant FastAPI
    participant Middleware
    participant Ana
    participant Serviços
    participant BancoDados

    Cliente->>FastAPI: Requisição HTTP
    FastAPI->>Middleware: Match de Rota
    
    alt Requisição Webhook
        Middleware->>Middleware: Verificar Assinatura Twilio
    else Requisição API
        Middleware->>Middleware: Rate Limiting
    end

    Middleware->>Ana: Processar Requisição
    Ana->>Serviços: Lógica de Negócio
    Serviços->>BancoDados: Operações de Dados
    BancoDados-->>Serviços: Resultados Consulta
    Serviços-->>Ana: Dados Processados
    Ana-->>FastAPI: Dados Resposta
    FastAPI-->>Cliente: Resposta HTTP
```

### 🔐 Capacidades do Agente Ana

O agente Ana suporta várias ferramentas e capacidades:

```mermaid
graph TD
    subgraph "Ferramentas Agente Ana"
        CALC[calculate_pricing]
        AVAIL[check_availability]
        CHECKIN[process_check_in]
        PAYMENT[generate_payment_link]
        SERVICE[request_service]
        INFO[get_hotel_info]
        VISION[analyze_image]
        TRANSLATE[translate_text]
    end

    subgraph "Tipos Entrada"
        TEXT[Mensagens Texto]
        IMAGE[Imagens/Documentos]
        VOICE[Mensagens Voz]
        LOCATION[Dados Localização]
    end

    subgraph "Tipos Saída"
        RESPONSE[Respostas Texto]
        MEDIA[Mídia Rica]
        LINKS[Links Pagamento]
        DOCS[Documentos/PDFs]
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

### 📊 Analytics & Monitoramento

Acesse os dashboards de monitoramento:

- **Documentação API**: http://localhost:8000/docs
- **Verificação Saúde**: http://localhost:8000/health
- **Métricas**: http://localhost:8000/metrics
- **Dashboard Grafana**: http://localhost:3000 (se usando Docker Compose)
- **Prometheus**: http://localhost:9090 (se usando Docker Compose)

### 🧪 Testando a API

```bash
# Testar endpoint principal
curl http://localhost:8000/

# Verificar status de saúde
curl http://localhost:8000/health

# Obter estatísticas da aplicação
curl http://localhost:8000/api/v1/stats

# Testar agente Ana via CLI
aria test-ana "Quais quartos estão disponíveis para hoje à noite?"

# Testar webhook WhatsApp (requer configuração Twilio)
aria test-whatsapp +5511999999999
```

### 🔧 Configuração Agno Framework

O Agente Ana usa o Agno Framework para processamento inteligente:

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
        self.request_service,
        self.analyze_image,
        # ... outras ferramentas
    ],
    markdown=True,
    temperature=0.7,
)
```

### 🔑 Variáveis de Ambiente

```env
# Serviços IA
GEMINI_API_KEY=sua-chave-gemini
OPENAI_API_KEY=sua-chave-openai  # opcional
GROQ_API_KEY=sua-chave-groq      # opcional

# Twilio
TWILIO_ACCOUNT_SID=seu-sid
TWILIO_AUTH_TOKEN=seu-token
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886

# Banco de Dados
DATABASE_URL=postgresql://user:pass@localhost/aria
REDIS_URL=redis://localhost:6379/0

# Aplicação
APP_ENV=development
LOG_LEVEL=INFO
WEBHOOK_BASE_URL=https://seu-dominio.com
```

### 🚢 Deploy

#### Usando Docker:
```bash
# Build e executar stack completo
docker-compose up --build
```

#### Deploy em produção:
```bash
# Build para produção
docker build -t aria-hotel-ai:latest .

# Executar com variáveis de produção
docker run --env-file .env.prod aria-hotel-ai:latest
```

### 📚 Documentação

- [Guia de Implementação](docs/implementation-guide.md)
- [Implementação Agno](docs/agno-implementation.md)
- [Status do Projeto](docs/implementation-status.md)
- [Referência API](docs/api-reference.md)
- [Guia Implementação Completa](docs/complete-implementation-guide.md)

## :memo: Licença

Este projeto está sob a licença **MIT**. [MIT](./LICENSE) ❤️

Gostou? Deixe uma estrela para ajudar o projeto ⭐

<br>

## 🤝 Contribuindo

1. Faça um fork do repositório
2. Crie sua branch de feature (`git checkout -b feature/funcionalidade-incrivel`)
3. Commit suas mudanças (`git commit -m 'Adicionar funcionalidade incrível'`)
4. Push para a branch (`git push origin feature/funcionalidade-incrivel`)
5. Abra um Pull Request

## 👥 Equipe

- **Gabriel Maia** - Desenvolvedor Principal - [gabrielmaialva33@gmail.com](mailto:gabrielmaialva33@gmail.com)

## 🙏 Agradecimentos

- **[Agno Framework](https://agno.dev)** - Framework de Agentes IA
- **[FastAPI](https://fastapi.tiangolo.com/)** - Framework Web Moderno
- **[Twilio](https://www.twilio.com/)** - API WhatsApp Business
- **[Google Gemini](https://deepmind.google/technologies/gemini/)** - Modelo IA Avançado
- Equipe **Hotel Passarim** pela expertise de domínio e testes no mundo real

<br>

<p align="center">
  <img src="https://raw.githubusercontent.com/gabrielmaialva33/gabrielmaialva33/master/assets/gray0_ctp_on_line.svg?sanitize=true" />
</p>

<p align="center">
  &copy; 2024-present <a href="https://github.com/gabrielmaialv33/" target="_blank">Gabriel Maia</a>
</p>