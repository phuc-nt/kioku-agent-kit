FROM python:3.12-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml .
COPY src/ src/

# Install kioku with all extras
RUN pip install --no-cache-dir ".[full]"

# Create data directories
RUN mkdir -p /data/memory /data/data

ENV KIOKU_MEMORY_DIR=/data/memory \
    KIOKU_DATA_DIR=/data/data \
    KIOKU_CHROMA_MODE=auto

COPY scripts/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

ENTRYPOINT ["/docker-entrypoint.sh"]

# Default: run MCP server via stdio
CMD ["mcp"]
