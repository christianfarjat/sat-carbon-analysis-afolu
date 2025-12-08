# Dockerfile para Carbon Analysis Platform AFOLU
# Streamlit + Google Earth Engine + Claude AI

# Usar imagen base de Python 3.11 slim
FROM python:3.11-slim

# Configuración de Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema necesarias para librerías geoespaciales
# GDAL, GEOS, y PROJ son necesarios para geopandas, shapely, etc.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gdal-bin \
    libgdal-dev \
    libgeos-dev \
    libproj-dev \
    && rm -rf /var/lib/apt/lists/*

# Configurar variables de entorno para GDAL
ENV GDAL_CONFIG=/usr/bin/gdal-config

# Copiar requirements.txt primero (para aprovechar cache de Docker)
COPY requirements.txt /app/

# Instalar dependencias de Python
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código
COPY . /app/

# Puerto para Cloud Run (Cloud Run inyecta PORT, default 8080)
ENV PORT=8080
EXPOSE 8080

# Crear directorio para configuración de Streamlit
RUN mkdir -p ~/.streamlit

# Configuración de Streamlit para producción
RUN echo '\
[server]\n\
port = 8080\n\
address = 0.0.0.0\n\
headless = true\n\
enableCORS = false\n\
enableXsrfProtection = false\n\
' > ~/.streamlit/config.toml

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \    CMD curl -f http://localhost:8080/_stcore/health || exit 1

# Comando para arrancar Streamlit
# Streamlit se ejecuta en el puerto definido por $PORT
CMD streamlit run app.py --server.port=$PORT --server.address=0.0.0.0
