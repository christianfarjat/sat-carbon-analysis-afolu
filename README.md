# 🌍 Carbon Analysis Platform AFOLU

## Sistema Profesional de Análisis de Potencial de Carbono

Aplicación Streamlit + Google Earth Engine + Claude AI para análisis geoespacial de proyectos AFOLU y certificación de créditos de carbono.

### ✨ Características Principales

#### 🗺️ **Análisis Geoespacial**
- Interfaz interactiva con mapas Folium
- Dibujo libre de AOI (Áreas de Interés)
- Acceso automático a 90+ petabytes de datos satelitales
- Imágenes Sentinel-2 (10m resolución) con filtro de nubes

#### 📊 **Cálculo Automático de Índices**
- **NDVI**: Normalized Difference Vegetation Index
- **EVI**: Enhanced Vegetation Index
- **LAI**: Leaf Area Index
- **NBR**: Normalized Burn Ratio

#### 🔬 **Estimación de Carbono (IPCC Tier 1)**
- Biomasa Aérea (AGB) en Mg/ha
- Stock de Carbono en tC/ha
- **Secuestro de CO₂: tCO₂/ha/año** ← Métrica crítica para créditos
- Análisis de cambio de cobertura de suelo

#### 🤖 **Inteligencia Artificial**
- Integración con Claude 3.5 Sonnet
- Análisis experto automático de datos geoespaciales
- Evaluación de elegibilidad para certificaciones
- Recomendaciones estratégicas para proyectos AFOLU

#### 📄 **Reportes Profesionales**
- Documento técnico completo (IPCC 2019 compliant)
- Exportación múltiples formatos (TXT, CSV)
- Apto para auditorías y verificación de créditos

---

## 🚀 Guía de Despliegue Rápido

### Opción 1: Streamlit Cloud (Más fácil - 5 minutos)

#### Paso 1: Crear cuenta Streamlit Cloud
```bash
1. Ir a share.streamlit.io
2. Click "Sign up"
3. Conectar GitHub
4. Autorizar Streamlit
```

#### Paso 2: Obtener token de Google Earth Engine

```bash
# En tu terminal local:
python
>>> import ee
>>> ee.Authenticate()
# Se abrirá navegador - Autoriza y copia código
# Presiona Enter

# El token se guardará en: ~/.config/earthengine/credentials
```

#### Paso 3: Crear repositorio GitHub

```bash
# Crear carpeta del proyecto
mkdir carbon-analysis-app
cd carbon-analysis-app

# Inicializar git
git init
git config user.name "Tu Nombre"
git config user.email "tu@email.com"

# Crear archivos (copiar app.py, requirements.txt, .streamlit/config.toml)

# Crear .gitignore
cat > .gitignore << EOF
.env
.streamlit/secrets.toml
__pycache__/
*.pyc
*.pyo
EOF

# Commit
git add .
git commit -m "Initial commit: Carbon Analysis Platform"

# Crear repositorio en GitHub
# 1. github.com/new
# 2. Nombre: carbon-analysis-afolu
# 3. Público
# 4. Crear

# Agregar remote
git remote add origin https://github.com/TU_USUARIO/carbon-analysis-afolu.git
git branch -M main
git push -u origin main
```

#### Paso 4: Desplegar en Streamlit Cloud

```bash
1. Ir a share.streamlit.io
2. Click "New app"
3. Seleccionar repository: carbon-analysis-afolu
4. Branch: main
5. Main file path: app.py
6. Click "Deploy"
```

#### Paso 5: Agregar secrets (Credenciales)

**En Streamlit Cloud:**
1. Click en el menú ⋯ (arriba a la derecha)
2. Settings → Secrets
3. Agregar:

```toml
[anthropic]
api_key = "sk-ant-XXXXX"  # Tu API key de Anthropic

[earthengine]
token = "... (contenido de ~/.config/earthengine/credentials)"
```

**¿Cómo obtener API Key de Anthropic?**
1. Ir a console.anthropic.com
2. Sign up o login
3. Click "API Keys"
4. "Create Key"
5. Copiar y pegar

**¿Cómo obtener EarthEngine Token?**
```bash
# Después de ee.Authenticate()
cat ~/.config/earthengine/credentials
# Copiar todo el contenido (es un JSON)
```

#### Paso 6: Acceder a tu app

```
URL: https://carbon-analysis-afolu.streamlit.app
(Tu usuario y nombre de repo)
```

