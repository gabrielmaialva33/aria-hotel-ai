# Quick Start Guide - ARIA Hotel AI

## 🚀 Começando Rapidamente

### Pré-requisitos

- Python 3.11 ou superior
- Redis
- Conta Twilio (para WhatsApp)
- Chaves de API (OpenAI/Groq)

### Instalação Rápida

1. **Clone o repositório**
```bash
git clone https://github.com/gabrielmaialv33/aria-hotel-ai.git
cd aria-hotel-ai
```

2. **Configure o ambiente**
```bash
# Copie o arquivo de exemplo
cp .env.example .env

# Edite com suas credenciais
nano .env
```

3. **Inicie o sistema**

**Opção 1: Desenvolvimento Local**
```bash
./scripts/start.sh
```

**Opção 2: Docker**
```bash
./scripts/docker-start.sh
```

## 🔧 Configuração do Twilio

### 1. Configure o WhatsApp Sandbox

1. Acesse [Twilio Console](https://console.twilio.com)
2. Vá para **Messaging > Try it out > Send a WhatsApp message**
3. Siga as instruções para ativar o sandbox
4. Configure o webhook:
   ```
   When a message comes in: https://seu-dominio.com/webhooks/whatsapp
   Status callback URL: https://seu-dominio.com/webhooks/whatsapp/status
   ```

### 2. Obtenha as Credenciais

No arquivo `.env`, configure:
```env
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886
```

## 📱 Testando o Sistema

### 1. Teste Local com CLI

```bash
# Teste a Ana
uv run aria test-ana "Olá, quero fazer uma reserva"

# Teste cálculo de preços
uv run aria calculate-price 2025-02-10 2025-02-12 2 --children "5,8"

# Envie uma mensagem de teste (se Twilio configurado)
uv run aria test-whatsapp +5511999999999 "Teste do sistema ARIA"
```

### 2. Teste via WhatsApp

1. Envie "join [palavra-chave]" para o número do sandbox
2. Depois envie uma mensagem normal:
   ```
   Olá, gostaria de saber valores para hospedagem
   ```

### 3. Teste via API

```bash
# Health check
curl http://localhost:8000/health

# Teste webhook manualmente
curl -X POST http://localhost:8000/webhooks/whatsapp/test \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "From=whatsapp:+5511999999999&Body=Olá&MessageSid=TEST123"
```

## 📊 Monitoramento

### Grafana Dashboard
- Acesse: http://localhost:3000
- Login: admin/admin
- Dashboard pré-configurado com métricas

### Logs
```bash
# Logs em tempo real (Docker)
docker-compose logs -f aria-api

# Logs locais
tail -f logs/aria.log
```

## 🧪 Executando Testes

```bash
# Todos os testes
uv run pytest

# Apenas testes unitários
uv run pytest tests/unit -v

# Com coverage
uv run pytest --cov
```

## 📝 Fluxos de Exemplo

### Reserva Simples

1. **Cliente**: "Olá"
2. **Ana**: Mensagem de boas-vindas
3. **Cliente**: "Quero fazer uma reserva"
4. **Ana**: "Para calcular os valores, preciso saber..."
5. **Cliente**: "10 a 12 de fevereiro, 2 adultos"
6. **Ana**: Apresenta opções de preços
7. **Cliente**: "Quero o apartamento térreo com café"
8. **Ana**: Gera link para finalizar reserva

### Consulta de Informações

1. **Cliente**: "Qual a senha do WiFi?"
2. **Ana**: "📶 Rede: HotelPassarim, Senha: passarim2025"

### Pacote de Feriado

1. **Cliente**: "Tem pacote para a Páscoa?"
2. **Ana**: Apresenta detalhes do pacote de Páscoa
3. **Cliente**: "Quanto fica para 2 adultos e 1 criança de 7 anos?"
4. **Ana**: Calcula valores específicos do pacote

## 🛠️ Troubleshooting

### Redis não está rodando
```bash
# macOS
brew services start redis

# Linux
sudo systemctl start redis

# Docker
docker run -d -p 6379:6379 redis:alpine
```

### Erro de API Key
- Verifique se as chaves no `.env` estão corretas
- Para Groq (gratuito): https://console.groq.com/keys
- Para OpenAI: https://platform.openai.com/api-keys

### WhatsApp não responde
1. Verifique se o webhook está acessível publicamente
2. Use ngrok para testes locais:
   ```bash
   ngrok http 8000
   # Use a URL do ngrok no Twilio
   ```

## 📚 Próximos Passos

1. **Personalize a Ana**: Edite `src/aria/agents/ana/prompts.py`
2. **Adicione novos agentes**: Veja `docs/creating-agents.md`
3. **Configure integrações**: PMS, sistemas de pagamento, etc.
4. **Deploy em produção**: Veja `docs/deployment.md`

## 💡 Dicas Úteis

- Use `uv run aria info` para verificar a configuração
- Monitore os logs em tempo real durante desenvolvimento
- Teste sempre com números reais no WhatsApp
- Configure rate limiting em produção
- Faça backup regular do Redis

## 🆘 Suporte

- Documentação: [/docs](/docs)
- Issues: [GitHub Issues](https://github.com/gabrielmaialv33/aria-hotel-ai/issues)
- Email: suporte@aria-hotel-ai.com
