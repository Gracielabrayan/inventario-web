import streamlit as st
import mysql.connector
import pandas as pd
import plotly.express as px
import bcrypt

# Configuración de la página (Esto tiene que ser lo primero)
st.set_page_config(page_title="IT INVENTORY PRO", layout="wide")

# Función de conexión usando st.secrets (Para Streamlit Cloud)
def conectar():
    return mysql.connector.connect(
        host=st.secrets["DB_HOST"],
        user=st.secrets["DB_USER"],
        password=st.secrets["DB_PASS"],
        database=st.secrets["DB_NAME"],
        port=int(st.secrets["DB_PORT"]),
        connect_timeout=20
    )

# Estado de autenticación
if 'auth' not in st.session_state:
    st.session_state['auth'] = False

# --- PANTALLA DE LOGIN ---
if not st.session_state['auth']:
    col_a, col_b, col_c = st.columns([1, 1.2, 1])
    with col_b:
        st.write("")
        with st.container(border=True):
            st.markdown("<h2 style='text-align: center;'>🔐 Acceso al Sistema</h2>", unsafe_allow_html=True)
            user_input = st.text_input("Usuario")
            pw_input = st.text_input("Clave", type="password")
            
            if st.button("ENTRAR", use_container_width=True, type="primary"):
                try:
                    conn = conectar()
                    cursor = conn.cursor(dictionary=True)
                    # Buscamos al usuario en la tabla
                    cursor.execute("SELECT password FROM usuarios WHERE usuario = %s", (user_input,))
                    res = cursor.fetchone()
                    conn.close()
                    
                    if res and bcrypt.checkpw(pw_input.encode('utf-8'), res['password'].encode('utf-8')):
                        st.session_state['auth'] = True
                        st.rerun()
                    else: 
                        st.error("Usuario o clave incorrectos")
                except Exception as e: 
                    st.error(f"Error de conexión: {e}")

# --- DASHBOARD (Solo si está autenticado) ---
else:
    with st.sidebar:
        st.title("IT Admin")
        st.write(f"Conectado a: {st.secrets['DB_NAME']}")
        if st.button("Cerrar Sesión", use_container_width=True):
            st.session_state['auth'] = False
            st.rerun()

    try:
        conn = conectar()
        
        # KPIs de las 1851 terminales y balanzas
        t_pos = pd.read_sql("SELECT COUNT(*) as t FROM relevamiento_pos_2024", conn)['t'][0]
        t_bal = pd.read_sql("SELECT COUNT(*) as t FROM relevamiento_balanzas_2024", conn)['t'][0]
        
        st.title("📊 Dashboard de Relevamiento 2024")
        
        c1, c2, c3 = st.columns(3)
        c1.metric("TOTAL POS", f"{t_pos:,}")
        c2.metric("TOTAL BALANZAS", f"{t_bal:,}")
        c3.metric("EQUIPOS TOTALES", f"{t_pos + t_bal:,}")

        tab1, tab2 = st.tabs(["🖥️ Terminales POS", "⚖️ Balanzas"])

        with tab1:
            st.subheader("Desglose por Hardware y Software")
            # Consulta para el gráfico de barras
            df_pos = pd.read_sql("""
                SELECT `TIPO CAJA`, `SOFTWARE CAJA`, COUNT(*) AS Total 
                FROM relevamiento_pos_2024 
                GROUP BY 1, 2 
                ORDER BY Total DESC
            """, conn)
            
            df_pos["Config"] = df_pos["TIPO CAJA"] + " (" + df_pos["SOFTWARE CAJA"] + ")"
            
            fig_pos = px.bar(df_pos, x='Total', y='Config', orientation='h',
                             color='SOFTWARE CAJA', text='Total',
                             title="Distribución de Cajas",
                             color_discrete_sequence=px.colors.qualitative.Bold)
            
            st.plotly_chart(fig_pos, use_container_width=True)

        with tab2:
            st.subheader("Marcas de Balanzas")
            df_bal = pd.read_sql("SELECT MARCA, COUNT(*) AS Total FROM relevamiento_balanzas_2024 GROUP BY 1", conn)
            
            fig_bal = px.pie(df_bal, values='Total', names='MARCA', 
                             title='Participación por Marca', hole=.4)
            st.plotly_chart(fig_bal, use_container_width=True)

        conn.close()
        
    except Exception as e:
        st.error(f"Error al cargar datos: {e}")