---

### Opción 2: Google Cloud Run (Más profesional - 15 minutos)

#### Requisitos Previos
- Cuenta Google Cloud
- Cloud Run habilitado
- Docker instalado

#### Paso 1: Crear Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

#### Paso 2: Crear .gcloudignore

```
.git
.gitignore
__pycache__
.pytest_cache
.streamlit/secrets.toml
.env
```

#### Paso 3: Desplegar

```bash
# Autenticar
gcloud auth login

# Configurar proyecto
gcloud config set project MI-PROYECTO

# Construir y desplegar
gcloud run deploy carbon-analysis \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

---

## 📖 Guía de Uso de la Aplicación

### 1. Análisis Geoespacial

```
1. En el mapa interactivo, dibuja tu AOI usando las herramientas
2. Ajusta los parámetros:
   - Fecha inicio / fin (rango máximo: 5 años)
   - Cobertura de nubes máxima (10-15% recomendado)
3. Click "PROCESAR ANÁLISIS"
4. La app descarga automáticamente Sentinel-2 para tu zona
```

**Herramientas del Mapa:**
- ✏️ Dibujar: Polígonos, líneas, puntos
- 🔍 Zoom: Rueda del ratón
- 📍 Basemaps: Selector arriba a la izquierda

### 2. Índices de Vegetación

```
Automáticamente verás:
- NDVI (0 a 1): Densidad de vegetación
- EVI (0 a 1): Índice mejorado
- LAI (0 a 8): Área foliar
- Cobertura forestal estimada
```

**Interpretación:**
- NDVI > 0.6 = Bosque denso ✓
- NDVI 0.4-0.6 = Bosque moderado
- NDVI < 0.2 = Poca vegetación

### 3. Estimaciones de Carbono

```
Recibirás automáticamente:
- Biomasa Aérea (AGB): Mg/ha
- Stock de Carbono: tC/ha
- Secuestro CO₂: tCO₂/ha/año ← MÉTRICA PRINCIPAL
```

**Validar resultados:**
- Comparar con datos de campo si disponibles
- Revisar literatura para ecosistema similar
- Rango típico bosque tropical: 5-15 tCO₂/ha/año

### 4. Análisis Inteligente

```
Claude AI genera:
1. Interpretación técnica de índices
2. Evaluación de metodología IPCC
3. Validación de cifras de carbono
4. Elegibilidad para certificación
5. Recomendaciones estratégicas
```

### 5. Generar Reporte

```
Click "Generar Reporte Completo":
- Documento técnico completo
- Apto para auditorías
- Descargar como TXT o CSV
```

---

## 🔧 Configuración Local (Desarrollo)

### Instalación

```bash
# Clonar repositorio
git clone https://github.com/TU_USUARIO/carbon-analysis-afolu.git
cd carbon-analysis-afolu

# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Configurar credenciales
mkdir -p ~/.streamlit
cat > ~/.streamlit/secrets.toml << EOF
[anthropic]
api_key = "sk-ant-XXXXX"

