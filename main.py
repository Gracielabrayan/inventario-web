import streamlit as st
import mysql.connector
import pandas as pd
import plotly.express as px
import bcrypt

# 1. Configuración de página
st.set_page_config(page_title="IT INVENTORY PRO", layout="wide")

# 2. Funciones con CACHÉ para optimizar velocidad
@st.cache_resource
def obtener_conexion():
    return mysql.connector.connect(
        host=st.secrets["DB_HOST"],
        user=st.secrets["DB_USER"],
        password=st.secrets["DB_PASS"],
        database=st.secrets["DB_NAME"],
        port=int(st.secrets["DB_PORT"]),
        connect_timeout=15
    )

@st.cache_data(ttl=600)
def cargar_datos_dashboard():
    conn = obtener_conexion()
    
    # KPIs
    t_pos = pd.read_sql("SELECT COUNT(*) as t FROM relevamiento_pos_2024", conn)['t'][0]
    t_bal = pd.read_sql("SELECT COUNT(*) as t FROM relevamiento_balanzas_2024", conn)['t'][0]
    
    # Datos para gráficos (Ordenados por Total en la query)
    df_pos = pd.read_sql("""
        SELECT `TIPO CAJA`, `SOFTWARE CAJA`, COUNT(*) AS Total 
        FROM relevamiento_pos_2024 
        GROUP BY 1, 2 
        ORDER BY Total ASC
    """, conn)
    
    df_bal = pd.read_sql("SELECT MARCA, COUNT(*) AS Total FROM relevamiento_balanzas_2024 GROUP BY 1", conn)
    
    return t_pos, t_bal, df_pos, df_bal

# 3. Lógica de Autenticación
if 'auth' not in st.session_state:
    st.session_state['auth'] = False

# --- PANTALLA DE LOGIN ---
if not st.session_state['auth']:
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.write("#")
        with st.container(border=True):
            st.markdown("<h2 style='text-align: center;'>🔐 Acceso al Sistema</h2>", unsafe_allow_html=True)
            user_input = st.text_input("Usuario")
            pw_input = st.text_input("Clave", type="password")
            
            if st.button("INGRESAR", use_container_width=True, type="primary"):
                try:
                    conn = obtener_conexion()
                    cursor = conn.cursor(dictionary=True)
                    cursor.execute("SELECT password FROM usuarios WHERE usuario = %s", (user_input,))
                    res = cursor.fetchone()
                    
                    if res and bcrypt.checkpw(pw_input.encode('utf-8'), res['password'].encode('utf-8')):
                        st.session_state['auth'] = True
                        st.rerun()
                    else: 
                        st.error("Credenciales incorrectas")
                except Exception as e:
                    st.error(f"Error de conexión: {e}")

# --- DASHBOARD PRINCIPAL ---
else:
    with st.sidebar:
        st.title("IT Admin")
        st.info(f"Base: {st.secrets['DB_NAME']}")
        if st.button("Cerrar Sesión", use_container_width=True):
            st.session_state['auth'] = False
            st.rerun()

    try:
        with st.spinner('Actualizando datos...'):
            t_pos, t_bal, df_pos, df_bal = cargar_datos_dashboard()
        
        st.title("📊 Relevamiento IT 2024")
        
        # Métricas principales
        m1, m2, m3 = st.columns(3)
        m1.metric("TERMINALES POS", f"{t_pos:,}")
        m2.metric("BALANZAS", f"{t_bal:,}")
        m3.metric("TOTAL EQUIPOS", f"{t_pos + t_bal:,}")

        tab_pos, tab_bal = st.tabs(["🖥️ Detalle POS", "⚖️ Detalle Balanzas"])

        with tab_pos:
            # Preparación de etiquetas
            df_pos["Config"] = df_pos["TIPO CAJA"] + " (" + df_pos["SOFTWARE CAJA"] + ")"
            
            # Creación del gráfico
            fig_pos = px.bar(df_pos, x='Total', y='Config', orientation='h',
                             color='SOFTWARE CAJA', text='Total',
                             title="Distribución por Hardware/Software",
                             height=600,
                             color_discrete_sequence=px.colors.qualitative.Pastel)

            # AJUSTE DE NÚMEROS: Horizontales, afuera y legibles
            fig_pos.update_traces(
                textposition='outside', 
                textangle=0,            # Fuerza posición horizontal
                cliponaxis=False,       # Evita que se corten los números
                textfont=dict(size=14)  # Aumenta un poco el tamaño
            )

            # Ordenar para que la barra más larga esté ARRIBA
            fig_pos.update_layout(
                yaxis={'categoryorder':'total ascending'},
                margin=dict(l=20, r=50, t=50, b=20) # Espacio para que el número no se salga del borde
            )
            
            st.plotly_chart(fig_pos, use_container_width=True)

        with tab_bal:
            fig_bal = px.pie(df_bal, values='Total', names='MARCA', 
                             title='Market Share de Balanzas', hole=.4)
            st.plotly_chart(fig_bal, use_container_width=True)

    except Exception as e:
        st.error(f"Error al cargar el dashboard: {e}")
