#!/bin/bash

# Start services if not running
echo "Starting Docker services..."
docker-compose -f docker-compose.dev.yml up --build

# Wait for services to be ready
echo "Waiting for services to be ready..."
sleep 10

# Run database migrations
echo "Running database migrations..."
docker-compose exec regen-api-dev alembic upgrade head

echo "Migrations completed!"