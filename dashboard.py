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
        df = pd.read_csv('plus_petrol_2026_pii_grupal.csv')
        
        column_map = {
            'q8_fecha_clase': 'Date',
            'q7_sesion': 'Sesion',
            'q4_institucion': 'Institucion', 
            'q5_grado': 'Grado',
            'q3_curso': 'Curso',
            'asistencia': 'Asistencia_Absoluta',
            'duration_h': 'Horas',
            'n_alumnos': 'Alumnos',
            'logro': 'Logro',
            'proceso': 'Proceso',
            'inicio': 'Inicio',
            'pct_asistencia': 'Pct_Asistencia',
            'pct_logro': 'Pct_Logro',
            'pct_inicio': 'Pct_Inicio',
            'pct_proceso': 'Pct_Proceso',
            'pct_puntaje': 'Pct_Puntaje',
            'una_vez_asistencia': 'una_vez_asistencia',
            'pct_una_asistencia': 'Pct_Una_Asistencia',
            'nunca_asistencia': 'nunca_asistencia',
            'pct_nunca_asistencia': 'Pct_Nunca_Asistencia',
            'pct_alto_rendimiento': 'Pct_Alto_Rendimiento',
            'pct_riesgo': 'Pct_Riesgo'
        }
        
        df = df.rename(columns=column_map)
        df['Date'] = pd.to_datetime(df['Date'], format='%d%b%Y', errors='coerce')
        df = df.dropna(subset=['Date'])
        
        cols_pct = ['Pct_Asistencia','Pct_Logro','Pct_Inicio','Pct_Proceso','Pct_Puntaje','Pct_Una_Asistencia', 'Pct_Nunca_Asistencia', 'Pct_Alto_Rendimiento', 'Pct_Riesgo']
        for col in cols_pct:
            if col in df.columns:
                if df[col].max() <= 1.0:
                   df[col] = df[col] * 100
        
        return df
    except Exception as e:
        st.error(f"Error al cargar los datos: {e}")
        return None

df_raw = load_data()

