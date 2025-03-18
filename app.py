import streamlit as st
import pandas as pd
import numpy as np
import io
from datetime import datetime
import base64
from io import BytesIO

# Importar bibliotecas opcionales con manejo de errores
try:
    import plotly.express as px
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    st.warning("La biblioteca Plotly no está instalada. Algunas visualizaciones no estarán disponibles. Instálala con: pip install plotly")

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import matplotlib.pyplot as plt
    import seaborn as sns
    MPL_AVAILABLE = True
except ImportError:
    MPL_AVAILABLE = False

# Configuración de la página
st.set_page_config(
    page_title="Control de Normas Gráficas",
    page_icon="🚌",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos CSS personalizados
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1E3A8A;
        text-align: center;
        margin-bottom: 1rem;
        padding-bottom: 1rem;
        border-bottom: 2px solid #1E3A8A;
    }
    .sub-header {
        font-size: 1.8rem;
        color: #1E3A8A;
        margin-top: 1rem;
        margin-bottom: 1rem;
    }
    .card {
        background-color: #F8F9FA;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin-bottom: 20px;
    }
    .metric-card {
        background-color: #E8F0FE;
        border-radius: 10px;
        padding: 15px;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    }
    .metric-value {
        font-size: 2.2rem;
        font-weight: bold;
        color: #0047AB;
    }
    .metric-label {
        font-size: 1rem;
        color: #555;
    }
    .highlight {
        background-color: #FFF9C4;
        padding: 2px 5px;
        border-radius: 3px;
    }
    .warning {
        color: #FFA500;
        font-weight: bold;
    }
    .success {
        color: #28A745;
        font-weight: bold;
    }
    .danger {
        color: #DC3545;
        font-weight: bold;
    }
    .info-box {
        background-color: #E7F5FE;
        border-left: 5px solid #0096FF;
        padding: 10px;
        margin: 10px 0;
    }
    .report-header {
        text-align: center;
        font-size: 24px;
        margin-bottom: 20px;
        color: #1E3A8A;
    }
    .report-section {
        margin-bottom: 15px;
    }
    .report-title {
        font-weight: bold;
        margin-bottom: 5px;
    }
    .footer {
        text-align: center;
        margin-top: 30px;
        padding-top: 10px;
        border-top: 1px solid #ddd;
        font-size: 0.8rem;
        color: #666;
    }
    .bus-selector {
        background-color: #F0F8FF;
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

# Función para cargar los datos
@st.cache_data
def load_data(file):
    try:
        # Intentar cargar con diferentes configuraciones de encabezado
        # El usuario mencionó que los encabezados están en A1 y los datos comienzan en A2
        df = pd.read_excel(file, header=0)  # Intenta con encabezado en fila 0 (A1)
        
        # Verificar que existan las columnas mínimas necesarias
        # Si no existen, intentamos con otras configuraciones
        if 'N° Interno' not in df.columns and 'PPU' not in df.columns:
            st.warning("No se encontraron columnas esperadas. Intentando con otras configuraciones...")
            # Intentar con diferentes configuraciones
            df = pd.read_excel(file, header=1)  # Intenta con encabezado en fila 1 (A2)
        
        return df
    except Exception as e:
        st.error(f"Error al cargar el archivo: {e}")
        return None

# Función para procesar los datos
def process_data(df):
    # Verificar y ajustar las columnas del DataFrame
    required_cols = ['N° Interno', 'PPU']
    
    # Verificar si las columnas requeridas están presentes
    for col in required_cols:
        if col not in df.columns:
            # Intentar encontrar columnas con nombres similares
            if col == 'N° Interno':
                similar_cols = [c for c in df.columns if 'intern' in c.lower() or 'numer' in c.lower()]
            elif col == 'PPU':
                similar_cols = [c for c in df.columns if 'ppu' in c.lower() or 'paten' in c.lower() or 'placa' in c.lower()]
            else:
                similar_cols = [c for c in df.columns if col.lower() in c.lower()]
                
            if similar_cols:
                # Renombrar la primera columna similar encontrada
                df = df.rename(columns={similar_cols[0]: col})
                st.info(f"Columna '{similar_cols[0]}' renombrada a '{col}'")
            else:
                # Si no se encuentra, crear una columna con valores predeterminados
                df[col] = [f"{col}_{i}" for i in range(len(df))]
                st.warning(f"Columna '{col}' no encontrada. Se ha creado con valores predeterminados.")
    
    # Lista de columnas de información básica que NO son normas
    info_cols = [
        'N° Interno', 'PPU', 'Unidad', 'Marca chasis', 'Modelo chasis', 'Subclase', 
        'N° plazas', 'Terminal', 'Taller', 'TERMINADOS', 'NORMA INSTALADA', 'FECHA DE RENOVACION',
        'CALL CENTER'  # Esta también parece ser una columna de información, no una norma
    ]
    
    # Filtrar solo las columnas de información que existen en el DataFrame
    cols_info = [col for col in info_cols if col in df.columns]
    
    # Todas las columnas después de la información básica son normas
    # IMPORTANTE: Excluir explícitamente FECHA DE RENOVACION y NORMA INSTALADA
    norm_cols = [col for col in df.columns if col not in cols_info and 
                'FECHA' not in col.upper() and 'NORMA INSTALADA' not in col.upper()]
    
    # Asegurarse de que hay columnas de normas
    if not norm_cols:
        st.error("No se encontraron columnas de normas. Verificar formato del archivo.")
        return df, cols_info, []
    
    # Para cada norma, determinamos si está instalada, no aplica o falta
    for col in norm_cols:
        # Convertir valores a string para manejar consistentemente
        df[col] = df[col].astype(str)
        # Reemplazar 'nan' por vacío (norma faltante)
        df[col] = df[col].replace('nan', '').replace('None', '')
        
    # Mostrar un resumen de las normas y los valores únicos encontrados
    st.markdown("### Valores encontrados en columnas de normas")
    unique_values = set()
    for col in norm_cols[:5]:  # Mostrar solo para las primeras 5 columnas para no saturar
        values = df[col].unique()
        unique_values.update([v for v in values if v and v.strip()])
    
    st.write(f"Valores únicos encontrados: {', '.join([repr(v) for v in unique_values if v and v.strip()])}")
    st.info("Interpretación: '1' o 'instalada' = Instalado, 'no aplica' = No Aplica, '' (vacío) = Pendiente")
        
    return df, cols_info, norm_cols

# Función para calcular métricas
def calculate_metrics(df, norm_cols):
    try:
        total_buses = len(df)
        metrics = {}
        
        # Si no hay buses, devolver métricas predeterminadas
        if total_buses == 0:
            return {
                'efficiency': 0,
                'total_buses': 0,
                'total_norms': len(norm_cols),
                'completed_installations': 0,
                'pending_installations': 0,
                'complete_buses': 0,
                'incomplete_buses': 0,
                'norm_progress': {},
                'bus_progress': {}
            }
        
        # Eficiencia global de instalación
        total_cells = total_buses * len(norm_cols)
        completed_cells = 0
        not_applicable_cells = 0
        
        # IMPORTANTE: Considerar "no aplica" como una norma completada
        for col in norm_cols:
            # IMPORTANTE: Interpretar valores como instalados
            values = df[col].str.lower()
            # Contar instaladas - valores que indiquen instalación
            is_installed = ((values == '1') | 
                           (values == 'instalada') | 
                           (values == 'instalado') |
                           (values.str.contains('instalad')))
            
            # Contar no aplica - variantes de "no aplica"
            is_not_applicable = values.str.contains('no aplica')
            
            # Sumar ambos como "completados" (instalado O no aplica)
            completed_cells += (is_installed | is_not_applicable).sum()
            not_applicable_cells += is_not_applicable.sum()
        
        # Calcular la eficiencia como (instaladas + no aplica) / total
        efficiency = (completed_cells / total_cells * 100) if total_cells > 0 else 0
        
        metrics['efficiency'] = round(efficiency, 2)
        metrics['total_buses'] = total_buses
        metrics['total_norms'] = len(norm_cols)
        metrics['completed_installations'] = int(completed_cells)
        metrics['pending_installations'] = int(total_cells - completed_cells)
        
        # Buses con instalación completa
        buses_complete = []
        buses_incomplete = []
        bus_completion_status = {}
        
        for idx, row in df.iterrows():
            # Determinar el ID del bus
            if 'N° Interno' in row and not pd.isna(row['N° Interno']):
                bus_id = str(row['N° Interno'])
            elif 'Numero Interno' in row and not pd.isna(row['Numero Interno']):
                bus_id = str(row['Numero Interno'])
            else:
                # Buscar otra columna con "INTERNO" en el nombre
                interno_cols = [col for col in row.index if 'INTERNO' in col.upper()]
                if interno_cols:
                    bus_id = str(row[interno_cols[0]])
                else:
                    # Usar PPU como fallback
                    if 'PPU' in row and not pd.isna(row['PPU']):
                        bus_id = f"PPU_{str(row['PPU'])}"
                    else:
                        # Último recurso: usar el índice
                        bus_id = f"Bus_{idx}"
            
            # Verificar si el bus está completo
            all_complete = True
            missing_norms = []
            
            for col in norm_cols:
                val = str(row[col]).lower().strip()
                # Verificar si la norma está instalada o no aplica
                is_installed = (val == '1' or 
                              val == 'instalada' or 
                              val == 'instalado' or
                              'instalad' in val)
                is_not_applicable = 'no aplica' in val
                
                # Si no está instalada Y no es "no aplica", está faltante
                if not (is_installed or is_not_applicable):
                    all_complete = False
                    missing_norms.append(col)
            
            if all_complete:
                buses_complete.append(bus_id)
            else:
                buses_incomplete.append(bus_id)
                bus_completion_status[bus_id] = missing_norms
        
        metrics['complete_buses'] = len(buses_complete)
        metrics['incomplete_buses'] = len(buses_incomplete)
        metrics['bus_completion_status'] = bus_completion_status
        
        # Lista de buses completos e incompletos
        metrics['complete_buses_list'] = buses_complete
        metrics['incomplete_buses_list'] = buses_incomplete
        
        # Calcular porcentaje de avance por norma
        norm_progress = {}
        for col in norm_cols:
            values = df[col].str.lower()
            # IMPORTANTE: Considerar "instalado" O "no aplica" como completado
            is_installed = ((values == '1') | 
                           (values == 'instalada') | 
                           (values == 'instalado') |
                           (values.str.contains('instalad')))
            
            is_not_applicable = values.str.contains('no aplica')
            
            # Contar como "completado" si está instalado O no aplica
            completed = (is_installed | is_not_applicable).sum()
            
            # El total siempre es el número de buses (no restamos "no aplica")
            progress = (completed / total_buses * 100) if total_buses > 0 else 0
            norm_progress[col] = round(progress, 2)
        
        metrics['norm_progress'] = norm_progress
        
        # Calcular porcentaje de avance por bus
        bus_progress = {}
        for idx, row in df.iterrows():
            # Determinar el ID del bus
            if 'N° Interno' in row and not pd.isna(row['N° Interno']):
                bus_id = str(row['N° Interno'])
            elif 'Numero Interno' in row and not pd.isna(row['Numero Interno']):
                bus_id = str(row['Numero Interno'])
            else:
                # Buscar otra columna con "INTERNO" en el nombre
                interno_cols = [col for col in row.index if 'INTERNO' in col.upper()]
                if interno_cols:
                    bus_id = str(row[interno_cols[0]])
                else:
                    # Usar PPU como fallback
                    if 'PPU' in row and not pd.isna(row['PPU']):
                        bus_id = f"PPU_{str(row['PPU'])}"
                    else:
                        # Último recurso: usar el índice
                        bus_id = f"Bus_{idx}"
            
            # IMPORTANTE: Contar normas y considerar "no aplica" como completada
            total_norms = len(norm_cols)  # Total de todas las normas
            completed_norms = 0
            applicable_norms = 0  # Normas que aplican a este bus
            
            for col in norm_cols:
                val = str(row[col]).lower().strip()
                is_not_applicable = 'no aplica' in val
                
                # Verificar si está instalada
                is_installed = (val == '1' or 
                             val == 'instalada' or 
                             val == 'instalado' or
                             'instalad' in val)
                
                # Si está instalada O no aplica, cuéntala como completada
                if is_installed or is_not_applicable:
                    completed_norms += 1
                
                # Contar cuántas normas son aplicables
                if not is_not_applicable:
                    applicable_norms += 1
            
            # Calcular progreso basado en el total de normas (no solo las aplicables)
            progress = (completed_norms / total_norms * 100) if total_norms > 0 else 0
            
            # Obtener información adicional con manejo seguro
            bus_info = {
                'progress': round(progress, 2),
                'completed': completed_norms,
                'total_norms': total_norms,
                'applicable_norms': applicable_norms,
                'ppu': row['PPU'] if 'PPU' in row and not pd.isna(row['PPU']) else 'N/A',
            }
            
            # Fecha de renovación
            if 'FECHA DE RENOVACION' in row and not pd.isna(row['FECHA DE RENOVACION']):
                bus_info['fecha_renovacion'] = row['FECHA DE RENOVACION']
            else:
                bus_info['fecha_renovacion'] = 'N/A'
                
            # Normas instaladas (contador)
            if 'NORMA INSTALADA' in row and not pd.isna(row['NORMA INSTALADA']):
                bus_info['normas_instaladas_contador'] = row['NORMA INSTALADA']
            else:
                # Contar solo las instaladas (sin los "no aplica")
                installed_only = 0
                for col in norm_cols:
                    val = str(row[col]).lower().strip()
                    if val == '1' or val == 'instalada' or val == 'instalado' or 'instalad' in val:
                        installed_only += 1
                bus_info['normas_instaladas_contador'] = installed_only
            
            # Terminal con manejo seguro
            terminal_col = next((col for col in row.index if 'term' in col.lower()), None)
            if terminal_col and not pd.isna(row[terminal_col]):
                bus_info['terminal'] = row[terminal_col]
            else:
                bus_info['terminal'] = 'N/A'
            
            # Subclase/Modelo con manejo seguro
            subclass_col = next((col for col in row.index if 'sub' in col.lower() or 'clas' in col.lower() or 'model' in col.lower()), None)
            if subclass_col and not pd.isna(row[subclass_col]):
                bus_info['subclase'] = row[subclass_col]
            else:
                bus_info['subclase'] = 'N/A'
            
            # Marcar si está completo o no
            bus_info['completo'] = bus_id in buses_complete
            
            # Normas faltantes específicas
            if bus_id in bus_completion_status:
                bus_info['normas_faltantes'] = bus_completion_status[bus_id]
            else:
                bus_info['normas_faltantes'] = []
            
            bus_progress[bus_id] = bus_info
        
        metrics['bus_progress'] = bus_progress
        
        return metrics
        
    except Exception as e:
        st.error(f"Error al calcular métricas: {str(e)}")
        # Devolver métricas predeterminadas en caso de error
        return {
            'efficiency': 0,
            'total_buses': total_buses if 'total_buses' in locals() else 0,
            'total_norms': len(norm_cols),
            'completed_installations': 0,
            'pending_installations': 0,
            'complete_buses': 0,
            'incomplete_buses': 0,
            'norm_progress': {},
            'bus_progress': {}
        }

# Función para generar informe detallado por bus
def generate_bus_report(df, bus_id, norm_cols):
    try:
        # Encontrar la fila correspondiente al bus, con manejo de diferentes tipos de ID
        bus_row = None
        if 'N° Interno' in df.columns:
            matching_rows = df[df['N° Interno'].astype(str) == str(bus_id)]
            if not matching_rows.empty:
                bus_row = matching_rows.iloc[0]
        
        # Si no se encontró, buscar en otras columnas posibles
        if bus_row is None and 'Numero Interno' in df.columns:
            matching_rows = df[df['Numero Interno'].astype(str) == str(bus_id)]
            if not matching_rows.empty:
                bus_row = matching_rows.iloc[0]
        
        # Si aún no se encontró, buscar por PPU si el ID parece ser una patente
        if bus_row is None and 'PPU' in df.columns and bus_id.startswith("PPU_"):
            ppu_value = bus_id.replace("PPU_", "")
            matching_rows = df[df['PPU'].astype(str) == ppu_value]
            if not matching_rows.empty:
                bus_row = matching_rows.iloc[0]
        
        # Si aún no se encontró, buscar por índice
        if bus_row is None and bus_id.startswith("Bus_"):
            try:
                idx = int(bus_id.replace("Bus_", ""))
                if idx < len(df):
                    bus_row = df.iloc[idx]
            except ValueError:
                pass
        
        # Si no se encontró el bus, devolver información predeterminada
        if bus_row is None:
            return {
                'N° Interno': bus_id,
                'PPU': 'N/A',
                'Error': 'No se encontró información para este bus'
            }, {col: 'Desconocido' for col in norm_cols}, 0
        
        # Información general del bus con manejo seguro
        bus_info = {'N° Interno': bus_id}
        
        # Campos comunes a buscar (información del bus, no normas)
        info_fields = [
            ('PPU', ['PPU', 'Patente', 'Placa']),
            ('Unidad', ['Unidad', 'Unid']),
            ('Marca chasis', ['Marca chasis', 'Marca', 'Marca Bus']),
            ('Modelo chasis', ['Modelo chasis', 'Modelo', 'Tipo']),
            ('Subclase', ['Subclase', 'Clase', 'Tipo Bus']),
            ('N° plazas', ['N° plazas', 'Plazas', 'Capacidad']),
            ('Terminal', ['Terminal', 'Base', 'Ubicacion']),
            ('Taller', ['Taller', 'Servicio']),
            ('FECHA DE RENOVACION', ['FECHA DE RENOVACION', 'Fecha']),
            ('NORMA INSTALADA', ['NORMA INSTALADA', 'Normas Instaladas', 'Total Instaladas'])
        ]
        
        # Buscar cada campo en las columnas disponibles
        for field_name, possible_cols in info_fields:
            # Buscar el primer nombre de columna que exista
            found_col = next((col for col in possible_cols if col in bus_row.index), None)
            if found_col:
                # Usar el valor si no es nulo
                value = bus_row[found_col]
                bus_info[field_name] = value if not pd.isna(value) else 'N/A'
            else:
                # Si no se encuentra, poner N/A
                bus_info[field_name] = 'N/A'
        
        # Estado de las normas con manejo seguro
        norm_status = {}
        for col in norm_cols:
            if col in bus_row.index:
                status = str(bus_row[col]).strip().lower()
                if status == '1' or status == 'instalada' or status == 'instalado' or 'instalad' in status:
                    status_text = "Instalada"
                elif 'no aplica' in status:
                    status_text = "No Aplica"
                elif status == '' or status == 'nan' or pd.isna(bus_row[col]):
                    status_text = "Pendiente"
                else:
                    status_text = "Pendiente"
            else:
                status_text = "No Disponible"
            
            norm_status[col] = status_text
        
        # Calcular porcentaje de avance
        required_norms = sum(1 for status in norm_status.values() if status != "No Aplica" and status != "No Disponible")
        if required_norms == 0:
            # Si no hay normas requeridas (todas son 'No Aplica' o 'No Disponible')
            return bus_info, norm_status, 100
            
        completed = sum(1 for status in norm_status.values() if status == "Instalada")
        progress = (completed / required_norms * 100) if required_norms > 0 else 0
        
        return bus_info, norm_status, round(progress, 2)
        
    except Exception as e:
        st.error(f"Error al generar reporte de bus: {str(e)}")
        # Devolver información predeterminada en caso de error
        return {
            'N° Interno': bus_id,
            'PPU': 'N/A',
            'Error': f'Error al generar reporte: {str(e)}'
        }, {col: 'Error' for col in norm_cols}, 0

# Función para generar exportable HTML del informe por bus
def generate_bus_report_html(bus_info, norm_status, progress):
    # Generar colores para el medidor de progreso
    progress_color = "#28A745" if progress >= 90 else "#FFC107" if progress >= 50 else "#DC3545"
    
    # Obtener fecha de renovación y normas instaladas (si existen)
    fecha_renovacion = bus_info.get('FECHA DE RENOVACION', 'No registrada')
    normas_instaladas = bus_info.get('NORMA INSTALADA', 'No registrado')
    
    # Crear HTML para el informe
    html = f'''
    <div style="font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 10px;">
        <div style="text-align: center; border-bottom: 2px solid #1E3A8A; padding-bottom: 15px; margin-bottom: 20px;">
            <h1 style="color: #1E3A8A; margin: 0;">Informe Detallado de Bus</h1>
            <h2 style="color: #555; margin: 10px 0 0 0;">N° Interno: {bus_info['N° Interno']} - PPU: {bus_info['PPU']}</h2>
        </div>
        
        <div style="display: flex; margin-bottom: 20px;">
            <div style="flex: 1; padding-right: 20px;">
                <h3 style="color: #1E3A8A; border-bottom: 1px solid #ddd; padding-bottom: 10px;">Información del Bus</h3>
                <table style="width: 100%; border-collapse: collapse;">
    '''
    
    # Agregar información del bus a la tabla
    for key, value in bus_info.items():
        if key not in ['N° Interno', 'PPU']:  # Estos ya están en el encabezado
            html += f'''
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #eee; font-weight: bold;">{key}</td>
                <td style="padding: 8px; border-bottom: 1px solid #eee;">{value}</td>
            </tr>
            '''
    
    # Agregar detalles sobre fecha de renovación y normas instaladas
    html += f'''
                </table>
                
                <h3 style="color: #1E3A8A; border-bottom: 1px solid #ddd; padding-bottom: 10px; margin-top: 20px;">Detalles de Instalación</h3>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 8px; border-bottom: 1px solid #eee; font-weight: bold;">Fecha de Renovación</td>
                        <td style="padding: 8px; border-bottom: 1px solid #eee;">{fecha_renovacion}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; border-bottom: 1px solid #eee; font-weight: bold;">Total Normas Instaladas</td>
                        <td style="padding: 8px; border-bottom: 1px solid #eee;">{normas_instaladas}</td>
                    </tr>
                </table>
            </div>
            
            <div style="flex: 1; padding-left: 20px; text-align: center;">
                <h3 style="color: #1E3A8A; border-bottom: 1px solid #ddd; padding-bottom: 10px;">Progreso de Instalación</h3>
                <div style="position: relative; width: 200px; height: 200px; margin: 0 auto; border-radius: 50%; background: #f3f3f3; overflow: hidden;">
                    <div style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; clip-path: polygon(50% 0%, 100% 0%, 100% 100%, 0% 100%, 0% 0%, 50% 0%); background: conic-gradient({progress_color} 0% {progress}%, #f3f3f3 {progress}% 100%); transform: rotate(0deg);"></div>
                    <div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); font-size: 40px; font-weight: bold; color: #333;">{progress}%</div>
                </div>
            </div>
        </div>
        
        <h3 style="color: #1E3A8A; border-bottom: 1px solid #ddd; padding-bottom: 10px;">Estado de Normas Gráficas</h3>
    '''
    
    # Dividir las normas por estado para mostrarlas agrupadas
    normas_pendientes = [norm for norm, status in norm_status.items() if status == "Pendiente"]
    normas_instaladas = [norm for norm, status in norm_status.items() if status == "Instalada"]
    normas_no_aplican = [norm for norm, status in norm_status.items() if status == "No Aplica"]
    
    # Primero mostrar un resumen
    html += f'''
        <div style="margin-bottom: 20px; display: flex; flex-wrap: wrap; gap: 10px;">
            <div style="flex: 1; min-width: 200px; background-color: #f8d7da; border-radius: 5px; padding: 10px; text-align: center;">
                <h4 style="margin: 0; color: #721c24;">Normas Pendientes</h4>
                <p style="font-size: 24px; font-weight: bold; margin: 10px 0;">{len(normas_pendientes)}</p>
            </div>
            <div style="flex: 1; min-width: 200px; background-color: #d4edda; border-radius: 5px; padding: 10px; text-align: center;">
                <h4 style="margin: 0; color: #155724;">Normas Instaladas</h4>
                <p style="font-size: 24px; font-weight: bold; margin: 10px 0;">{len(normas_instaladas)}</p>
            </div>
            <div style="flex: 1; min-width: 200px; background-color: #e2e3e5; border-radius: 5px; padding: 10px; text-align: center;">
                <h4 style="margin: 0; color: #383d41;">Normas No Aplican</h4>
                <p style="font-size: 24px; font-weight: bold; margin: 10px 0;">{len(normas_no_aplican)}</p>
            </div>
        </div>
    '''
    
    # Agregar sección específica para normas pendientes (lo más importante)
    if normas_pendientes:
        html += f'''
        <div style="margin-top: 20px; border: 2px dashed #DC3545; padding: 15px; border-radius: 5px;">
            <h4 style="color: #DC3545; margin-top: 0;">⚠️ Normas Pendientes por Instalar ({len(normas_pendientes)})</h4>
            <ul style="columns: 2; column-gap: 20px; list-style-type: none; padding-left: 0;">
        '''
        
        for norm in normas_pendientes:
            html += f'<li style="margin-bottom: 8px; padding: 5px; background-color: #fff5f5; border-left: 3px solid #DC3545;">✘ {norm}</li>'
        
        html += '''
            </ul>
        </div>
        '''
    else:
        html += '''
        <div style="margin-top: 20px; border: 2px solid #28A745; padding: 15px; border-radius: 5px; text-align: center;">
            <h4 style="color: #28A745; margin-top: 0;">✓ ¡Todas las normas requeridas están instaladas!</h4>
        </div>
        '''
    
    # Tabla completa de todas las normas
    html += '''
        <h4 style="margin-top: 20px;">Detalle Completo de Normas</h4>
        <table style="width: 100%; border-collapse: collapse;">
            <tr style="background-color: #f2f2f2;">
                <th style="padding: 12px; text-align: left; border-bottom: 2px solid #ddd;">Norma</th>
                <th style="padding: 12px; text-align: center; border-bottom: 2px solid #ddd;">Estado</th>
            </tr>
    '''
    
    # Agregar estado de normas a la tabla
    for norm, status in norm_status.items():
        status_color = "#28A745" if status == "Instalada" else "#6C757D" if status == "No Aplica" else "#DC3545"
        status_icon = "✓" if status == "Instalada" else "○" if status == "No Aplica" else "✘"
        
        html += f'''
        <tr>
            <td style="padding: 8px; border-bottom: 1px solid #eee;">{norm}</td>
            <td style="padding: 8px; border-bottom: 1px solid #eee; text-align: center;">
                <span style="display: inline-block; padding: 5px 10px; border-radius: 5px; background-color: {status_color}; color: white;">{status_icon} {status}</span>
            </td>
        </tr>
        '''
    
    html += f'''
        </table>
        
        <div style="margin-top: 30px; border-top: 1px solid #ddd; padding-top: 15px; text-align: center; color: #777; font-size: 0.9em;">
            <p>Informe generado el {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
        </div>
    </div>
    '''
    
    return html

# Función para crear un enlace de descarga para un archivo HTML
def get_html_download_link(html, filename="informe_bus.html", text="Descargar informe"):
    b64 = base64.b64encode(html.encode()).decode()
    href = f'<a href="data:text/html;base64,{b64}" download="{filename}" style="display: inline-block; padding: 10px 20px; background-color: #4CAF50; color: white; text-decoration: none; border-radius: 5px; font-weight: bold;">{text}</a>'
    return href

# Función para general gráficos de pastel por categorías
def create_pie_charts(df, norm_cols):
    try:
        if not PLOTLY_AVAILABLE:
            st.warning("No se pueden crear gráficos. Por favor instala plotly: pip install plotly")
            return None, None
            
        # Crear el gráfico de estado global de instalación
        total_normas = len(df) * len(norm_cols)
        instaladas = 0
        no_aplica = 0
        pendientes = 0
        
        for col in norm_cols:
            # Contar instaladas - valor '1' o 'instalado'
            values = df[col].astype(str).str.lower()
            instaladas += ((values == '1') | 
                          (values == 'instalada') | 
                          (values == 'instalado') |
                          (values.str.contains('instalad'))).sum()
            
            # Contar no aplica - variantes de "no aplica"
            no_aplica += values.str.contains('no aplica').sum()
        
        pendientes = total_normas - instaladas - no_aplica
        
        fig_global = px.pie(
            names=['Instaladas', 'No Aplican', 'Pendientes'],
            values=[instaladas, no_aplica, pendientes],
            title="Estado Global de Instalación",
            color_discrete_sequence=['#28A745', '#6C757D', '#DC3545'],
            hole=0.4
        )
        fig_global.update_layout(
            legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)
        )
        
        # Crear el gráfico de avance por terminal
        fig_terminal = go.Figure()
        
        # Verificar si existe alguna columna de terminal
        terminal_col = None
        if 'Terminal' in df.columns:
            terminal_col = 'Terminal'
        else:
            # Buscar columnas con nombre similar
            similar_cols = [col for col in df.columns if 'term' in col.lower()]
            if similar_cols:
                terminal_col = similar_cols[0]
        
        if terminal_col:
            terminal_progress = {}
            for terminal in df[terminal_col].dropna().unique():
                if not terminal or pd.isna(terminal):
                    continue
                    
                # Filtrar por terminal
                df_terminal = df[df[terminal_col].astype(str) == str(terminal)]
                if df_terminal.empty:
                    continue
                    
                total = len(df_terminal) * len(norm_cols)
                installed = 0
                not_applicable = 0
                
                # Contar instaladas y no aplica
                for col in norm_cols:
                    values = df_terminal[col].astype(str).str.lower()
                    installed += ((values == '1') | 
                                 (values == 'instalada') | 
                                 (values == 'instalado') |
                                 (values.str.contains('instalad'))).sum()
                    
                    not_applicable += values.str.contains('no aplica').sum()
                
                required = total - not_applicable
                if required > 0:
                    progress = (installed / required * 100)
                    terminal_progress[str(terminal)] = round(progress, 2)
            
            if terminal_progress:  # Solo si hay datos
                fig_terminal = px.bar(
                    x=list(terminal_progress.keys()),
                    y=list(terminal_progress.values()),
                    title=f"Porcentaje de Avance por {terminal_col}",
                    labels={'x': terminal_col, 'y': 'Avance (%)'},
                    color=list(terminal_progress.values()),
                    color_continuous_scale='Viridis'
                )
                fig_terminal.update_layout(coloraxis_showscale=False)
            else:
                fig_terminal.update_layout(title=f"No hay datos suficientes para mostrar avance por {terminal_col}")
        else:
            fig_terminal.update_layout(title="No hay datos de terminales disponibles")
        
        return fig_global, fig_terminal
        
    except Exception as e:
        # Si hay algún error, mostrar un mensaje de error
        st.error(f"Error al crear gráficos: {str(e)}")
        return None, None

