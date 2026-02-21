# Usamos una imagen oficial de Python ligera y segura (slim)
FROM python:3.12-slim

# Evita que Python genere archivos .pyc y fuerza logs en tiempo real
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Directorio de trabajo dentro del contenedor
WORKDIR /app

# Instalamos git, curl, y Node.js (requerido para los servidores MCP vía npx)
RUN apt-get update && apt-get install -y git curl && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | \
    bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
# Instalamos las dependencias del proyecto y uv para el servidor MCP de Atlassian
RUN pip install --no-cache-dir --upgrade pip uv && \
    pip install --no-cache-dir -e .

# Copiamos el resto del código
COPY . .

# Exponemos el puerto 8000
EXPOSE 8000

# Comando por defecto al levantar (apuntando a 0.0.0.0 para que se vea desde fuera)
CMD ["uvicorn", "src.software_factory_poc.main:app", "--host", "0.0.0.0", "--port", "8000"]