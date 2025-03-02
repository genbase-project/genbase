# Genbase

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![GitHub Stars](https://img.shields.io/github/stars/genbase-ai/genbase.svg)](https://github.com/genbase-ai/genbase/stargazers)
[![Discord](https://img.shields.io/discord/1224567890123456?label=discord)](https://discord.gg/genbase)

> A modular platform for specialized AI agents that collaborate to solve complex problems.

## What is Genbase?

Genbase is an open platform that enables AI-powered collaboration through specialized modules. Instead of building one agent that knows a little about everything, Genbase allows you to combine domain-specific agents that each bring deep expertise to their area.

![Genbase Platform Overview](https://placeholder-image.com/genbase-overview.png)

### Key Features

- **Specialized Modules**: Package domain expertise into modules with purpose-built agents
- **Collaborative Workflows**: Agents work together through well-defined relationships
- **Git-Based Workspaces**: Agents operate on real repositories with full filesystem access
- **Extensible Architecture**: Add new capabilities by creating or combining modules

## Why Genbase?

Traditional AI assistants try to know everything but often lack depth in specialized areas. Genbase takes a different approach:

```
┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
│  Next.js Expert │   │PostgreSQL Expert│   │ Docker Expert   │
│                 │◄──►                 │◄──►                 │
└─────────────────┘   └─────────────────┘   └─────────────────┘
```

- **Web Developer Module**: Deep knowledge of frameworks, components and best practices
- **Database Module**: Expertise in schema design, query optimization and administration
- **Deployment Module**: Specialized in containerization, networking and cloud services

Modules collaborate through actions, sharing context, and workspace access - creating solutions no single agent could provide alone.

## Getting Started

### Running with Docker Compose (Recommended)

1. Clone the repository:
   ```bash
   git clone https://github.com/genbase-ai/genbase.git
   cd genbase
   ```

2. Copy the environment templates:
   ```bash
   cp docker/.env.template docker/.env
   cp engine/.env.template engine/.env
   cp studio/.env.template studio/.env
   ```

3. Edit the `.env` files with your credentials (at minimum, add an LLM API key):
   ```bash
   nano engine/.env
   ```

4. Make scripts executable:
   ```bash
   chmod +x scripts/*.sh
   ```

5. Start Genbase:
   ```bash
   ./scripts/docker-run.sh up
   ```

6. Access the applications:
   - Studio: http://localhost:5173
   - Engine API: http://localhost:8000

### Running Locally

1. Make sure you have Python 3.11+ and Node.js 18+ installed.
2. Follow steps 1-3 above.
3. Run the local script:
   ```bash
   ./scripts/run-local.sh
   ```

## Quick Demo

1. Create a new project
2. Add the Next.js Web Developer module from the registry
3. Start the development workflow
4. Ask the specialized agent to create a feature
5. Watch as it generates code, runs tests, and explains its approach

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

### Testing and Troubleshooting

#### Quick Test Guide

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

## Documentation

- [Getting Started Guide](https://docs.genbase.io/getting-started)
- [Core Concepts](https://docs.genbase.io/concepts)
- [Architecture](https://docs.genbase.io/architecture)
- [Creating Modules](https://docs.genbase.io/creating-modules)

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for details on how to get started.

## License

Genbase is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.