# Función para crear heatmap de instalación por norma
def create_norm_heatmap(metrics):
    if not PLOTLY_AVAILABLE:
        st.warning("No se pueden crear gráficos. Por favor instala plotly: pip install plotly")
        return None
        
    norm_progress = metrics['norm_progress']
    
    # Ordenar las normas por porcentaje de avance
    sorted_norms = sorted(norm_progress.items(), key=lambda x: x[1])
    norm_names = [item[0] for item in sorted_norms]
    norm_values = [item[1] for item in sorted_norms]
    
    # Crear un dataframe para el heatmap
    df_heatmap = pd.DataFrame({'Norma': norm_names, 'Avance (%)': norm_values})
    
    # Determinar el color basado en el porcentaje
    colors = []
    for value in norm_values:
        if value >= 90:
            colors.append('#28A745')  # Verde para alto avance
        elif value >= 70:
            colors.append('#FFC107')  # Amarillo para avance medio
        else:
            colors.append('#DC3545')  # Rojo para bajo avance
    
    fig = px.bar(
        df_heatmap,
        y='Norma',
        x='Avance (%)',
        orientation='h',
        title="Porcentaje de Avance por Norma",
        color='Avance (%)',
        color_continuous_scale=['#DC3545', '#FFC107', '#28A745'],
        range_color=[0, 100]
    )
    
    fig.update_layout(
        height=max(400, len(norm_names) * 20),
        margin=dict(l=200),
        yaxis=dict(autorange="reversed")
    )
    
    return fig