if df_raw is not None:
    # --- BARRA LATERAL ---
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
        df_filtered = df_filtered[(df_filtered['Date'].dt.date >= sel_dates[0]) & (df_filtered['Date'].dt.date <= sel_dates[1])]

    st.title("📊 Panel de Monitoreo: Asistencia y Notas de Escuela de Nivelación Educativa en el Bajo Urubamba 2026 🏫")
    st.markdown("---")

    tab1, tab2 = st.tabs(["📋 Asistencia", "📝 Rendimiento Académico"])

    with tab1:
        st.header("Resumen de Asistencia")
        m1, m2, m3, m4 = st.columns(4)
        
        if not df_filtered.empty:
            df_sesiones_unicas = df_filtered.groupby(['Date', 'Institucion', 'Sesion'])['Horas'].first().reset_index()
            num_sesiones = len(df_sesiones_unicas)
            horas_totales = df_sesiones_unicas['Horas'].sum()
            total_asistentes = df_filtered['Asistencia_Absoluta'].sum()
            total_inscritos = df_filtered['Alumnos'].sum()
            asistencia_global = (total_asistentes / total_inscritos * 100) if total_inscritos > 0 else 0
            prom_niños = total_asistentes / num_sesiones if num_sesiones > 0 else 0

            m1.metric("Número de sesiones", num_sesiones)
            m2.metric("Horas efectivas ⏱️", f"{horas_totales:.1f} h")
            m3.metric("Promedio asistencia", f"{prom_niños:.1f} alum.")
            m4.metric("Promedio de asistencia (%)", f"{asistencia_global:.1f}%")

            st.markdown("---")
            st.subheader("👥Tendencia Diaria de Asistencia")
            df_asistencia_diaria = df_filtered.groupby(['Date', 'Grado'])['Pct_Asistencia'].mean().reset_index()
            fig_asist = px.bar(df_asistencia_diaria, x='Date', y='Pct_Asistencia', color='Grado', barmode='group', text_auto='.1f')
            fig_asist.update_yaxes(range=[0, 100])
            st.plotly_chart(fig_asist, use_container_width=True)
            st.info("""
                💡 **¿Cómo interpretar este gráfico?** Cada barra representa el porcentaje de estudiantes respecto del total registrado que asistieron a las clases.
            """)

            st.markdown("---")
            st.subheader("📈 Análisis de Tendencia (Media móvil de 3 sesiones)")
            df_tendencia = df_filtered.groupby('Date')['Pct_Asistencia'].mean().reset_index().sort_values('Date')
            df_tendencia['Media_Movil'] = df_tendencia['Pct_Asistencia'].rolling(window=3, min_periods=1).mean()
            fig_media_movil = px.line(df_tendencia, x='Date', y='Media_Movil', line_shape='spline')
            fig_media_movil.add_scatter(x=df_tendencia['Date'], y=df_tendencia['Pct_Asistencia'], mode='markers', name='Dato Diario')
            st.plotly_chart(fig_media_movil, use_container_width=True)
            st.info("""
                💡 **¿Cómo interpretar este gráfico?** Cada punto representa un porcentaje promedio de asistencia de las últimas 3 sesiones.
            """)

            st.markdown("---")
            # --- TABLA DE DATOS (RAW DATA) AL ESTILO LATERITE ---
        with st.expander("📂 View filtered raw data"):
            # 1. Definimos las columnas que queremos mostrar (basado en tus nombres actuales)
            cols_mostrar = [
                'Date', 'Institucion', 'Grado', 'Curso', 'Sesion', 
                'Asistencia_Absoluta', 'Alumnos', 'Pct_Asistencia', 'Horas', 
            ]
            
            # 2. Creamos una copia del dataframe filtrado con esas columnas
            # (Usamos cols_reales para que no de error si alguna columna falta)
            cols_reales = [c for c in cols_mostrar if c in df_filtered.columns]
            df_tabla = df_filtered[cols_reales].copy()
            
            # 3. Formateamos la fecha para que sea idéntica al CSV original
            df_tabla['Date'] = df_tabla['Date'].dt.strftime('%d-%m-%Y')
            
            # 4. Mostramos la tabla interactiva
            st.dataframe(
                df_tabla.sort_values('Date', ascending=False), 
                use_container_width=True,
                hide_index=True
            )
            st.caption("Esta tabla muestra los registros exactos que están alimentando los gráficos superiores.")
            
    # --- TAB 2: NOTAS ---
    with tab2:
        st.header("🎯 Rendimiento Académico (Exit Tickets)")
        
        if not df_filtered.empty:
            # --- 1. PRIMERO PREPARAMOS LOS DATOS (Esto resuelve el NameError) ---
            df_notas = df_filtered.groupby(['Date', 'Grado'])[['Pct_Logro', 'Pct_Puntaje']].mean().reset_index()
            df_notas = df_notas.sort_values('Date')
        
            # --- 1. CÁLCULOS DE MÉTRICAS ACTUALIZADOS ---
 # --- 1. CÁLCULOS DE MÉTRICAS ACTUALIZADOS ---
            
            # Métrica 1: Días con Exit Tickets Aplicados
            # Filtramos las filas que tienen puntaje y contamos cuántas fechas únicas existen
            dias_con_datos = df_filtered[df_filtered['Pct_Puntaje'].notna()]
            numero_aplicados = dias_con_datos['Date'].nunique()
            
            # Métrica 2: Puntaje Promedio (Escala corregida)
            prom_puntaje_raw = df_filtered['Pct_Puntaje'].mean()
            promedio_puntaje_real = prom_puntaje_raw * 100 if prom_puntaje_raw <= 1.0 else prom_puntaje_raw
            
            # Métrica 3: % de Estudiantes en Logro (Ponderado sobre el total de alumnos)
            total_estudiantes_evaluados = df_filtered[['Logro', 'Proceso', 'Inicio']].sum().sum()
            total_estudiantes_logro = df_filtered['Logro'].sum()
            promedio_logro_real = (total_estudiantes_logro / total_estudiantes_evaluados * 100) if total_estudiantes_evaluados > 0 else 0

            # --- 2. VISUALIZACIÓN EN COLUMNAS ---
            m1, m2, m3 = st.columns(3)
            
            m1.metric(
                label="Número de Exit Tickets Aplicados", 
                value=f"{numero_aplicados}", # Ahora refleja días/sesiones únicas
                help="Cada sesión es finalizada con una evaluación de salida (exit ticket)."
            )
            
            m2.metric(
                label="Respuestas correctas (% Exit Ticket)", 
                value=f"{promedio_puntaje_real:.1f}%",
                help="Porcentaje del exit ticket respondido correctamente. El exit ticket tiene usualmente entre 4 y 5 preguntas."
            )
            
            m3.metric(
                label="Estudiantes con Nivel Logro", 
                value=f"{promedio_logro_real:.1f}%",
                help="Porcentaje total de alumnos que resolvieron correctamente el 80% o más del exit ticket (nivel logro)."
            )

            st.markdown("---")           


