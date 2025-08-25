FROM python:3.11-slim

# Instalar dependencias del sistema incluyendo ffmpeg
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Establecer directorio de trabajo
WORKDIR /app

# Copiar requirements.txt primero para optimizar cache
COPY requirements.txt .

# Instalar dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código
COPY . .

# Verificar estructura copiada
RUN echo "=== ESTRUCTURA COPIADA ===" && \
    find /app -name "*.py" | grep -E "(server|run)" | head -10 && \
    echo "=== DIRECTORIO ava_bot ===" && \
    ls -la /app/ava_bot/ || echo "ava_bot no existe" && \
    echo "=== BUSCANDO ARCHIVOS SERVIDOR ===" && \
    find /app -name "*server*.py" -type f

# Exponer puerto
EXPOSE 8080

# Comando flexible que busca el archivo correcto
CMD echo "Iniciando servidor..." && \
    if [ -f "/app/ava_bot/mcp_server/run_server.py" ]; then \
        echo "Usando ruta estándar" && python /app/ava_bot/mcp_server/run_server.py; \
    elif [ -f "/app/run_server.py" ]; then \
        echo "Usando ruta raíz" && python /app/run_server.py; \
    else \
        echo "Buscando archivo servidor..." && \
        SERVER_FILE=$(find /app -name "*server*.py" -type f | head -1) && \
        if [ -n "$SERVER_FILE" ]; then \
            echo "Ejecutando: $SERVER_FILE" && python "$SERVER_FILE"; \
        else \
            echo "ERROR: No se encontró archivo servidor" && exit 1; \
        fi; \
    fi