# Función para crear un treemap de estado de normas por bus
def create_bus_treemap(df, bus_id, norm_cols):
    try:
        if not PLOTLY_AVAILABLE:
            st.warning("No se pueden crear gráficos de detalle. Por favor instala plotly: pip install plotly")
            return None
            
        # Buscar el bus de forma más robusta
        bus_row = None
        
        # Intentar diferentes estrategias para encontrar el bus
        if 'N° Interno' in df.columns:
            matching_rows = df[df['N° Interno'].astype(str) == str(bus_id)]
            if not matching_rows.empty:
                bus_row = matching_rows.iloc[0]
        
        # Si no se encontró, buscar en "Numero Interno"
        if bus_row is None and 'Numero Interno' in df.columns:
            matching_rows = df[df['Numero Interno'].astype(str) == str(bus_id)]
            if not matching_rows.empty:
                bus_row = matching_rows.iloc[0]
                
        # Probar con NUMERO INTERNO (mayúsculas)
        if bus_row is None:
            for col in df.columns:
                if 'NUMERO' in col.upper() and 'INTERNO' in col.upper():
                    matching_rows = df[df[col].astype(str) == str(bus_id)]
                    if not matching_rows.empty:
                        bus_row = matching_rows.iloc[0]
                        break
        
        # Si aún no se encontró, buscar por índice
        if bus_row is None and bus_id.startswith("Bus_"):
            try:
                idx = int(bus_id.replace("Bus_", ""))
                if idx < len(df):
                    bus_row = df.iloc[idx]
            except:
                pass
        
        # Si no se encontró, mostrar mensaje de error
        if bus_row is None:
            st.error(f"Error: Bus {bus_id} no encontrado")
            return None
        
        # Preparar datos para el treemap
        treemap_data = []
        
        # Crear treemap dividido en dos grandes categorías: Instaladas y Pendientes
        for col in norm_cols:
            if col in bus_row.index:
                status = str(bus_row[col]).strip().lower()
                
                # Clasificar el estado de la norma
                if status == '1' or status == 'instalada' or status == 'instalado' or 'instalad' in status:
                    status_text = "Instaladas"
                    color = '#28A745'
                elif 'no aplica' in status:
                    status_text = "No Aplican"
                    color = '#6C757D'
                else:
                    status_text = "Pendientes"
                    color = '#DC3545'
                
                treemap_data.append({
                    'Norma': col,
                    'Estado': status_text,
                    'Valor': 1,
                    'Color': color
                })
        
        # Crear dataframe
        df_treemap = pd.DataFrame(treemap_data)
        
        # Si no hay datos, mostrar mensaje
        if df_treemap.empty:
            st.info(f"Bus {bus_id}: Sin datos de normas")
            return None
        
        # Contar normas por estado
        pendientes = df_treemap[df_treemap['Estado'] == 'Pendientes']
        instaladas = df_treemap[df_treemap['Estado'] == 'Instaladas']
        no_aplican = df_treemap[df_treemap['Estado'] == 'No Aplican']
        
        # Añadir contador a los estados para mejor visualización
        estados_modificados = []
        
        if not pendientes.empty:
            estados_modificados.append(f"Pendientes ({len(pendientes)})")
        else:
            estados_modificados.append("Pendientes (0)")
            
        if not instaladas.empty:
            estados_modificados.append(f"Instaladas ({len(instaladas)})")
        else:
            estados_modificados.append("Instaladas (0)")
            
        if not no_aplican.empty:
            estados_modificados.append(f"No Aplican ({len(no_aplican)})")
        else:
            estados_modificados.append("No Aplican (0)")
        
        # Actualizar el DataFrame
        df_treemap['Estado'] = df_treemap['Estado'].replace({
            'Pendientes': estados_modificados[0],
            'Instaladas': estados_modificados[1],
            'No Aplican': estados_modificados[2]
        })
        
        # Crear treemap
        fig = px.treemap(
            df_treemap,
            path=['Estado', 'Norma'],
            values='Valor',
            color='Estado',
            color_discrete_map={
                estados_modificados[1]: '#28A745',  # Instaladas
                estados_modificados[2]: '#6C757D',  # No Aplican
                estados_modificados[0]: '#DC3545'   # Pendientes
            },
            title=f"Estado de Normas - Bus {bus_id}"
        )
        
        fig.update_layout(margin=dict(t=50, l=25, r=25, b=25))
        
        return fig
    
    except Exception as e:
        # En caso de error, mostrar mensaje
        st.error(f"Error al procesar datos para Bus {bus_id}: {str(e)}")
        return None

