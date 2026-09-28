# 1. LA BASE: Debian slim (optimizado para Python, sin los problemas de Alpine)
FROM python:3.12-slim

# 2. VARIABLES DE ENTORNO (Sin caché de bytecode y logs en tiempo real)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# 3. DIRECTORIO DE TRABAJO
WORKDIR /app

# 4. DEPENDENCIAS DEL SISTEMA (Librerías necesarias para conectarse a Postgres y curl para healthchecks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 5. CACHÉ DE DEPENDENCIAS (Instalamos esto ANTES de copiar el código)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# 6. COPIAR EL CÓDIGO FUENTE (Copiamos tu main.py limpio y el resto de tu API)
COPY . .

# 7. SEGURIDAD: USUARIO SIN PRIVILEGIOS ROOT
RUN adduser --disabled-password --gecos "" saas_user \
    && chown -R saas_user:saas_user /app
USER saas_user

# 8. PUERTO EXPUESTO (Para que la red interna de Docker sepa dónde escuchar)
EXPOSE 8000

# 9. ARRANQUE EN PRODUCCIÓN (El control total lo tiene Uvicorn)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]