#!/bin/bash
# Start ARIA Hotel AI in development mode

set -e

echo "🚀 Starting ARIA Hotel AI..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "📝 Creating .env from .env.example..."
    cp .env.example .env
    echo "⚠️  Please edit .env with your configuration!"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d .venv ]; then
    echo "🔧 Creating virtual environment..."
    uv venv
fi

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
echo "📦 Installing dependencies..."
uv pip install -e .

# Start Redis if not running
if ! command -v redis-cli &> /dev/null || ! redis-cli ping &> /dev/null; then
    echo "🔴 Redis is not running. Please start Redis first:"
    echo "   brew services start redis (macOS)"
    echo "   sudo systemctl start redis (Linux)"
    exit 1
fi

# Run database migrations (when implemented)
# echo "🗄️  Running database migrations..."
# alembic upgrade head

# Start the API server
echo "✅ Starting API server..."
uv run aria serve --reload