[earthengine]
token = "..."
EOF
```

### Ejecutar Localmente

```bash
streamlit run app.py
```

Accede a: http://localhost:8501

---

## 📊 Datos y Metodología

### Fuentes de Datos

| Fuente | Resolución | Cobertura | Actualización |
|--------|-----------|-----------|---------------|
| **Sentinel-2** | 10m | Global | 5 días |
| **Landsat 8/9** | 30m | Global | 16 días |
| **WorldCover** | 10m | Global | Anual |
| **SRTM DEM** | 30m | 56°N-60°S | Estático |
| **GEDI** | Variable | Entre 52°N-52°S | Continuo |

### Fórmulas Implementadas

#### NDVI (Normalized Difference Vegetation Index)
```
NDVI = (NIR - RED) / (NIR + RED)
```
- Rango: -1 a +1
- 0.6+: Vegetación densa
- <0.2: Poca/sin vegetación

#### Biomasa Aérea (IPCC Tier 1)
```
AGB (Mg/ha) = 10.5 × NDVI^1.5
```
- Válido para bosques tropicales
- Incertidumbre: ±20-30%

#### Stock de Carbono
```
C (tC/ha) = AGB × 0.47
```
- Factor 0.47 = fracción de carbono en biomasa seca

#### Secuestro de CO₂
```
CO₂ (tCO₂/ha/año) = C × 3.67
```
- Factor 3.67 = masa molecular CO₂/C

### Certificaciones Compatibles

- ✓ **Verra VCS** (stricto)
- ✓ **Gold Standard** (precio mayor)
- ✓ **Plan Vivo** (comunitarios)
- ✓ **UNCCD LDN** (degradación)

---

## 🤖 Integración Claude AI

### Capabilities

- **Análisis de imágenes geoespaciales**: Interpreta mapas NDVI/EVI
- **Evaluación metodológica**: Verifica IPCC Tier 1
- **Validación de carbono**: Contrasta cifras con benchmarks
- **Elegibilidad de créditos**: Evalúa cumplimiento de estándares
- **Recomendaciones**: Sugiere mejoras y próximos pasos

### Costo API

- **Entrada**: $0.003 por 1K tokens (texto)
- **Salida**: $0.015 por 1K tokens (texto)
- **Típico por análisis**: $0.50-1.00

### Limitar Uso (Opcional)

```python
# En app.py, modificar:
message = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1500,  # Reducir de 2000 a 1500
    messages=[...]
)
```

---

## 🐛 Troubleshooting

### Error: "Earth Engine client library not initialized"

**Solución:**
```toml
# En .streamlit/secrets.toml:
[earthengine]
token = "..."  # Completa con contenido de ~/.config/earthengine/credentials
```

No usar `ee.Authenticate()` en el código (geemap lo maneja).

### Error: "ANTHROPIC_API_KEY not found"

**Solución:**
1. Crear cuenta en console.anthropic.com
2. Crear API key
3. Agregar a secrets.toml:
```toml
[anthropic]
api_key = "sk-ant-XXXXX"
```

### La app es lenta

**Optimizaciones:**
```python
# Reducir rango temporal
end_date = start_date + timedelta(days=90)

# Aumentar filtro de nubes
cloud_cover = 20  # De 10 a 20

# Reducir resolución
scale = 60  # De 30 a 60 metros
```

### No aparece el mapa

**Verificar:**
1. Conexión a internet
2. Geemap instalado: `pip install -U geemap`
3. Folium disponible: `pip install folium`

---

## 📈 Casos de Uso

### Caso 1: Proyecto de Reforestación (Perú)

```
Entrada: KMZ con 500 ha de reforestación
Análisis: NDVI → Biomasa → CO₂
Resultado: 3,750 tCO₂/año (500 × 7.5)
Ingresos: $56,250/año (precio $15/tCO₂)
```

### Caso 2: Evaluación de Degradación (Brasil)

```
Entrada: Polígonos de deforestación 2018-2024
Análisis: Cambio de cobertura + emisiones
Resultado: 50 tCO₂/ha emitidas
Acción: Restauración inmediata
```

### Caso 3: Validación de Línea Base (Colombia)

```
Entrada: AOI de 10,000 ha de bosque
Análisis: NDVI histórico (2015-2024)
Resultado: Tendencia estable (elegible para certificación)
Certificación: VCS + Gold Standard
```

---

## 📚 Referencias

- [IPCC 2019 Refinement](https://www.ipcc-nggip.iges.or.jp/public/2019rf/)
- [GFOI Methods v3.1](https://www.reddcompass.org/mgd-v3-1-en)
- [Verra VCS Standard](https://verra.org/programs/verified-carbon-standard/)
- [Google Earth Engine](https://earthengine.google.com/)
- [Streamlit Docs](https://docs.streamlit.io/)
- [Anthropic Claude](https://www.anthropic.com/)

---

## 📄 Licencia

MIT License - Libre para usar, modificar y distribuir.

## 🤝 Contribuciones

Las contribuciones son bienvenidas. Por favor:
1. Fork el repositorio
2. Crear rama feature (`git checkout -b feature/AmazingFeature`)
3. Commit cambios (`git commit -m 'Add AmazingFeature'`)
4. Push a rama (`git push origin feature/AmazingFeature`)
5. Open Pull Request

---

## 📞 Soporte

- 📧 Email: support@carbonanalysis.io
- 🐛 Issues: GitHub Issues
- 💬 Comunidad: [Discord](#)

---

**Versión**: 1.0.0  
**Última actualización**: Diciembre 2025  
**Mantener actualizado**: `pip install -U geemap streamlit anthropic`

---

Made with ❤️ for AFOLU Carbon Projects