# Función para crear gráficos de avance por tipo de bus (subclase)
def create_subclass_charts(df, norm_cols):
    if not PLOTLY_AVAILABLE:
        st.warning("No se pueden crear gráficos. Por favor instala plotly: pip install plotly")
        return None
        
    if 'Subclase' not in df.columns:
        st.info("No hay datos de subclase disponibles")
        return None
    
    subclass_progress = {}
    for subclass in df['Subclase'].unique():
        if pd.isna(subclass):
            continue
            
        df_subclass = df[df['Subclase'] == subclass]
        total = len(df_subclass) * len(norm_cols)
        installed = 0
        not_applicable = 0
        
        for col in norm_cols:
            values = df_subclass[col].astype(str).str.lower()
            installed += ((values == '1') | 
                         (values == 'instalada') | 
                         (values == 'instalado') |
                         (values.str.contains('instalad'))).sum()
                         
            not_applicable += values.str.contains('no aplica').sum()
        
        required = total - not_applicable
        progress = (installed / required * 100) if required > 0 else 0
        subclass_progress[subclass] = round(progress, 2)
    
    # Si no hay datos, devolver None
    if not subclass_progress:
        st.info("No hay suficientes datos para generar un gráfico por subclase")
        return None
        
    # Crear gráfico
    fig = px.bar(
        x=list(subclass_progress.keys()),
        y=list(subclass_progress.values()),
        title="Porcentaje de Avance por Tipo de Bus (Subclase)",
        labels={'x': 'Subclase', 'y': 'Avance (%)'},
        color=list(subclass_progress.values()),
        color_continuous_scale='Viridis',
        text=list(subclass_progress.values())
    )
    
    fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
    fig.update_layout(uniformtext_minsize=10, uniformtext_mode='hide', coloraxis_showscale=False)
    
    return fig