# --- 3. SECCIÓN: LOGRO (Línea de tiempo) ---
        st.subheader("🌟 Respuestas Correctas en el Exit Ticket (% total de preguntas)")
        
        fig_puntaje = px.line(
            df_notas, # Ahora df_notas ya existe
            x='Date', 
            y='Pct_Puntaje', 
            color='Grado',
            title='Porcentaje Respuestas Correctas',
            markers=True,
            labels={'Pct_Puntaje': 'Puntaje (%)'}
        )
        
        fig_puntaje.update_traces(connectgaps=True)
        st.plotly_chart(fig_puntaje, use_container_width=True)
        st.info("""
                💡 **¿Cómo interpretar este gráfico?** Cada punto representa el porcentaje promedio de preguntas respondidas correctamente del exit ticket.
            """)
        st.markdown("---")
        
            # --- 5. SECCIÓN: DISTRIBUCIÓN DE NIVELES (Barras apiladas) ---
        st.subheader("📊 Distribución de Niveles de Aprendizaje ")
        
        if not df_filtered.empty:
            # 1. Agrupamos y promediamos
            df_niveles = df_filtered.groupby('Date')[['Pct_Logro', 'Pct_Proceso', 'Pct_Inicio']].mean().reset_index()
            
            # 2. Calculamos los No Evaluados (Diferencia para llegar a 100)
            # Usamos fillna(0) solo para el cálculo matemático
            df_niveles['Pct_No_Evaluados'] = 100 - df_niveles[['Pct_Logro', 'Pct_Proceso', 'Pct_Inicio']].sum(axis=1)
            df_niveles['Pct_No_Evaluados'] = df_niveles['Pct_No_Evaluados'].clip(lower=0)
            
            # 3. Transformamos a formato largo
            df_melted = df_niveles.melt(
                id_vars='Date', 
                value_vars=['Pct_Logro', 'Pct_Proceso', 'Pct_Inicio', 'Pct_No_Evaluados'],
                var_name='Estado', 
                value_name='Porcentaje'
            )

            # Limpiamos los nombres: quitamos 'Pct_' y cambiamos guiones bajos por espacios
            df_melted['Estado'] = df_melted['Estado'].str.replace('Pct_', '').str.replace('_', ' ')
            
            # REPARACIÓN CRÍTICA: Eliminamos cualquier fila que haya quedado con Porcentaje nulo
            df_melted = df_melted.dropna(subset=['Porcentaje'])

            # 4. Creación del gráfico con manejo de excepciones
            try:
                fig_niveles = px.bar(
                    df_melted, 
                    x='Date', 
                    y='Porcentaje', 
                    color='Estado',
                    barmode='stack',
                    title="Composición Total del Salón (Evaluados vs. No Evaluados)",
                    # Asegúrate de que estos nombres coincidan con el .replace de arriba
                    color_discrete_map={
                        'Logro': '#00CC96',       # Verde
                        'Proceso': '#FECB52',     # Amarillo
                        'Inicio': '#EF553B',      # Rojo
                        'No Evaluados': '#D3D3D3' # Gris
                    },
                    text_auto='.1f'
                )
                
                fig_niveles.update_traces(textposition='inside', insidetextanchor='middle')
                fig_niveles.update_layout(
                    xaxis_tickformat='%d %b',
                    bargap=0.3,
                    yaxis_range=[0, 105],
                    legend_title="Condición"
                )
                
                st.plotly_chart(fig_niveles, use_container_width=True)
                st.info("""💡 **Guía de Interpretación:** Cada columna representa el universo total de estudiantes registrados. Los niveles se definen según el desempeño en el *Exit Ticket*:
                ***Logro:** Estudiantes con 80% o más de respuestas correctas.
                ***En Proceso:** Estudiantes con un desempeño entre el 50% y 79%.
                ***Inicio:** Estudiantes con un desempeño inferior al 50%.
                """)
            except Exception as e:
                st.error(f"Error al generar el gráfico de barras: {e}")