# Stage 1: Builder para dependencias y compilación
FROM python:3.9-slim AS builder

WORKDIR /app

# Variables de entorno para optimización Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Instalar dependencias del sistema necesarias
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements primero para aprovechar caché de Docker
COPY requirements.txt .

# Instalar dependencias Python
RUN pip install --user --no-warn-script-location \
    --no-cache-dir -r requirements.txt

# Stage 2: Runtime (imagen final ligera)
FROM python:3.9-slim AS runtime

WORKDIR /app

# Crear usuario no-root para seguridad
RUN groupadd -r mlops && useradd -r -g mlops mlops \
    && mkdir -p /app \
    && chown -R mlops:mlops /app

# Copiar solo dependencias instaladas desde el builder
COPY --from=builder /root/.local /home/mlops/.local

# Copiar aplicación
COPY --chown=mlops:mlops src/ ./src/
COPY --chown=mlops:mlops models/ ./models/

# Configurar entorno
ENV PATH="/home/mlops/.local/bin:${PATH}" \
    PYTHONPATH="/app/src" \
    PORT=8080

# Cambiar a usuario no-root
USER mlops

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:${PORT}/health', timeout=2)"

# Exponer puerto
EXPOSE 8080

# Comando de ejecución
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "4"]