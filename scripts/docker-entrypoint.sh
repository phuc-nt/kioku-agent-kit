#!/bin/bash
set -e

# Wait for optional dependencies to be ready
wait_for_service() {
    local host=$1
    local port=$2
    local name=$3
    local max_attempts=30

    echo "Waiting for $name ($host:$port)..."
    for i in $(seq 1 $max_attempts); do
        if python -c "import socket; s=socket.socket(); s.settimeout(1); s.connect(('$host', $port)); s.close()" 2>/dev/null; then
            echo "$name is ready."
            return 0
        fi
        sleep 1
    done
    echo "WARNING: $name not available after ${max_attempts}s, continuing without it."
    return 0  # Don't fail — graceful degradation
}

# Wait for ChromaDB if in server mode
if [ "${KIOKU_CHROMA_MODE}" = "server" ] || [ "${KIOKU_CHROMA_MODE}" = "auto" ]; then
    if [ -n "${KIOKU_CHROMA_HOST}" ] && [ -n "${KIOKU_CHROMA_PORT}" ]; then
        wait_for_service "${KIOKU_CHROMA_HOST}" "${KIOKU_CHROMA_PORT}" "ChromaDB"
    fi
fi

# Wait for FalkorDB if configured
if [ -n "${KIOKU_FALKORDB_HOST}" ] && [ -n "${KIOKU_FALKORDB_PORT}" ]; then
    wait_for_service "${KIOKU_FALKORDB_HOST}" "${KIOKU_FALKORDB_PORT}" "FalkorDB"
fi

# Wait for Ollama and pull model if needed
if [ -n "${KIOKU_OLLAMA_HOST}" ]; then
    OLLAMA_HOST_CLEAN=$(echo "${KIOKU_OLLAMA_HOST}" | sed 's|http://||;s|https://||')
    OLLAMA_PORT=$(echo "${OLLAMA_HOST_CLEAN}" | cut -d: -f2)
    OLLAMA_HOSTNAME=$(echo "${OLLAMA_HOST_CLEAN}" | cut -d: -f1)

    if wait_for_service "${OLLAMA_HOSTNAME}" "${OLLAMA_PORT}" "Ollama"; then
        MODEL="${KIOKU_OLLAMA_MODEL:-nomic-embed-text}"
        echo "Checking Ollama model: $MODEL"
        if ! curl -sf "${KIOKU_OLLAMA_HOST}/api/tags" | python -c "import sys,json; models=[m['name'] for m in json.load(sys.stdin).get('models',[])]; sys.exit(0 if '$MODEL' in models or '${MODEL}:latest' in models else 1)" 2>/dev/null; then
            echo "Pulling Ollama model: $MODEL (this may take a while on first run)..."
            curl -sf "${KIOKU_OLLAMA_HOST}/api/pull" -d "{\"name\": \"$MODEL\"}" > /dev/null 2>&1 || echo "WARNING: Failed to pull model $MODEL"
        else
            echo "Ollama model $MODEL already available."
        fi
    fi
fi

# Route to the right command
case "${1}" in
    mcp)
        echo "Starting Kioku MCP Server..."
        exec python -m kioku.server
        ;;
    cli)
        shift
        exec kioku "$@"
        ;;
    *)
        exec "$@"
        ;;
esac
