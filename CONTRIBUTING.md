# Contributing to GenBase

Thank you for your interest in contributing to GenBase! This document provides guidelines and instructions for contributing to this project.

## Project Structure


- **Engine**: Genbase Server  (Python)
- **Studio**: Frontend application for Genbase
```
.
├── engine/                    # FastAPI backend
├── studio/                    # React/Vite frontend
├── docker/                    # Docker configurations
│   ├── docker-compose.yml
│   └── .env.template
└── scripts/                   # Utility scripts
    ├── build.sh
    ├── run-local.sh
    └── docker-run.sh
```

## Development Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- PDM (Python Dependency Manager)
- Docker and Docker Compose (for containerized development)
- Git

### Getting Started

1. Clone the repository:
   ```bash
   git clone https://github.com/your-organization/genbase.git
   cd genbase
   ```

2. Set up environment files:
   ```bash
   cp docker/.env.template .env
   cp engine/example.env engine/.env
   cp studio/example.env studio/.env
   ```

3. Edit the environment files with your credentials.

4. Make scripts executable:
   ```bash
   chmod +x scripts/*.sh
   ```

5. Install dependencies:
   ```bash
   # For Engine
   cd engine
   pdm install
   
   # For Studio
   cd ../studio
   npm install
   ```

6. Run the applications:
   ```bash
   # Using the convenience script
   ./scripts/run-local.sh
   
   # Or separately
   # Terminal 1
   cd engine
   pdm run start
   
   # Terminal 2
   cd studio
   npm run dev
   ```

### Using Docker

To run the entire application stack with Docker:

```bash
./scripts/docker-run.sh up
```

## Development Workflow

### Branching Strategy

We follow a modified Git Flow workflow:

- `main`: Production-ready code
- `develop`: Integration branch for features
- `feature/XXX`: New features
- `bugfix/XXX`: Bug fixes
- `hotfix/XXX`: Urgent fixes

### Pull Request Process

1. Create a new branch from `develop` for your feature or fix
2. Make your changes and commit with clear messages
3. Push your branch and create a pull request to `develop`
4. Ensure tests pass and code meets quality standards
5. Request reviews from maintainers
6. Address review feedback
7. Your PR will be merged once approved


## Testing

### Engine Tests

```bash
cd engine
pdm run pytest
```


## Documentation

- Update docs folder with any relevant changes
- Add docstrings to Python functions and classes
- Document API endpoints using FastAPI's documentation features

## Troubleshooting

If you encounter issues during development:

1. Check the logs:
   ```bash
   ./scripts/docker-run.sh logs
   ```

2. Ensure your environment variables are correctly set
3. Verify that all dependencies are installed
4. Check that database migrations have run successfully

## Contact

If you have questions or need help:

- Open an issue on GitHub
- Contact [utkarshkanwat@gmail.com]
- Join our community chat

Thank you for contributing to GenBase!