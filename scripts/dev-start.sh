#!/bin/bash
set -e

echo "🚀 Starting reGen Development Server..."

# Check if frontend needs to be built
if [ -d "/app/frontend" ] && [ -f "/app/frontend/package.json" ]; then
    echo "📦 Installing frontend dependencies..."
    cd /app/frontend
    
    # Only install if node_modules doesn't exist or package.json changed
    if [ ! -d "node_modules" ] || [ "package.json" -nt "node_modules" ]; then
        npm install
    fi
    
    echo "🔨 Building React frontend..."
    npm run build 
    
    cd /app
    echo "✅ Frontend build complete!"
else
    echo "⚠️  Frontend directory not found, skipping build"
fi

echo "🐍 Starting FastAPI server with hot reload..."
exec python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
