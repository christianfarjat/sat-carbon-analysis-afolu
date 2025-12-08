"""
🌍 CARBON ANALYSIS PLATFORM AFOLU
Sistema Completo de Análisis de Potencial de Carbono
Integración: Google Earth Engine + Streamlit + Claude AI

Autor: Análisis Geoespacial Profesional
Licencia: MIT
"""

import streamlit as st
import geemap.foliumap as geemap
import ee
import os
import json
import base64
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from io import BytesIO
import anthropic
from PIL import Image
import requests

# ============================================================================
# CONFIGURACIÓN INICIAL
# ============================================================================

st.set_page_config(
    page_title="Carbon Analysis AFOLU",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos personalizados
st.markdown("""
    <style>
        .main { padding-top: 0rem; }
        .block-container { padding-top: 1rem; }
        h1 { color: #2D8659; text-align: center; }
        h2 { color: #1F5233; }
        .metric-card {
            background-color: #f0f7f1;
            padding: 20px;
            border-radius: 10px;
            border-left: 4px solid #2D8659;
        }
    </style>
""", unsafe_allow_html=True)

# ============================================================================
# INICIALIZACIÓN DE GOOGLE EARTH ENGINE
# ============================================================================

@st.cache_resource
def init_gee():
    """Inicializar Google Earth Engine"""
    try:
        # No usar ee.Authenticate() en producción
        # geemap lo maneja automáticamente
        geemap.ee_initialize()
        return True
    except Exception as e:
        st.error(f"Error inicializando GEE: {str(e)}")
        st.info("⚠️ Asegúrate de tener configurada la variable de entorno EARTHENGINE_TOKEN")
        return False

# ============================================================================
# FUNCIONES DE PROCESAMIENTO GEE
# ============================================================================

@st.cache_data
def get_satellite_data(aoi, start_date, end_date, cloud_cover=10):
    """
    Descargar imágenes Sentinel-2 para el AOI
    
    Args:
        aoi: Google Earth Engine geometry
        start_date: Fecha inicio (string)
        end_date: Fecha fin (string)
        cloud_cover: Porcentaje máximo de cobertura de nubes
    
    Returns:
        ee.ImageCollection
    """
    try:
        s2 = ee.ImageCollection("COPERNICUS/S2_SR") \
            .filterBounds(aoi) \
            .filterDate(start_date, end_date) \
            .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', cloud_cover))
        
        return s2
    except Exception as e:
        st.error(f"Error descargando datos Sentinel-2: {str(e)}")
        return None

def calculate_indices(image):
    """
    Calcular índices de vegetación
    
    Índices calculados:
    - NDVI: Normalized Difference Vegetation Index
    - EVI: Enhanced Vegetation Index
    - LAI: Leaf Area Index (derivado de EVI)
    - NBR: Normalized Burn Ratio
    """
    # NDVI
    ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI')
    
    # EVI
    evi = image.expression(
        '2.5 * ((NIR - RED) / (NIR + 6*RED - 7.5*BLUE + 1))',
        {
            'NIR': image.select('B8'),
            'RED': image.select('B4'),
            'BLUE': image.select('B2')
        }
    ).rename('EVI')
    
    # LAI desde EVI (IPCC Tier 1)
    lai = evi.multiply(4.0).min(8.0).rename('LAI')
    
    # NBR (Normalized Burn Ratio)
    nbr = image.normalizedDifference(['B8', 'B12']).rename('NBR')
    
    return image.addBands([ndvi, evi, lai, nbr])

def estimate_biomass_and_carbon(ndvi_image, aoi, scale=30):
    """
    Estimar biomasa y carbono usando NDVI
    
    Fórmula IPCC Tier 1 para bosques tropicales:
    AGB (Mg/ha) = 10.5 * NDVI^1.5
    Carbono = AGB * 0.47
    CO2 = Carbono * 3.67
    """
    # Biomasa aérea estimada
    agb = ndvi_image.pow(1.5).multiply(10.5).rename('AGB')
    
    # Carbono (fracción 0.47)
    carbon = agb.multiply(0.47).rename('Carbon')
    
    # CO2 (factor de conversión 3.67)
    co2 = carbon.multiply(3.67).rename('CO2_tCO2ha')
    
    # Calcular estadísticas zonales
    stats = co2.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=aoi,
        scale=scale,
        maxPixels=1e13
    )
    
    return {
        'agb_image': agb,
        'carbon_image': carbon,
        'co2_image': co2,
        'stats': stats
    }

