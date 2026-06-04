import streamlit as st
import pandas as pd
import plotly.express as px

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Seguimiento Individual- Laterite",
    page_icon="👤",
    layout="wide"
)

# --- 1. PROTECCIÓN POR CONTRASEÑA ---
def check_password():
    def password_entered():
        if st.session_state["password"] == st.secrets["PASSWORD"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if st.session_state.get("password_correct", False):
        return True

    st.title("🔐 Acceso al Sistema de Seguimiento")
    st.text_input("Ingrese la contraseña del programa:", type="password", on_change=password_entered, key="password")
    if "password_correct" in st.session_state and not st.session_state["password_correct"]:
        st.error("😕 Contraseña incorrecta. Intente de nuevo.")
    return False

if check_password():

    # --- 2. CARGA DE DATOS ---
    @st.cache_data
    def load_data():
        try:
            # Uso de 'utf-8-sig' para proteger la integridad de tildes y caracteres especiales
            df = pd.read_csv("plus_petrol_2026_pii_individual.csv", encoding='utf-8-sig')
            
            # Limpieza crítica de espacios ocultos en los nombres de las columnas
            df.columns = df.columns.str.strip()
            
            # Renombramos q8_fecha_clase a Date para compatibilidad con filtros temporales
            df = df.rename(columns={'q8_fecha_clase': 'Date'})
            
            # Convertir a datetime de forma segura
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            df = df.dropna(subset=['Date'])
            
            return df
        except Exception as e:
            st.error(f"Error al cargar el archivo CSV: {e}")
            return None

    df_raw = load_data()

    if df_raw is not None:
        # --- 3. BARRA LATERAL (FILTROS) ---
        st.sidebar.header("Filtros de Búsqueda")
        
        sel_inst = st.sidebar.selectbox("Institución:", ['Todas'] + sorted(df_raw['q4_institucion'].unique().astype(str).tolist()))
        sel_grado = st.sidebar.selectbox("Grado:", ['Todos'] + sorted(df_raw['q5_grado'].unique().astype(str).tolist()))
        
        # --- FILTRO POR SECCIÓN INTELIGENTE ---
        if sel_inst != 'Todas':
            secciones_disponibles = df_raw[df_raw['q4_institucion'] == sel_inst]['q6_seccion'].dropna().unique()
        else:
            secciones_disponibles = df_raw['q6_seccion'].dropna().unique()

        if len(secciones_disponibles) > 0:
            opciones_seccion = ['Todas'] + sorted(secciones_disponibles.astype(str).tolist())
            sel_seccion = st.sidebar.selectbox("Sección:", opciones_seccion)
        else:
            sel_seccion = 'Todas'
            st.sidebar.info("Este colegio cuenta con una única sección por grado.")

        # --- FILTRO CURSO AMIGABLE ("4" -> "Taller de Identidad Cultural") ---
        cursos_reales = sorted(df_raw['q3_curso'].unique().astype(str).tolist())
        opciones_curso_visual = []
        for curso in cursos_reales:
            if curso.strip() == '4':
                opciones_curso_visual.append("Taller de Identidad Cultural")
            else:
                opciones_curso_visual.append(curso)
        sel_curso = st.sidebar.selectbox("Curso:", ['Todos'] + opciones_curso_visual)
        
        # --- RANGO DE FECHAS ---
        min_date = df_raw['Date'].min().date()
        max_date = df_raw['Date'].max().date()
        sel_dates = st.sidebar.date_input("Rango de Fechas:", value=(min_date, max_date), min_value=min_date, max_value=max_date)

        # --- FILTRO SESIÓN AMIGABLE ("Sesión de reforzamiento" -> "Sesión Regular") ---
        sesiones_reales = sorted(df_raw['q7_sesion'].unique().astype(str).tolist())
        opciones_sesion_visual = []
        for sesion in sesiones_reales:
            if sesion.strip().lower() in ['sesión de reforzamiento', 'sesion de reforzamiento']:
                opciones_sesion_visual.append("Sesión Regular")
            else:
                opciones_sesion_visual.append(sesion)
                
        lista_final_sesiones = ['Todos'] + opciones_sesion_visual
        idx_def = lista_final_sesiones.index('Sesión Regular') if 'Sesión Regular' in lista_final_sesiones else 0
        sel_sesion = st.sidebar.selectbox("Tipo de Sesión:", lista_final_sesiones, index=idx_def)

        # --- LIMPIEZA DE CACHE ---
        st.sidebar.markdown("---")
        if st.sidebar.button("🔄 Recargar Base de Datos ", use_container_width=True):
            st.cache_data.clear() 
            st.success("¡Datos actualizados!")
            st.rerun()

        # =========================================================================
        # --- LÓGICA DE FILTRADO CON EXCLUSIÓN DE SEMANAS DE RECESO ---
        # =========================================================================
        df_filtered = df_raw.copy()
        
        if sel_inst != 'Todas': 
            df_filtered = df_filtered[df_filtered['q4_institucion'] == sel_inst]
            
        if sel_grado != 'Todos': 
            df_filtered = df_filtered[df_filtered['q5_grado'] == sel_grado]

        if sel_seccion != 'Todas': 
            df_filtered = df_filtered[df_filtered['q6_seccion'] == sel_seccion]
            
        if sel_curso != 'Todos': 
            if sel_curso == "Taller de Identidad Cultural":
                df_filtered = df_filtered[df_filtered['q3_curso'].astype(str).str.strip() == '4']
            else:
                df_filtered = df_filtered[df_filtered['q3_curso'] == sel_curso]
            
        if sel_sesion != 'Todos': 
            if sel_sesion == "Sesión Regular":
                df_filtered = df_filtered[df_filtered['q7_sesion'].astype(str).str.strip().str.lower().isin(['sesión de reforzamiento', 'sesion de reforzamiento'])]
            else:
                df_filtered = df_filtered[df_filtered['q7_sesion'] == sel_sesion]
        
        if isinstance(sel_dates, tuple) and len(sel_dates) == 2:
            start_date, end_date = sel_dates
            df_filtered = df_filtered[
                (df_filtered['Date'].dt.date >= start_date) & 
                (df_filtered['Date'].dt.date <= end_date)
            ]

        # ✂️ TIJERA AUTOMÁTICA DE RECESO: Excluye el periodo inactivo (17 al 31 de mayo de 2026)
        receso_inicio = pd.to_datetime('2026-05-17').date()
        receso_fin = pd.to_datetime('2026-05-31').date()
        df_filtered = df_filtered[
            ~((df_filtered['Date'].dt.date >= receso_inicio) & (df_filtered['Date'].dt.date <= receso_fin))
        ]

        # --- 4. TÍTULO Y DECLARACIÓN DE LAS TRES PESTAÑAS ---
        st.title("📚 Panel de Seguimiento de Estudiantes: Proyecto de Nivelación Educativa en el Bajo Urubamba 🏫")
        tab1, tab2, tab3 = st.tabs(["📋 Asistencia Individual", "🎯 Rendimiento Académico", "🚨 Alertas de Monitoreo"])

        # --- TAB 1: ASISTENCIA ---
        with tab1:
            st.subheader("📅 Matriz de Asistencia Diaria")
            if not df_filtered.empty:
                asist_pivot = df_filtered.pivot_table(
                    index=['row_key', 'nombre'], 
                    columns='Date', 
                    values='asistencia', 
                    aggfunc='first'
                ).sort_index()
                
                asist_pivot = asist_pivot.dropna(axis=1, how='all')

                if not asist_pivot.empty:
                    asist_pivot['Total Asist.'] = asist_pivot.sum(axis=1, skipna=True)
                    asist_pivot['Sesiones'] = asist_pivot.drop(columns=['Total Asist.']).count(axis=1)

                    fechas_timestamps = list(asist_pivot.columns[:-2])

                    asist_pivot.columns = [
                        c.strftime('%d-%m') if isinstance(c, pd.Timestamp) else c 
                        for c in asist_pivot.columns
                    ]
                    
                    columnas_fechas_str = [c.strftime('%d-%m') for c in fechas_timestamps]
                    
                    def style_asist(val):
                        if val == 1: return 'background-color: #2ecc71; color: #2ecc71' 
                        if val == 0: return 'background-color: #e74c3c; color: #e74c3c' 
                        return 'background-color: #f0f2f6; color: #f0f2f6' 

                    df_interactivo = asist_pivot.reset_index()
                    
                    st.dataframe(
                        df_interactivo.style.map(style_asist, subset=columnas_fechas_str)
                        .format("{:.0f}", na_rep=" ", subset=columnas_fechas_str)
                        .format("{:.0f}", subset=['Total Asist.', 'Sesiones']), 
                        use_container_width=True,
                        hide_index=True
                    )
                    st.info("🟩 **Verde**: Asistió  |  🟥 **Rojo**: Falta  |  ⚪ **Sin registro**")
                    
                    # --- TABLA EXCLUSIVA DE COMENTARIOS ---
                    st.markdown("---")
                    st.subheader("💬 Registro Centralizado de Observaciones del Alumno")
                    
                    col_A = 'comentarios'
                    if col_A in df_filtered.columns:
                        df_comentarios = df_filtered.copy()
                        txt_A_limpio = df_comentarios[col_A].astype(str).str.strip()
                        
                        df_tabla_comentarios = df_comentarios[
                            (df_comentarios[col_A].notna()) & 
                            (txt_A_limpio != "") & 
                            (txt_A_limpio != "nan") & 
                            (txt_A_limpio != "None")
                        ].copy()
                        
                        if not df_tabla_comentarios.empty:
                            df_tabla_comentarios = df_tabla_comentarios.sort_values(by=['Date', 'nombre'], ascending=[False, True])
                            df_tabla_comentarios['Fecha'] = df_tabla_comentarios['Date'].dt.strftime('%d-%b-%Y')
                            df_tabla_comentarios['Asistencia'] = df_tabla_comentarios['asistencia'].map({1: '🟩 Asistió', 0: '🟥 Faltó'}).fillna('Sin Registro')
                            df_tabla_comentarios[col_A] = df_tabla_comentarios[col_A].astype(str).replace(['nan', 'None'], '')
                                
                            df_render = df_tabla_comentarios[['Fecha', 'nombre', 'q3_curso', 'Asistencia', col_A]].rename(columns={
                                'nombre': 'Estudiante',
                                'q3_curso': 'Curso',
                                col_A: 'Comentario Alumno'
                            })
                            
                            st.write(f"Se encontraron **{len(df_render)}** observaciones de estudiantes en las fechas seleccionadas:")
                            st.dataframe(df_render, use_container_width=True, hide_index=True)
                        else:
                            st.info("✨ No se registran comentarios individuales en la columna 'comentarios' para los filtros de fecha seleccionados.")
                    else:
                        st.warning(f"⚠️ La columna '{col_A}' no se encuentra en el archivo CSV.")

        # --- TAB 2: RENDIMIENTO ---
        with tab2:
            st.subheader("🎯 Matriz de Notas y Niveles de Logro")
            if not df_filtered.empty:
                df_labels = df_filtered.copy()
                
                def get_label(row):
                    if row['logro'] == 1: return 'Logro'
                    if row['proceso'] == 1: return 'Proceso'
                    if row['inicio'] == 1: return 'Inicio'
                    return None 

                df_labels['nivel_texto'] = df_labels.apply(get_label, axis=1)

                # Pivot principal para las notas por fecha
                notas_pivot = df_labels.pivot_table(
                    index=['row_key', 'nombre'], 
                    columns='Date', 
                    values='nivel_texto', 
                    aggfunc='first'
                ).sort_index()

                notas_pivot = notas_pivot.dropna(axis=1, how='all')

                if not notas_pivot.empty:
                    # --- 1. CÁLCULO DE PROMEDIOS INDIVIDUALES (EXIT TICKETS) ---
                    df_filtered['pct_puntaje_num'] = pd.to_numeric(df_filtered['pct_puntaje'], errors='coerce')
                    df_solo_notas_reales = df_filtered[df_filtered['pct_puntaje_num'].notna()].copy()
                    
                    df_promedios = df_solo_notas_reales.groupby(['row_key', 'nombre'])['pct_puntaje_num'].mean().reset_index()
                    df_promedios = df_promedios.set_index(['row_key', 'nombre'])
                    
                    columnas_fechas_originales = list(notas_pivot.columns)

                    # --- 2. CÁLCULO DE MÉTRICAS GRUPALES RESUMEN ---
                    conteo_logro = (notas_pivot == 'Logro').sum(axis=0)
                    total_asistentes_fecha = notas_pivot.notna().sum(axis=0)
                    porcentaje_logro = (conteo_logro / total_asistentes_fecha * 100).fillna(0)

                    # Multiplicamos por 100 el promedio bruto de los Exit Tickets
                    notas_pivot['Promedio ET'] = df_promedios['pct_puntaje_num'] * 100

                    # --- 3. EXTRACCIÓN HISTÓRICA DIRECTA DE EXÁMENES DESDE EL CSV ORIGINAL ---
                    name_col_m = 'pct_LB_m'
                    name_col_l = 'pct_LB_l'

                    # Control dinámico de visibilidad lateral en estricta coherencia con el Filtro de Curso
                    incluir_m = True
                    incluir_l = True
                    if sel_curso != 'Todos':
                        if 'mat' in sel_curso.lower(): incluir_l = False
                        elif 'lect' in sel_curso.lower() or 'comu' in sel_curso.lower(): incluir_m = False

                    mapa_m = {}
                    mapa_l = {}
                    
                    df_raw_clean = df_raw.copy()
                    df_raw_clean['row_key_str'] = df_raw_clean['row_key'].astype(str).str.strip()

                    # Procesamos Línea de Base - Matemática
                    if incluir_m and name_col_m in df_raw_clean.columns:
                        df_raw_clean[name_col_m] = pd.to_numeric(df_raw_clean[name_col_m], errors='coerce')
                        df_valid_m = df_raw_clean.dropna(subset=[name_col_m])
                        if not df_valid_m.empty:
                            mapa_m = (df_valid_m.groupby('row_key_str')[name_col_m].max() * 100).to_dict()

                    # Procesamos Línea de Base - Lectoescritura
                    if incluir_l and name_col_l in df_raw_clean.columns:
                        df_raw_clean[name_col_l] = pd.to_numeric(df_raw_clean[name_col_l], errors='coerce')
                        df_valid_l = df_raw_clean.dropna(subset=[name_col_l])
                        if not df_valid_l.empty:
                            mapa_l = (df_valid_l.groupby('row_key_str')[name_col_l].max() * 100).to_dict()

                    # --- 4. PREPARACIÓN Y CONSOLIDACIÓN DEL DATAFRAME FINAL ---
                    df_notas_completo = notas_pivot.reset_index()
                    
                    df_notas_completo['row_key_lookup'] = df_notas_completo['row_key'].astype(str).str.strip()
                    
                    if incluir_m:
                        df_notas_completo['LB Matemática'] = df_notas_completo['row_key_lookup'].map(mapa_m)
                    if incluir_l:
                        df_notas_completo['LB Lectoescritura'] = df_notas_completo['row_key_lookup'].map(mapa_l)

                    df_notas_completo = df_notas_completo.drop(columns=['row_key_lookup'])

                    # Convertimos columnas de fecha de tipo Timestamp a formato dd-mm texto
                    columnas_fechas_str = []
                    mapeo_columnas = {}
                    for c in df_notas_completo.columns:
                        if isinstance(c, pd.Timestamp):
                            nombre_str = c.strftime('%d-%m')
                            mapeo_columnas[c] = nombre_str
                            columnas_fechas_str.append(nombre_str)
                        else:
                            mapeo_columnas[c] = c

                    df_notas_completo = df_notas_completo.rename(columns=mapeo_columnas)

                    # Consolidamos el set de columnas que recibirán formato de porcentaje
                    columnas_porcentaje = ['Promedio ET']
                    if incluir_m and 'LB Matemática' in df_notas_completo.columns:
                        columnas_porcentaje.append('LB Matemática')
                    if incluir_l and 'LB Lectoescritura' in df_notas_completo.columns:
                        columnas_porcentaje.append('LB Lectoescritura')

                    # Nos aseguramos de que los datos se mantengan numéricos antes del formateador
                    for col in columnas_porcentaje:
                        if col in df_notas_completo.columns:
                            df_notas_completo[col] = pd.to_numeric(df_notas_completo[col], errors='coerce')

                    # 🎨 CORRECCIÓN DE INVISIBILIDAD: color transparente remueve textos 'None' u objetos 'nan' de las fechas de raíz
                    def style_por_texto(val):
                        if val == 'Logro': return 'background-color: #2ecc71; color: white' 
                        elif val == 'Proceso': return 'background-color: #f1c40f; color: black' 
                        elif val == 'Inicio': return 'background-color: #e74c3c; color: white' 
                        return 'color: transparent;' 

                    # Diccionario unificado de formatos estrictos por celda para evitar duplicidades
                    mapeo_formatos = {}
                    for col in columnas_porcentaje:
                        mapeo_formatos[col] = lambda x: " " if pd.isna(x) or x is None or str(x).strip() in ["None", "", "nan"] else f"{float(x):.1f}%"
                    for col_fecha in columnas_fechas_str:
                        mapeo_formatos[col_fecha] = lambda x: " " if pd.isna(x) or x is None or str(x).strip() in ["None", "", "nan"] else str(x)

                    # --- RENDER DE LA MATRIZ PRINCIPAL FINAL INDESTRUCTIBLE ---
                    st.dataframe(
                        df_notas_completo.style.map(style_por_texto, subset=columnas_fechas_str)
                        .format(mapeo_formatos),
                        use_container_width=True,
                        hide_index=True
                    )
                    
                    st.markdown("""
                    **Referencia de niveles individuales:** 🟢 **Logro** | 🟡 **Proceso** | 🔴 **Inicio** | ⚪ **Sin evaluación / Inasistencia**
                    """)
                    
                    # =========================================================================
                    # --- MATRIZ SEPARADA ABAJO: RESUMEN ESTADÍSTICO GRUPAL POR FECHA ---
                    # =========================================================================
                    st.markdown("---")
                    st.subheader("📊 Resumen de Logros Grupales por Sesión")
                    
                    fila_cant_final = {'Métrica': '📈 Estudiantes en nivel Logro (Nro)'}
                    fila_pct_final = {'Métrica': '📊 % Logro / Estudiantes Asistentes'}
                    
                    for c_orig in columnas_fechas_originales:
                        c_str = mapeo_columnas[c_orig]
                        fila_cant_final[c_str] = f"{conteo_logro[c_orig]:.0f}"
                        fila_pct_final[c_str] = f"{porcentaje_logro[c_orig]:.1f}%"

                    df_cuadro_estadistica = pd.DataFrame([fila_cant_final, fila_pct_final])
                    columnas_resumen_ordenadas = ['Métrica'] + columnas_fechas_str

                    st.dataframe(
                        df_cuadro_estadistica[columnas_resumen_ordenadas],
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.info("No hay evaluaciones registradas para este grupo en las fechas seleccionadas.")
            else:
                st.warning("No hay datos disponibles.")

        # --- TAB 3: ALERTAS DE MONITOREO (SISTEMA INTEGRADO) ---
        with tab3:
            st.subheader("🚨 Sistema de Alertas de Rendimiento y Asistencia Crítica")
            st.markdown("Identificación automatizada de perfiles estudiantiles para priorizar estrategias pedagógicas o intervenciones de nivelación focalizadas.")
            
            if not df_filtered.empty:
                df_alertas_base = df_filtered.copy()
                
                # Consolidamos las variables de logro en una columna de texto única
                df_alertas_base['nivel_eval'] = df_alertas_base.apply(
                    lambda r: 'Logro' if r['logro'] == 1 else ('Proceso' if r['proceso'] == 1 else ('Inicio' if r['inicio'] == 1 else None)), 
                    axis=1
                )
                
                # Filtramos para quedarnos con registros que tengan notas de Exit Ticket reales
                df_eval_validas = df_alertas_base[df_alertas_base['nivel_eval'].notna()].copy()
                
                if not df_eval_validas.empty:
                    # Agrupamos por la clave de estudiante
                    grupo_estudiantes = df_eval_validas.groupby(['row_key', 'nombre'])
                    
                    resumen_alertas = grupo_estudiantes.agg(
                        Sesiones_Evaluadas=('nivel_eval', 'count'),
                        Niveles_Unicos=('nivel_eval', lambda x: set(x)),
                        Primer_Nivel=('nivel_eval', 'first')
                    ).reset_index()
                    
                    # 🔍 PROCESAMIENTO MATEMÁTICO DE LOS 4 PERFILES:
                    # 1) Estudiantes que solo asistieron una vez y obtuvieron nivel Inicio/Proceso
                    p1 = resumen_alertas[(resumen_alertas['Sesiones_Evaluadas'] == 1) & (resumen_alertas['Primer_Nivel'].isin(['Inicio', 'Proceso']))]
                    
                    # 2) Estudiantes que solo asistieron una vez y obtuvieron nivel Logro
                    p2 = resumen_alertas[(resumen_alertas['Sesiones_Evaluadas'] == 1) & (resumen_alertas['Primer_Nivel'] == 'Logro')]
                    
                    # 3) Estudiantes recurrentes que en TODAS sus evaluaciones obtienen nivel Inicio
                    p3 = resumen_alertas[(resumen_alertas['Sesiones_Evaluadas'] > 1) & (resumen_alertas['Niveles_Unicos'] == {'Inicio'})]
                    
                    # 4) Estudiantes recurrentes que en TODAS sus evaluaciones obtienen nivel Logro
                    p4 = resumen_alertas[(resumen_alertas['Sesiones_Evaluadas'] > 1) & (resumen_alertas['Niveles_Unicos'] == {'Logro'})]
                    
                    # --- INTERFAZ VISUAL DEL PANEL DE CONTROL ---
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.error(f"⚠️ 1) Única Asistencia - Nivel Inicio/Proceso ({len(p1)})")
                        st.caption("Alumnos que registran una sola participación y no lograron el nivel esperado. Prioridad alta de contactación.")
                        if not p1.empty:
                            st.dataframe(p1[['row_key', 'nombre', 'Primer_Nivel']].rename(columns={'row_key': 'ID', 'nombre': 'Estudiante', 'Primer_Nivel': 'Nivel Obtenido'}), use_container_width=True, hide_index=True)
                        else:
                            st.success("No se registran alumnos en este perfil.")
                            
                        st.markdown("---")
                        st.warning(f"🛑 3) Persistencia en Nivel Inicio ({len(p3)})")
                        st.caption("Estudiantes constantes que en el 100% de las sesiones evaluadas permanecen estancados en el nivel inicial.")
                        if not p3.empty:
                            st.dataframe(p3[['row_key', 'nombre', 'Sesiones_Evaluadas']].rename(columns={'row_key': 'ID', 'nombre': 'Estudiante', 'Sesiones_Evaluadas': 'Evaluaciones en Inicio'}), use_container_width=True, hide_index=True)
                        else:
                            st.success("No se registran alumnos en este perfil.")

                    with col2:
                        st.info(f"ℹ️ 2) Única Asistencia - Nivel Logro ({len(p2)})")
                        st.caption("Alumnos con alta capacidad que alcanzaron el nivel de logro en su única sesión, pero discontinuaron su asistencia.")
                        if not p2.empty:
                            st.dataframe(p2[['row_key', 'nombre', 'Primer_Nivel']].rename(columns={'row_key': 'ID', 'nombre': 'Estudiante', 'Primer_Nivel': 'Nivel Obtenido'}), use_container_width=True, hide_index=True)
                        else:
                            st.success("No se registran alumnos en este perfil.")
                            
                        st.markdown("---")
                        st.success(f"🌟 4) Excelencia Sostenida - Nivel Logro ({len(p4)})")
                        st.caption("Estudiantes destacados que mantienen un estándar perfecto de rendimiento (100% Logro) en todo el ciclo.")
                        if not p4.empty:
                            st.dataframe(p4[['row_key', 'nombre', 'Sesiones_Evaluadas']].rename(columns={'row_key': 'ID', 'nombre': 'Estudiante', 'Sesiones_Evaluadas': 'Evaluaciones en Logro'}), use_container_width=True, hide_index=True)
                        else:
                            st.success("No se registran alumnos en este perfil.")
                else:
                    st.info("No hay suficientes evaluaciones históricas con notas válidas para estructurar las alertas de rendimiento.")
            else:
                st.warning("No hay datos disponibles para procesar el panel de alertas.")