# APLICACIÓN PRINCIPAL
def main():
    st.markdown('<h1 class="main-header">Sistema de Control de Instalación de Normas Gráficas</h1>', unsafe_allow_html=True)
    
    # Barra lateral para carga de archivos y filtros
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/2821/2821637.png", width=100)
        st.markdown("### Carga de Datos")
        uploaded_file = st.file_uploader("Cargar archivo Excel", type=['xlsx', 'xls'])
        
        if uploaded_file is not None:
            df = load_data(uploaded_file)
            
            if df is not None:
                st.success(f"Archivo cargado correctamente! {len(df)} registros encontrados.")
                
                # Mostrar información sobre las columnas disponibles
                st.markdown("### Columnas detectadas")
                st.write(df.columns.tolist())
                
                # Filtros de Terminal con manejo extremadamente robusto
                terminal_filter = None
                try:
                    # Intentar encontrar la columna 'Terminal' o similares
                    terminal_column = None
                    if 'Terminal' in df.columns:
                        terminal_column = 'Terminal'
                    else:
                        # Buscar columnas con nombre similar
                        similar_columns = [col for col in df.columns if 'term' in col.lower()]
                        if similar_columns:
                            terminal_column = similar_columns[0]
                            st.info(f"Usando '{terminal_column}' como columna de Terminal")
                    
                    # Si encontramos una columna adecuada, crear el filtro
                    if terminal_column:
                        # Obtener valores únicos no nulos
                        terminal_values = df[terminal_column].dropna().unique()
                        if len(terminal_values) > 0:
                            terminal_options = [str(t) for t in terminal_values if t and str(t).strip()]
                            if terminal_options:
                                terminal_filter = st.multiselect(
                                    f"Filtrar por {terminal_column}", 
                                    options=terminal_options,
                                    default=terminal_options
                                )
                except Exception as e:
                    st.warning(f"No se pudo crear el filtro de Terminal: {e}")
                    terminal_filter = None
                
                # Filtros de Subclase con manejo extremadamente robusto
                subclass_filter = None
                try:
                    # Intentar encontrar la columna 'Subclase' o similares
                    subclass_column = None
                    if 'Subclase' in df.columns:
                        subclass_column = 'Subclase'
                    else:
                        # Buscar columnas con nombre similar
                        similar_columns = [col for col in df.columns if 'clas' in col.lower() or 'model' in col.lower()]
                        if similar_columns:
                            subclass_column = similar_columns[0]
                            st.info(f"Usando '{subclass_column}' como columna de Subclase/Modelo")
                    
                    # Si encontramos una columna adecuada, crear el filtro
                    if subclass_column:
                        # Obtener valores únicos no nulos
                        subclass_values = df[subclass_column].dropna().unique()
                        if len(subclass_values) > 0:
                            subclass_options = [str(s) for s in subclass_values if s and str(s).strip()]
                            if subclass_options:
                                subclass_filter = st.multiselect(
                                    f"Filtrar por {subclass_column}", 
                                    options=subclass_options,
                                    default=subclass_options
                                )
                except Exception as e:
                    st.warning(f"No se pudo crear el filtro de Subclase: {e}")
                    subclass_filter = None
                
                # Filtrar dataframe con manejo ultra-seguro
                filtered_df = df.copy()  # Empezar con una copia del dataframe original
                
                # Aplicar filtro de terminal si existe
                if terminal_filter and terminal_column and terminal_column in filtered_df.columns:
                    filtered_df = filtered_df[filtered_df[terminal_column].astype(str).isin(terminal_filter)]
                
                # Aplicar filtro de subclase si existe
                if subclass_filter and subclass_column and subclass_column in filtered_df.columns:
                    filtered_df = filtered_df[filtered_df[subclass_column].astype(str).isin(subclass_filter)]
                
                # Verificar que el filtrado dejó algún dato
                if filtered_df.empty:
                    st.warning("Los filtros aplicados no dejaron datos. Mostrando todos los datos.")
                    filtered_df = df.copy()
                
                # Procesar datos
                processed_df, cols_info, norm_cols = process_data(filtered_df)
                metrics = calculate_metrics(processed_df, norm_cols)
                
                # Mostrar fecha de actualización
                st.markdown("### Información")
                st.info(f"Última actualización: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
                
                # Mostrar métricas globales
                st.markdown("### Métricas Globales")
                st.markdown(f"**Eficiencia global:** <span class='metric-value'>{metrics['efficiency']}%</span>", unsafe_allow_html=True)
                st.markdown(f"**Buses completos:** {metrics['complete_buses']} de {metrics['total_buses']}")
                
                # Descargar datos filtrados
                if st.button("Exportar Datos Filtrados"):
                    try:
                        # Intentar guardar con xlsxwriter
                        buffer = io.BytesIO()
                        try:
                            # Intentar usar xlsxwriter primero
                            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                                processed_df.to_excel(writer, sheet_name='Datos', index=False)
                            buffer.seek(0)
                            st.download_button(
                                label="Descargar Excel",
                                data=buffer,
                                file_name=f"datos_filtrados_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                                mime="application/vnd.ms-excel"
                            )
                        except ImportError:
                            # Si no está disponible xlsxwriter, usar CSV
                            csv = processed_df.to_csv(index=False)
                            b64 = base64.b64encode(csv.encode()).decode()
                            href = f'<a href="data:file/csv;base64,{b64}" download="datos_filtrados_{datetime.now().strftime("%Y%m%d_%H%M")}.csv">Descargar como CSV</a>'
                            st.markdown(href, unsafe_allow_html=True)
                            st.warning("La biblioteca xlsxwriter no está instalada. Se ha generado un archivo CSV en su lugar. Para poder descargar en formato Excel, instala xlsxwriter con: pip install xlsxwriter")
                    except Exception as e:
                        st.error(f"Error al exportar datos: {str(e)}")
                        st.info("Sugerencia: Para exportar a Excel, instale xlsxwriter con el comando: pip install xlsxwriter")
        else:
            st.warning("Por favor, carga un archivo Excel para comenzar.")
            # Mostrar información de demo
            st.markdown("""
            ### Información de Uso
            
            Este sistema le permite:
            
            - Visualizar el avance de instalación de normas gráficas
            - Generar reportes detallados por bus
            - Analizar tendencias por terminal y tipo de bus
            - Identificar buses con normas pendientes
            - Exportar datos e informes
            
            Cargue un archivo Excel para comenzar.
            """)
    
    # Contenido principal
    if 'uploaded_file' in locals() and uploaded_file is not None and 'processed_df' in locals():
        
        # Dashboard principal
        st.markdown('<h2 class="sub-header">Dashboard Principal</h2>', unsafe_allow_html=True)
        
        # Resumen en tarjetas
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{metrics['efficiency']}%</div>
                <div class="metric-label">Eficiencia Global</div>
            </div>
            """, unsafe_allow_html=True)
            
        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{metrics['total_buses']}</div>
                <div class="metric-label">Total de Buses</div>
            </div>
            """, unsafe_allow_html=True)
            
        with col3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{metrics['complete_buses']}</div>
                <div class="metric-label">Buses Completos</div>
            </div>
            """, unsafe_allow_html=True)
            
        with col4:
            incomplete = metrics['total_buses'] - metrics['complete_buses']
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{incomplete}</div>
                <div class="metric-label">Buses Incompletos</div>
            </div>
            """, unsafe_allow_html=True)
        
        # Gráficos principales
        st.markdown('<h3 class="sub-header">Análisis de Avance</h3>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Estado global de instalación (gráfico de pastel)
            fig_global, fig_terminal = create_pie_charts(processed_df, norm_cols)
            if fig_global:
                st.plotly_chart(fig_global, use_container_width=True)
            else:
                st.info("No se pudo generar el gráfico circular. Para ver todos los gráficos, instala plotly con: pip install plotly")
                # Mostrar un resumen básico en texto como alternativa
                total_normas = len(processed_df) * len(norm_cols)
                instaladas = 0
                no_aplica = 0
                
                for col in norm_cols:
                    # Contar instaladas y no aplica
                    values = processed_df[col].astype(str).str.lower()
                    instaladas += ((values == '1') | 
                                  (values == 'instalada') | 
                                  (values == 'instalado') |
                                  (values.str.contains('instalad'))).sum()
                    no_aplica += values.str.contains('no aplica').sum()
                
                pendientes = total_normas - instaladas - no_aplica
                
                st.write(f"**Resumen de estado:**")
                st.write(f"- Normas instaladas: {instaladas} ({instaladas/total_normas*100:.1f}%)")
                st.write(f"- Normas no aplicables: {no_aplica} ({no_aplica/total_normas*100:.1f}%)")
                st.write(f"- Normas pendientes: {pendientes} ({pendientes/total_normas*100:.1f}%)")
            
        with col2:
            # Avance por terminal
            if fig_terminal:
                st.plotly_chart(fig_terminal, use_container_width=True)
            else:
                st.info("No se pudo generar el gráfico por terminal.")
                # Si no hay gráfico, mostrar métricas básicas
                terminal_col = next((col for col in processed_df.columns if 'term' in col.lower()), None)
                if terminal_col:
                    st.write(f"**Terminales presentes en los datos:**")
                    terminals = processed_df[terminal_col].dropna().unique()
                    for terminal in terminals:
                        if pd.isna(terminal):
                            continue
                        st.write(f"- {terminal}")
                else:
                    st.write("No se encontró información de terminales en los datos.")
        
        # Resumen global de completos vs pendientes
        st.markdown('<h3 class="sub-header">Resumen de Estado de Buses</h3>', unsafe_allow_html=True)
        
        if PLOTLY_AVAILABLE:
            # Gráfico comparativo de buses completos vs pendientes
            fig_completion = px.pie(
                names=['Buses Completos', 'Buses Pendientes'],
                values=[metrics['complete_buses'], metrics['incomplete_buses']],
                title="Distribución de Buses por Estado de Completitud",
                color_discrete_sequence=['#28A745', '#DC3545'],
                hole=0.4
            )
            fig_completion.update_layout(legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5))
            
            # Mostrar desglose por rangos de avance
            avance_ranges = {
                "90-100%": 0,
                "70-89%": 0,
                "50-69%": 0,
                "25-49%": 0,
                "0-24%": 0
            }
            
            for bus_id, info in metrics['bus_progress'].items():
                progress = info['progress']
                if progress >= 90:
                    avance_ranges["90-100%"] += 1
                elif progress >= 70:
                    avance_ranges["70-89%"] += 1
                elif progress >= 50:
                    avance_ranges["50-69%"] += 1
                elif progress >= 25:
                    avance_ranges["25-49%"] += 1
                else:
                    avance_ranges["0-24%"] += 1
            
            # Mostrar resumen de rangos en gráfico
            fig_ranges = px.bar(
                x=list(avance_ranges.keys()),
                y=list(avance_ranges.values()),
                labels={'x': 'Rango de Avance', 'y': 'Cantidad de Buses'},
                title="Distribución de Buses por Rango de Avance",
                color=list(avance_ranges.keys()),
                color_discrete_map={
                    "90-100%": '#28A745',
                    "70-89%": '#5CB85C',
                    "50-69%": '#FFC107',
                    "25-49%": '#FF9800',
                    "0-24%": '#DC3545'
                }
            )
            
            col1, col2 = st.columns(2)
            with col1:
                st.plotly_chart(fig_completion, use_container_width=True)
            
            with col2:
                st.plotly_chart(fig_ranges, use_container_width=True)
        else:
            # Versión de texto si plotly no está disponible
            st.info("No se pueden mostrar los gráficos. Para ver gráficos, instala plotly: pip install plotly")
            
            # Mostrar resumen en texto
            col1, col2 = st.columns(2)
            with col1:
                st.write("**Distribución de Buses por Estado:**")
                st.write(f"- Buses Completos: {metrics['complete_buses']} ({metrics['complete_buses']/metrics['total_buses']*100:.1f}%)")
                st.write(f"- Buses Pendientes: {metrics['incomplete_buses']} ({metrics['incomplete_buses']/metrics['total_buses']*100:.1f}%)")
            
            with col2:
                # Calcular rangos sin gráficos
                avance_ranges = {
                    "90-100%": 0,
                    "70-89%": 0,
                    "50-69%": 0,
                    "25-49%": 0,
                    "0-24%": 0
                }
                
                for bus_id, info in metrics['bus_progress'].items():
                    progress = info['progress']
                    if progress >= 90:
                        avance_ranges["90-100%"] += 1
                    elif progress >= 70:
                        avance_ranges["70-89%"] += 1
                    elif progress >= 50:
                        avance_ranges["50-69%"] += 1
                    elif progress >= 25:
                        avance_ranges["25-49%"] += 1
                    else:
                        avance_ranges["0-24%"] += 1
                
                st.write("**Distribución de Buses por Rango de Avance:**")
                for rango, cantidad in avance_ranges.items():
                    if cantidad > 0:
                        st.write(f"- {rango}: {cantidad} buses ({cantidad/metrics['total_buses']*100:.1f}%)")
        
        # Mostrar resumen estadístico
        st.markdown("""
        <div class="card">
            <h4>Resumen Estadístico de Instalación</h4>
            <div style="display: flex; flex-wrap: wrap; justify-content: space-between;">
        """, unsafe_allow_html=True)
        
        # Computar estadísticas adicionales
        progress_values = [info['progress'] for info in metrics['bus_progress'].values()]
        stats = {
            "Promedio de Avance": f"{sum(progress_values) / len(progress_values):.1f}%" if progress_values else "N/A",
            "Mediana de Avance": f"{sorted(progress_values)[len(progress_values)//2]:.1f}%" if progress_values else "N/A",
            "Máximo Avance": f"{max(progress_values):.1f}%" if progress_values else "N/A",
            "Mínimo Avance": f"{min(progress_values):.1f}%" if progress_values else "N/A",
            "Buses Completos": f"{metrics['complete_buses']} ({metrics['complete_buses']/metrics['total_buses']*100:.1f}%)" if metrics['total_buses'] > 0 else "0 (0%)",
            "Buses Pendientes": f"{metrics['incomplete_buses']} ({metrics['incomplete_buses']/metrics['total_buses']*100:.1f}%)" if metrics['total_buses'] > 0 else "0 (0%)"
        }
        
        for key, value in stats.items():
            st.markdown(f"""
            <div style="flex: 0 0 30%; margin-bottom: 15px;">
                <p style="font-weight: bold; margin-bottom: 5px;">{key}</p>
                <p style="font-size: 1.2rem; color: #1E3A8A;">{value}</p>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("""
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Análisis por tipo de norma
        st.markdown('<h3 class="sub-header">Análisis por Tipo de Norma</h3>', unsafe_allow_html=True)
        
        # Heatmap de instalación por norma
        fig_heatmap = create_norm_heatmap(metrics)
        if fig_heatmap:
            st.plotly_chart(fig_heatmap, use_container_width=True)
        else:
            st.info("No se pudo generar el gráfico de normas. Para ver este gráfico, instala plotly.")
            # Alternativa: Mostrar las normas y su porcentaje en una tabla
            norm_progress = metrics['norm_progress']
            sorted_norms = sorted(norm_progress.items(), key=lambda x: x[1])
            
            # Crear dataframe para mostrar las normas
            df_normas = pd.DataFrame(sorted_norms, columns=['Norma', 'Avance (%)'])
            df_normas['Avance (%)'] = df_normas['Avance (%)'].round(1).astype(str) + '%'
            
            # Mostrar tabla con formato condicional
            st.write("**Porcentaje de avance por norma:**")
            st.dataframe(df_normas, use_container_width=True)
        
        # Análisis por tipo de bus (subclase)
        st.markdown('<h3 class="sub-header">Análisis por Tipo de Bus</h3>', unsafe_allow_html=True)
        
        fig_subclass = create_subclass_charts(processed_df, norm_cols)
        if fig_subclass:
            st.plotly_chart(fig_subclass, use_container_width=True)
        else:
            st.info("No se pudo generar el gráfico por tipo de bus.")
            # Mostrar información básica sobre subclases como alternativa
            subclass_col = next((col for col in processed_df.columns if 'sub' in col.lower() or 'clas' in col.lower() or 'model' in col.lower()), None)
            if subclass_col:
                st.write(f"**Tipos de bus presentes en los datos:**")
                subclases = [s for s in processed_df[subclass_col].dropna().unique() if not pd.isna(s)]
                for subclase in subclases:
                    count = len(processed_df[processed_df[subclass_col] == subclase])
                    st.write(f"- {subclase}: {count} buses")
            else:
                st.write("No se encontró información de tipos de bus en los datos.")
        
        # Análisis de normas faltantes más comunes
        if 'bus_completion_status' in metrics and metrics['bus_completion_status']:
            st.markdown('<h3 class="sub-header">Análisis de Normas Faltantes</h3>', unsafe_allow_html=True)
            
            # Contar cuántas veces aparece cada norma como faltante
            normas_faltantes_conteo = {}
            for bus_id, missing_norms in metrics['bus_completion_status'].items():
                for norm in missing_norms:
                    if norm in normas_faltantes_conteo:
                        normas_faltantes_conteo[norm] += 1
                    else:
                        normas_faltantes_conteo[norm] = 1
            
            if normas_faltantes_conteo:
                # Ordenar por frecuencia
                normas_sorted = sorted(normas_faltantes_conteo.items(), key=lambda x: x[1], reverse=True)
                
                # Mostrar el top 10 de normas más faltantes
                st.markdown("""
                <div class="info-box">
                    <p><strong>Normas más frecuentemente faltantes:</strong> Estas son las normas gráficas que faltan instalar en más buses.</p>
                </div>
                """, unsafe_allow_html=True)
                
                # Preparar datos para gráfico
                top_normas = normas_sorted[:10]
                fig_top_normas = px.bar(
                    x=[norm[0] for norm in top_normas],
                    y=[norm[1] for norm in top_normas],
                    labels={'x': 'Norma', 'y': 'Cantidad de Buses'},
                    title="Top 10 Normas Faltantes",
                    color=[norm[1] for norm in top_normas],
                    color_continuous_scale='Reds'
                )
                fig_top_normas.update_layout(xaxis={'categoryorder': 'total descending'})
                st.plotly_chart(fig_top_normas, use_container_width=True)
                
                # Mostrar tabla de normas faltantes
                normas_df = pd.DataFrame([
                    {'Norma': norm[0], 'Cantidad de Buses': norm[1], 'Porcentaje': f"{(norm[1]/metrics['total_buses']*100):.1f}%"}
                    for norm in normas_sorted
                ])
                st.dataframe(normas_df, use_container_width=True)
                
                # Recomendaciones basadas en las normas faltantes
                st.markdown("""
                <div class="card">
                    <h4>Recomendaciones para Priorización de Instalación</h4>
                    <p>Basado en el análisis de normas faltantes, se recomienda priorizar la instalación de las normas más frecuentemente ausentes.</p>
                    <ol>
                """, unsafe_allow_html=True)
                
                for i, (norm, count) in enumerate(normas_sorted[:5]):
                    st.markdown(f"""
                    <li><strong>{norm}</strong>: Falta en {count} buses ({(count/metrics['total_buses']*100):.1f}% de la flota)</li>
                    """, unsafe_allow_html=True)
                
                st.markdown("""
                    </ol>
                </div>
                """, unsafe_allow_html=True)
        
        # Lista detallada de buses con normas faltantes
        if 'bus_completion_status' in metrics and metrics['bus_completion_status']:
            st.markdown('<h3 class="sub-header">Listado Detallado de Buses Pendientes</h3>', unsafe_allow_html=True)
            
            # Opciones de filtro y ordenamiento
            col1, col2 = st.columns(2)
            with col1:
                filter_min_missing = st.slider(
                    "Filtrar buses con al menos X normas faltantes", 
                    min_value=1, 
                    max_value=max([len(missing) for missing in metrics['bus_completion_status'].values()]) if metrics['bus_completion_status'] else 1,
                    value=1
                )
            
            with col2:
                sort_option = st.selectbox(
                    "Ordenar por", 
                    ["Número de normas faltantes (mayor a menor)", "Número de normas faltantes (menor a mayor)", "Número Interno"]
                )
            
            # Crear dataframe de buses pendientes con detalles
            buses_pendientes_data = []
            for bus_id, missing_norms in metrics['bus_completion_status'].items():
                if len(missing_norms) >= filter_min_missing:
                    # Obtener información adicional del bus
                    bus_info = metrics['bus_progress'].get(bus_id, {})
                    
                    buses_pendientes_data.append({
                        'Número Interno': bus_id,
                        'PPU': bus_info.get('ppu', 'N/A'),
                        'Terminal': bus_info.get('terminal', 'N/A'),
                        'Subclase': bus_info.get('subclase', 'N/A'),
                        'Normas Faltantes': len(missing_norms),
                        'Progreso': f"{bus_info.get('progress', 0):.1f}%",
                        'Detalle': ", ".join(missing_norms[:3]) + ("..." if len(missing_norms) > 3 else "")
                    })
            
            # Ordenar según la opción seleccionada
            if sort_option == "Número de normas faltantes (mayor a menor)":
                buses_pendientes_data.sort(key=lambda x: x['Normas Faltantes'], reverse=True)
            elif sort_option == "Número de normas faltantes (menor a mayor)":
                buses_pendientes_data.sort(key=lambda x: x['Normas Faltantes'])
            else:  # Por número interno
                buses_pendientes_data.sort(key=lambda x: x['Número Interno'])
            
            # Crear dataframe
            if buses_pendientes_data:
                buses_pendientes_df = pd.DataFrame(buses_pendientes_data)
                
                # Mostrar con formato condicional
                def highlight_progress(val):
                    progress = float(val.strip('%'))
                    if progress >= 90:
                        return 'background-color: #d4edda; color: #155724'
                    elif progress >= 70:
                        return 'background-color: #fff3cd; color: #856404'
                    else:
                        return 'background-color: #f8d7da; color: #721c24'
                
                styled_df = buses_pendientes_df.style.applymap(highlight_progress, subset=['Progreso'])
                st.dataframe(styled_df, use_container_width=True)
                
                # Opción para exportar la lista
                try:
                    # Intentar guardar con xlsxwriter
                    buffer = io.BytesIO()
                    try:
                        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                            buses_pendientes_df.to_excel(writer, sheet_name='Buses Pendientes', index=False)
                        buffer.seek(0)
                        
                        st.download_button(
                            label="📄 Descargar Listado de Buses Pendientes",
                            data=buffer,
                            file_name=f"buses_pendientes_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                            mime="application/vnd.ms-excel"
                        )
                    except ImportError:
                        # Si xlsxwriter no está disponible, convertir a CSV
                        csv = buses_pendientes_df.to_csv(index=False)
                        b64 = base64.b64encode(csv.encode()).decode()
                        href = f'<a href="data:file/csv;base64,{b64}" download="buses_pendientes_{datetime.now().strftime("%Y%m%d_%H%M")}.csv">📄 Descargar como CSV</a>'
                        st.markdown(href, unsafe_allow_html=True)
                        st.warning("La biblioteca xlsxwriter no está instalada. Se ha generado un archivo CSV en su lugar. Para poder descargar en formato Excel, instala xlsxwriter con: pip install xlsxwriter")
                except Exception as e:
                    st.error(f"Error al exportar datos: {str(e)}")
                    st.info("Sugerencia: Instale xlsxwriter con el comando: pip install xlsxwriter")
            else:
                st.info("No hay buses que cumplan con los criterios de filtrado.")
        
        # Lista completa de buses con su estado
        st.markdown('<h3 class="sub-header">Reporte Completo por Bus</h3>', unsafe_allow_html=True)
        
        # Crear reporte completo
        reporte_buses = []
        for bus_id, info in metrics['bus_progress'].items():
            reporte_buses.append({
                'Número Interno': bus_id,
                'PPU': info.get('ppu', 'N/A'),
                'Terminal': info.get('terminal', 'N/A'),
                'Subclase': info.get('subclase', 'N/A'),
                'Progreso': f"{info.get('progress', 0):.1f}%",
                'Estado': "Completo" if info.get('completo', False) else "Pendiente",
                'Normas Faltantes': len(info.get('normas_faltantes', [])),
                'Detalle': ", ".join(info.get('normas_faltantes', [])[:3]) + ("..." if len(info.get('normas_faltantes', [])) > 3 else "")
            })
        
        # Ordenar por progreso
        reporte_buses.sort(key=lambda x: float(x['Progreso'].strip('%')), reverse=True)
        
        # Crear dataframe
        if reporte_buses:
            reporte_df = pd.DataFrame(reporte_buses)
            
            # Formato condicional
            def highlight_estado(val):
                if val == 'Completo':
                    return 'background-color: #d4edda; color: #155724'
                else:
                    return 'background-color: #f8d7da; color: #721c24'
            
            def highlight_progress(val):
                progress = float(val.strip('%'))
                if progress >= 90:
                    return 'background-color: #d4edda; color: #155724'
                elif progress >= 70:
                    return 'background-color: #fff3cd; color: #856404'
                else:
                    return 'background-color: #f8d7da; color: #721c24'
            
            styled_df = reporte_df.style.applymap(highlight_estado, subset=['Estado']).applymap(highlight_progress, subset=['Progreso'])
            st.dataframe(styled_df, use_container_width=True)
            
            # Opción para exportar
            try:
                # Intentar guardar con xlsxwriter
                buffer = io.BytesIO()
                try:
                    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                        reporte_df.to_excel(writer, sheet_name='Reporte Completo', index=False)
                    buffer.seek(0)
                    
                    st.download_button(
                        label="📄 Descargar Reporte Completo",
                        data=buffer,
                        file_name=f"reporte_completo_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                        mime="application/vnd.ms-excel"
                    )
                except ImportError:
                    # Si xlsxwriter no está disponible, convertir a CSV
                    csv = reporte_df.to_csv(index=False)
                    b64 = base64.b64encode(csv.encode()).decode()
                    href = f'<a href="data:file/csv;base64,{b64}" download="reporte_completo_{datetime.now().strftime("%Y%m%d_%H%M")}.csv">📄 Descargar como CSV</a>'
                    st.markdown(href, unsafe_allow_html=True)
                    st.warning("La biblioteca xlsxwriter no está instalada. Se ha generado un archivo CSV en su lugar. Para poder descargar en formato Excel, instala xlsxwriter con: pip install xlsxwriter")
            except Exception as e:
                st.error(f"Error al exportar datos: {str(e)}")
                st.info("Sugerencia: Instale xlsxwriter con el comando: pip install xlsxwriter")
        
        # Lista de buses con progreso
        st.markdown('<h3 class="sub-header">Detalle por Bus</h3>', unsafe_allow_html=True)
        
        # Opciones de filtro para la lista de buses
        col1, col2 = st.columns(2)
        with col1:
            filter_option = st.selectbox(
                "Filtrar buses por estado",
                ["Todos", "Completos", "Incompletos", "Críticos (menos de 50%)"]
            )
        
        with col2:
            sort_option = st.selectbox(
                "Ordenar por",
                ["Número Interno", "Progreso (mayor a menor)", "Progreso (menor a mayor)"]
            )
        
        # Filtrar y ordenar la lista de buses
        bus_progress = metrics['bus_progress']
        bus_list = list(bus_progress.items())
        
        if filter_option == "Completos":
            bus_list = [(bus_id, data) for bus_id, data in bus_list if data['progress'] == 100]
        elif filter_option == "Incompletos":
            bus_list = [(bus_id, data) for bus_id, data in bus_list if data['progress'] < 100]
        elif filter_option == "Críticos (menos de 50%)":
            bus_list = [(bus_id, data) for bus_id, data in bus_list if data['progress'] < 50]
        
        if sort_option == "Número Interno":
            bus_list.sort(key=lambda x: x[0])
        elif sort_option == "Progreso (mayor a menor)":
            bus_list.sort(key=lambda x: x[1]['progress'], reverse=True)
        elif sort_option == "Progreso (menor a mayor)":
            bus_list.sort(key=lambda x: x[1]['progress'])
        
        # Mostrar lista paginada
        bus_list_chunked = [bus_list[i:i + 10] for i in range(0, len(bus_list), 10)]
        
        if len(bus_list_chunked) > 0:
            page_number = st.selectbox(f"Página (1-{len(bus_list_chunked)})", list(range(1, len(bus_list_chunked) + 1)))
            current_page = bus_list_chunked[page_number - 1]
            
            # Mostrar tabla con los buses de la página actual
            for bus_id, data in current_page:
                progress = data['progress']
                progress_color = "success" if progress >= 90 else "warning" if progress >= 50 else "danger"
                
                # Obtener el texto correcto para mostrar las normas
                if 'total_norms' in data:
                    # Mostrar el total considerando los "no aplica" como completados
                    normas_texto = f"Normas: {data['completed']} de {data['total_norms']} (incluye 'no aplica')"
                    # Si tenemos el conteo de aplicables, mostrarlo también
                    if 'applicable_norms' in data:
                        normas_texto += f" | Aplicables: {data['applicable_norms']}"
                else:
                    # Versión anterior (fallback)
                    normas_texto = f"Normas: {data.get('completed', 0)} de {data.get('required', 0)} instaladas"
                
                # Estado de completitud
                estado = "Completo" if data.get('completo', False) else f"Faltan {len(data.get('normas_faltantes', []))} normas"
                
                st.markdown(f"""
                <div class="card">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <h4>Bus N° {bus_id} - PPU: {data['ppu']}</h4>
                            <p>Terminal: {data['terminal']} | Tipo: {data['subclase']}</p>
                            <p>{normas_texto}</p>
                            <p style="font-weight: bold; color: {'#28A745' if data.get('completo', False) else '#DC3545'}">
                                Estado: {estado}
                            </p>
                        </div>
                        <div style="text-align: right;">
                            <div class="{progress_color}" style="font-size: 24px; font-weight: bold;">
                                {progress}%
                            </div>
                            <button id="btn_{bus_id}" onclick="showBusDetail('{bus_id}')" 
                                style="padding: 5px 10px; background-color: #007BFF; color: white; border: none; border-radius: 5px; cursor: pointer;">
                                Ver Detalle
                            </button>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Crear una sección colapsable para cada bus
                with st.expander(f"Detalles del Bus {bus_id}", expanded=False):
                    bus_info, norm_status, progress = generate_bus_report(processed_df, bus_id, norm_cols)
                    
                    col1, col2 = st.columns([1, 2])
                    
                    with col1:
                        # Información básica del bus
                        st.markdown("### Información General")
                        for key, value in bus_info.items():
                            if key not in ['NORMA INSTALADA', 'FECHA DE RENOVACION']:
                                st.markdown(f"**{key}:** {value}")
                        
                        # Detalles de instalación
                        st.markdown("### Información de Instalación")
                        st.markdown(f"**Fecha de Renovación:** {bus_info.get('FECHA DE RENOVACION', 'N/A')}")
                        st.markdown(f"**Normas Instaladas:** {bus_info.get('NORMA INSTALADA', 'N/A')}")
                        
                        # Medidor de progreso
                        st.markdown("### Progreso de Instalación")
                        st.progress(progress / 100)
                        st.markdown(f"<h2 style='text-align: center;'>{progress}%</h2>", unsafe_allow_html=True)
                    
                    with col2:
                        # Crear treemap
                        fig_treemap = create_bus_treemap(processed_df, bus_id, norm_cols)
                        if fig_treemap:
                            st.plotly_chart(fig_treemap, use_container_width=True)
                        else:
                            # Mostrar un resumen en forma de tabla
                            bus_info, norm_status, progress = generate_bus_report(processed_df, bus_id, norm_cols)
                            
                            # Contar normas por estado
                            instaladas = sum(1 for status in norm_status.values() if status == "Instalada")
                            no_aplican = sum(1 for status in norm_status.values() if status == "No Aplica")
                            pendientes = sum(1 for status in norm_status.values() if status == "Pendiente")
                            
                            st.write("**Resumen de normas por estado:**")
                            col1, col2, col3 = st.columns(3)
                            col1.metric("Instaladas", instaladas)
                            col2.metric("No Aplican", no_aplican)
                            col3.metric("Pendientes", pendientes)
                            
                            # Mostrar lista de normas pendientes
                            if pendientes > 0:
                                st.write("**Normas pendientes:**")
                                for norm, status in norm_status.items():
                                    if status == "Pendiente":
                                        st.write(f"- {norm}")
                    
                    # Resumen de normas por estado
                    normas_pendientes = [norm for norm, status in norm_status.items() if status == "Pendiente"]
                    if normas_pendientes:
                        st.markdown("### Normas Pendientes por Instalar")
                        st.markdown(f"Este bus tiene **{len(normas_pendientes)} normas pendientes** por instalar:")
                        
                        # Mostrar en formato de tabla o lista según cantidad
                        if len(normas_pendientes) <= 10:
                            for norm in normas_pendientes:
                                st.markdown(f"- ❌ **{norm}**")
                        else:
                            # Para muchas normas, usar columnas
                            cols = st.columns(3)
                            for i, norm in enumerate(normas_pendientes):
                                cols[i % 3].markdown(f"- ❌ **{norm}**")
                    else:
                        st.success("✅ Todas las normas requeridas están instaladas en este bus.")
                    
                    # Tabla de estado de normas
                    st.markdown("### Estado Completo de Normas Gráficas")
                    
                    # Crear un DataFrame para mostrar las normas
                    df_norms = pd.DataFrame(list(norm_status.items()), columns=['Norma', 'Estado'])
                    
                    # Aplicar estilo condicional
                    def highlight_status(val):
                        if val == 'Instalada':
                            return 'background-color: #d4edda; color: #155724'
                        elif val == 'No Aplica':
                            return 'background-color: #e2e3e5; color: #383d41'
                        else:
                            return 'background-color: #f8d7da; color: #721c24'
                    
                    styled_df = df_norms.style.applymap(highlight_status, subset=['Estado'])
                    st.dataframe(styled_df, use_container_width=True)
                    
                    # Generar informe HTML descargable
                    bus_report_html = generate_bus_report_html(bus_info, norm_status, progress)
                    st.markdown(get_html_download_link(bus_report_html, f"informe_bus_{bus_id}.html", "📄 Descargar Informe Detallado"), unsafe_allow_html=True)
        else:
            st.warning("No se encontraron buses que cumplan con los criterios de filtrado.")
        
        # Pie de página
        st.markdown("""
        <div class="footer">
            <p>Sistema de Control de Instalación de Normas Gráficas © 2025</p>
        </div>
        """, unsafe_allow_html=True)
    
    else:
        # Mostrar instrucciones cuando no hay archivo cargado
        st.markdown("""
        <div class="card">
            <h3>Bienvenido al Sistema de Control de Instalación de Normas Gráficas</h3>
            <p>Este sistema le permite visualizar y analizar el progreso de instalación de normas gráficas en su flota de buses.</p>
            <p>Para comenzar, cargue un archivo Excel con los datos de instalación utilizando el panel lateral.</p>
            
            <h4>Características principales:</h4>
            <ul>
                <li>Dashboard interactivo con métricas clave</li>
                <li>Análisis detallado por bus, terminal y tipo de norma</li>
                <li>Reportes personalizados y exportables</li>
                <li>Identificación de buses en estado crítico</li>
                <li>Filtros avanzados para análisis específicos</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        # Mostrar ejemplo de dashboard
        st.markdown('<h3 class="sub-header">Vista previa del dashboard</h3>', unsafe_allow_html=True)
        st.image("https://i.imgur.com/NvNGJO3.png", caption="Ejemplo de visualización del dashboard")

if __name__ == "__main__":
    main()
