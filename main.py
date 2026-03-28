import streamlit as st
import mysql.connector
import pandas as pd
import plotly.express as px
import bcrypt

# 1. Configuración de página (Debe ser la primera instrucción de Streamlit)
st.set_page_config(page_title="IT INVENTORY PRO", layout="wide")

# 2. Función de conexión ROBUSTA (Sin caché de recurso para evitar conexiones muertas)
def obtener_conexion():
    try:
        conn = mysql.connector.connect(
            host=st.secrets["DB_HOST"],
            user=st.secrets["DB_USER"],
            password=st.secrets["DB_PASS"],
            database=st.secrets["DB_NAME"],
            port=int(st.secrets["DB_PORT"]),
            connect_timeout=20,
            autocommit=True
        )
        return conn
    except Exception as e:
        st.error(f"Error crítico al conectar con la base de datos: {e}")
        return None

# 3. Carga de datos con Caché (Se guarda el resultado, no la conexión)
@st.cache_data(ttl=300) # Se actualiza cada 5 minutos
def cargar_datos_dashboard():
    conn = obtener_conexion()
    if conn is None:
        return None, None, None, None
    
    try:
        # KPIs
        t_pos = pd.read_sql("SELECT COUNT(*) as t FROM relevamiento_pos_2024", conn)['t'][0]
        t_bal = pd.read_sql("SELECT COUNT(*) as t FROM relevamiento_balanzas_2024", conn)['t'][0]
        
        # Datos para gráfico de POS
        df_pos = pd.read_sql("""
            SELECT `TIPO CAJA`, `SOFTWARE CAJA`, COUNT(*) AS Total 
            FROM relevamiento_pos_2024 
            GROUP BY 1, 2 
            ORDER BY Total ASC
        """, conn)
        
        # Datos para gráfico de Balanzas
        df_bal = pd.read_sql("SELECT MARCA, COUNT(*) AS Total FROM relevamiento_balanzas_2024 GROUP BY 1", conn)
        
        return t_pos, t_bal, df_pos, df_bal
    except Exception as e:
        st.error(f"Error al leer tablas: {e}")
        return None, None, None, None
    finally:
        if conn and conn.is_connected():
            conn.close() # CERRAMOS para liberar el cupo en Clever Cloud

# 4. Estado de sesión para Login
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
                conn_login = obtener_conexion()
                if conn_login:
                    try:
                        cursor = conn_login.cursor(dictionary=True)
                        cursor.execute("SELECT password FROM usuarios WHERE usuario = %s", (user_input,))
                        res = cursor.fetchone()
                        
                        if res and bcrypt.checkpw(pw_input.encode('utf-8'), res['password'].encode('utf-8')):
                            st.session_state['auth'] = True
                            st.rerun()
                        else: 
                            st.error("Usuario o clave incorrectos")
                    finally:
                        conn_login.close()

# --- DASHBOARD ---
else:
    with st.sidebar:
        st.title("IT Admin")
        st.info(f"Conectado a: {st.secrets['DB_NAME']}")
        if st.button("Cerrar Sesión", use_container_width=True):
            st.session_state['auth'] = False
            st.cache_data.clear() # Limpiamos caché al salir
            st.rerun()

    # Carga de datos
    t_pos, t_bal, df_pos, df_bal = cargar_datos_dashboard()

    if t_pos is not None:
        st.title("📊 Relevamiento IT 2024")
        
        # Métricas
        m1, m2, m3 = st.columns(3)
        m1.metric("TERMINALES POS", f"{t_pos:,}")
        m2.metric("BALANZAS", f"{t_bal:,}")
        m3.metric("TOTAL EQUIPOS", f"{t_pos + t_bal:,}")

        tab1, tab2 = st.tabs(["🖥️ Detalle POS", "⚖️ Detalle Balanzas"])

        with tab1:
            df_pos["Config"] = df_pos["TIPO CAJA"] + " (" + df_pos["SOFTWARE CAJA"] + ")"
            fig_pos = px.bar(df_pos, x='Total', y='Config', orientation='h',
                             color='SOFTWARE CAJA', text='Total',
                             title="Distribución por Hardware/Software",
                             height=600,
                             color_discrete_sequence=px.colors.qualitative.Bold)

            # Ajuste de etiquetas horizontales y afuera
            fig_pos.update_traces(
                textposition='outside', 
                textangle=0, 
                cliponaxis=False,
                textfont=dict(size=14, color="white")
            )
            
            # Ordenar: Más grande arriba
            fig_pos.update_layout(yaxis={'categoryorder':'total ascending'})
            
            st.plotly_chart(fig_pos, use_container_width=True)

        with tab2:
            fig_bal = px.pie(df_bal, values='Total', names='MARCA', 
                             title='Market Share de Balanzas', hole=.4)
            st.plotly_chart(fig_bal, use_container_width=True)
    else:
        st.warning("No se pudo cargar la información. Reintentá en unos segundos.")
        if st.button("Reintentar ahora"):
            st.rerun()
