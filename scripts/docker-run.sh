#!/bin/bash

# Script to run GenBase applications with Docker Compose

set -e

# Get the root directory of the monorepo
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Print banner
echo "=================================="
echo "Running GenBase with Docker Compose"
echo "=================================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Docker is not installed. Please install Docker and try again."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "Docker Compose is not installed. Please install Docker Compose and try again."
    exit 1
fi

# Go to the root directory
cd "$ROOT_DIR"

# Check for environment files and create from templates if needed
if [ ! -f "$ROOT_DIR/.env" ]; then
    echo "Root .env file not found. Creating one from template..."
    cp "$ROOT_DIR/docker/.env.template" "$ROOT_DIR/.env"
    echo "Created root .env file. Please edit with your credentials."
fi

# Check for engine .env
if [ ! -f "$ROOT_DIR/engine/.env" ]; then
    echo "Engine .env file not found. Creating one from template..."
    if [ -f "$ROOT_DIR/engine/.env.template" ]; then
        cp "$ROOT_DIR/engine/.env.template" "$ROOT_DIR/engine/.env"
        echo "Created engine .env file. Please edit with your credentials."
    else
        echo "Warning: Engine .env.template not found. Engine may not have all required environment variables."
    fi
fi

# Check for studio .env (needed for build args)
if [ ! -f "$ROOT_DIR/studio/.env" ]; then
    echo "Studio .env file not found. Creating one from template..."
    if [ -f "$ROOT_DIR/studio/.env.template" ]; then
        cp "$ROOT_DIR/studio/.env.template" "$ROOT_DIR/studio/.env"
        echo "Created studio .env file. Please edit with your credentials."
    else
        echo "Warning: Studio .env.template not found. Studio build may not have all required environment variables."
    fi
fi

# Set the docker-compose file location
COMPOSE_FILE="$ROOT_DIR/docker/docker-compose.yml"

# Option handling
if [ "$1" == "up" ] || [ -z "$1" ]; then
    echo "Starting services..."
    docker-compose -f "$COMPOSE_FILE" up -d
    echo "Services started. Access the applications at:"
    echo "- Engine: http://localhost:8000"
    echo "- Studio: http://localhost:5173"
elif [ "$1" == "down" ]; then
    echo "Stopping services..."
    docker-compose -f "$COMPOSE_FILE" down
    echo "Services stopped."
elif [ "$1" == "logs" ]; then
    echo "Showing logs..."
    docker-compose -f "$COMPOSE_FILE" logs -f
elif [ "$1" == "build" ]; then
    echo "Building images..."
    docker-compose -f "$COMPOSE_FILE" build
    echo "Images built."
elif [ "$1" == "restart" ]; then
    echo "Restarting services..."
    docker-compose -f "$COMPOSE_FILE" restart
    echo "Services restarted."
else
    echo "Unknown command: $1"
    echo "Usage: $0 [up|down|logs|build|restart]"
    exit 1
fi

echo "=================================="
echo "Command executed successfully!"
echo "=================================="