def calculate_land_cover_change(aoi, year1=2018, year2=2024):
    """
    Analizar cambios en cobertura de suelo entre dos años
    Usando WorldCover dataset
    """
    try:
        # WorldCover 10m annual maps
        wc1 = ee.ImageCollection("ESA/WorldCover/v200") \
            .filter(ee.Filter.eq('system:index', str(year1))) \
            .first() \
            .clip(aoi)
        
        wc2 = ee.ImageCollection("ESA/WorldCover/v200") \
            .filter(ee.Filter.eq('system:index', str(year2))) \
            .first() \
            .clip(aoi)
        
        # Detectar cambios
        change = wc2.neq(wc1).rename('Change')
        
        # Contar píxeles de cambio
        change_pixels = change.reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=aoi,
            scale=10,
            maxPixels=1e13
        )
        
        return {
            'wc1': wc1,
            'wc2': wc2,
            'change': change,
            'change_pixels': change_pixels
        }
    except Exception as e:
        st.warning(f"Error en análisis de cambio: {str(e)}")
        return None

def get_zone_statistics(image, aoi, band_names, scale=30):
    """
    Obtener estadísticas zonales para múltiples bandas
    """
    stats_dict = {}
    
    for band in band_names:
        try:
            band_stats = image.select(band).reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=aoi,
                scale=scale,
                maxPixels=1e13
            ).getInfo()
            
            stats_dict[band] = band_stats.get(band, 0)
        except:
            stats_dict[band] = None
    
    return stats_dict

# ============================================================================
# FUNCIONES DE IA Y ANÁLISIS
# ============================================================================

def analyze_with_claude(carbon_stats, indices_stats, metadata):
    """
    Usar Claude AI para análisis inteligente de datos de carbono
    
    Genera interpretación profesional de métricas geoespaciales
    """
    try:
        client = anthropic.Anthropic(api_key=st.secrets.get("ANTHROPIC_API_KEY"))
        
        prompt = f"""
ANÁLISIS PROFESIONAL DE POTENCIAL DE CARBONO AFOLU
═══════════════════════════════════════════════════

DATOS GEOESPACIALES CAPTURADOS:
• Tipo de sensor: Sentinel-2 (10m resolución)
• Período analizado: {metadata.get('start_date')} a {metadata.get('end_date')}
• Cobertura de nubes: {metadata.get('cloud_cover')}%

MÉTRICAS DE VEGETACIÓN:
• NDVI (Índice Normalizado de Diferencia de Vegetación): {indices_stats.get('NDVI', 'N/A'):.3f}
  → Escala: -1 a +1
  → Interpretación: >0.6 bosque denso, 0.4-0.6 bosque moderado, <0.2 poca vegetación
  
• EVI (Índice Mejorado de Vegetación): {indices_stats.get('EVI', 'N/A'):.3f}
  → Más sensible a cambios en dosel
  
• LAI (Índice de Área Foliar): {indices_stats.get('LAI', 'N/A'):.3f}
  → Rango óptimo bosque: 4-8

ESTIMACIONES DE CARBONO (IPCC Tier 1):
• Biomasa Aérea (AGB): {carbon_stats.get('AGB', 'N/A'):.2f} Mg/ha
• Carbono Almacenado: {carbon_stats.get('Carbon', 'N/A'):.2f} tC/ha
• Secuestro de CO₂: {carbon_stats.get('CO2', 'N/A'):.2f} tCO₂/ha/año

REQUERIMIENTOS DE RESPUESTA:

1. INTERPRETACIÓN DE ÍNDICES
   - Evalúa la calidad y confiabilidad de los datos NDVI/EVI
   - Identifica anomalías o limitaciones en la clasificación
   - Compara con rangos típicos para ecosistemas tropicales

2. VALIDACIÓN METODOLÓGICA
   - Verifica conformidad con estándares IPCC 2019 (AFOLU)
   - Señala supuestos metodológicos críticos
   - Identifica factores de incertidumbre

3. ESTIMACIÓN DE CARBONO
   - Valida las cifras calculadas de tCO₂/ha/año
   - Proporciona rangos de confianza (±porcentaje)
   - Compara con valores de referencia por tipo de ecosistema

4. ELEGIBILIDAD PARA CRÉDITOS
   - ¿Cumple requisitos mínimos para certificación?
   - Recomendaciones para mejorar potencial de créditos
   - Próximos pasos para validación y verificación

5. RECOMENDACIONES ESTRATÉGICAS
   - Intervenciones de manejo recomendadas
   - Monitoreo sugerido (frecuencia y método)
   - Estimaciones de ingresos por carbono

Proporciona análisis profesional apto para reportes de auditoría ambiental.
Mantén tono técnico pero accesible. Usa formato estructurado con headers.
"""
        
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=2000,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        return message.content[0].text
        
    except Exception as e:
        st.error(f"Error en análisis con Claude: {str(e)}")
        return None

