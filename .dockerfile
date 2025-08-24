# Usar una imagen base de Python
FROM python:3.11-slim

# Establecer el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copiar el archivo de dependencias
COPY requirements.txt .

# Instalar las dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Copiar todo el código fuente al contenedor
COPY . .

# Exponer el puerto gRPC
EXPOSE 50051

# Comando para ejecutar el servidor MCP
CMD ["python", "mcp_server/run_server.py"]
