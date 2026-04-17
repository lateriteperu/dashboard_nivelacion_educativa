import streamlit as st
import pandas as pd
import plotly.express as px

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Monitoreo de Asistencia y Notas",
    page_icon="📚",
    layout="wide"
)

# --- PROTECCIÓN POR CONTRASEÑA ---
def check_password():
    def password_entered():
        if st.session_state["password"] == st.secrets["PASSWORD"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if st.session_state.get("password_correct", False):
        return True

    st.text_input("Ingrese su contraseña", type="password", on_change=password_entered, key="password")
    if "password_correct" in st.session_state and not st.session_state["password_correct"]:
        st.error("Contraseña incorrecta")
    return False

if not check_password():
    st.stop()

# --- CARGA DE DATOS ---
@st.cache_data
def load_data():
    try:
        # Cargamos tu archivo local exacto
        df = pd.read_csv('plus_petrol_2026_pii_grupal.csv')
        
        # Mapeo corregido según tu CSV real
        column_map = {
            'q8_fecha_clase': 'Date',
            'q7_sesion': 'Sesion',
            'q4_institucion': 'Institucion', 
            'q5_grado': 'Grado',
            'q3_curso': 'Curso',
            'asistencia': 'Asistencia_Absoluta',
            'duration_h': 'Horas',
            'pct_asistencia': 'Pct_Asistencia',
            'pct_logro': 'Pct_Logro',
            'pct_inicio': 'Pct_Inicio',
            'pct_puntaje': 'Pct_Puntaje',
            'pct_una_asistencia': 'Pct_Una_Asistencia',
            'pct_nunca_asistencia': 'Pct_Nunca_Asistencia',
            'pct_alto_rendimiento': 'Pct_Alto_Rendimiento',
            'pct_riesgo': 'Pct_Riesgo'
        }
        
        df = df.rename(columns=column_map)
        
        # Convertir fecha (maneja el formato 06apr2026)
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df = df.dropna(subset=['Date'])
        
        # Convertir decimales a porcentajes (0.36 -> 36%)
        for col in ['Pct_Asistencia', 'Pct_Logro', 'Pct_Inicio','Pct_Puntaje','Pct_Una_Asistencia', 'Pct_Nunca_Asistencia', 'Pct_Alto_Rendimiento', 'Pct_Riesgo']:
            if col in df.columns:
                df[col] = df[col] * 100
        
        return df
    except Exception as e:
        st.error(f"Error al cargar los datos: {e}")
        return None

df_raw = load_data()

if df_raw is not None:
    # --- BARRA LATERAL (FILTROS) ---
    st.sidebar.header("Filtros del Dashboard")
    
    sel_inst = st.sidebar.selectbox("Seleccionar Institución:", ['Todas'] + sorted(df_raw['Institucion'].unique().tolist()))
    sel_grado = st.sidebar.selectbox("Seleccionar Grado:", ['Todos'] + sorted(df_raw['Grado'].unique().tolist()))
    sel_curso = st.sidebar.selectbox("Seleccionar Curso:", ['Todos'] + sorted(df_raw['Curso'].unique().tolist()))
    sel_sesion = st.sidebar.selectbox("Seleccionar Tipo de Sesión :", ['Todos'] + sorted(df_raw['Sesion'].unique().tolist()))
    

    min_d, max_d = df_raw['Date'].min().date(), df_raw['Date'].max().date()
    sel_dates = st.sidebar.date_input("Rango de fechas:", [min_d, max_d])

    # --- LÓGICA DE FILTRADO ---
    df_filtered = df_raw.copy()

if sel_inst != 'Todas':
    df_filtered = df_filtered[df_filtered['Institucion'] == sel_inst]
if sel_grado != 'Todos':
    df_filtered = df_filtered[df_filtered['Grado'] == sel_grado]
if sel_curso != 'Todos':
    df_filtered = df_filtered[df_filtered['Curso'] == sel_curso]
if sel_sesion != 'Todos':
    df_filtered = df_filtered[df_filtered['Sesion'] == sel_sesion]

if len(sel_dates) == 2:
    df_filtered = df_filtered[
        (df_filtered['Date'].dt.date >= sel_dates[0]) & 
        (df_filtered['Date'].dt.date <= sel_dates[1])
    ]

    st.title("📊 Panel de Monitoreo: Asistencia y Notas de Escuela de Nivelación Educativa en el Bajo Urubamba 2026 🏫")
    st.markdown("---")

    tab1, tab2 = st.tabs(["📋 Asistencia", "📝 Rendimiento Académico"])

    # --- TAB 1: ASISTENCIA ---
with tab1:
        st.header("Resumen de Asistencia")
        m1, m2, m3, m4 = st.columns(4)
        
        if not df_filtered.empty:
            # --- PASO 1: Identificar Sesiones Únicas ---
            # Agrupamos por Fecha, Institución y Tipo de Sesión. 
            # Esto garantiza que si en un mismo día hubo Reforzamiento y Consolidación, se cuenten como 2.
            # Pero si hay varios grados en la misma sesión, se cuenten como 1.
            df_sesiones_unicas = df_filtered.groupby(['Date', 'Institucion', 'Sesion'])['Horas'].first().reset_index()
            
            # --- PASO 2: Cálculos Reales ---
            num_sesiones = len(df_sesiones_unicas)
            horas_totales = df_sesiones_unicas['Horas'].sum()
            
            # --- PASO 3: Asistencia Global -----------------
            total_asistentes = df_filtered['Asistencia_Absoluta'].sum()
            total_inscritos = df_filtered['n_alumnos'].sum()
            asistencia_global = (total_asistentes / total_inscritos * 100) if total_inscritos > 0 else 0
            
            # Promedio de niños por sesión (opcional)
            prom_niños = total_asistentes / num_sesiones if num_sesiones > 0 else 0
        else:
            num_sesiones = 0
            horas_totales = 0
            asistencia_global = 0
            prom_niños = 0

        # --- MOSTRAR MÉTRICAS ---
        m1.metric("Número de sesiones", num_sesiones)
        m2.metric("Horas efectivas ⏱️", f"{horas_totales:.1f} h")
        m3.metric("Promedio asistencia", f"{prom_niños:.1f} alum.")
        m4.metric("Promedio de asistencia (%)", f"{asistencia_global:.1f}%")

        st.markdown("---")
        st.subheader("👥Tendencia Diaria de Asistencia")

        df_asistencia_diaria = df_filtered.groupby(['Date', 'Grado'])['Pct_Asistencia'].mean().reset_index()
        # Gráfico con leyenda de Grado (4to/5to) 
        fig_asist = px.bar(
            df_asistencia_diaria, # Usamos la nueva tabla agrupada
            x='Date', 
            y='Pct_Asistencia', 
            color='Grado',
            title='Porcentaje de Asistencia por Día (%)',
            labels={'Pct_Asistencia': 'Asistencia (%)', 'Date': 'Día'},
            barmode='group' # Muestra las barras de 4to y 5to una al lado de la otra
        )
        
        # Forzamos a que el eje Y siempre llegue al 100% para que sea fácil de leer
        fig_asist.update_yaxes(range=[0, 100])
        
        st.plotly_chart(fig_asist, use_container_width=True)

        st.info("""
            💡 **¿Cómo leer este gráfico?** Las **barras** muestran el porcentaje de estudiantes que asistieron a clases diariamente.
        """)

        # --- ANÁLISIS DE TENDENCIA REAL MEDIA MÓVIL DE 3 SESIONES ---
        st.markdown("---")
        st.subheader("📈 Análisis de Tendencia (Media móvil de 3 sesiones)")
        
        # 1. Preparamos los datos ordenados por fecha
        # Agrupamos por fecha (promediando instituciones) para tener una sola línea
        df_tendencia = df_filtered.groupby('Date')['Pct_Asistencia'].mean().reset_index().sort_values('Date')
        
        # 2. Calculamos la Media Móvil (ventana de 3 sesiones)
        # Usamos min_periods=1 para que empiece a graficar desde el primer día
        df_tendencia['Media_Movil'] = df_tendencia['Pct_Asistencia'].rolling(window=3, min_periods=1).mean()
        
        # 3. Creamos el gráfico comparativo
        fig_media_movil = px.line(
            df_tendencia, 
            x='Date', 
            y='Media_Movil',
            title='Evolución Suavizada de la Asistencia (Promedio de 3 sesiones)',
            labels={'Media_Movil': 'Tendencia (%)', 'Date': 'Fecha'},
            line_shape='spline', # Esto hace que la línea sea curva y elegante
            render_mode='svg'
        )
        
        # Añadimos los puntos reales con transparencia para comparar
        fig_media_movil.add_scatter(
            x=df_tendencia['Date'], 
            y=df_tendencia['Pct_Asistencia'], 
            mode='markers', 
            name='Dato Diario',
            marker=dict(color='rgba(135, 206, 250, 0.5)', size=8)
        )
        
        # Ajustamos el eje Y al 100%
        fig_media_movil.update_yaxes(range=[0, 105])
        
        st.plotly_chart(fig_media_movil, use_container_width=True)
        
        st.info("""
            💡 **¿Cómo leer este gráfico?** La **línea continua** muestra la dirección del proyecto, ignorando caídas o subidas bruscas de un solo día. 
            Si la línea sube significa que el compromiso está en proceso de mejora.
        """)

        st.subheader("🚩 Análisis de Permanencia y Deserción")
        col_fid1, col_fid2 = st.columns(2)
        
        # Agrupamos por fecha para ver la evolución de estos indicadores
        df_fidelidad_diaria = df_filtered.groupby('Date')[['Pct_Nunca_Asistencia', 'Pct_Una_Asistencia']].mean().reset_index()
        
        with col_fid1:
            fig_nunca_daily = px.bar(
                df_fidelidad_diaria,
                x='Date', 
                y='Pct_Nunca_Asistencia',
                title="Evolución: % Estudiantes que NUNCA asistieron",
                labels={'Date': 'Fecha', 'Pct_Nunca_Asistencia': 'Porcentaje (%)'},
                color_discrete_sequence=['#ef553b'],
                text_auto='.1f'
            )
            fig_nunca_daily.update_yaxes(range=[0, 100])
            fig_nunca_daily.update_layout(xaxis_tickformat='%d %b')
            st.plotly_chart(fig_nunca_daily, use_container_width=True)
            st.caption("🔍 Un descenso en estas barras significa que estamos captando alumnos nuevos.")

        with col_fid2:
            fig_una_daily = px.bar(
                df_fidelidad_diaria,
                x='Date', 
                y='Pct_Una_Asistencia',
                title="Evolución: % Estudiantes con RIESGO de Abandono",
                labels={'Date': 'Fecha', 'Pct_Una_Asistencia': 'Porcentaje (%)'},
                color_discrete_sequence=['#fecb52'],
                text_auto='.1f'
            )
            fig_una_daily.update_yaxes(range=[0, 100])
            fig_una_daily.update_layout(xaxis_tickformat='%d %b')
            st.plotly_chart(fig_una_daily, use_container_width=True)
            st.caption("🔍 Monitorea si este grupo crece; son alumnos que asistieron una vez y no volvieron.")

        st.markdown("---")

        with st.expander("📂 Ver detalle de datos filtrados (Raw Data)"):
            # Seleccionamos las columnas más importantes para no saturar la vista
            cols_mostrar = [
                'Date', 'Institucion', 'Grado', 'Curso', 'Sesion', 
                'Asistencia_Absoluta', 'Alumnos', 'Pct_Asistencia', 'Horas', 'una_vez_asistencia', 'Pct_Una_Asistencia', 'nunca_asistencia', 'Pct_Nunca_Asistencia', 
            ]
            
            # Formateamos la fecha para que se vea mejor en la tabla
            df_tabla = df_filtered[cols_mostrar].copy()
            df_tabla['Date'] = df_tabla['Date'].dt.strftime('%d-%m-%Y')
            
            st.dataframe(
                df_tabla.sort_values('Date', ascending=False), 
                use_container_width=True,
                hide_index=True
            )
            st.caption("Esta tabla muestra los registros exactos que están alimentando los gráficos superiores.")

    # --- TAB 2: NOTAS ---
with tab2:
        st.header("🎯 Rendimiento Académico (Exit Tickets)")
        
        # 1. Cálculos de los indicadores resumen
        # Promedio general de puntaje
        promedio_puntaje = df_filtered['Pct_Puntaje'].mean() if not df_filtered.empty else 0
        
        # Promedio de nivel logro
        promedio_logro = df_filtered['Pct_Logro'].mean() if not df_filtered.empty else 0
        
        # Cálculo de nivel NO logrado (el complemento del logro)
        promedio_no_logro = 100 - promedio_logro if not df_filtered.empty else 0

        # 2. Mostramos las métricas en 3 columnas
        m1, m2, m3 = st.columns(3)
        
        m1.metric("Puntaje Promedio (% Exit ticket)", f"{promedio_puntaje:.1f}%")
        m2.metric("Nivel Logro - Alcanzado (% Estudiantes)", f"{promedio_logro:.1f}%")
        m3.metric("Nivel Logro - No Alcanzado (% Estudiantes)", f"{promedio_no_logro:.1f}%", delta_color="inverse")

        st.markdown("---") # Separador visual
        
        # 1. Preparación de datos (Igual que antes)
        df_notas = df_filtered.groupby(['Date', 'Grado'])[['Pct_Logro', 'Pct_Puntaje']].mean().reset_index()
        df_notas = df_notas.sort_values('Date')

        # --- SECCIÓN 1: LOGRO (ARRIBA) ---
        st.subheader(" 🎯 Porcentaje de Logro en Exit Ticket (%)")
        fig_logro = px.line(
            df_notas, 
            x='Date', 
            y='Pct_Logro', 
            color='Grado',
            title='% Estudiantes con Nivel de Logro',
            markers=True,
            labels={'Pct_Logro': 'Logro (%)'}
        )
        fig_logro.update_traces(connectgaps=True)
        st.plotly_chart(fig_logro, use_container_width=True)
        
        st.info("""
            💡 **¿Cómo leer este gráfico?** Los **puntos** representan el porcentaje de estudiantes que alcanzaron el nivel de logro. 
            Para esto, el estudiante debe responder el 80% o más de la evaluación correctamente.
        """)

        # Una línea divisoria para separar los dos análisis
        st.markdown("---")

        # --- SECCIÓN 2: PUNTAJE (ABAJO) ---
        st.subheader("🌟Puntaje del Exit Ticket (%)")
        fig_puntaje = px.line(
            df_notas, 
            x='Date', 
            y='Pct_Puntaje', 
            color='Grado',
            title='Promedio de Respuestas Correctas',
            markers=True,
            labels={'Pct_Puntaje': 'Puntaje (%)'}
        )
        fig_puntaje.update_traces(connectgaps=True)
        st.plotly_chart(fig_puntaje, use_container_width=True)

        st.info("""
            💡 **¿Cómo leer este gráfico?** Los **puntos** representan el porcentaje promedio del exit ticket completado correctamente. Para alcanzar el nivel de logro por sesión, el salón debería responder, en promedio, el 80% o más de la evaluación correctamente.
        """)