#!/bin/bash
# Initial setup script for ARIA Hotel AI

set -e

echo "🏨 ARIA Hotel AI - Setup Inicial"
echo "================================"
echo ""

# Check Python version
echo "🐍 Verificando Python..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
required_version="3.11"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then 
    echo "❌ Python $required_version ou superior é necessário (encontrado: $python_version)"
    exit 1
fi
echo "✅ Python $python_version"

# Check if uv is installed
echo ""
echo "📦 Verificando uv..."
if ! command -v uv &> /dev/null; then
    echo "📥 Instalando uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
fi
echo "✅ uv instalado"

# Create virtual environment
echo ""
echo "🔧 Criando ambiente virtual..."
uv venv
echo "✅ Ambiente virtual criado"

# Install dependencies
echo ""
echo "📚 Instalando dependências..."
source .venv/bin/activate
uv pip install -e ".[dev]"
echo "✅ Dependências instaladas"

# Create .env file
echo ""
echo "⚙️ Configurando variáveis de ambiente..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "✅ Arquivo .env criado"
    echo ""
    echo "📝 IMPORTANTE: Edite o arquivo .env com suas credenciais:"
    echo "   - Twilio (WhatsApp)"
    echo "   - OpenAI/Groq (IA)"
    echo "   - URLs do webhook"
else
    echo "✅ Arquivo .env já existe"
fi

# Check Redis
echo ""
echo "🔴 Verificando Redis..."
if command -v redis-cli &> /dev/null && redis-cli ping &> /dev/null; then
    echo "✅ Redis está rodando"
else
    echo "⚠️ Redis não está rodando"
    echo ""
    echo "Para instalar Redis:"
    echo "  macOS:  brew install redis && brew services start redis"
    echo "  Ubuntu: sudo apt install redis-server && sudo systemctl start redis"
    echo "  Docker: docker run -d -p 6379:6379 redis:alpine"
fi

# Create necessary directories
echo ""
echo "📁 Criando diretórios..."
mkdir -p logs data/uploads data/cache
echo "✅ Diretórios criados"

# Run tests
echo ""
echo "🧪 Executando testes..."
if uv run pytest tests/unit -v --tb=short; then
    echo "✅ Testes passaram!"
else
    echo "⚠️ Alguns testes falharam (isso é normal no início)"
fi

# Final instructions
echo ""
echo "🎉 Setup concluído!"
echo ""
echo "Próximos passos:"
echo "1. Edite o arquivo .env com suas credenciais"
echo "2. Configure o webhook do Twilio"
echo "3. Inicie o servidor: ./scripts/start.sh"
echo ""
echo "Para mais informações: cat docs/quickstart.md"
echo ""
echo "Comandos úteis:"
echo "  uv run aria info          - Verificar configuração"
echo "  uv run aria serve         - Iniciar servidor"
echo "  uv run aria test-ana MSG  - Testar Ana"
echo "  uv run aria webhook-url   - Ver URLs dos webhooks"
