## Building and Deployment

### Building for Production

To build both applications for production:

```bash
./scripts/build.sh
```

### Docker Commands

- Start all services: `./scripts/docker-run.sh up`
- Stop all services: `./scripts/docker-run.sh down`
- View logs: `./scripts/docker-run.sh logs`
- Rebuild images: `./scripts/docker-run.sh build`
- Restart services: `./scripts/docker-run.sh restart`

### Key Environment Variables

#### Engine (FastAPI)

The Engine supports many environment variables. Key ones include:

```
# LLM API Keys (At least one is required)
ANTHROPIC_API_KEY=your_anthropic_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
GROQ_API_KEY=your_groq_api_key
MISTRAL_API_KEY=your_mistral_api_key
DEEPSEEK_API_KEY=your_deepseek_api_key
# Many more

# Core settings
REGISTRY_URL=http://localhost:5173
DATA_DIR=".data"
ADMIN_USERNAME="admin"
ADMIN_PASSWORD="your_secure_password_here"
DATABASE_URL="postgresql://user:password@host/database?sslmode=require"

# Additional settings
LOG_LEVEL="INFO"
API_HOST="0.0.0.0"
API_PORT="8000"
# ... and many more (see engine/.env.template)
```

#### Studio (React/Vite)

```
# Core settings
VITE_ENGINE_URL="http://localhost:8000"
VITE_API_USERNAME="admin"
VITE_API_PASSWORD="your_secure_password_here"
```

> **Note:** When running with Docker Compose, the Engine container will use its own `.env` file mounted as a volume, allowing for runtime configuration changes without rebuilding the container.

## Getting Started

### Running with Docker Compose (Recommended)

1. Make sure you have Docker and Docker Compose installed.
2. Copy the environment templates:
   ```
   cp docker/.env.template .env
   cp engine/.env.template engine/.env
   cp studio/.env.template studio/.env
   ```
3. Edit all `.env` files with your credentials.
4. Make scripts executable:
   ```
   chmod +x scripts/*.sh
   ```
5. Run the Docker Compose script:
   ```
   ./scripts/docker-run.sh up
   ```
6. Access the applications:
   - Engine: http://localhost:8000
   - Studio: http://localhost:5173

### Running Locally

1. Make sure you have Python 3.11+ and Node.js 18+ installed.
2. Copy the environment templates:
   ```
   cp engine/example.env engine/.env
   cp studio/example.env studio/.env
   ```
3. Edit the `.env` files with your credentials.
4. Make scripts executable:
   ```
   chmod +x scripts/*.sh
   ```
5. Run the local script:
   ```
   ./scripts/run-local.sh
   ```
6. Access the applications:
   - Engine: http://localhost:8000
   - Studio: http://localhost:5173

### Testing and Troubleshooting

### Quick Test Guide

1. **Check environment files**
   - Verify `.env`, `engine/.env`, and `studio/.env` exist and contain the right variables

2. **Test the applications**
   - Engine API: Make API calls to http://localhost:8000
   - Studio UI: Open http://localhost:5173 in your browser
   - Try logging in with the configured admin credentials

3. **Common troubleshooting**
   - View logs: `./scripts/docker-run.sh logs`
   - Restart services: `./scripts/docker-run.sh restart`
   - Check container status: `docker ps -a`
