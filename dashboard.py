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
@st.cache_data
def load_data():
    try:
        # 1. Carga de archivos con los nombres actuales
        # Cambiamos 'plus_petrol_2026_pii_grupal.csv' por el nuevo nombre:
        df_clases = pd.read_csv('plus_petrol_2026_pii_grupal_clases.csv')
        df_talleres = pd.read_csv('plus_petrol_2026_pii_grupal_talleres.csv')
        
        # Mapa de columnas (Basado en tus archivos)
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
            'nombre_tema_B': 'nombre_tema_B'
        }

        def clean_and_process(df):
            # Limpieza crítica: quitar espacios en los nombres de las columnas del CSV
            df.columns = df.columns.str.strip()
            
            # Renombrar
            df = df.rename(columns=column_map)
            
            # Asegurar que la columna Horas exista (si duration_h falló, ponemos 0)
            if 'Horas' not in df.columns:
                df['Horas'] = 0
            
            # Procesar fechas
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            df = df.dropna(subset=['Date'])
            
            # Limpiar espacios en los datos de texto
            text_cols = ['Institucion', 'Grado', 'Curso', 'Sesion']
            for col in text_cols:
                if col in df.columns:
                    df[col] = df[col].astype(str).str.strip()
            
            return df

        df_clases = clean_and_process(df_clases)
        # Específico para clases acadmicas
        df_clases['Sesion'] = df_clases['Sesion'].replace(
            ['Sesión de reforzamiento', 'Sesión de Reforzamiento'], 'Sesión regular'
        )

        df_talleres = clean_and_process(df_talleres)
        
        return df_clases, df_talleres
    except Exception as e:
        st.error(f"Error crítico al cargar archivos: {e}")
        return None, None

df_raw, df_talleres_raw = load_data()

