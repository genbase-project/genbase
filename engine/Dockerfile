FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install PDM
RUN pip install --no-cache-dir pdm

# Copy PDM files
COPY pyproject.toml pdm.lock ./


# Install dependencies using PDM
RUN pdm install --no-self

# Copy application code
COPY . .

# Create data directory
RUN mkdir -p .data

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8000
ENV PYTHONPATH=/app

# Expose the application port
EXPOSE 8000

# Start the application using PDM
CMD ["pdm", "run", "start"]