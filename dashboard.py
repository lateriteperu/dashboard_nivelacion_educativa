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

# @st.cache_data
def load_data():
    try:
        df = pd.read_csv('plus_petrol_2026_pii_grupal.csv')
        
        # 1. Definimos el mapa de columnas
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
            'pct_puntaje': 'Pct_Puntaje'
        }

        # 2. Renombramos las columnas PRIMERO
        df = df.rename(columns=column_map)

        # 2. REEMPLAZO ROBUSTO:
        # Convertimos a minúsculas, quitamos espacios extra y reemplazamos
        df['Sesion'] = df['Sesion'].str.strip() # Limpia espacios invisibles
        
        # Usamos un reemplazo directo según lo que veo en tu captura:
        df['Sesion'] = df['Sesion'].replace('Sesión de reforzamiento', 'Sesión regular')
        
        # Por si acaso existiera con la R mayúscula también:
        df['Sesion'] = df['Sesion'].replace('Sesión de Reforzamiento', 'Sesión regular')
        
        # 4. Procesamos fechas
        df['Date'] = pd.to_datetime(df['Date'], format='%d%b%Y', errors='coerce')
        df = df.dropna(subset=['Date'])
        
        # 5. Corregimos escalas de porcentajes
        cols_pct = ['Pct_Asistencia','Pct_Logro','Pct_Inicio','Pct_Proceso','Pct_Puntaje']
        for col in cols_pct:
            if col in df.columns:
                # Si el valor máximo es <= 1 (ej: 0.8), lo llevamos a escala 100
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

    # --- TAB 1: ASISTENCIA ---
    with tab1:
        st.header("📅 Resumen de Asistencia")
        if not df_filtered.empty:
            # Cálculos
            df_sesiones_unicas = df_filtered.groupby(['Date', 'Institucion', 'Sesion'])['Horas'].first().reset_index()
            num_sesiones = len(df_sesiones_unicas)
            horas_totales = df_sesiones_unicas['Horas'].sum()
            total_asistentes = df_filtered['Asistencia_Absoluta'].sum()
            total_inscritos = df_filtered['Alumnos'].sum()
            asistencia_global = (total_asistentes / total_inscritos * 100) if total_inscritos > 0 else 0
            prom_niños = total_asistentes / num_sesiones if num_sesiones > 0 else 0
            
            # Métricas
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Número de sesiones", num_sesiones)
            m2.metric("Horas efectivas ⏱️", f"{horas_totales:.1f} h")
            m3.metric("Promedio asistencia", f"{prom_niños:.1f} alum.")
            m4.metric("Asistencia Global (%)", f"{asistencia_global:.1f}%")

            st.markdown("---")
            st.subheader("👥 Tendencia Diaria de Asistencia")
            df_asistencia_diaria = df_filtered.groupby(['Date', 'Grado'])['Pct_Asistencia'].mean().reset_index()
            fig_asist = px.bar(df_asistencia_diaria, x='Date', y='Pct_Asistencia', color='Grado', barmode='group', text_auto='.1f')
            fig_asist.update_layout(yaxis_range=[0, 105], yaxis_title="Asistencia (%)")
            st.plotly_chart(fig_asist, use_container_width=True)

            
            # --- GRÁFICO DE ASISTENCIA CON PROMEDIO MÓVIL (COMPARATIVO) ---
            st.markdown("---")
            st.subheader("📈 Análisis de Tendencia (Media móvil de 3 sesiones)")

            if not df_filtered.empty:
        # 1. Crear el DataFrame base según la selección
               if sel_inst == 'Todas':
              # Datos por cada institución
                  df_plot = df_filtered.groupby(['Date', 'Institucion'])['Pct_Asistencia'].mean().reset_index()
        
              # Datos del Promedio General
                  df_promedio = df_filtered.groupby('Date')['Pct_Asistencia'].mean().reset_index()
                  df_promedio['Institucion'] = 'PROMEDIO GENERAL'
        
              # Unimos ambos
                  df_final = pd.concat([df_plot, df_promedio], ignore_index=True)
               else:
              # Solo el colegio seleccionado
                   df_final = df_filtered.groupby(['Date'])['Pct_Asistencia'].mean().reset_index()
                   df_final['Institucion'] = sel_inst

             # 2. Corrección de escala (0-100)
               if df_final['Pct_Asistencia'].max() <= 1.0:
                  df_final['Pct_Asistencia'] = df_final['Pct_Asistencia'] * 100

            # 3. Cálculo de Media Móvil (Importante: ordenar por fecha)
               df_final = df_final.sort_values(['Institucion', 'Date'])
               df_final['Media_Movil'] = df_final.groupby('Institucion')['Pct_Asistencia'].transform(
                   lambda x: x.rolling(window=3, min_periods=1).mean()
    )

             # 4. Creación del gráfico
             # Usamos siempre 'Institucion' en color para evitar el ValueError
               fig_comparativo = px.line(
                   df_final, 
                   x='Date', 
                   y='Media_Movil', 
                   color='Institucion',
                   line_shape='spline',
                   title="Tendencia de Asistencia: Comparativa",
                   labels={'Media_Movil': 'Asistencia (%)', 'Date': 'Fecha'},
                   color_discrete_map={'PROMEDIO GENERAL': '#333333'} 

    )

            if 'PROMEDIO GENERAL' in df_final['Institucion'].values:
                    fig_comparativo.update_traces(
                        patch={"line": {"width": 5, "dash": 'dot'}}, 
                        selector={'name': 'PROMEDIO GENERAL'}
                    )
                
            fig_comparativo.update_layout(yaxis_range=[0, 105], legend_title="Institución")
            st.plotly_chart(fig_comparativo, use_container_width=True)
 
            st.info("💡 **Interpretación:** La línea representa la tendencia suavizada. El promedio general aparece resaltado en color oscuro.")

        with st.expander("📂 Ver datos de asistencia (Raw Data)"):
                df_tabla_asist = df_filtered[['Date', 'Institucion', 'Grado', 'Asistencia_Absoluta', 'Alumnos', 'Pct_Asistencia']].copy()
                df_tabla_asist['Date'] = df_tabla_asist['Date'].dt.strftime('%d-%m-%Y')
                st.dataframe(df_tabla_asist.sort_values('Date', ascending=False), use_container_width=True, hide_index=True)

 # --- TAB 2: RENDIMIENTO ACADÉMICO ---
    with tab2:
        st.header("🎯 Rendimiento Académico (Exit Tickets)")
        if not df_filtered.empty:
            # --- 1. Cálculos de Métricas ---
            
            # Total de sesiones en el periodo filtrado (independientemente de si hubo nota o no)
            total_sesiones_periodo = df_filtered.groupby(['Date', 'Institucion', 'Sesion']).ngroups
            
            # Sesiones que SÍ tienen evaluación (Pct_Puntaje no es nulo)
            dias_con_evaluacion = df_filtered[df_filtered['Pct_Puntaje'].notna()]
            numero_aplicados = dias_con_evaluacion.groupby(['Date', 'Institucion', 'Sesion']).ngroups
            
            # CÁLCULO NUEVO: Porcentaje de aplicación
            pct_aplicacion = (numero_aplicados / total_sesiones_periodo * 100) if total_sesiones_periodo > 0 else 0
            
            # Promedio de puntaje
            prom_puntaje_raw = df_filtered['Pct_Puntaje'].mean()
            promedio_puntaje_real = prom_puntaje_raw * 100 if prom_puntaje_raw <= 1.0 else prom_puntaje_raw
            
            # Estudiantes en Logro
            total_est_eval = df_filtered[['Logro', 'Proceso', 'Inicio']].sum().sum()
            total_est_logro = df_filtered['Logro'].sum()
            promedio_logro_real = (total_est_logro / total_est_eval * 100) if total_est_eval > 0 else 0

            # --- 2. Render de Métricas (Ahora con 4 columnas) ---
            m1, m2, m3, m4 = st.columns(4)
            
            m1.metric("Sesiones con Evaluación", f"{numero_aplicados}")
            
            # La nueva métrica conectada a la anterior
            m2.metric("Sesiones con Evaluación (%)", f"{pct_aplicacion:.1f}%", 
                      help="Porcentaje de sesiones realizadas que cuentan con un Exit Ticket registrado.")
            
            m3.metric("Puntaje Promedio", f"{promedio_puntaje_real:.1f}%")
            
            m4.metric("Estudiantes en Logro", f"{promedio_logro_real:.1f}%")

            st.markdown("---")

            # 3. Gráfico de Líneas (Puntaje)
            st.subheader("🌟 Evolución de Respuestas Correctas")
            df_notas = df_filtered.groupby(['Date', 'Grado'])['Pct_Puntaje'].mean().reset_index()
            # Corrección de escala para el gráfico
            df_notas['Pct_Puntaje'] = df_notas['Pct_Puntaje'].apply(lambda x: x*100 if x <= 1.0 else x)
            
            fig_linea = px.line(df_notas, x='Date', y='Pct_Puntaje', color='Grado', markers=True)
            fig_linea.update_layout(yaxis_range=[0, 105], yaxis_title="Puntaje (%)")
            st.plotly_chart(fig_linea, use_container_width=True)

            st.markdown("---")

            # 4. Gráfico de Barras (Niveles sobre Asistentes)
            st.subheader("📊 Distribución de Niveles (Solo Asistentes)")
            df_counts = df_filtered.groupby('Date')[['Logro', 'Proceso', 'Inicio']].sum().reset_index()
            df_counts['Total'] = df_counts[['Logro', 'Proceso', 'Inicio']].sum(axis=1)
            
            for col in ['Logro', 'Proceso', 'Inicio']:
                df_counts[col] = (df_counts[col] / df_counts['Total']) * 100
            
            df_melt = df_counts.melt(id_vars='Date', value_vars=['Logro', 'Proceso', 'Inicio'], var_name='Nivel', value_name='Porcentaje')
            
            fig_barras = px.bar(
                df_melt, x='Date', y='Porcentaje', color='Nivel', barmode='stack', text_auto='.1f',
                color_discrete_map={'Logro': '#00CC96', 'Proceso': '#FECB52', 'Inicio': '#EF553B'}
            )
            fig_barras.update_layout(yaxis_range=[0, 105])
            st.plotly_chart(fig_barras, use_container_width=True)

            st.info("""💡 **Guía de Interpretación:** La barra representa el 100% de los asistentes. Logro (≥80%), Proceso (50-79%), Inicio (<50%).""")

            st.markdown("---")

            # 5. Tabla Raw Data (Tab 2)
            with st.expander("📂 Ver datos detallados de rendimiento"):
                cols_raw = ['Date', 'Institucion', 'Grado', 'Alumnos', 'Asistencia_Absoluta', 'Logro', 'Proceso', 'Inicio', 'Pct_Puntaje']
                df_t = df_filtered[cols_raw].copy()
                df_t['Date'] = df_t['Date'].dt.strftime('%d-%m-%Y')
                # Formatear el puntaje a % en la tabla
                df_t['Pct_Puntaje'] = df_t['Pct_Puntaje'].apply(lambda x: x*100 if x <= 1.0 else x)
                st.dataframe(df_t.sort_values('Date', ascending=False), use_container_width=True, hide_index=True)