if df_raw is not None:
    # --- BARRA LATERAL ---
    st.sidebar.header("Filtros del Dashboard")
    # Los filtros solo se alimentan de la base de CLASES (Académica)
    sel_inst = st.sidebar.selectbox("Seleccionar Institución:", ['Todas'] + sorted(df_raw['Institucion'].unique().tolist()))
    sel_grado = st.sidebar.selectbox("Seleccionar Grado:", ['Todos'] + sorted(df_raw['Grado'].unique().tolist()))
    sel_curso = st.sidebar.selectbox("Seleccionar Curso:", ['Todos'] + sorted(df_raw['Curso'].unique().tolist()))
    sel_sesion = st.sidebar.selectbox("Seleccionar Tipo de Sesión:", ['Todos'] + sorted(df_raw['Sesion'].unique().tolist()))

    min_d, max_d = df_raw['Date'].min().date(), df_raw['Date'].max().date()
    sel_dates = st.sidebar.date_input("Rango de fechas:", [min_d, max_d])

    # --- LÓGICA DE FILTRADO ---
    # 1. Filtramos la base Académica (Tab 1 y 2)
    df_filtered = df_raw.copy()
    if sel_inst != 'Todas': df_filtered = df_filtered[df_filtered['Institucion'] == sel_inst]
    if sel_grado != 'Todos': df_filtered = df_filtered[df_filtered['Grado'] == sel_grado]
    if sel_curso != 'Todos': df_filtered = df_filtered[df_filtered['Curso'] == sel_curso]
    if sel_sesion != 'Todos': df_filtered = df_filtered[df_filtered['Sesion'] == sel_sesion]
    if len(sel_dates) == 2:
        df_filtered = df_filtered[(df_filtered['Date'].dt.date >= sel_dates[0]) & (df_filtered['Date'].dt.date <= sel_dates[1])]

    # 2. Filtramos la base de Talleres (Tab 3) - Solo por Inst, Grado y Fecha
    df_talleres_filtered = df_talleres_raw.copy()
    if sel_inst != 'Todas': df_talleres_filtered = df_talleres_filtered[df_talleres_filtered['Institucion'] == sel_inst]
    if sel_grado != 'Todos': df_talleres_filtered = df_talleres_filtered[df_talleres_filtered['Grado'] == sel_grado]
    if len(sel_dates) == 2:
        df_talleres_filtered = df_talleres_filtered[(df_talleres_filtered['Date'].dt.date >= sel_dates[0]) & (df_talleres_filtered['Date'].dt.date <= sel_dates[1])]

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

            st.markdown("---")

            # 4. Gráfico de Barras (Niveles sobre Asistentes)
            st.subheader("📊 Distribución de Niveles de Resultado en el Exit Ticket ")
            df_counts = df_filtered.groupby('Date')[['Logro', 'Proceso', 'Inicio']].sum().reset_index()
            df_counts['Total'] = df_counts[['Logro', 'Proceso', 'Inicio']].sum(axis=1)
            
            for col in ['Logro', 'Proceso', 'Inicio']:
                df_counts[col] = (df_counts[col] / df_counts['Total']) * 100
            
            df_melt = df_counts.melt(id_vars='Date', value_vars=['Logro', 'Proceso', 'Inicio'], var_name='Nivel', value_name='Porcentaje')
            
            fig_barras = px.bar(
                df_melt, x='Date', y='Porcentaje', color='Nivel', barmode='stack', text_auto='.1f', title="Porcentaje de estudiantes asistentes por nivel de resultado en el Exit Ticket (%)",
                color_discrete_map={'Logro': '#00CC96', 'Proceso': '#FECB52', 'Inicio': '#EF553B'}
            )
            fig_barras.update_layout(yaxis_range=[0, 105])
            st.plotly_chart(fig_barras, use_container_width=True)

            st.info("""💡 **Guía de Interpretación:** La barra representa el 100% de los asistentes. Logro (≥80% de respuestas correctas), Proceso (50-79% de respuestas correctas), Inicio (<50% de respuestas correctas).""")

            st.markdown("---")

            # 5. Avance temático por sesión
            st.markdown("---")
            st.subheader("📋 Matriz de Avance Temático por Sesión")
            
            if 'nombre_tema_A' in df_filtered.columns:
                df_curriculo = df_filtered.copy()
                
                # Mapeo de nombres cortos para optimizar espacio en las filas
                map_nombres_cortos = {
                    'I.E Monseñor Javier Aris Huarte (Kirigueti)': 'Kirigueti',
                    'I.E Carlos Ríos Ríos (Nuevo Mundo)': 'Nuevo Mundo',
                    'I.E Juan Santos Atahualpa (Camisea)': 'Camisea',
                    'I.E N° 64518 (Segakiato)': 'Segakiato'
                }
                df_curriculo['Institucion_Corta'] = df_curriculo['Institucion'].map(map_nombres_cortos).fillna(df_curriculo['Institucion'])
                
                # 1. ORDENAMOS CRONOLÓGICAMENTE PARA PODER CALCULAR EL NÚMERO CORRELATIVO CORRECTAMENTE
                df_curriculo = df_curriculo.sort_values(['Curso', 'Institucion_Corta', 'Date'])
                
                # Calculamos el N° de Clase (1, 2, 3...) de forma independiente por cada Curso y Colegio
                df_curriculo['No_Clase'] = df_curriculo.groupby(['Curso', 'Institucion_Corta']).cumcount() + 1
                
                # Función para consolidar dobles temas en la misma celda
                def consolidar_temas(row):
                    tema_a = str(row['nombre_tema_A']).strip() if pd.notna(row['nombre_tema_A']) else ""
                    tema_b = str(row['nombre_tema_B']).strip() if pd.notna(row['nombre_tema_B']) else ""
                    
                    if tema_a and tema_b and tema_a != "nan" and tema_b != "nan" and tema_b != "":
                        return f"{tema_a} / {tema_b}"
                    elif tema_a and tema_a != "nan" and tema_a != "":
                        return tema_a
                    elif tema_b and tema_b != "nan" and tema_b != "":
                        return tema_b
                    return "Sin Registrar"
                
                df_curriculo['Tema_Consolidado'] = df_curriculo.apply(consolidar_temas, axis=1)
                
                # Identificar cursos a graficar en base al filtro de la barra lateral
                cursos_a_graficar = [sel_curso] if sel_curso != 'Todos' else sorted(df_curriculo['Curso'].unique().tolist())
                
                for curso_item in cursos_a_graficar:
                    df_curso_matriz = df_curriculo[df_curriculo['Curso'] == curso_item]
                    
                    if not df_curso_matriz.empty:
                        # 2. PIVOTAMOS UTILIZANDO EL NÚMERO DE CLASE COMO COLUMNA
                        df_pivot = df_curso_matriz.pivot_table(
                            index='Institucion_Corta',
                            columns='No_Clase',
                            values='Tema_Consolidado',
                            aggfunc='first'
                        ).fillna("No dictada")
                        
                        # Mapear strings únicos a enteros para asignar colores discretos en el Heatmap
                        temas_unicos = sorted(list(set(df_curso_matriz['Tema_Consolidado'].unique().tolist() + ["No dictada"])))
                        dict_indices = {tema: i for i, tema in enumerate(temas_unicos)}
                        df_pivot_num = df_pivot.map(lambda x: dict_indices.get(x, 0))
                        
                        # Paleta de colores categórica vibrante que simula tus reportes de Excel
                        paleta_viva = px.colors.qualitative.Prism if len(temas_unicos) > 5 else px.colors.qualitative.Bold
                        
                        # 3. CREACIÓN DEL HEATMAP POR N° DE CLASE
                        fig_matriz = px.imshow(
                            df_pivot_num,
                            labels=dict(x="Número de Clase", y="Institución", color="Contenido"),
                            x=df_pivot.columns,
                            y=df_pivot.index,
                            color_continuous_scale=paleta_viva,
                            title=f"Distribución Curricular Acumulada - {curso_item}"
                        )
                        
                        # Customización del Hover para leer el tema completo al pasar el ratón
                        fig_matriz.update_traces(
                            hovertemplate="<b>Colegio:</b> %{y}<br><b>Clase N°:</b> %{x}<br><b>Tema:</b> %{customdata}<extra></extra>",
                            customdata=df_pivot.values,
                            showscale=False
                        )
                        
                        fig_matriz.update_layout(
                            xaxis_title="Número correlativo de sesión dictada",
                            yaxis_title=None,
                            xaxis=dict(dtick=1, gridcolor='white', gridwidth=3),
                            yaxis=dict(gridcolor='white', gridwidth=3),
                            plot_bgcolor='rgba(0,0,0,0)',
                            margin=dict(t=50, b=30, l=40, r=40)
                        )
                        
                        st.plotly_chart(fig_matriz, use_container_width=True)
                        
                        # Índice interactivo de temas abajo
                        st.markdown(f"**📖 Índice de temas registrados para {curso_item}:**")
                        cols_leyenda = st.columns(3)
                        for idx, tema_item in enumerate(temas_unicos):
                            if tema_item != "No dictada":
                                with cols_leyenda[idx % 3]:
                                    st.markdown(f"🔹 {tema_item}")
                
                st.info("💡 **Guía de lectura:** Las columnas representan el número correlativo de sesión del curso. Esto permite comparar el avance de todos los colegios de forma compacta e independiente de sus semanas de rotación en el calendario.")
            else:
                st.warning("⚠️ Columnas curriculares no detectadas para procesar el avance temático.")

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
        
        # Filtramos específicamente por el curso del segundo archivo
        taller_target = "Taller de Habilidades Socioemocionales"
        df_final_talleres = df_talleres_filtered[
            df_talleres_filtered['Curso'].str.contains('Habilidades Socioemocionales', case=False, na=False) |
            df_talleres_filtered['Curso'].str.contains('Taller de Hab', case=False, na=False)
        ].copy()
        
        if not df_final_talleres.empty:
            st.subheader(f"❤️{taller_target}")
            
            # 1. Agrupamos por Fecha E Institución para poder diferenciar colores
            df_asist_plot = df_final_talleres.groupby(['Date', 'Institucion'])['Asistencia_Absoluta'].sum().reset_index()
            
            # 2. Ordenamos cronológicamente
            df_asist_plot = df_asist_plot.sort_values('Date')

            # 3. Definimos la paleta de colores intensos manualmente
            # Asocia cada institución con su color correspondiente (Rojo intenso, Azul, Verde, Amarillo)
            colores_intensos = {
                'I.E Monseñor Javier Aris Huarte (Kirigueti)': '#FF0000', # Rojo intenso
                'I.E Carlos Ríos Ríos (Nuevo Mundo)': '#0000FF',         # Azul fuerte
                'I.E Juan Santos Atahualpa (Camisea)': '#008000',         # Verde
                'I.E N° 64518 (Segakiato)': "#D8DF0B"                    # Amarillo
            }

            # 4. Creamos el gráfico con los nuevos colores
            fig_taller = px.bar(
                df_asist_plot, 
                x='Date', 
                y='Asistencia_Absoluta',
                color='Institucion',  # Esto crea la leyenda y la diferencia de colores
                barmode='group',      # Las barras de colegios del mismo día se ponen una al lado de otra
                text_auto=True,
                title="Asistencia por institución, grado y fecha",
                color_discrete_map=colores_intensos # Aplicamos el mapeo de colores intensos
            )

            # Ajustes de ejes y formato
            fig_taller.update_xaxes(
                type='date',
                tickformat='%d-%b',
                dtick="D1"
            )
            
            fig_taller.update_layout(
                xaxis_title="Fecha de Sesión",
                yaxis_title="Número de Estudiantes",
                legend_title="Institución",
                bargap=0.2 # Espacio entre grupos de barras
            )

            st.plotly_chart(fig_taller, use_container_width=True)
            
            st.info(f"💡 Visualizando datos para {sel_inst} y Grado: {sel_grado}.")
        else:
            st.warning("⚠️ No se encontraron registros de talleres para los filtros seleccionados.")

        # Filtramos específicamente por el taller de identidad Cultural
        taller_target = "Taller de Identidad Cultural"
        df_final_talleres = df_talleres_filtered[
            df_talleres_filtered['Curso'].str.contains('Identidad Cultural', case=False, na=False) |
            df_talleres_filtered['Curso'].str.contains('Identidad', case=False, na=False)
        ].copy()
        
        if not df_final_talleres.empty:
            st.subheader(f"🌍{taller_target}")
            
            # 1. Agrupamos por Fecha E Institución para poder diferenciar colores
            df_asist_plot = df_final_talleres.groupby(['Date', 'Institucion'])['Asistencia_Absoluta'].sum().reset_index()
            
            # 2. Ordenamos cronológicamente
            df_asist_plot = df_asist_plot.sort_values('Date')

            # 3. Definimos la paleta de colores intensos manualmente
            # Asocia cada institución con su color correspondiente (Rojo intenso, Azul, Verde, Amarillo)
            colores_intensos = {
                'I.E Monseñor Javier Aris Huarte (Kirigueti)': '#FF0000', # Rojo intenso
                'I.E Carlos Ríos Ríos (Nuevo Mundo)': '#0000FF',         # Azul fuerte
                'I.E Juan Santos Atahualpa (Camisea)': '#008000',         # Verde
                'I.E N° 64518 (Segakiato)': "#D8DF0B"                    # Amarillo
            }

            # 4. Creamos el gráfico con los nuevos colores
            fig_taller = px.bar(
                df_asist_plot, 
                x='Date', 
                y='Asistencia_Absoluta',
                color='Institucion',  # Esto crea la leyenda y la diferencia de colores
                barmode='group',      # Las barras de colegios del mismo día se ponen una al lado de otra
                text_auto=True,
                title="Asistencia por institución, grado y fecha",
                color_discrete_map=colores_intensos # Aplicamos el mapeo de colores intensos
            )

            # Ajustes de ejes y formato
            fig_taller.update_xaxes(
                type='date',
                tickformat='%d-%b',
                dtick="D1"
            )
            
            fig_taller.update_layout(
                xaxis_title="Fecha de Sesión",
                yaxis_title="Número de Estudiantes",
                legend_title="Institución",
                bargap=0.2 # Espacio entre grupos de barras
            )

            st.plotly_chart(fig_taller, use_container_width=True)
            
            st.info(f"💡 Visualizando datos para {sel_inst} y Grado: {sel_grado}.")
        else:
            st.warning("⚠️ No se encontraron registros de talleres para los filtros seleccionados.")