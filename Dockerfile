# Usamos una imagen oficial de Python ligera y segura (slim)
FROM python:3.12-slim

# Evita que Python genere archivos .pyc y fuerza logs en tiempo real
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Directorio de trabajo dentro del contenedor
WORKDIR /app

# Instalamos git, curl, Node.js y DUMB-INIT (el salvavidas de los subprocesos)
RUN apt-get update && apt-get install -y git curl dumb-init && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | \
    bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
# Instalamos dependencias y uv
RUN pip install --no-cache-dir --upgrade pip uv && \
    pip install --no-cache-dir -e .

# Copiamos el resto del código
COPY . .

EXPOSE 8000

# Esto garantiza que al hacer 'docker compose down', todas las sesiones MCP (npx/uvx) mueran instantáneamente.
ENTRYPOINT ["/usr/bin/dumb-init", "--"]

# Comando por defecto al levantar
CMD ["uvicorn", "src.software_factory_poc.main:app", "--host", "0.0.0.0", "--port", "8000"]