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

# --- 2. CARGA DE DATOS OPTIMIZADA CON CACHÉ ---
@st.cache_data
def load_data():
    try:
        # Carga de archivos CSV correspondientes al dashboard grupal
        df_clases = pd.read_csv('plus_petrol_2026_pii_grupal_clases.csv')
        df_talleres = pd.read_csv('plus_petrol_2026_pii_grupal_talleres.csv')
        
        # Diccionario de homologación de nombres de columnas
        column_map = {
            'q8_fecha_clase': 'Date', 
            'q4_institucion': 'Institucion', 
            'q5_grado': 'Grado', 
            'q3_curso': 'Curso', 
            'asistencia': 'Asistencia_Absoluta',
            'q7_sesion': 'Sesion', 
            'pct_asistencia': 'Pct_Asistencia', 
            'pct_puntaje': 'Pct_Puntaje',
            'duration_h': 'Horas', 
            'n_alumnos': 'Alumnos',
            'logro': 'Logro', 
            'proceso': 'Proceso', 
            'inicio': 'Inicio',
            'pct_logro': 'Pct_Logro', 
            'pct_inicio': 'Pct_Inicio', 
            'pct_proceso': 'Pct_Proceso',
            'nombre_tema_A': 'nombre_tema_A',
            'nombre_tema_B': 'nombre_tema_B',
            'comment_class': 'comment_class'
        }

        def clean_and_process(df):
            # Limpieza crítica: remover espacios en blanco en la cabecera de las columnas
            df.columns = df.columns.str.strip()
            
            # Renombrar columnas según el mapeo estándar
            df = df.rename(columns=column_map)
            
            # Garantizar la existencia de la columna Horas
            if 'Horas' not in df.columns:
                df['Horas'] = 0
            
            # Procesar y formatear objetos de fecha de manera segura
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            df = df.dropna(subset=['Date'])
            
            # Normalizar textos eliminando espacios residuales en los registros
            text_cols = ['Institucion', 'Grado', 'Curso', 'Sesion']
            for col in text_cols:
                if col in df.columns:
                    df[col] = df[col].astype(str).str.strip()
            
            return df

        # Procesamos la base académica de clases
        df_clases = clean_and_process(df_clases)
        
        # 🔄 CORRECCIÓN CRÍTICA: Reemplazo nativo sobre las filas de la serie 'Sesion'
        if 'Sesion' in df_clases.columns:
            df_clases['Sesion'] = df_clases['Sesion'].replace(
                ['Sesión de reforzamiento', 'Sesión de Reforzamiento'], 'Sesión regular'
            )

        # Procesamos la base de talleres
        df_talleres = clean_and_process(df_talleres)
        
        return df_clases, df_talleres
    except Exception as e:
        st.error(f"Error crítico al cargar archivos: {e}")
        return None, None

df_raw, df_talleres_raw = load_data()

