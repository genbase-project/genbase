#!/bin/bash

# Script to run GenBase applications locally

set -e

# Get the root directory of the monorepo
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Load environment variables
if [ -f "$ROOT_DIR/.env" ]; then
    export $(grep -v '^#' "$ROOT_DIR/.env" | xargs)
fi

# Print banner
echo "=================================="
echo "Starting GenBase applications locally"
echo "=================================="

# Function to stop processes on script exit
function cleanup {
    echo "Stopping all processes..."
    if [ ! -z "$ENGINE_PID" ]; then
        kill $ENGINE_PID 2>/dev/null || true
    fi
    if [ ! -z "$STUDIO_PID" ]; then
        kill $STUDIO_PID 2>/dev/null || true
    fi
}

# Set trap for clean exit
trap cleanup EXIT INT TERM

# Start Engine (FastAPI)
echo "Starting Engine (FastAPI)..."
cd "$ROOT_DIR/engine"
if [ -f ".env" ]; then
    echo "Using Engine's existing .env file"
else
    echo "Creating Engine's .env file from template"
    if [ -f ".env.template" ]; then
        cp .env.template .env
        echo "Created from template. Please edit the .env file with your credentials."
    elif [ -f "$ROOT_DIR/.env" ]; then
        echo "No template found. Creating .env from root .env file"
        # Copy all variables that might be used by the engine
        cat "$ROOT_DIR/.env" > .env
    else
        echo "Warning: No environment file found for Engine. Some features may not work correctly."
        touch .env
    fi
fi
# Run with PDM instead of directly with Python
pdm run start &
ENGINE_PID=$!
echo "Engine started with PID: $ENGINE_PID"

# Wait for Engine to start
echo "Waiting for Engine to start..."
sleep 5

# Start Studio (React/Vite)
echo "Starting Studio (React/Vite)..."
cd "$ROOT_DIR/studio"
if [ -f ".env" ]; then
    echo "Using Studio's existing .env file"
else
    echo "Creating Studio's .env file from template"
    if [ -f ".env.template" ]; then
        cp .env.template .env
        echo "Created from template. Please edit the .env file with your credentials."
    elif [ -f "$ROOT_DIR/.env" ]; then
        echo "No template found. Creating .env from root .env file"
        # Extract Vite-specific variables
        grep -E '^VITE_' "$ROOT_DIR/.env" > .env
    else
        echo "Warning: No environment file found for Studio. Some features may not work correctly."
        touch .env
    fi
fi
npm run dev &
STUDIO_PID=$!
echo "Studio started with PID: $STUDIO_PID"

echo "=================================="
echo "All applications started successfully!"
echo "Engine running at: http://localhost:8000"
echo "Studio running at: http://localhost:5173"
echo "Press Ctrl+C to stop all services"
echo "=================================="

# Wait for processes to complete
wait $ENGINE_PID $STUDIO_PID