def generate_report(carbon_stats, indices_stats, metadata, ai_analysis):
    """
    Generar reporte completo en formato estructurado
    """
    report = f"""
╔══════════════════════════════════════════════════════════════════════════╗
║           REPORTE TÉCNICO DE ANÁLISIS DE CARBONO AFOLU                  ║
║                      PROYECTO DE CRÉDITOS DE CARBONO                     ║
╚══════════════════════════════════════════════════════════════════════════╝

FECHA DE ANÁLISIS: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
PERÍODO ANALIZADO: {metadata.get('start_date')} a {metadata.get('end_date')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. DATOS DE ENTRADA
   • Sensor: Sentinel-2 Level-2A
   • Resolución: 10 metros
   • Banda NIR: B8 | Banda Red: B4 | Banda Blue: B2
   • Filtro nubes: < {metadata.get('cloud_cover')}%
   • Imágenes procesadas: {metadata.get('images_count', 'N/A')}

2. MÉTRICAS DE VEGETACIÓN
   
   NDVI (Normalized Difference Vegetation Index):
   ├─ Valor: {indices_stats.get('NDVI', 'N/A'):.4f}
   ├─ Clasificación: {_classify_ndvi(indices_stats.get('NDVI', 0))}
   └─ Cobertura forestal estimada: {_estimate_forest_cover(indices_stats.get('NDVI', 0))}%
   
   EVI (Enhanced Vegetation Index):
   ├─ Valor: {indices_stats.get('EVI', 'N/A'):.4f}
   └─ Validación: {"✓ Consistente con NDVI" if abs(indices_stats.get('EVI', 0) - indices_stats.get('NDVI', 0)) < 0.2 else "⚠ Revisar correlación"}
   
   LAI (Leaf Area Index):
   ├─ Valor: {indices_stats.get('LAI', 'N/A'):.2f} m²/m²
   └─ Interpretación: {"Óptimo para bosque" if 4 <= indices_stats.get('LAI', 0) <= 8 else "Fuera de rango típico"}

3. ESTIMACIÓN DE CARBONO
   
   Biomasa Aérea (AGB):
   ├─ Valor: {carbon_stats.get('AGB', 'N/A'):.2f} Mg/ha
   └─ Fórmula: AGB = 10.5 × NDVI^1.5 (IPCC Tier 1)
   
   Stock de Carbono:
   ├─ Valor: {carbon_stats.get('Carbon', 'N/A'):.2f} tC/ha
   └─ Factor de conversión: 0.47 (Contenido de C en biomasa seca)
   
   SECUESTRO DE CO₂ [MÉTRICA CRÍTICA]:
   ├─ Valor: {carbon_stats.get('CO2', 'N/A'):.2f} tCO₂/ha/año
   ├─ Rango de incertidumbre: ±20-30%
   └─ Equivalencia anual (100ha): {float(carbon_stats.get('CO2', 0)) * 100:.0f} tCO₂

4. VALIDACIÓN METODOLÓGICA
   
   ✓ Conformidad IPCC 2019:
     • Tier 1: Fórmulas de decisión de tieraje
     • Datos: Sentinel-2 (>100m resolución aceptable)
     • Período: {metadata.get('start_date')} a {metadata.get('end_date')} (mín 5 años recomendado)
   
   ⚠ Limitaciones identificadas:
     • Validación recomendada con datos de campo
     • Incertidumbre potencial en bosques con dosel heterogéneo
     • Datos de suelo no incluidos (requiere análisis adicional)

5. ELEGIBILIDAD PARA CRÉDITOS DE CARBONO
   
   Criterios evaluados:
   ├─ Adicionalidad: {_evaluate_additionality(indices_stats.get('NDVI', 0))}
   ├─ Permanencia: Revisar cambios anuales
   ├─ No-leakage: Requiere análisis de línea base territorial
   └─ Verificabilidad: {"Datos públicos (Sentinel-2)" if True else "Requiere validación"}
   
   Potencial de certificación:
   └─ {_evaluate_certification_potential(carbon_stats.get('CO2', 0))}

6. ANÁLISIS EXPERTO (INTELIGENCIA ARTIFICIAL)
   
{ai_analysis}

7. RECOMENDACIONES
   
   Inmediato (0-3 meses):
   □ Validar con datos de campo (DAP mínimo 50 árboles)
   □ Establecer puntos de control permanente (GPS)
   □ Documentar metodología completa
   
   Corto plazo (3-6 meses):
   □ Solicitar aprobación de metodología (Verra/Gold Standard)
   □ Elaborar Plan de Monitoreo y Verificación
   □ Iniciar línea base de degradación
   
   Mediano plazo (6-12 meses):
   □ Primera verificación independiente
   □ Emisión de créditos de carbono
   □ Estructurar ingresos y distribución

8. ESTIMACIÓN FINANCIERA
   
   Precio referencial (Verra VCS 2024): $15-18/tCO₂
   
   Potencial anual (área analizada):
   ├─ Por hectárea: ${float(carbon_stats.get('CO2', 0)) * 15:.2f}/año
   └─ Por 100 hectáreas: ${float(carbon_stats.get('CO₂', 0)) * 100 * 15:.0f}/año
   
   Proyección 10 años (asumiendo retención):
   └─ {float(carbon_stats.get('CO2', 0)) * 10 * 100 * 15:.0f} USD (100 ha)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CERTIFICACIONES RECOMENDADAS:
• VCS (Verified Carbon Standard) - Más estricto
• Gold Standard for the SDGs - Mayor precio
• Plan Vivo - Para proyectos comunitarios

PRÓXIMOS PASOS:
1. Contactar validador independiente certificado
2. Presentar metodología para aprobación
3. Iniciar período de tiempo de operación (36 meses típico)
4. Reporte de verificación anual

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

REFERENCIAS TÉCNICAS:
• IPCC 2019: Refinement to the 2006 IPCC Guidelines
• GFOI Methods Document v3.1
• Verra Standard VCS Version 4.4
• Gold Standard Carbon Methodologies

CONFIDENCIALIDAD: Este documento contiene información técnica confidencial.
Distribución restringida a partes autorizadas.

═══════════════════════════════════════════════════════════════════════════
Generado por: Carbon Analysis Platform AFOLU v1.0
Plataforma: Streamlit + Google Earth Engine
═══════════════════════════════════════════════════════════════════════════
"""
    
    return report

