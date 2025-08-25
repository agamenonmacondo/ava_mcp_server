FROM python:3.11-slim

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiar requirements e instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar todo el código fuente
COPY . .

# ✅ DEBUG: Verificar estructura real copiada
RUN echo "=== ESTRUCTURA REAL ===" && \
    ls -la /app/ && \
    echo "=== CONTENIDO mcp_server ===" && \
    ls -la /app/mcp_server/ 2>/dev/null || echo "mcp_server no existe" && \
    echo "=== BUSCANDO run_server.py ===" && \
    find /app -name "run_server.py" -type f

# Exponer puerto para Cloud Run
EXPOSE 8080

# ✅ COMANDO CORREGIDO para estructura: carpeta_principal/mcp_server/run_server.py
CMD echo "=== INICIANDO AVA BOT SERVER ===" && \
    echo "Puerto: ${PORT:-8080}" && \
    echo "Directorio actual: $(pwd)" && \
    echo "Contenido /app:" && ls -la /app/ && \
    echo "=== EJECUTANDO SERVIDOR ===" && \
    if [ -f "/app/mcp_server/run_server.py" ]; then \
        echo "✅ Ejecutando desde /app/mcp_server/run_server.py" && \
        cd /app && python mcp_server/run_server.py; \
    else \
        echo "❌ /app/mcp_server/run_server.py no encontrado" && \
        echo "Archivos disponibles:" && \
        find /app -name "*.py" | head -10 && \
        exit 1; \
    fi
