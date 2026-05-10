#!/bin/bash

# Build and run Docker containers for PharmAssist backend

echo "🚀 Starting PharmAssist Backend..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Copying from .env.example..."
    cp .env.example .env
    echo "✅ Created .env file. Please edit it with your settings."
fi

# Build and start containers
echo "🐳 Building and starting Docker containers..."
docker-compose up --build

echo "✅ PharmAssist Backend is running!"
echo "📖 Swagger UI: http://localhost:8000/docs"
echo "🏥 Health check: http://localhost:8000/health"