if df_raw is not None:
    # --- 3. BARRA LATERAL (FILTROS) ---
    st.sidebar.header("Filtros del Dashboard")
    
    sel_inst = st.sidebar.selectbox("Seleccionar Institución:", ['Todas'] + sorted(df_raw['Institucion'].unique().tolist()))
    sel_grado = st.sidebar.selectbox("Seleccionar Grado:", ['Todos'] + sorted(df_raw['Grado'].unique().tolist()))
    sel_curso = st.sidebar.selectbox("Seleccionar Curso:", ['Todos'] + sorted(df_raw['Curso'].unique().tolist()))
    sel_sesion = st.sidebar.selectbox("Seleccionar Tipo de Sesión:", ['Todos'] + sorted(df_raw['Sesion'].unique().tolist()))

    min_d, max_d = df_raw['Date'].min().date(), df_raw['Date'].max().date()
    sel_dates = st.sidebar.date_input("Rango de fechas:", [min_d, max_d])

    # --- BOTÓN DE LIMPIEZA DE CACHÉ ---
    st.sidebar.markdown("---")
    if st.sidebar.button("🔄 Recargar Base de Datos", use_container_width=True):
        st.cache_data.clear() 
        st.success("¡Datos actualizados!")
        st.rerun()

    # --- LÓGICA DE FILTRADO ---
    # 1. Filtramos la base Académica (Tab 1 y 2)
    df_filtered = df_raw.copy()
    if sel_inst != 'Todas': df_filtered = df_filtered[df_filtered['Institucion'] == sel_inst]
    if sel_grado != 'Todos': df_filtered = df_filtered[df_filtered['Grado'] == sel_grado]
    if sel_curso != 'Todos': df_filtered = df_filtered[df_filtered['Curso'] == sel_curso]
    if sel_sesion != 'Todos': df_filtered = df_filtered[df_filtered['Sesion'] == sel_sesion]
    if isinstance(sel_dates, list) and len(sel_dates) == 2:
        df_filtered = df_filtered[(df_filtered['Date'].dt.date >= sel_dates[0]) & (df_filtered['Date'].dt.date <= sel_dates[1])]

    # 2. Filtramos la base de Talleres (Tab 3) - Solo por Inst, Grado y Fecha
    df_talleres_filtered = df_talleres_raw.copy()
    if sel_inst != 'Todas': df_talleres_filtered = df_talleres_filtered[df_talleres_filtered['Institucion'] == sel_inst]
    if sel_grado != 'Todos': df_talleres_filtered = df_talleres_filtered[df_talleres_filtered['Grado'] == sel_grado]
    if isinstance(sel_dates, list) and len(sel_dates) == 2:
        df_talleres_filtered = df_talleres_filtered[(df_talleres_filtered['Date'].dt.date >= sel_dates[0]) & (df_talleres_filtered['Date'].dt.date <= sel_dates[1])]

