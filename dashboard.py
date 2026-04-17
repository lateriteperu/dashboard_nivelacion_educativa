import streamlit as st
import pandas as pd
import plotly.express as px

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Monitoreo Pluspetrol 2026",
    page_icon="📊",
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
    df = pd.read_csv('plus_petrol_2026_pii_grupal.csv')
    
    # Mapeo de columnas
    df = df.rename(columns={
        'q3_curso': 'Curso',
        'q4_institucion': 'Institución',
        'q5_grado': 'Grado',
        'q7_sesion': 'Sesión',
        'q8_fecha_clase': 'Fecha'
    })
    
    # Convertir fecha
    df['Fecha'] = pd.to_datetime(df['Fecha'], format='%d%b%Y')
    
    # Normalización de porcentajes a escala 0-100
    cols_pct = [
        'pct_asistencia', 'pct_logro', 'pct_proceso', 'pct_puntaje', 
        'pct_alto_rendimiento', 'pct_riesgo', 'pct_una_asistencia', 'pct_nunca_asistencia'
    ]
    for col in cols_pct:
        if df[col].max() <= 1.0:
            df[col] = df[col] * 100
            
    return df

df = load_data()

# --- BARRA LATERAL (FILTROS) ---
st.sidebar.header("🔍 Filtros de Análisis")

inst_list = st.sidebar.multiselect("Institución", df['Institución'].unique(), df['Institución'].unique())
grado_list = st.sidebar.multiselect("Grado", df['Grado'].unique(), df['Grado'].unique())
curso_list = st.sidebar.multiselect("Curso", df['Curso'].unique(), df['Curso'].unique())
sesion_list = st.sidebar.multiselect("Tipo de Sesión", df['Sesión'].unique(), df['Sesión'].unique())

# Aplicar filtros
df_filtered = df[
    (df['Institución'].isin(inst_list)) & 
    (df['Grado'].isin(grado_list)) & 
    (df['Curso'].isin(curso_list)) &
    (df['Sesión'].isin(sesion_list))
]

# --- TÍTULO ---
st.title("📊 Dashboard de Impacto Pluspetrol 2026")
st.markdown("---")

# --- SOLO DOS PESTAÑAS ---
tab1, tab2 = st.tabs(["👥 Asistencia y Fidelización", "🎯 Rendimiento Académico"])

# --- TAB 1: ASISTENCIA ---
with tab1:
    st.header("🏫 Gestión de Asistencia y Permanencia")
    
    # Indicadores Resumen (Incluyendo los nuevos)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Asistencia Promedio", f"{df_filtered['pct_asistencia'].mean():.1f}%")
    m2.metric("Horas Efectivas", f"{df_filtered['duration_h'].sum():.1f} h")
    m3.metric("Nunca Asistieron 🚩", f"{df_filtered['pct_nunca_asistencia'].mean():.1f}%")
    m4.metric("Solo 1 Asistencia ⚠️", f"{df_filtered['pct_una_asistencia'].mean():.1f}%")

    st.markdown("---")
    
    # Gráfico de Tendencia
    st.subheader("📈 Evolución y Media Móvil de Asistencia")
    df_trend = df_filtered.groupby('Fecha')['pct_asistencia'].mean().reset_index().sort_values('Fecha')
    df_trend['Media_Movil'] = df_trend['pct_asistencia'].rolling(window=3, min_periods=1).mean()
    
    fig_asist = px.line(df_trend, x='Fecha', y='Media_Movil', title="Tendencia de Asistencia (Suavizada)", line_shape='spline')
    fig_asist.add_scatter(x=df_trend['Fecha'], y=df_trend['pct_asistencia'], mode='markers', name='Dato Diario')
    st.plotly_chart(fig_asist, use_container_width=True)

    # Gráfico de Retención Acumulada
    st.markdown("---")
    st.subheader("📉 Distribución de Fidelización de Estudiantes")
    nunca = df_filtered['pct_nunca_asistencia'].mean()
    una_vez = df_filtered['pct_una_asistencia'].mean()
    recurrentes = 100 - (nunca + una_vez)
    
    df_pie = pd.DataFrame({
        'Estado': ['Nunca Asistieron', 'Solo Una Vez', 'Asistentes Recurrentes'],
        'Porcentaje': [nunca, una_vez, recurrentes]
    })
    
    fig_pie = px.pie(df_pie, values='Porcentaje', names='Estado', hole=0.4,
                     color='Estado',
                     color_discrete_map={
                         'Nunca Asistieron': '#EF553B', 
                         'Solo Una Vez': '#FECB52', 
                         'Asistentes Recurrentes': '#00CC96'
                     })
    st.plotly_chart(fig_pie, use_container_width=True)
    st.info("💡 **Análisis de Fidelización:** El grupo 'Recurrentes' (Verde) representa la base sólida del proyecto, mientras que el área roja es el objetivo de recuperación.")

# --- TAB 2: RENDIMIENTO ---
with tab2:
    st.header("🎓 Rendimiento y Calidad Educativa")
    
    # Nuevos Indicadores de Notas
    cobertura = (df_filtered['pct_puntaje'].count() / len(df_filtered) * 100) if len(df_filtered)>0 else 0
    alto_rend = df_filtered['pct_alto_rendimiento'].mean()
    riesgo_acad = df_filtered['pct_riesgo'].mean()

    n1, n2, n3, n4 = st.columns(4)
    n1.metric("Puntaje Promedio", f"{df_filtered['pct_puntaje'].mean():.1f}%")
    n2.metric("Cobertura Exit Ticket", f"{cobertura:.1f}%")
    n3.metric("Alto Rendimiento 🏆", f"{alto_rend:.1f}%")
    n4.metric("Riesgo Académico 🚩", f"{riesgo_acad:.1f}%")

    st.markdown("---")
    
    # Evolución de Logro (Línea)
    st.subheader("📈 Evolución de Niveles de Logro por Grado")
    df_notas = df_filtered.groupby(['Fecha', 'Grado'])[['pct_logro', 'pct_puntaje']].mean().reset_index().sort_values('Fecha')
    fig_logro = px.line(df_notas, x='Fecha', y='pct_logro', color='Grado', markers=True, title="% Estudiantes con Nivel Logro")
    fig_logro.update_traces(connectgaps=True)
    st.plotly_chart(fig_logro, use_container_width=True)

    st.markdown("---")
    
    # Perfiles Extremos (Barras)
    st.subheader("📊 Comparativa: Excelencia vs. Riesgo por Curso")
    df_ext = df_filtered.groupby('Curso')[['pct_alto_rendimiento', 'pct_riesgo']].mean().reset_index()
    fig_ext = px.bar(df_ext, x='Curso', y=['pct_alto_rendimiento', 'pct_riesgo'], barmode='group',
                     title="Consistencia de Rendimiento", 
                     color_discrete_sequence=['#2ecc71', '#e74c3c'],
                     labels={'value': 'Porcentaje (%)', 'variable': 'Perfil'})
    st.plotly_chart(fig_ext, use_container_width=True)
    
    st.info("💡 **Nota Académica:** El Riesgo Académico identifica estudiantes que no logran superar el nivel de inicio de forma constante.")

# Tabla final
with st.expander("📂 Ver base de datos detallada"):
    st.dataframe(df_filtered)