import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import base64
import io
import os
from PIL import Image
from io import BytesIO
import matplotlib.pyplot as plt
import seaborn as sns
import altair as alt

# Configurar el tema y la página
st.set_page_config(
    page_title="Sistema Avanzado de Análisis de Normas Gráficas",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado para mejorar el diseño
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 20px;
        text-align: center;
        padding: 1rem;
        border-bottom: 2px solid #E5E7EB;
    }
    .sub-header {
        font-size: 1.5rem;
        font-weight: 600;
        color: #1E3A8A;
        margin-top: 20px;
        margin-bottom: 10px;
        padding-bottom: 5px;
        border-bottom: 1px solid #E5E7EB;
    }
    .metric-card {
        background-color: #F8F9FA;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        text-align: center;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        color: #1E3A8A;
    }
    .metric-label {
        font-size: 0.9rem;
        color: #6B7280;
        margin-top: 5px;
    }
    .status-complete {
        background-color: #D1FAE5;
        padding: 5px 10px;
        border-radius: 5px;
        color: #065F46;
        font-weight: 600;
    }
    .status-pending {
        background-color: #FEF3C7;
        padding: 5px 10px;
        border-radius: 5px;
        color: #92400E;
        font-weight: 600;
    }
    .status-na {
        background-color: #F3F4F6;
        padding: 5px 10px;
        border-radius: 5px;
        color: #4B5563;
        font-weight: 600;
    }
    .dashboard-card {
        background-color: white;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin-bottom: 20px;
    }
    .info-box {
        background-color: #EFF6FF;
        border-left: 5px solid #3B82F6;
        padding: 10px 15px;
        margin-bottom: 15px;
    }
    .warning-box {
        background-color: #FEF3C7;
        border-left: 5px solid #F59E0B;
        padding: 10px 15px;
        margin-bottom: 15px;
    }
    .error-box {
        background-color: #FEE2E2;
        border-left: 5px solid #EF4444;
        padding: 10px 15px;
        margin-bottom: 15px;
    }
    .success-box {
        background-color: #D1FAE5;
        border-left: 5px solid #10B981;
        padding: 10px 15px;
        margin-bottom: 15px;
    }
    .filter-section {
        background-color: #F9FAFB;
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 20px;
    }
    .highlight-text {
        font-weight: 600;
        color: #1E3A8A;
    }
    .stButton>button {
        width: 100%;
    }
    div[data-testid="stVerticalBlock"] div[style*="flex-direction: column;"] div[data-testid="stVerticalBlock"] {
        background-color: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

# Header personalizado
st.markdown('<div class="main-header">Sistema Avanzado de Análisis de Normas Gráficas</div>', unsafe_allow_html=True)

# Función para procesar el archivo Excel con mejor manejo de errores
@st.cache_data
def procesar_archivo(uploaded_file):
    try:
        # Leer desde la fila 2 (índice 1) porque la fila 1 tiene el título
        df = pd.read_excel(uploaded_file, skiprows=1)
        
        # Convertir todas las columnas relevantes a string para evitar problemas con .str
        for col in df.columns:
            if col not in ['N° Interno', 'N° plazas']:  # Mantener algunos como numéricos
                df[col] = df[col].astype(str)
        
        # Limpiar datos: reemplazar 'nan' con cadenas vacías
        df = df.replace('nan', '')
        
        # Verificar si las columnas clave existen
        columnas_requeridas = ['N° Interno', 'PPU', 'Terminal']
        for col in columnas_requeridas:
            if col not in df.columns:
                st.error(f"Columna requerida '{col}' no encontrada en el archivo.")
                return pd.DataFrame()
        
        # Calcular métricas adicionales
        df = calcular_metricas(df)
        
        return df
    except Exception as e:
        st.error(f"Error al procesar el archivo: {str(e)}")
        st.error("Asegúrese de que el archivo tiene el formato correcto y contiene las columnas necesarias.")
        return pd.DataFrame()

# Calcular métricas adicionales para análisis
def calcular_metricas(df):
    try:
        # Determinar cuáles son las columnas de normas (excluyendo info del bus y columnas calculadas)
        # Identificamos columnas de normas basándonos en que generalmente empiezan después de cierta columna
        # y tienen nombres específicos o patrones.
        columnas_info = ['N° Interno', 'PPU', 'Unidad', 'Marca chasis', 'Modelo chasis', 
                        'Subclase', 'N° plazas', 'Terminal', 'Taller', 'TERMINADOS', 
                        'NORMA INSTALADA', 'FECHA DE RENOVACION']
        
        columnas_normas = [col for col in df.columns if col not in columnas_info]
        
        # Mostrar información de las columnas detectadas
        st.session_state['columnas_normas'] = columnas_normas
        
        # Calcular normas instaladas (1), no aplicables (no aplica) y faltantes (vacío) por bus
        df['total_normas'] = len(columnas_normas)
        
        # Usando conversión explícita a string para evitar errores
        df['normas_instaladas'] = df[columnas_normas].apply(
            lambda x: sum(1 for val in x if str(val).strip() == '1'), axis=1)
        
        df['normas_no_aplica'] = df[columnas_normas].apply(
            lambda x: sum(1 for val in x if str(val).lower().strip() == 'no aplica'), axis=1)
        
        df['normas_faltantes'] = df[columnas_normas].apply(
            lambda x: sum(1 for val in x if str(val).strip() == ''), axis=1)
        
        # Calcular porcentaje de avance por bus (considerando solo las aplicables)
        df['normas_aplicables'] = df['total_normas'] - df['normas_no_aplica']
        df['porcentaje_avance'] = (df['normas_instaladas'] / df['normas_aplicables'] * 100).round(2)
        
        # Manejar casos donde normas_aplicables = 0 para evitar división por cero
        df.loc[df['normas_aplicables'] == 0, 'porcentaje_avance'] = 0
        
        # Reemplazar infinito y NaN con 0
        df['porcentaje_avance'] = df['porcentaje_avance'].replace([np.inf, -np.inf, np.nan], 0)
        
        return df
    except Exception as e:
        st.error(f"Error al calcular métricas: {str(e)}")
        return df

# Función para generar gráficos avanzados
def generar_graficos(df):
    if df.empty:
        return {}
    
    # 1. Resumen general de instalación
    total_buses = len(df)
    buses_completos = len(df[df['normas_faltantes'] == 0])
    porcentaje_flota_completa = (buses_completos / total_buses * 100) if total_buses > 0 else 0
    
    # 2. Distribución de normas por estado
    total_normas = df['total_normas'].iloc[0] * len(df)
    total_instaladas = df['normas_instaladas'].sum()
    total_no_aplica = df['normas_no_aplica'].sum()
    total_faltantes = df['normas_faltantes'].sum()
    
    data_estado_normas = pd.DataFrame([
        {'Estado': 'Instaladas', 'Cantidad': total_instaladas, 'Porcentaje': (total_instaladas / total_normas * 100)},
        {'Estado': 'No Aplica', 'Cantidad': total_no_aplica, 'Porcentaje': (total_no_aplica / total_normas * 100)},
        {'Estado': 'Faltantes', 'Cantidad': total_faltantes, 'Porcentaje': (total_faltantes / total_normas * 100)}
    ])
    
    # Gráfico de pie interactivo y atractivo
    fig_estado_normas = px.pie(
        data_estado_normas, 
        names='Estado', 
        values='Cantidad',
        color='Estado',
        color_discrete_map={'Instaladas':'#10B981', 'No Aplica':'#F59E0B', 'Faltantes':'#EF4444'},
        title='Distribución de Normas por Estado',
        hole=0.4  # Donut chart
    )
    fig_estado_normas.update_traces(textposition='inside', textinfo='percent+label')
    fig_estado_normas.update_layout(
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        margin=dict(t=60, b=40, l=10, r=10),
        font=dict(family="Arial, sans-serif"),
        hoverlabel=dict(font_size=14, font_family="Arial, sans-serif"),
        height=400
    )
    
    # 3. Top 10 normas faltantes (mejorado)
    try:
        columnas_normas = st.session_state['columnas_normas']
        normas_faltantes = {}
        
        for col in columnas_normas:
            # Usar conversión explícita a string
            count_empty = sum(1 for val in df[col] if str(val).strip() == '')
            count_na = sum(1 for val in df[col] if str(val).lower().strip() == 'no aplica')
            count_applicable = len(df) - count_na
            
            if count_applicable > 0:
                porcentaje_faltante = (count_empty / count_applicable) * 100
                normas_faltantes[col] = {
                    'cantidad': count_empty, 
                    'porcentaje': porcentaje_faltante,
                    'aplicables': count_applicable
                }
        
        # Ordenar por cantidad faltante
        normas_faltantes_sorted = sorted(normas_faltantes.items(), key=lambda x: x[1]['cantidad'], reverse=True)
        top_10_faltantes = normas_faltantes_sorted[:10]
        
        data_top_faltantes = pd.DataFrame([
            {'Norma': k, 'Cantidad': v['cantidad'], 'Porcentaje': v['porcentaje']} 
            for k, v in top_10_faltantes
        ])
        
        fig_top_faltantes = px.bar(
            data_top_faltantes, 
            x='Norma', 
            y='Cantidad',
            text='Cantidad',
            color='Porcentaje',
            color_continuous_scale='Reds',
            title='Top 10 Normas Faltantes'
        )
        fig_top_faltantes.update_layout(
            xaxis_tickangle=-45,
            height=500,
            xaxis_title="",
            yaxis_title="Cantidad de Buses",
            coloraxis_colorbar=dict(title="% Faltante"),
            margin=dict(t=60, b=140, l=60, r=40),
            hoverlabel=dict(font_size=14, font_family="Arial, sans-serif")
        )
        fig_top_faltantes.update_traces(texttemplate='%{text}', textposition='outside')
    except Exception as e:
        st.error(f"Error al generar gráfico de normas faltantes: {str(e)}")
        fig_top_faltantes = go.Figure()
    
    # 4. Distribución de avance por terminal (mejorado)
    try:
        avance_por_terminal = df.groupby('Terminal')['porcentaje_avance'].agg(['mean', 'count']).reset_index()
        avance_por_terminal.columns = ['Terminal', 'Promedio', 'Buses']
        avance_por_terminal['Promedio'] = avance_por_terminal['Promedio'].round(2)
        
        # Ordenar por promedio descendente
        avance_por_terminal = avance_por_terminal.sort_values('Promedio', ascending=False)
        
        fig_avance_terminal = px.bar(
            avance_por_terminal,
            x='Terminal',
            y='Promedio',
            text='Promedio',
            color='Promedio',
            color_continuous_scale='blues',
            title='Porcentaje de Avance por Terminal',
            hover_data=['Buses']
        )
        fig_avance_terminal.update_layout(
            height=500,
            xaxis_title="",
            yaxis_title="Avance Promedio (%)",
            yaxis_range=[0, 100],
            coloraxis_colorbar=dict(title="% Avance"),
            margin=dict(t=60, b=40, l=60, r=40),
            hoverlabel=dict(font_size=14, font_family="Arial, sans-serif")
        )
        fig_avance_terminal.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
    except Exception as e:
        st.error(f"Error al generar gráfico de avance por terminal: {str(e)}")
        fig_avance_terminal = go.Figure()
    
    # 5. Histograma de porcentajes de avance (mejorado)
    try:
        fig_histograma = px.histogram(
            df, 
            x='porcentaje_avance',
            nbins=20,
            color_discrete_sequence=['#3B82F6'],
            title='Distribución de Buses por Porcentaje de Avance',
            labels={'porcentaje_avance': 'Porcentaje de Avance (%)'}
        )
        fig_histograma.update_layout(
            height=400,
            xaxis_title="Porcentaje de Avance (%)",
            yaxis_title="Número de Buses",
            margin=dict(t=60, b=40, l=60, r=40),
            hoverlabel=dict(font_size=14, font_family="Arial, sans-serif")
        )
    except Exception as e:
        st.error(f"Error al generar histograma: {str(e)}")
        fig_histograma = go.Figure()
    
    # 6. Mapa de calor por modelo y terminal (nuevo)
    try:
        # Si hay muchos modelos, tomamos los top 10 con más buses
        modelos_count = df['Modelo chasis'].value_counts().nlargest(10).index.tolist()
        df_heatmap = df[df['Modelo chasis'].isin(modelos_count)].copy()
        
        # Crear pivot table
        heatmap_data = df_heatmap.pivot_table(
            index='Terminal', 
            columns='Modelo chasis', 
            values='porcentaje_avance', 
            aggfunc='mean'
        ).round(2)
        
        # Rellenar NaN con 0
        heatmap_data = heatmap_data.fillna(0)
        
        # Crear heatmap
        fig_heatmap = px.imshow(
            heatmap_data,
            text_auto='.1f',
            color_continuous_scale='blues',
            title='Mapa de Calor: Avance por Terminal y Modelo',
            labels=dict(x="Modelo", y="Terminal", color="% Avance")
        )
        fig_heatmap.update_layout(
            height=400,
            margin=dict(t=60, b=40, l=100, r=40),
            coloraxis_colorbar=dict(title="% Avance"),
            hoverlabel=dict(font_size=14, font_family="Arial, sans-serif")
        )
    except Exception as e:
        st.error(f"Error al generar mapa de calor: {str(e)}")
        fig_heatmap = go.Figure()
    
    # 7. Gráfico de avance semanal o mensual (simulado)
    try:
        # Crear datos de ejemplo (en producción, esto vendría de datos históricos)
        ultimas_semanas = ['Sem 1', 'Sem 2', 'Sem 3', 'Sem 4', 'Actual']
        avance_semanal = [
            porcentaje_flota_completa * 0.75,
            porcentaje_flota_completa * 0.80,
            porcentaje_flota_completa * 0.85,
            porcentaje_flota_completa * 0.92,
            porcentaje_flota_completa
        ]
        
        tendencia_data = pd.DataFrame({
            'Semana': ultimas_semanas,
            'Avance': avance_semanal
        })
        
        fig_tendencia = px.line(
            tendencia_data,
            x='Semana',
            y='Avance',
            markers=True,
            title='Tendencia de Avance (Últimas 5 semanas)',
            color_discrete_sequence=['#10B981']
        )
        fig_tendencia.update_traces(line=dict(width=4), marker=dict(size=10))
        fig_tendencia.update_layout(
            height=400,
            xaxis_title="",
            yaxis_title="Avance Total (%)",
            yaxis_range=[0, 100],
            margin=dict(t=60, b=40, l=60, r=40),
            hoverlabel=dict(font_size=14, font_family="Arial, sans-serif")
        )
    except Exception as e:
        st.error(f"Error al generar gráfico de tendencia: {str(e)}")
        fig_tendencia = go.Figure()
    
    # 8. Comparación entre terminales (nuevo)
    try:
        # Agrupar y calcular métricas por terminal
        terminal_metrics = df.groupby('Terminal').agg(
            total_buses=('N° Interno', 'count'),
            promedio_avance=('porcentaje_avance', 'mean'),
            buses_completos=('normas_faltantes', lambda x: sum(x == 0)),
            buses_criticos=('porcentaje_avance', lambda x: sum(x < 50))
        ).reset_index()
        
        terminal_metrics['porcentaje_completos'] = (terminal_metrics['buses_completos'] / terminal_metrics['total_buses'] * 100).round(2)
        terminal_metrics['promedio_avance'] = terminal_metrics['promedio_avance'].round(2)
        
        # Ordenar por promedio_avance descendente
        terminal_metrics = terminal_metrics.sort_values('promedio_avance', ascending=False)
        
        # Crear gráfico de barras múltiples
        fig_terminales = px.bar(
            terminal_metrics,
            x='Terminal',
            y=['promedio_avance', 'porcentaje_completos'],
            barmode='group',
            title='Comparación entre Terminales',
            labels={
                'value': 'Porcentaje (%)',
                'variable': 'Métrica'
            },
            color_discrete_map={
                'promedio_avance': '#3B82F6',
                'porcentaje_completos': '#10B981'
            }
        )
        fig_terminales.update_layout(
            height=500,
            xaxis_title="",
            yaxis_title="Porcentaje (%)",
            yaxis_range=[0, 100],
            margin=dict(t=60, b=40, l=60, r=40),
            legend=dict(
                title="Métrica",
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="center",
                x=0.5
            ),
            hoverlabel=dict(font_size=14, font_family="Arial, sans-serif")
        )
        
        # Cambiar nombres en la leyenda para mejor comprensión
        newnames = {'promedio_avance': 'Avance Promedio (%)', 'porcentaje_completos': 'Buses Completos (%)'}
        fig_terminales.for_each_trace(lambda t: t.update(name = newnames[t.name]))
    except Exception as e:
        st.error(f"Error al generar comparación entre terminales: {str(e)}")
        fig_terminales = go.Figure()
    
    return {
        'fig_estado_normas': fig_estado_normas,
        'fig_top_faltantes': fig_top_faltantes,
        'fig_avance_terminal': fig_avance_terminal,
        'fig_histograma': fig_histograma,
        'fig_heatmap': fig_heatmap,
        'fig_tendencia': fig_tendencia,
        'fig_terminales': fig_terminales,
        'total_buses': total_buses,
        'buses_completos': buses_completos,
        'porcentaje_flota_completa': porcentaje_flota_completa,
        'promedio_avance': df['porcentaje_avance'].mean(),
        'estado_normas': data_estado_normas
    }

# Función para mostrar badge de estado con mejor diseño
def get_estado_badge(valor):
    valor = str(valor).strip().lower()
    if valor == '1':
        return "✅ INSTALADA"
    elif valor == 'no aplica':
        return "⚠️ NO APLICA"
    else:
        return "❌ PENDIENTE"

# Función para generar informe PDF (simulado)
def generate_pdf_report(bus_data):
    # Esta función simularía la generación de un PDF
    # En una implementación real, usaría ReportLab o otra biblioteca para crear PDFs
    return "PDF Report Content"

# Sidebar con logo y filtros
with st.sidebar:
    st.image("https://via.placeholder.com/150x60?text=LOGO", width=150)
    st.markdown("### Control de Normas Gráficas")
    
    # Área para cargar el archivo
    st.markdown("#### Cargar Archivo")
    uploaded_file = st.file_uploader("Seleccione el archivo Excel", type=["xlsx"])
    
    # Si hay un archivo cargado, mostrar información
    if uploaded_file is not None:
        file_details = {
            "Nombre": uploaded_file.name,
            "Tamaño": f"{uploaded_file.size / 1024:.2f} KB",
            "Tipo": uploaded_file.type
        }
        
        st.markdown("#### Detalles del Archivo")
        for key, value in file_details.items():
            st.write(f"**{key}:** {value}")
        
        st.markdown("---")

# Contenido principal
if uploaded_file is not None:
    # Procesar archivo
    with st.spinner('Procesando el archivo...'):
        df = procesar_archivo(uploaded_file)
    
    if not df.empty:
        # Guardar df en session_state para usarlo en otras partes
        st.session_state['df'] = df
        
        # Área de filtros
        st.markdown('<div class="sub-header">Filtros de Búsqueda</div>', unsafe_allow_html=True)
        
        with st.expander("Mostrar/Ocultar Filtros", expanded=True):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                # Filtro por Terminal
                terminales = ["Todos"] + sorted(df['Terminal'].unique().tolist())
                terminal_seleccionada = st.selectbox("Terminal:", terminales)
            
            with col2:
                # Filtro por Subclase si existe la columna
                if 'Subclase' in df.columns:
                    subclases = ["Todos"] + sorted(df['Subclase'].unique().tolist())
                    subclase_seleccionada = st.selectbox("Subclase:", subclases)
                else:
                    subclase_seleccionada = "Todos"
                    
            with col3:
                # Filtro por rango de avance
                rango_avance = st.slider(
                    "Rango de avance (%)",
                    min_value=0,
                    max_value=100,
                    value=(0, 100)
                )
        
        # Aplicar filtros
        df_filtrado = df.copy()
        
        if terminal_seleccionada != "Todos":
            df_filtrado = df_filtrado[df_filtrado['Terminal'] == terminal_seleccionada]
            
        if 'Subclase' in df.columns and subclase_seleccionada != "Todos":
            df_filtrado = df_filtrado[df_filtrado['Subclase'] == subclase_seleccionada]
            
        df_filtrado = df_filtrado[
            (df_filtrado['porcentaje_avance'] >= rango_avance[0]) & 
            (df_filtrado['porcentaje_avance'] <= rango_avance[1])
        ]
        
        # Mostrar mensaje si no hay datos después de filtrar
        if df_filtrado.empty:
            st.markdown('<div class="warning-box">No hay datos que coincidan con los filtros aplicados. Por favor, ajuste los criterios de filtrado.</div>', unsafe_allow_html=True)
            st.stop()
            
        # Generar gráficos con datos filtrados
        with st.spinner('Generando visualizaciones...'):
            graficos = generar_graficos(df_filtrado)
        
        # Dashboard de KPIs
        st.markdown('<div class="sub-header">Métricas Clave</div>', unsafe_allow_html=True)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{graficos['total_buses']}</div>
                <div class="metric-label">Total Buses</div>
            </div>
            """, unsafe_allow_html=True)
            
        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{graficos['buses_completos']}</div>
                <div class="metric-label">Buses Completos</div>
            </div>
            """, unsafe_allow_html=True)
            
        with col3:
            color = "#10B981" if graficos['porcentaje_flota_completa'] >= 75 else "#F59E0B" if graficos['porcentaje_flota_completa'] >= 50 else "#EF4444"
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value" style="color: {color};">{graficos['porcentaje_flota_completa']:.1f}%</div>
                <div class="metric-label">Avance Total Flota</div>
            </div>
            """, unsafe_allow_html=True)
            
        with col4:
            color = "#10B981" if graficos['promedio_avance'] >= 75 else "#F59E0B" if graficos['promedio_avance'] >= 50 else "#EF4444"
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value" style="color: {color};">{graficos['promedio_avance']:.1f}%</div>
                <div class="metric-label">Promedio Avance por Bus</div>
            </div>
            """, unsafe_allow_html=True)
        
        # Dashboard principal con tabs
        st.markdown('<div class="sub-header">Dashboard Interactivo</div>', unsafe_allow_html=True)
        
        tabs = st.tabs(["Resumen General", "Análisis por Terminal", "Análisis por Norma", "Tendencias"])
        
        # Tab 1: Resumen General
        with tabs[0]:
            col1, col2 = st.columns(2)
            
            with col1:
                st.plotly_chart(graficos['fig_estado_normas'], use_container_width=True)
                
            with col2:
                st.plotly_chart(graficos['fig_histograma'], use_container_width=True)
                
            col1, col2 = st.columns(2)
            
            with col1:
                st.plotly_chart(graficos['fig_tendencia'], use_container_width=True)
                
            with col2:
                # Tabla de resumen
                st.markdown("### Resumen por Estado")
                estado_df = graficos['estado_normas']
                estado_df['Porcentaje'] = estado_df['Porcentaje'].round(2).astype(str) + '%'
                st.dataframe(
                    estado_df,
                    column_config={
                        "Estado": st.column_config.TextColumn("Estado"),
                        "Cantidad": st.column_config.NumberColumn("Cantidad"),
                        "Porcentaje": st.column_config.TextColumn("Porcentaje")
                    },
                    hide_index=True,
                    use_container_width=True
                )
        
        # Tab 2: Análisis por Terminal
        with tabs[1]:
            col1, col2 = st.columns(2)
            
            with col1:
                st.plotly_chart(graficos['fig_avance_terminal'], use_container_width=True)
                
            with col2:
                st.plotly_chart(graficos['fig_terminales'], use_container_width=True)
                
            st.plotly_chart(graficos['fig_heatmap'], use_container_width=True)
        
        # Tab 3: Análisis por Norma
        with tabs[2]:
            st.plotly_chart(graficos['fig_top_faltantes'], use_container_width=True)
            
            # Análisis de cada norma
            st.markdown("### Detalle por Norma")
            
            try:
                columnas_normas = st.session_state['columnas_normas']
                
                # Crear dataframe para mostrar estado de cada norma
                normas_analysis = []
                for norma in columnas_normas:
                    instaladas = sum(1 for val in df_filtrado[norma] if str(val).strip() == '1')
                    no_aplica = sum(1 for val in df_filtrado[norma] if str(val).lower().strip() == 'no aplica')
                    pendientes = sum(1 for val in df_filtrado[norma] if str(val).strip() == '')
                    total_aplicables = len(df_filtrado) - no_aplica
                    porcentaje = (instaladas / total_aplicables * 100) if total_aplicables > 0 else 0
                    
                    normas_analysis.append({
                        "Norma": norma,
                        "Instaladas": instaladas,
                        "Pendientes": pendientes,
                        "No Aplica": no_aplica,
                        "% Avance": round(porcentaje, 2)
                    })
                
                # Ordenar por porcentaje de avance
                normas_df = pd.DataFrame(normas_analysis).sort_values("% Avance")
                
                # Mostrar tabla con formato condicional
                st.dataframe(
                    normas_df,
                    column_config={
                        "Norma": st.column_config.TextColumn("Norma"),
                        "Instaladas": st.column_config.NumberColumn("Instaladas"),
                        "Pendientes": st.column_config.NumberColumn("Pendientes", help="Buses con norma pendiente"),
                        "No Aplica": st.column_config.NumberColumn("No Aplica"),
                        "% Avance": st.column_config.ProgressColumn(
                            "% Avance",
                            format="%f",
                            min_value=0,
                            max_value=100
                        )
                    },
                    hide_index=True,
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"Error al generar análisis por norma: {str(e)}")
        
        # Tab 4: Tendencias
        with tabs[3]:
            st.markdown("### Evolución de Instalación de Normas")
            st.info("En una versión de producción, esta sección mostraría tendencias históricas basadas en datos de seguimiento previos.")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.plotly_chart(graficos['fig_tendencia'], use_container_width=True)
            
            with col2:
                # Proyección simulada
                st.markdown("### Proyección de Finalización")
                
                # Cálculo simulado de días estimados para completar
                total_faltantes = df_filtrado['normas_faltantes'].sum()
                promedio_diario = total_faltantes * 0.02  # Simulando un 2% de avance diario
                dias_estimados = int(total_faltantes / promedio_diario) if promedio_diario > 0 else 0
                
                fecha_actual = datetime.now()
                fecha_estimada = fecha_actual.replace(day=fecha_actual.day + dias_estimados)
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Normas pendientes", f"{total_faltantes}")
                with col2:
                    st.metric("Días estimados para completar", f"{dias_estimados}")
                
                st.markdown(f"**Fecha estimada de finalización:** {fecha_estimada.strftime('%d/%m/%Y')}")
                
                # Gráfico de proyección simulada
                fechas = pd.date_range(start=fecha_actual, end=fecha_estimada, periods=10)
                valores = np.linspace(graficos['porcentaje_flota_completa'], 100, 10)
                
                proyeccion_df = pd.DataFrame({
                    'Fecha': fechas,
                    'Avance Proyectado': valores
                })
                
                fig_proyeccion = px.line(
                    proyeccion_df,
                    x='Fecha',
                    y='Avance Proyectado',
                    markers=True,
                    title='Proyección de Avance',
                    color_discrete_sequence=['#3B82F6']
                )
                fig_proyeccion.update_traces(line=dict(width=4), marker=dict(size=10))
                fig_proyeccion.update_layout(
                    height=400,
                    xaxis_title="",
                    yaxis_title="Avance Proyectado (%)",
                    yaxis_range=[0, 100],
                    margin=dict(t=60, b=40, l=60, r=40)
                )
                
                st.plotly_chart(fig_proyeccion, use_container_width=True)
        
        # Tabla de buses filtrable
        st.markdown('<div class="sub-header">Listado de Buses</div>', unsafe_allow_html=True)
        
        # Columnas para mostrar en la tabla principal
        columnas_tabla = [
            'N° Interno', 'PPU', 'Terminal', 'normas_instaladas', 'normas_faltantes', 'porcentaje_avance'
        ]
        
        # Agregar columnas adicionales si existen
        optional_cols = ['Marca chasis', 'Modelo chasis', 'Unidad', 'Subclase']
        for col in optional_cols:
            if col in df_filtrado.columns:
                columnas_tabla.insert(3, col)
        
        # Renombrar columnas para mejor visualización
        df_tabla = df_filtrado[columnas_tabla].copy()
        column_mapping = {
            'N° Interno': 'N° Interno', 
            'PPU': 'PPU', 
            'Terminal': 'Terminal',
            'Marca chasis': 'Marca',
            'Modelo chasis': 'Modelo',
            'Unidad': 'Unidad',
            'Subclase': 'Subclase',
            'normas_instaladas': 'Instaladas', 
            'normas_faltantes': 'Faltantes', 
            'porcentaje_avance': 'Avance (%)'
        }
        df_tabla = df_tabla.rename(columns={k: v for k, v in column_mapping.items() if k in df_tabla.columns})
        
        # Añadir columna de estado
        df_tabla['Estado'] = df_tabla['Faltantes'].apply(
            lambda x: "Completo" if x == 0 else (
                "Crítico" if x > df_filtrado['normas_faltantes'].mean() else "En Proceso"
            )
        )
        
        # Configuración de la tabla interactiva
        tabla_config = {
            "N° Interno": st.column_config.TextColumn("N° Interno"),
            "PPU": st.column_config.TextColumn("PPU"),
            "Avance (%)": st.column_config.ProgressColumn(
                "Avance (%)",
                format="%f",
                min_value=0,
                max_value=100
            ),
            "Estado": st.column_config.TextColumn("Estado")
        }
        
        # Creación de tabla interactiva con formato condicional
        st.dataframe(
            df_tabla,
            column_config=tabla_config,
            hide_index=True,
            use_container_width=True
        )
        
        # Número de buses que coinciden con el filtro
        st.markdown(f"**{len(df_filtrado)} buses** coinciden con los criterios de filtrado")
        
        # Botones de exportación
        col1, col2 = st.columns(2)
        
        with col1:
            # Botón para descargar datos filtrados
            csv = df_filtrado.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Descargar Datos Filtrados (CSV)",
                data=csv,
                file_name=f"normas_graficas_filtrado_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv"
            )
        
        with col2:
            # Botón para generar informe
            st.download_button(
                label="Generar Informe Completo (PDF)",
                data=b"Reporte simulado",  # Aquí iría la generación real del PDF
                file_name=f"informe_normas_graficas_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                mime="application/pdf"
            )
        
        # Detalle de bus
        st.markdown('<div class="sub-header">Detalle por Bus</div>', unsafe_allow_html=True)
        
        # Dropdown para seleccionar un bus específico
        col1, col2 = st.columns([3, 1])
        
        with col1:
            bus_interno_options = df_filtrado['N° Interno'].astype(str).tolist()
            selected_bus_interno = st.selectbox("Seleccione un bus para ver detalles:", bus_interno_options)
        
        with col2:
            # Añadir botón de búsqueda avanzada que no hace nada pero mejora la apariencia
            if st.button("Búsqueda Avanzada", key="advanced_search"):
                st.session_state['show_advanced'] = True
        
        if selected_bus_interno:
            # Obtener datos del bus seleccionado
            bus_data = df_filtrado[df_filtrado['N° Interno'].astype(str) == selected_bus_interno].iloc[0]
            
            # Tarjeta con información detallada del bus
            with st.container():
                # Usar markdown para un diseño más profesional
                st.markdown(f"""
                <div style="background-color: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">
                    <h3 style="margin-top: 0; color: #1E3A8A;">Bus N° {bus_data['N° Interno']}</h3>
                    <p><strong>PPU:</strong> {bus_data['PPU']} | <strong>Terminal:</strong> {bus_data['Terminal']}</p>
                    <p><strong>Modelo:</strong> {bus_data['Marca chasis']} {bus_data['Modelo chasis']} | <strong>Subclase:</strong> {bus_data.get('Subclase', 'No especificado')}</p>
                </div>
                """, unsafe_allow_html=True)
                
                # Mostrar estado de avance
                st.markdown(f"""
                <div style="background-color: #F8F9FA; padding: 20px; border-radius: 10px; margin-top: 20px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <h4 style="margin: 0; color: #1E3A8A;">Estado de Avance</h4>
                            <p style="margin: 5px 0 0 0;">Instalación de Normas Gráficas</p>
                        </div>
                        <div style="text-align: right;">
                            <h2 style="margin: 0; color: {'#10B981' if bus_data['porcentaje_avance'] >= 75 else '#F59E0B' if bus_data['porcentaje_avance'] >= 50 else '#EF4444'};">{bus_data['porcentaje_avance']}%</h2>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Resumen de normas en formato de tarjetas
                st.markdown("""
                <h4 style="margin-top: 20px; margin-bottom: 10px; color: #1E3A8A;">Resumen de Normas</h4>
                """, unsafe_allow_html=True)
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.markdown(f"""
                    <div style="background-color: #D1FAE5; padding: 15px; border-radius: 10px; text-align: center;">
                        <h2 style="margin: 0; color: #065F46;">{bus_data['normas_instaladas']}</h2>
                        <p style="margin: 5px 0 0 0; color: #065F46;">Normas Instaladas</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    st.markdown(f"""
                    <div style="background-color: #FEE2E2; padding: 15px; border-radius: 10px; text-align: center;">
                        <h2 style="margin: 0; color: #991B1B;">{bus_data['normas_faltantes']}</h2>
                        <p style="margin: 5px 0 0 0; color: #991B1B;">Normas Faltantes</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col3:
                    st.markdown(f"""
                    <div style="background-color: #F3F4F6; padding: 15px; border-radius: 10px; text-align: center;">
                        <h2 style="margin: 0; color: #4B5563;">{bus_data['normas_no_aplica']}</h2>
                        <p style="margin: 5px 0 0 0; color: #4B5563;">No Aplicables</p>
                    </div>
                    """, unsafe_allow_html=True)
            
            # Detalle de normas
            st.markdown("""
            <h4 style="margin-top: 30px; margin-bottom: 10px; color: #1E3A8A;">Detalle de Normas Gráficas</h4>
            """, unsafe_allow_html=True)
            
            # Obtener columnas de normas
            try:
                columnas_normas = st.session_state['columnas_normas']
                
                # Crear dataframe para mostrar estado de normas
                normas_status = []
                for norma in columnas_normas:
                    normas_status.append({
                        "Norma": norma,
                        "Estado": get_estado_badge(bus_data[norma])
                    })
                
                df_normas = pd.DataFrame(normas_status)
                
                # Crear tabs para ver las normas por estado
                estado_tabs = st.tabs(["Todas", "Pendientes", "Instaladas", "No Aplicables"])
                
                with estado_tabs[0]:
                    # Mostrar todas las normas en una tabla con mejor formato
                    st.dataframe(
                        df_normas,
                        column_config={
                            "Norma": st.column_config.TextColumn("Norma"),
                            "Estado": st.column_config.TextColumn("Estado"),
                        },
                        hide_index=True,
                        use_container_width=True
                    )
                
                with estado_tabs[1]:
                    # Mostrar solo normas pendientes
                    pendientes_df = df_normas[df_normas['Estado'] == "❌ PENDIENTE"]
                    if not pendientes_df.empty:
                        st.dataframe(
                            pendientes_df,
                            hide_index=True,
                            use_container_width=True
                        )
                    else:
                        st.success("¡Todas las normas aplicables están instaladas!")
                
                with estado_tabs[2]:
                    # Mostrar solo normas instaladas
                    instaladas_df = df_normas[df_normas['Estado'] == "✅ INSTALADA"]
                    if not instaladas_df.empty:
                        st.dataframe(
                            instaladas_df,
                            hide_index=True,
                            use_container_width=True
                        )
                    else:
                        st.error("No hay normas instaladas en este bus.")
                
                with estado_tabs[3]:
                    # Mostrar solo normas no aplicables
                    no_aplica_df = df_normas[df_normas['Estado'] == "⚠️ NO APLICA"]
                    if not no_aplica_df.empty:
                        st.dataframe(
                            no_aplica_df,
                            hide_index=True,
                            use_container_width=True
                        )
                    else:
                        st.warning("Todas las normas son aplicables a este bus.")
            except Exception as e:
                st.error(f"Error al mostrar detalle de normas: {str(e)}")
            
            # Botones de acción
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("Generar Informe Detallado para este Bus", key="detail_report"):
                    # Simulando la generación del informe
                    st.success("Informe generado con éxito. Haga clic en 'Descargar Informe' para obtenerlo.")
                    st.session_state['report_generated'] = True
            
            with col2:
                if st.session_state.get('report_generated', False):
                    st.download_button(
                        label="Descargar Informe",
                        data="Informe detallado para el bus",  # Aquí iría el contenido real del informe
                        file_name=f"informe_bus_{bus_data['N° Interno']}.pdf",
                        mime="application/pdf"
                    )
                else:
                    st.button("Marcar como Revisado", disabled=False, key="mark_reviewed")
    else:
        # Mostrar mensaje de error si no se pudieron procesar los datos
        st.markdown('<div class="error-box"><strong>Error:</strong> No se pudo procesar el archivo. Verifique que tiene el formato correcto y contiene las columnas necesarias.</div>', unsafe_allow_html=True)
        
        # Mostrar ejemplo del formato esperado
        st.markdown('<div class="sub-header">Formato de Archivo Esperado</div>', unsafe_allow_html=True)
        
        st.markdown("""
        El archivo Excel debe tener la siguiente estructura:
        
        1. **Primera fila**: Título general (se omite en la importación)
        2. **Segunda fila**: Encabezados de columnas
        3. **Columnas requeridas**:
            - N° Interno: Identificador único del bus
            - PPU: Patente del vehículo
            - Terminal: Terminal al que pertenece el bus
            - Columnas para cada norma gráfica
        
        **Valores esperados para normas**:
        - "1": Norma instalada
        - "no aplica": Norma no aplicable al modelo
        - "" (vacío): Norma pendiente de instalación
        """)
        
        ejemplo_data = {
            'N° Interno': [123, 124, 125],
            'PPU': ['ABCD12', 'EFGH34', 'IJKL56'],
            'Terminal': ['Terminal A', 'Terminal B', 'Terminal A'],
            'CALL CENTER': ['1', '', 'no aplica'],
            'NUMERO INTERNO': ['1', '1', ''],
            'SEÑAL SUBIDA Y BAJADA': ['1', '', '1']
        }
        
        ejemplo_df = pd.DataFrame(ejemplo_data)
        st.dataframe(ejemplo_df)
else:
    # Página de inicio cuando no hay archivo cargado
    st.markdown('<div class="info-box">Por favor, cargue un archivo Excel para comenzar el análisis.</div>', unsafe_allow_html=True)
    
    # Mostrar información sobre la aplicación
    st.markdown('<div class="sub-header">Sistema Avanzado de Análisis de Normas Gráficas</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("""
        ### Características principales:
        
        - ✅ Análisis detallado del estado de instalación de normas gráficas en buses
        - ✅ Dashboard interactivo con múltiples visualizaciones
        - ✅ Filtros avanzados por terminal, subclase y porcentaje de avance
        - ✅ Informes detallados por bus y resúmenes generales
        - ✅ Proyección de avance y fechas estimadas de finalización
        - ✅ Exportación de datos e informes en diferentes formatos
        
        ### Cómo comenzar:
        
        1. Suba un archivo Excel con los datos de normas gráficas usando el panel lateral
        2. Aplique filtros para analizar segmentos específicos de su flota
        3. Explore el dashboard interactivo para obtener insights
        4. Genere informes detallados para compartir con su equipo
        """)
    
    with col2:
        # Imagen ilustrativa
        st.image("https://via.placeholder.com/400x300?text=Dashboard+Preview")
        
    # Mostrar instrucciones adicionales
    st.markdown('<div class="sub-header">Formato del Archivo Excel</div>', unsafe_allow_html=True)
    
    st.markdown("""
    El sistema está diseñado para procesar archivos Excel con la siguiente estructura:
    
    - **Primera fila**: Título general
    - **Segunda fila**: Nombres de las columnas
    - **Columnas obligatorias**:
      - N° Interno (identificador único del bus)
      - PPU (patente)
      - Terminal (ubicación)
      - Columnas para cada tipo de norma gráfica
      
    Para cada norma gráfica, use los siguientes valores:
    - "1" para indicar que la norma está instalada
    - "no aplica" cuando la norma no aplica al modelo específico
    - Dejar la celda vacía cuando la norma está pendiente de instalación
    """)
    
    # Ejemplo visual
    st.markdown('<div class="sub-header">Ejemplo de Estructura de Datos</div>', unsafe_allow_html=True)
    
    ejemplo_data = {
        'N° Interno': [123, 124, 125],
        'PPU': ['ABCD12', 'EFGH34', 'IJKL56'],
        'Terminal': ['Terminal A', 'Terminal B', 'Terminal A'],
        'CALL CENTER': ['1', '', 'no aplica'],
        'NUMERO INTERNO': ['1', '1', ''],
        'SEÑAL SUBIDA Y BAJADA': ['1', '', '1']
    }
    
    ejemplo_df = pd.DataFrame(ejemplo_data)
    st.dataframe(ejemplo_df)

# Pie de página
st.markdown("""
<div style="background-color: #F3F4F6; padding: 20px; border-radius: 10px; margin-top: 30px; text-align: center; font-size: 0.8rem; color: #6B7280;">
    <p>© 2025 Sistema Avanzado de Análisis de Normas Gráficas • Todos los derechos reservados</p>
    <p>Última actualización: 18/03/2025</p>
</div>
""", unsafe_allow_html=True)