# ✂️ RECESO: Excluye el periodo inactivo (17 al 31 de mayo de 2026)
        receso_inicio = pd.to_datetime('2026-05-17').date()
        receso_fin = pd.to_datetime('2026-05-31').date()
        df_filtered = df_filtered[
            ~((df_filtered['Date'].dt.date >= receso_inicio) & (df_filtered['Date'].dt.date <= receso_fin))
        ]

    st.title("📊 Panel de Monitoreo: Asistencia y Notas de Escuela de Nivelación Educativa en el Bajo Urubamba 2026 🏫")
    st.markdown("---")

    tab1, tab2, tab3 = st.tabs(["📋 Asistencia", "📝 Rendimiento Académico", "🎨 Talleres"])

    # --- TAB 1: ASISTENCIA ---
    with tab1:
        st.header("📅 Resumen de Asistencia por Sesión")
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
            m1.metric("Número de sesiones", num_sesiones, help="Número de clases dictadas. Se imparte una sesión diariamente de lunes a sábado.")
            m2.metric("Horas efectivas clase", f"{horas_totales:.1f}", help="Cada sesión regular tiene una duración de 160 minutos y cada sesión de consolidación (reforzamiento adicional), 80 minutos.")
            m3.metric("Prom.Estudiantes asistentes", f"{prom_niños:.1f}", help="Promedio de estudiantes asistentes")
            m4.metric("Asistencia Promedio por sesión (%)", f"{asistencia_global:.1f}%", help="Porcentaje de estudiantes asistentes respecto al total de estudiantes que deberían asistir por día.")

            st.markdown("---")
            st.subheader("📋 Metas de Asistencia Diaria a Sesiones Regulares")
            
     # 1. Creamos los datos manualmente 
            data_metas = {
            "LUNES": ["Nuevo Mundo - 4to (28)", "Kirigueti - 4to A (23)", "Camisea - 4to (24)", "Segakiato - 4to y 5to (14)", "**Total: 89**"],
            "MARTES": ["Nuevo Mundo - 5to (23)", "Kirigueti - 4to B (22)", "Camisea - 5to (23)", "Segakiato - 4to y 5to (14)", "**Total: 82**"],
            "JUEVES": ["Nuevo Mundo - 4to (28)", "Kirigueti - 5to A (22)", "Camisea - 4to (24)", "Segakiato - 4to y 5to (14)", "**Total: 88**"],
            "VIERNES": ["Nuevo Mundo - 5to (23)", "Kirigueti - 5to B (21)", "Camisea - 5to (23)", "Segakiato - 4to y 5to (14)", "**Total: 81**"]
            }          
            df_estatico = pd.DataFrame(data_metas)
            st.table(df_estatico)
            st.caption("Nota: Esta tabla muestra el número de estudiantes esperados diariamente. El número total de estudiantes registrados en todos los colegios hasta el 03/05/2026 es de 200. No obstante, de acuerdo al horario del proyecto de nivelación, el día lunes y jueves asiste solo 4to de secundaria, mientras que, martes y viernes, solo 5to. Hay excepciones como el colegio de Segakiato en el que hay pocos alumnos por lo cual se invita a ambos grados todos los días. En el caso de Kirigueti, debido a la afluencia de estudiantes, el lunes se enseña a 4to A, martes a 4to B, jueves a 5to A y viernes a 5to B. Los días miércoles y sábados se realizan las clases de consolidación (reforzamiento adicional) dirigida a los estudiantes que requieren más apoyo en ambos grados (4to y 5to). ")
    
            st.markdown("---")
            st.subheader("👥 Tendencia Diaria de Asistencia por Sesión")
            
            if not df_filtered.empty:
                # 1. Agrupamiento y ordenamiento cronológico
                df_asistencia_diaria = df_filtered.groupby(['Date', 'Grado']).agg({
                    'Pct_Asistencia': 'mean', 
                    'Asistencia_Absoluta': 'sum', 
                    'Alumnos': 'sum'
                }).reset_index().sort_values('Date')
                
                # 2. CORRECCIÓN DE ESCALA (0.75 -> 75)
                # Si el promedio máximo es menor o igual a 1.1, multiplicamos por 100
                if df_asistencia_diaria['Pct_Asistencia'].max() <= 1.1:
                    df_asistencia_diaria['Pct_Asistencia'] = df_asistencia_diaria['Pct_Asistencia'] * 100
                
                # 3. Configuración del gráfico
                fig_asist = px.bar(
                    df_asistencia_diaria, 
                    x='Date', 
                    y='Pct_Asistencia', 
                    color='Grado', 
                    barmode='group', 
                    text_auto='.1f', 
                    title="Porcentaje de estudiantes asistentes (%)",
                    hover_data=['Asistencia_Absoluta', 'Alumnos'],
                    labels={
                        'Asistencia_Absoluta': 'Asistentes Reales', 
                        'Alumnos': 'Total Inscritos', 
                        'Pct_Asistencia': 'Asistencia (%)'
                    } 
                )
                
                # 4. Ajustes de ejes y espaciado
                fig_asist.update_xaxes(
                    type='date', 
                    tickformat='%d-%b',
                    dtick="D1" 
                )
                
                fig_asist.update_layout(
                    yaxis_range=[0, 105], 
                    yaxis_title="Asistencia (%)",
                    bargap=0.25,         
                    bargroupgap=0.1      
                )
                
                st.plotly_chart(fig_asist, use_container_width=True)
                st.info("💡 **¿Cómo interpretar este gráfico?:** Cada barra representa el porcentaje de estudiantes asistentes respecto del total registrado en las listas de clase.")
            else:
                st.warning("No hay datos para graficar con los filtros seleccionados.")

            # --- TOTAL DE ESTUDIANTES ASISTENTES POR DÍA ---
            st.markdown("---")
            st.subheader("👥 Cantidad Total de Estudiantes Asistentes por Sesión")
            
            if not df_filtered.empty:
                # 1. Agrupamos por Fecha e Institución
                df_asistencia_total = df_filtered.groupby(['Date', 'Institucion'])['Asistencia_Absoluta'].sum().reset_index()
                
                # 2. Calculamos el total por día para las etiquetas superiores
                df_sumas_diarias = df_asistencia_total.groupby('Date')['Asistencia_Absoluta'].sum().reset_index()
                
                # 3. Creamos el gráfico base
                fig_total_asist = px.bar(
                    df_asistencia_total,
                    x='Date',
                    y='Asistencia_Absoluta',
                    color='Institucion',
                    title="Número Total de Estudiantes en Clase",
                    labels={'Asistencia_Absoluta': 'Número de Estudiantes', 'Date': 'Fecha'},
                    text_auto=True, 
                    barmode='stack'
                )

                # 4. AGREGAMOS LAS ETIQUETAS DEL TOTAL ENCIMA DE LAS BARRAS
                fig_total_asist.add_scatter(
                    x=df_sumas_diarias['Date'],
                    y=df_sumas_diarias['Asistencia_Absoluta'],
                    mode='text',
                    text=df_sumas_diarias['Asistencia_Absoluta'],
                    textposition='top center',
                    showlegend=False,
                    hoverinfo='skip' # Para que no interfiera con el hover de las barras
                )

                # 5. Configuración estética
                fig_total_asist.update_layout(
                    xaxis_title="Fecha",
                    yaxis_title="Cantidad de Estudiantes",
                    legend_title="Institución",
                    hovermode="x unified",
                    yaxis_range=[0, df_sumas_diarias['Asistencia_Absoluta'].max() * 1.15] # Espacio extra para que el texto no se corte
                )

                st.plotly_chart(fig_total_asist, use_container_width=True)
                
                st.info("💡 **Interpretación:** El número sobre cada barra indica el total global de asistentes del día. Los números internos muestran el aporte de cada institución.")
            
            # --- GRÁFICO DE ASISTENCIA CON PROMEDIO MÓVIL (COMPARATIVO) ---
            st.markdown("---")
            st.subheader("📈 Análisis de Tendencia de Asistencia Diaria (Promedio móvil de 3 sesiones)")

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
                if df_final['Pct_Asistencia'].max() <= 1.1:
                    df_final['Pct_Asistencia'] = df_final['Pct_Asistencia'] * 100

                # 3. Cálculo de Media Móvil (Importante: ordenar por fecha)
                df_final = df_final.sort_values(['Institucion', 'Date'])
                df_final['Media_Movil'] = df_final.groupby('Institucion')['Pct_Asistencia'].transform(
                    lambda x: x.rolling(window=3, min_periods=1).mean()
                )

                # 4. Definición de Colores Intensos (Personalizados)
                colores_grafico = {
                    'I.E Monseñor Javier Aris Huarte (Kirigueti)': '#FF0000', # Rojo intenso
                    'I.E Carlos Ríos Ríos (Nuevo Mundo)': '#0000FF',         # Azul fuerte
                    'I.E Juan Santos Atahualpa (Camisea)': '#008000',         # Verde
                    'I.E N° 64518 (Segakiato)': '#FFD700',                    # Amarillo/Oro
                    'PROMEDIO GENERAL': '#333333'                             # Gris oscuro
                }

                # 5. Creación del gráfico
                fig_comparativo = px.line(
                    df_final, 
                    x='Date', 
                    y='Media_Movil', 
                    color='Institucion',
                    line_shape='spline',
                    title="Porcentaje de estudiantes asistentes (Media móvil de 3 sesiones)",
                    labels={'Media_Movil': 'Asistencia (%)', 'Date': 'Fecha'},
                    color_discrete_map=colores_grafico 
                )

                if 'PROMEDIO GENERAL' in df_final['Institucion'].values:
                    fig_comparativo.update_traces(
                        patch={"line": {"width": 5, "dash": 'dot'}}, 
                        selector={'name': 'PROMEDIO GENERAL'}
                    )
                
                fig_comparativo.update_layout(yaxis_range=[0, 105], legend_title="Institución")
                st.plotly_chart(fig_comparativo, use_container_width=True)
                
                st.info("💡 **¿Cómo interpretar este gráfico?:** Las líneas representa tendencias suavizadas obtenidas a partir del promedio de los porcentajes de asistencia de las última tres sesiones. El promedio general aparece en línes punteadas oscuras.")


        with st.expander("📂 Ver datos detallados de asistencia"):
                df_tabla_asist = df_filtered[['Date', 'Institucion', 'Grado', 'Asistencia_Absoluta', 'Alumnos', 'Pct_Asistencia']].copy()
                df_tabla_asist['Date'] = df_tabla_asist['Date'].dt.strftime('%d-%m-%Y')
                st.dataframe(df_tabla_asist.sort_values('Date', ascending=False), use_container_width=True, hide_index=True)

            # =========================================================================
            # --- TABLA CONTINUA DE INCIDENCIAS DE CLASE ---
            # =========================================================================
        st.markdown("---")
        st.subheader("💬 Registro Centralizado de Incidencias y Observaciones de Aula")
            
        if 'comment_class' in df_filtered.columns:
                df_incidencias = df_filtered.copy()
                
                # Evaluamos de forma segura el texto de las observaciones de aula
                txt_class_limpio = df_incidencias['comment_class'].astype(str).str.strip()
                
                # FILTRO: Conservamos solo los días/secciones donde el docente escribió una incidencia real
                df_tabla_incidencias = df_incidencias[
                    (df_incidencias['comment_class'].notna()) & 
                    (txt_class_limpio != "") & 
                    (txt_class_limpio != "nan") & 
                    (txt_class_limpio != "None")
                ].copy()
                
                if not df_tabla_incidencias.empty:
                    # Ordenamos cronológicamente (más reciente arriba)
                    df_tabla_incidencias = df_tabla_incidencias.sort_values(by='Date', ascending=False)
                    df_tabla_incidencias['Fecha'] = df_tabla_incidencias['Date'].dt.strftime('%d-%b-%Y')
                    df_tabla_incidencias['comment_class'] = df_tabla_incidencias['comment_class'].astype(str).replace(['nan', 'None'], '')
                    
                    # Estructuramos las columnas visibles de manera clara para auditoría grupal
                    df_render_incidencias = df_tabla_incidencias[['Fecha', 'Institucion', 'Grado', 'Curso', 'Sesion', 'comment_class']].rename(columns={
                        'comment_class': 'Incidencias / Observaciones de la Clase',
                        'Sesion': 'Tipo de Sesión'
                    })
                    
                    st.write(f"Se encontraron **{len(df_render_incidencias)}** reportes grupales en el periodo seleccionado:")
                    st.dataframe(
                        df_render_incidencias,
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.info("✨ No se registraron incidencias grupales para los filtros seleccionados en este rango de fechas.")
        else:
                st.warning("⚠️ La variable 'comment_class' no fue encontrada en el archivo CSV de clases.")
            # =========================================================================

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
            
            m1.metric("Sesiones con Evaluación", f"{numero_aplicados}", help="Cada sesión es culminada con una evaluación de salida (exit ticket)")
            
            # La nueva métrica conectada a la anterior
            m2.metric("Sesiones con Evaluación (%)", f"{pct_aplicacion:.1f}%", 
                      help="Porcentaje de sesiones realizadas que cuentan con un Exit Ticket registrado.")
            
            m3.metric("Puntaje Promedio", f"{promedio_puntaje_real:.1f}%", help="Porcentaje del exit ticket completado correctamente. Cada exit ticket tiene como máximo 5 preguntas.")
            
            m4.metric("Estudiantes en Logro", f"{promedio_logro_real:.1f}%", help="Un estudiante alcanza el nivel de logro cuando responde correctamente el 80% o más del exit ticket. Por ejemplo, si la evaluación tiene 5 preguntas en total, el estudiante debe responder 4 o más para ser considerado en ese nivel.")

            st.markdown("---")

            # 3. Gráfico de Líneas (Puntaje)
            st.subheader("🌟 Evolución de Respuestas Correctas en el Exit Ticket (%)")
            df_notas = df_filtered.groupby(['Date', 'Grado'])['Pct_Puntaje'].mean().reset_index()
            # Corrección de escala para el gráfico
            df_notas['Pct_Puntaje'] = df_notas['Pct_Puntaje'].apply(lambda x: x*100 if x <= 1.0 else x)
            
            fig_linea = px.line(df_notas, x='Date', y='Pct_Puntaje', color='Grado', markers=True)
            fig_linea.update_traces(connectgaps=True)
            fig_linea.update_layout(yaxis_range=[0, 105], yaxis_title="Puntaje (%)",title="Puntaje Promedio del Exit Ticket (%)")
            st.plotly_chart(fig_linea, use_container_width=True)

            # 4. Distrubución de Resultados en el exit ticket
            st.subheader("📊 Distribución de Niveles de Resultado en el Exit Ticket ")
            
            # Función auxiliar para agrupar y formatear los temas avanzados en la misma fila/fecha
            def consolidar_temas_fecha(row):
                tema_a = str(row['nombre_tema_A']).strip() if pd.notna(row['nombre_tema_A']) else ""
                tema_b = str(row['nombre_tema_B']).strip() if pd.notna(row['nombre_tema_B']) else ""
                if tema_a and tema_b and tema_a != "nan" and tema_b != "nan" and tema_b != "":
                    return f"{tema_a} / {tema_b}"
                elif tema_a and tema_a != "nan" and tema_a != "":
                    return tema_a
                elif tema_b and tema_b != "nan" and tema_b != "":
                    return tema_b
                return "No especificado"

            df_rendimiento_temas = df_filtered.copy()
            df_rendimiento_temas['Tema_Dictado'] = df_rendimiento_temas.apply(consolidar_temas_fecha, axis=1)

            # Función para combinar de forma inteligente los temas únicos de diferentes colegios sin duplicar
            def combinar_temas_unicos(series):
                temas_limpios = [str(t).strip() for t in series if pd.notna(t) and str(t).strip() != "" and str(t).strip() != "nan" and str(t).strip() != "No especificado"]
                temas_unicos = sorted(list(set(temas_limpios)))  # Elimina duplicados si coinciden en el mismo tema
                if not temas_unicos:
                    return "No especificado"
                return ", ".join(temas_unicos)  # Los une en una sola línea de texto para el tooltip

            # Agrupamos por fecha obteniendo la suma de niveles y la combinación de todos los temas de ese día
            df_counts = df_rendimiento_temas.groupby('Date').agg({
                'Logro': 'sum',
                'Proceso': 'sum',
                'Inicio': 'sum',
                'Tema_Dictado': combinar_temas_unicos  # <-- Reemplazamos 'first' por nuestra función inteligente
            }).reset_index()
            
            df_counts['Total'] = df_counts[['Logro', 'Proceso', 'Inicio']].sum(axis=1)
            
            for col in ['Logro', 'Proceso', 'Inicio']:
                df_counts[col] = (df_counts[col] / df_counts['Total']) * 100
            
            # Hacemos el melt reteniendo la columna de la etiqueta temática consolidada
            df_melt = df_counts.melt(
                id_vars=['Date', 'Tema_Dictado'], 
                value_vars=['Logro', 'Proceso', 'Inicio'], 
                var_name='Nivel', 
                value_name='Porcentaje'
            )
            
            fig_barras = px.bar(
                df_melt, 
                x='Date', 
                y='Porcentaje', 
                color='Nivel', 
                barmode='stack', 
                text_auto='.1f', 
                title="Porcentaje de estudiantes asistentes por nivel de resultado en el Exit Ticket (%)",
                color_discrete_map={'Logro': '#00CC96', 'Proceso': '#FECB52', 'Inicio': '#EF553B'},
                hover_data={'Tema_Dictado': True, 'Porcentaje': ':.1f', 'Nivel': True, 'Date': True}
            )
            
            # Estructuración explícita de las cabeceras de información contextual emergente
            fig_barras.update_traces(
                hovertemplate="<b>Fecha:</b> %{x}<br><b>Nivel:</b> %{customdata[1]}<br><b>Porcentaje:</b> %{y:.1f}%<br><b>Tema Avanzado:</b> %{customdata[0]}<extra></extra>"
            )
            
            fig_barras.update_layout(yaxis_range=[0, 105], yaxis_title="Porcentaje (%)", xaxis_title="Fecha")
            st.plotly_chart(fig_barras, use_container_width=True)

            st.info("""💡 **Guía de Interpretación:** La barra representa el 100% de los asistentes. Logro (≥80% de respuestas correctas), Proceso (50-79% de respuestas correctas), Inicio (<50% de respuestas correctas). Pasa el cursor por encima de cualquier barra para observar qué contenido temático se impartió.""")

            st.markdown("---")

            # 5. Tabla Raw Data (Tab 2)
            with st.expander("📂 Ver datos detallados de rendimiento"):
                cols_raw = ['Date', 'Institucion', 'Grado', 'Alumnos', 'Asistencia_Absoluta', 'Logro', 'Proceso', 'Inicio', 'Pct_Puntaje']
                df_t = df_filtered[cols_raw].copy()
                df_t['Date'] = df_t['Date'].dt.strftime('%d-%m-%Y')
                # Formatear el puntaje a % en la tabla
                df_t['Pct_Puntaje'] = df_t['Pct_Puntaje'].apply(lambda x: x*100 if x <= 1.0 else x)
                st.dataframe(df_t.sort_values('Date', ascending=False), use_container_width=True, hide_index=True)

# --- TAB 3: TALLERES ---
    with tab3:
        st.header("🌈 Monitoreo de Asistencia a Talleres")
        
        colores_intensos = {
            'I.E Monseñor Javier Aris Huarte (Kirigueti)': '#FF0000', 
            'I.E Carlos Ríos Ríos (Nuevo Mundo)': '#0000FF',         
            'I.E Juan Santos Atahualpa (Camisea)': '#008000',         
            'I.E N° 64518 (Segakiato)': "#D8DF0B"                    
        }

        # Función auxiliar para formatear los temas avanzados en la misma fila/fecha del taller
        def consolidar_temas_fecha_taller(row):
            tema_a = str(row['nombre_tema_A']).strip() if ('nombre_tema_A' in row and pd.notna(row['nombre_tema_A'])) else ""
            tema_b = str(row['nombre_tema_B']).strip() if ('nombre_tema_B' in row and pd.notna(row['nombre_tema_B'])) else ""
            if tema_a and tema_b and tema_a != "nan" and tema_b != "nan" and tema_b != "":
                return f"{tema_a} / {tema_b}"
            elif tema_a and tema_a != "nan" and tema_a != "":
                return tema_a
            elif tema_b and tema_b != "nan" and tema_b != "":
                return tema_b
            return "No especificado"

        # Función para combinar de forma inteligente los temas únicos de diferentes colegios sin duplicar
        def combinar_temas_taller_unicos(series):
            temas_limpios = [str(t).strip() for t in series if pd.notna(t) and str(t).strip() != "" and str(t).strip() != "nan" and str(t).strip() != "No especificado"]
            temas_unicos = sorted(list(set(temas_limpios)))
            if not temas_unicos:
                return "No especificado"
            return ", ".join(temas_unicos)

        # --- 1. TALLER DE HABILIDADES SOCIOEMOCIONALES ---
        taller_target = "Taller de Habilidades Socioemocionales"
        df_final_talleres = df_talleres_filtered[
            df_talleres_filtered['Curso'].str.contains('Habilidades Socioemocionales', case=False, na=False) |
            df_talleres_filtered['Curso'].str.contains('Taller de Hab', case=False, na=False)
        ].copy()
        
        if not df_final_talleres.empty:
            st.subheader(f"❤️ {taller_target}")
            
            # Asignamos la columna consolidada de temas
            df_final_talleres['Tema_Taller'] = df_final_talleres.apply(consolidar_temas_fecha_taller, axis=1)
            
            # Agrupamos por Fecha E Institución incluyendo la consolidación inteligente de temas
            df_asist_plot = df_final_talleres.groupby(['Date', 'Institucion']).agg({
                'Asistencia_Absoluta': 'sum',
                'Tema_Taller': combinar_temas_taller_unicos
            }).reset_index()
            
            df_asist_plot = df_asist_plot.sort_values('Date')

            # Creamos el gráfico vinculando la variable temática al hover_data
            fig_taller = px.bar(
                df_asist_plot, 
                x='Date', 
                y='Asistencia_Absoluta',
                color='Institucion',  
                barmode='group',      
                text_auto=True,
                title="Asistencia por institución, grado y fecha",
                color_discrete_map=colores_intensos,
                hover_data={'Tema_Taller': True, 'Asistencia_Absoluta': True, 'Institucion': True, 'Date': '|%d-%b'},
                labels={
                    'Tema_Taller': 'Tema del Taller',
                    'Asistencia_Absoluta': 'Estudiantes Asistentes',
                    'Institucion': 'Institución',
                    'Date': 'Fecha'
                }
            )

            fig_taller.update_xaxes(type='date', tickformat='%d-%b', dtick="D1")
            fig_taller.update_layout(
                xaxis_title="Fecha de Sesión",
                yaxis_title="Número de Estudiantes",
                legend_title="Institución",
                bargap=0.2 
            )
            st.plotly_chart(fig_taller, use_container_width=True)
            st.info(f"💡 Visualizando datos para {sel_inst} y Grado: {sel_grado}. Pasa el cursor sobre las barras para observar el contenido temático desarrollado.")
        else:
            st.warning("⚠️ No se encontraron registros de talleres de habilidades socioemocionales para los filtros seleccionados.")

        # --- 2. TALLER DE IDENTIDAD CULTURAL ---
        taller_cultural = "Taller de Identidad Cultural"
        df_final_talleres_cultural = df_talleres_filtered[
            df_talleres_filtered['Curso'].str.contains('Identidad Cultural', case=False, na=False) |
            df_talleres_filtered['Curso'].str.contains('Identidad', case=False, na=False)
        ].copy()
        
        if not df_final_talleres_cultural.empty:
            st.markdown("---")
            st.subheader(f"🌍 {taller_cultural}")
            
            # Asignamos la columna consolidada de temas
            df_final_talleres_cultural['Tema_Taller'] = df_final_talleres_cultural.apply(consolidar_temas_fecha_taller, axis=1)
            
            # Agrupamos por Fecha E Institución incluyendo la consolidación inteligente de temas
            df_asist_plot_cultural = df_final_talleres_cultural.groupby(['Date', 'Institucion']).agg({
                'Asistencia_Absoluta': 'sum',
                'Tema_Taller': combinar_temas_taller_unicos
            }).reset_index()
            
            df_asist_plot_cultural = df_asist_plot_cultural.sort_values('Date')

            # Creamos el gráfico de identidad cultural vinculando el tema al hover_data
            fig_cultural = px.bar(
                df_asist_plot_cultural, 
                x='Date', 
                y='Asistencia_Absoluta',
                color='Institucion',  
                barmode='group',      
                text_auto=True,
                title="Asistencia por institución, grado y fecha",
                color_discrete_map=colores_intensos,
                hover_data={'Tema_Taller': True, 'Asistencia_Absoluta': True, 'Institucion': True, 'Date': '|%d-%b'},
                labels={
                    'Tema_Taller': 'Tema del Taller',
                    'Asistencia_Absoluta': 'Estudiantes Asistentes',
                    'Institucion': 'Institución',
                    'Date': 'Fecha'
                }
            )

            fig_cultural.update_xaxes(type='date', tickformat='%d-%b', dtick="D1")
            fig_cultural.update_layout(
                xaxis_title="Fecha de Sesión",
                yaxis_title="Número de Estudiantes",
                legend_title="Institución",
                bargap=0.2
            )
            st.plotly_chart(fig_cultural, use_container_width=True)
            st.info(f"💡 Visualizando datos para {sel_inst} y Grado: {sel_grado}. Pasa el cursor sobre las barras para observar el contenido temático desarrollado.")
        else:
            st.warning("⚠️ No se encontraron registros de talleres de identidad cultural para los filtros seleccionados.")