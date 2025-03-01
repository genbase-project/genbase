#!/bin/bash

# Build script for GenBase monorepo

set -e

# Get the root directory of the monorepo
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Print banner
echo "=================================="
echo "Building GenBase applications"
echo "=================================="

# Build Engine (FastAPI)
echo "Building Engine (FastAPI)..."
cd "$ROOT_DIR/engine"
# Install Python dependencies if needed
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
fi
echo "Engine build completed."

# Build Studio (React/Vite)
echo "Building Studio (React/Vite)..."
cd "$ROOT_DIR/studio"
# Install npm dependencies if needed
if [ -f "package.json" ]; then
    npm install
    npm run build
fi
echo "Studio build completed."

echo "=================================="
echo "Build process completed successfully!"
echo "=================================="