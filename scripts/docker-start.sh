#!/bin/bash
# Start ARIA Hotel AI with Docker Compose

set -e

echo "🐳 Starting ARIA Hotel AI with Docker..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "📝 Creating .env from .env.example..."
    cp .env.example .env
    echo "⚠️  Please edit .env with your configuration!"
    exit 1
fi

# Build and start containers
echo "🔨 Building containers..."
docker-compose build

echo "🚀 Starting services..."
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 5

# Check health
echo "🏥 Checking service health..."
curl -f http://localhost:8000/health || echo "⚠️  API not ready yet"

echo "✅ ARIA Hotel AI is running!"
echo ""
echo "📍 Services:"
echo "   - API: http://localhost:8000"
echo "   - API Docs: http://localhost:8000/api/docs"
echo "   - Grafana: http://localhost:3000 (admin/admin)"
echo "   - Prometheus: http://localhost:9090"
echo ""
echo "📝 View logs: docker-compose logs -f"
echo "🛑 Stop: docker-compose down"
