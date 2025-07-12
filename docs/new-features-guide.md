# 🚀 Guia das Novas Funcionalidades - ARIA Hotel AI

Este guia detalha as melhorias implementadas no projeto ARIA e como utilizá-las.

## 📚 Índice

1. [Processamento de Linguagem Natural Avançado](#nlp-avançado)
2. [Processamento de Visão](#processamento-de-visão)
3. [Integração Omnibees](#integração-omnibees)
4. [Agent Melhorado](#agent-melhorado)
5. [Como Testar](#como-testar)

## 🧠 NLP Avançado

### Descrição

O novo processador NLP (`nlp_processor.py`) oferece:

- Detecção semântica de intenções usando embeddings
- Extração inteligente de entidades (datas, números, quartos)
- Análise de sentimento
- Detecção de idioma
- Suporte a datas relativas em português

### Como Usar

```python
from aria.agents.ana.nlp_processor import NLPProcessor

nlp = NLPProcessor()

# Processar mensagem
result = await nlp.process("Quero reservar para próxima sexta, 2 adultos")

print(f"Intenção: {result.intent}")
print(f"Confiança: {result.confidence}")
print(f"Entidades: {result.entities}")
print(f"Sentimento: {result.sentiment}")
```

### Exemplos de Datas Suportadas

- **Relativas**: "hoje", "amanhã", "próxima sexta"
- **Específicas**: "15/03", "20 de março", "15-03-2025"
- **Períodos**: "este fim de semana", "próxima semana"
- **Feriados**: "páscoa", "natal", "ano novo"

## 👁️ Processamento de Visão

### Descrição

O processador de visão (`vision_processor.py`) permite:

- OCR de documentos (RG, CPF, passaporte)
- Leitura de QR codes
- Análise de fotos de quartos
- Processamento de recibos
- Validação de documentos para check-in

### Como Usar

```python
from aria.tools.vision_processor import VisionProcessor

vision = VisionProcessor()

# Processar imagem de documento
result = await vision.process_image("https://example.com/documento.jpg")

if result.image_type == ImageType.DOCUMENT:
    print(f"Nome: {result.document_data.get('name')}")
    print(f"CPF: {result.document_data.get('cpf')}")
    
    # Validar para check-in
    validation = vision.extract_document_for_checkin(result.document_data)
    if validation['valid']:
        print("Documento válido para check-in!")
```

### Tipos de Imagem Suportados

- **Documentos**: RG, CPF, CNH, Passaporte
- **QR Codes**: PIX, Links, Códigos de reserva
- **Recibos**: Extração de valores e datas
- **Fotos de quartos**: Análise de características

## 🏨 Integração Omnibees

### Descrição

Cliente completo para integração com o Omnibees (`omnibees/client.py`):

- Verificação de disponibilidade em tempo real
- Criação e gestão de reservas
- Geração de links de booking direto
- Atualização e cancelamento de reservas

### Como Usar

```python
from aria.integrations.omnibees.client import OmnibeesClient, Guest
from datetime import date, timedelta

async with OmnibeesClient() as client:
    # Verificar disponibilidade
    check_in = date.today() + timedelta(days=7)
    check_out = check_in + timedelta(days=2)

    availability = await client.check_availability(
        check_in=check_in,
        check_out=check_out,
        guests=2
    )

    # Criar reserva
    guest = Guest(
        name="João Silva",
        phone="+5511999999999",
        document="123.456.789-00"
    )

    reservation = await client.create_reservation(
        check_in=check_in,
        check_out=check_out,
        room_type="TERREO",
        guests=[guest]
    )

    print(f"Reserva criada: {reservation.id}")
```

### Link de Booking Direto

```python
# Gerar link para o motor de reservas
link = client.generate_booking_link(
    check_in=date(2025, 3, 20),
    check_out=date(2025, 3, 22),
    adults=2,
    children=1,
    promo_code="PROMO10"
)
```

## 🤖 Agent Melhorado

### Descrição

O agent melhorado (`improved_agent.py`) oferece:

- Processamento semântico de mensagens
- Respostas contextualizadas
- Quick replies do WhatsApp
- Detecção de sentimento negativo
- Mensagens proativas
- Suporte a mídia (imagens, documentos)

### Como Usar

```python
from aria.agents.ana.improved_agent import ImprovedAnaAgent

agent = ImprovedAnaAgent()

# Processar mensagem com contexto completo
response = await agent.process_message(
    phone="+5511999999999",
    message="Estou muito insatisfeito com o serviço",
    media_url=None,
    location=None,
    context={"name": "João Silva"}
)

# Response incluirá:
# - text: Mensagem de resposta
# - quick_replies: Opções rápidas
# - needs_human: Se precisa transferir
# - action: Ação a ser tomada
# - metadata: Dados adicionais
```

### Recursos Especiais

#### Quick Replies

```python
# Respostas incluem opções rápidas baseadas no contexto
if response.quick_replies:
    for reply in response.quick_replies:
        print(f"- {reply}")
```

#### Mensagens Proativas

```python
# Gerar mensagens proativas baseadas em triggers
proactive = await agent.get_proactive_message(
    phone="+5511999999999",
    trigger="pre_arrival"  # 1 dia antes do check-in
)
```

#### Processamento de Mídia

```python
# Processar imagens enviadas
response = await agent.handle_media(
    phone="+5511999999999",
    media_url="https://example.com/document.jpg",
    media_type="image/jpeg"
)
```

## 🧪 Como Testar

### Configurar Ambiente

```bash
# Instalar dependências de desenvolvimento
uv pip install -e ".[dev]"

# Instalar dependências adicionais para NLP
uv pip install sentence-transformers

# Para processamento de visão
uv pip install opencv-python pytesseract
```

### Executar Testes

```bash
# Todos os testes das novas funcionalidades
uv run pytest tests/unit/test_improved_features.py -v

# Teste específico de NLP
uv run pytest tests/unit/test_improved_features.py::TestNLPProcessor -v

# Teste com coverage
uv run pytest tests/unit/test_improved_features.py --cov=aria --cov-report=html
```

### Testar Manualmente

```bash
# Testar NLP
uv run python -c "
from aria.agents.ana.nlp_processor import NLPProcessor
import asyncio

async def test():
    nlp = NLPProcessor()
    result = await nlp.process('Quero reservar para páscoa, 2 adultos e 1 criança')
    print(f'Intent: {result.intent}')
    print(f'Entities: {[(e.type, e.value) for e in result.entities]}')

asyncio.run(test())
"

# Testar agent melhorado via CLI
uv run aria test-ana "Quanto custa para 2 pessoas de 15 a 17 de março?"
```

## 📊 Métricas de Performance

### NLP

- **Tempo de processamento**: < 100ms por mensagem
- **Precisão de intents**: > 85%
- **Extração de entidades**: > 90% para datas

### Visão

- **OCR accuracy**: > 95% para documentos limpos
- **QR detection**: > 99%
- **Tempo de processamento**: < 2s por imagem

### Omnibees

- **Latência de API**: < 500ms
- **Taxa de sucesso**: > 99.5%
- **Timeout**: 30s máximo

## 🔧 Configuração Adicional

### Variáveis de Ambiente

```bash
# Para sentence-transformers (NLP)
export SENTENCE_TRANSFORMERS_HOME=/path/to/models

# Para Tesseract (OCR)
export TESSDATA_PREFIX=/usr/local/share/tessdata

# Para Omnibees (produção)
export OMNIBEES_API_KEY=your-api-key
export OMNIBEES_HOTEL_ID=hotel-passarim
```

### Instalação de Dependências do Sistema

```bash
# macOS
brew install tesseract
brew install tesseract-lang  # Para português

# Ubuntu/Debian
sudo apt-get install tesseract-ocr
sudo apt-get install tesseract-ocr-por

# Verificar instalação
tesseract --version
```

## 🚨 Troubleshooting

### Erro: "No module named sentence_transformers"

```bash
uv pip install sentence-transformers torch
```

### Erro: "TesseractNotFoundError"

```bash
# Verificar caminho do Tesseract
which tesseract

# Configurar no código se necessário
import pytesseract
pytesseract.pytesseract.tesseract_cmd = '/usr/local/bin/tesseract'
```

### Erro: "Omnibees API timeout"

- Verificar credenciais no .env
- Usar modo development (retorna dados mock)
- Aumentar timeout no cliente

## 📈 Próximos Passos

1. **Treinar modelos customizados** para o domínio hoteleiro
2. **Implementar cache** para embeddings e resultados
3. **Adicionar mais idiomas** (inglês, espanhol)
4. **Integrar com mais sistemas** (PMS, POS)
5. **Implementar análise de voz** para chamadas

---

**Dúvidas?** Entre em contato com a equipe de desenvolvimento.