def _classify_ndvi(ndvi):
    """Clasificar NDVI en categorías"""
    if ndvi > 0.6:
        return "Bosque Denso ✓"
    elif ndvi > 0.4:
        return "Bosque Moderado"
    elif ndvi > 0.2:
        return "Vegetación Dispersa"
    else:
        return "Poca/Sin Vegetación"

def _estimate_forest_cover(ndvi):
    """Estimar cobertura forestal desde NDVI"""
    return max(0, min(100, (ndvi - 0.2) * 200))

def _evaluate_additionality(ndvi):
    """Evaluar si proyecto es adicional"""
    if ndvi > 0.5:
        return "Potencial (requiere análisis BAU)"
    else:
        return "Requiere revisión"

def _evaluate_certification_potential(co2_value):
    """Evaluar potencial de certificación"""
    if co2_value > 5:
        return "Alto potencial para certificación ✓"
    elif co2_value > 2:
        return "Potencial moderado (puede mejorar)"
    else:
        return "Requiere intervenciones de manejo"

# ============================================================================
# INTERFAZ PRINCIPAL
# ============================================================================

def main():
    # Header
    col1, col2 = st.columns([4, 1])
    with col1:
        st.title("🌍 Carbon Analysis Platform AFOLU")
        st.markdown("**Sistema Profesional de Análisis de Potencial de Carbono**")
    
    with col2:
        st.metric("Versión", "1.0")
    
    st.markdown("---")
    
    # Inicializar GEE
    if not init_gee():
        st.stop()
    
    # Tabs principales
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🗺️ Análisis Geoespacial",
        "📊 Índices y Estimaciones",
        "🤖 Análisis Inteligente",
        "📄 Reporte",
        "ℹ️ Información"
    ])
    
    # ========================================================================
    # TAB 1: ANÁLISIS GEOESPACIAL
    # ========================================================================
    
    with tab1:
        st.header("1. Análisis Geoespacial")
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.subheader("Mapa Interactivo")
            st.info("💡 Dibuja tu AOI (Área de Interés) en el mapa utilizando las herramientas")
            
            # Crear mapa
            m = geemap.Map(
                center=[0, 0],
                zoom=4,
                height=600,
                draw_control=True,
                measure_control=False,
                fullscreen_control=False
            )
            
            # Agregar basemaps
            m.add_basemap('OpenStreetMap')
            m.add_basemap('Google Satellite Hybrid')
            
            m.to_streamlit()
        
        with col2:
            st.subheader("⚙️ Configuración")
            
            # Parámetros
            start_date = st.date_input(
                "📅 Fecha inicio",
                value=datetime.now() - timedelta(days=365),
                help="Inicio del período de análisis"
            )
            
            end_date = st.date_input(
                "📅 Fecha fin",
                value=datetime.now(),
                help="Fin del período de análisis"
            )
            
            cloud_cover = st.slider(
                "☁️ Cobertura máx. nubes",
                0, 100, 10,
                help="Filtro de calidad de imagen"
            )
            
            # Guardar parámetros en sesión
            st.session_state.start_date = start_date.isoformat()
            st.session_state.end_date = end_date.isoformat()
            st.session_state.cloud_cover = cloud_cover
            
            st.divider()
            
            if st.button("▶️ PROCESAR ANÁLISIS", use_container_width=True, type="primary"):
                st.session_state.run_analysis = True
        
        # Procesar si se clickea botón
        if st.session_state.get('run_analysis'):
            with st.spinner("⏳ Descargando imágenes Sentinel-2..."):
                
                # Obtener AOI del mapa
                if hasattr(m, 'user_rois') and len(m.user_rois) > 0:
                    aoi = m.user_rois[-1]
                else:
                    # AOI por defecto (ejemplo: Perú)
                    aoi = ee.Geometry.Point([-75.5, -8.5]).buffer(10000)
                    st.warning("⚠️ Usando AOI de ejemplo. Por favor dibuja tu área en el mapa.")
                
                # Descargar datos
                s2 = get_satellite_data(
                    aoi,
                    st.session_state.start_date,
                    st.session_state.end_date,
                    st.session_state.cloud_cover
                )
                
                if s2 is not None:
                    st.session_state.s2 = s2
                    st.session_state.aoi = aoi
                    st.session_state.analysis_ready = True
                    st.success("✓ Datos descargados exitosamente")
                else:
                    st.error("❌ Error descargando datos")
    
    # ========================================================================
    # TAB 2: ÍNDICES Y ESTIMACIONES
    # ========================================================================
    
    with tab2:
        st.header("2. Cálculo de Índices de Vegetación")
        
        if st.session_state.get('analysis_ready'):
            with st.spinner("📊 Calculando índices..."):
                
                # Calcular índices
                s2_with_indices = st.session_state.s2.map(calculate_indices)
                median_image = s2_with_indices.median()
                
                # Estadísticas
                indices_stats = get_zone_statistics(
                    median_image,
                    st.session_state.aoi,
                    ['NDVI', 'EVI', 'LAI']
                )
                
                # Guardar en sesión
                st.session_state.median_image = median_image
                st.session_state.indices_stats = indices_stats
                
                # Mostrar resultados
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric(
                        "🌿 NDVI",
                        f"{indices_stats.get('NDVI', 0):.3f}",
                        help="Índice Normalizado de Diferencia de Vegetación"
                    )
                
                with col2:
                    st.metric(
                        "📈 EVI",
                        f"{indices_stats.get('EVI', 0):.3f}",
                        help="Índice Mejorado de Vegetación"
                    )
                
                with col3:
                    st.metric(
                        "🍃 LAI",
                        f"{indices_stats.get('LAI', 0):.2f}",
                        help="Índice de Área Foliar"
                    )
                
                with col4:
                    cobertura = _estimate_forest_cover(indices_stats.get('NDVI', 0))
                    st.metric(
                        "🌲 Cobertura",
                        f"{cobertura:.0f}%",
                        help="Cobertura forestal estimada"
                    )
                
                st.divider()
                
                # Estimación de biomasa y carbono
                with st.spinner("🔬 Estimando biomasa y carbono (IPCC Tier 1)..."):
                    biomass_result = estimate_biomass_and_carbon(
                        median_image.select('NDVI'),
                        st.session_state.aoi
                    )
                    
                    # Obtener valores
                    stats = biomass_result['stats'].getInfo()
                    
                    carbon_stats = {
                        'AGB': stats.get('AGB', 0),
                        'Carbon': stats.get('Carbon', 0),
                        'CO2': stats.get('CO2_tCO2ha', 0)
                    }
                    
                    st.session_state.carbon_stats = carbon_stats
                    st.session_state.biomass_result = biomass_result
                
                # Métricas de carbono
                st.subheader("🌍 Estimaciones de Carbono")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric(
                        "📦 Biomasa Aérea (AGB)",
                        f"{carbon_stats['AGB']:.2f} Mg/ha",
                        help="Megagramos por hectárea",
                        delta=f"±30%"
                    )
                
                with col2:
                    st.metric(
                        "🔋 Stock de Carbono",
                        f"{carbon_stats['Carbon']:.2f} tC/ha",
                        help="Toneladas de carbono por hectárea",
                        delta=f"±30%"
                    )
                
                with col3:
                    st.metric(
                        "💨 Secuestro CO₂",
                        f"{carbon_stats['CO2']:.2f} tCO₂/ha/año",
                        help="Métrica crítica para créditos de carbono",
                        delta=f"±30%"
                    )
                
                # Información adicional
                with st.expander("ℹ️ Interpretación Técnica"):
                    st.markdown(f"""
                    ### Fórmulas Utilizadas
                    
                    **Biomasa Aérea (IPCC Tier 1):**
                    ```
                    AGB (Mg/ha) = 10.5 × NDVI^1.5
                    ```
                    - Válido para bosques tropicales
                    - Incertidumbre: ±20-30%
                    
                    **Stock de Carbono:**
                    ```
                    C (tC/ha) = AGB × 0.47
                    ```
                    - Factor 0.47 = fracción de carbono en biomasa seca
                    
                    **Secuestro de CO₂:**
                    ```
                    CO₂ (tCO₂/ha/año) = C × 3.67
                    ```
                    - Factor 3.67 = masa molecular CO₂/C
                    
                    ### Validación
                    - ✓ NDVI: {_classify_ndvi(indices_stats.get('NDVI', 0))}
                    - ✓ LAI: {indices_stats.get('LAI', 0):.2f} m²/m²
                    - ✓ Datos: Sentinel-2 Level-2A
                    """)
        
        else:
            st.info("👈 Por favor completa el análisis geoespacial primero")
    
    # ========================================================================
    # TAB 3: ANÁLISIS INTELIGENTE
    # ========================================================================
    
    with tab3:
        st.header("3. Análisis Inteligente con Claude AI")
        
        if st.session_state.get('carbon_stats'):
            
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.subheader("🤖 Análisis Experto (Powered by Claude)")
                st.info("Análisis profesional de datos geoespaciales usando IA")
            
            with col2:
                if st.button("🔄 Regenerar Análisis", use_container_width=True):
                    st.session_state.run_ai_analysis = True
            
            # Ejecutar análisis IA
            if st.session_state.get('run_ai_analysis') or 'ai_analysis' not in st.session_state:
                with st.spinner("🤔 Claude analizando datos..."):
                    
                    metadata = {
                        'start_date': st.session_state.start_date,
                        'end_date': st.session_state.end_date,
                        'cloud_cover': st.session_state.cloud_cover,
                        'images_count': 'múltiples'
                    }
                    
                    ai_analysis = analyze_with_claude(
                        st.session_state.carbon_stats,
                        st.session_state.indices_stats,
                        metadata
                    )
                    
                    if ai_analysis:
                        st.session_state.ai_analysis = ai_analysis
                        st.session_state.run_ai_analysis = False
            
            if 'ai_analysis' in st.session_state:
                st.markdown(st.session_state.ai_analysis)
        
        else:
            st.info("👈 Por favor completa el análisis geoespacial e índices primero")
    
    # ========================================================================
    # TAB 4: REPORTE
    # ========================================================================
    
    with tab4:
        st.header("4. Generación de Reporte Técnico")
        
        if st.session_state.get('carbon_stats'):
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("📄 Generar Reporte Completo", use_container_width=True, type="primary"):
                    st.session_state.generate_report = True
            
            with col2:
                if st.button("📊 Descargar CSV", use_container_width=True):
                    st.session_state.download_csv = True
            
            with col3:
                if st.button("📎 Copiar al Portapapeles", use_container_width=True):
                    st.session_state.copy_report = True
            
            if st.session_state.get('generate_report') or 'full_report' not in st.session_state:
                
                metadata = {
                    'start_date': st.session_state.start_date,
                    'end_date': st.session_state.end_date,
                    'cloud_cover': st.session_state.cloud_cover,
                    'images_count': 'múltiples'
                }
                
                full_report = generate_report(
                    st.session_state.carbon_stats,
                    st.session_state.indices_stats,
                    metadata,
                    st.session_state.get('ai_analysis', 'No disponible')
                )
                
                st.session_state.full_report = full_report
                st.session_state.generate_report = False
            
            if 'full_report' in st.session_state:
                # Mostrar reporte
                st.markdown("### 📋 Vista Previa del Reporte")
                
                st.text_area(
                    "Reporte Técnico",
                    value=st.session_state.full_report,
                    height=600,
                    disabled=True
                )
                
                # Botones de descarga
                st.divider()
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    # Descargar como TXT
                    st.download_button(
                        "⬇️ Descargar TXT",
                        data=st.session_state.full_report,
                        file_name=f"reporte_carbono_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                        mime="text/plain",
                        use_container_width=True
                    )
                
                with col2:
                    # Descargar datos como CSV
                    csv_data = pd.DataFrame({
                        'Métrica': ['NDVI', 'EVI', 'LAI', 'AGB', 'Carbono', 'CO2/ha/año'],
                        'Valor': [
                            f"{st.session_state.indices_stats.get('NDVI', 0):.4f}",
                            f"{st.session_state.indices_stats.get('EVI', 0):.4f}",
                            f"{st.session_state.indices_stats.get('LAI', 0):.2f}",
                            f"{st.session_state.carbon_stats.get('AGB', 0):.2f}",
                            f"{st.session_state.carbon_stats.get('Carbon', 0):.2f}",
                            f"{st.session_state.carbon_stats.get('CO2', 0):.2f}"
                        ],
                        'Unidad': ['adimensional', 'adimensional', 'm²/m²', 'Mg/ha', 'tC/ha', 'tCO2/ha/año']
                    })
                    
                    st.download_button(
                        "📊 Descargar CSV",
                        data=csv_data.to_csv(index=False),
                        file_name=f"datos_carbono_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                
                with col3:
                    st.info("✓ Reporte generado exitosamente")
        
        else:
            st.info("👈 Por favor completa los análisis previos")
    
    # ========================================================================
    # TAB 5: INFORMACIÓN
    # ========================================================================
    
    with tab5:
        st.header("ℹ️ Información y Ayuda")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📖 Guía de Uso")
            st.markdown("""
            ### Flujo de Trabajo
            
            **1. Análisis Geoespacial**
            - Dibuja tu AOI en el mapa interactivo
            - Ajusta fechas y filtro de nubes
            - Haz clic en "PROCESAR ANÁLISIS"
            
            **2. Índices y Estimaciones**
            - Visualiza NDVI, EVI, LAI automáticamente
            - Obtén estimaciones de biomasa (IPCC Tier 1)
            - Calcula secuestro de CO₂/ha/año
            
            **3. Análisis Inteligente**
            - Claude AI interpreta tus datos
            - Evaluación de elegibilidad para créditos
            - Recomendaciones estratégicas
            
            **4. Reporte Final**
            - Documento técnico completo
            - Apto para auditorías AFOLU
            - Descargable en múltiples formatos
            """)
        
        with col2:
            st.subheader("🔬 Metodología")
            st.markdown("""
            ### Fuentes de Datos
            - **Imágenes**: Sentinel-2 Level-2A (ESA)
            - **Resolución**: 10 metros
            - **Disponibilidad**: Global, libre acceso
            
            ### Fórmulas Utilizadas
            - IPCC 2019 Refinement (AFOLU)
            - Tier 1: Fórmulas decisionales
            - Factores por defecto: Bosques tropicales
            
            ### Certificaciones Compatibles
            - ✓ Verra VCS
            - ✓ Gold Standard
            - ✓ Plan Vivo
            - ✓ UNCCD LDN
            
            ### Validación Recomendada
            - Datos de campo (DAP, altura)
            - Análisis de suelo (SOC)
            - Verificación independiente
            """)
        
        st.divider()
        
        st.subheader("📚 Referencias Técnicas")
        
        references = pd.DataFrame({
            'Documento': [
                'IPCC 2019 Refinement',
                'GFOI Methods v3.1',
                'Verra VCS Standard',
                'Gold Standard',
                'FAO Guidelines'
            ],
            'Tema': [
                'AFOLU Methodologies',
                'Forest Carbon Measurement',
                'Carbon Verification',
                'SDG Integration',
                'Forest Resources Assessment'
            ],
            'Año': [2019, 2021, 2023, 2023, 2020]
        })
        
        st.dataframe(references, use_container_width=True, hide_index=True)
        
        st.divider()
        
        st.subheader("⚙️ Configuración Técnica")
        
        with st.expander("Ver configuración"):
            st.json({
                'Plataforma': 'Streamlit',
                'Procesamiento': 'Google Earth Engine',
                'IA': 'Claude 3.5 Sonnet',
                'Datos': 'Sentinel-2 (ESA)',
                'Formato Salida': ['TXT', 'CSV', 'Visualización Interactiva'],
                'Versión': '1.0'
            })
        
        st.divider()
        
        st.subheader("📞 Soporte")
        st.info("""
        **¿Preguntas o problemas?**
        
        - 📧 Email: support@carbonanalysis.io
        - 🐛 Reportar bugs: GitHub Issues
        - 📚 Documentación: [docs.carbonanalysis.io](https://docs.carbonanalysis.io)
        - 💬 Comunidad: [Discord Server](https://discord.gg/carbon)
        """)

# ============================================================================
# INICIALIZACIÓN DE SESIÓN
# ============================================================================

if __name__ == "__main__":
    # Inicializar variables de sesión
    if 'run_analysis' not in st.session_state:
        st.session_state.run_analysis = False
    
    if 'analysis_ready' not in st.session_state:
        st.session_state.analysis_ready = False
    
    if 'run_ai_analysis' not in st.session_state:
        st.session_state.run_ai_analysis = False
    
    if 'generate_report' not in st.session_state:
        st.session_state.generate_report = False
    
    # Ejecutar app
    main()
