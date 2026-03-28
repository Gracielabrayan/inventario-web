import flet as ft
import mysql.connector
import bcrypt
import os
from dotenv import load_dotenv

# --- CONFIGURACIÓN ---
load_dotenv()
BG_MAIN = "#0b0e14"
BG_CARD = "#151921"
ACCENT = "#00f2ff"
TEXT_MAIN = "#e0e6ed"
DANGER = "#c40a0a"

# --- LÓGICA DE BASE DE DATOS (Se mantiene igual que en tu script original) ---
def conectar():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"), 
        user=os.getenv("DB_USER"), 
        password=os.getenv("DB_PASS"), 
        database=os.getenv("DB_NAME"),
        port=os.getenv("DB_PORT")
    )

def obtener_resumen_db():
    try:
        conn = conectar(); cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM resumen_relevamiento")
        datos = cursor.fetchall(); conn.close()
        return datos
    except: return []

# --- INTERFAZ PRINCIPAL ---
def main(page: ft.Page):
    page.title = "IT INVENTORY SYSTEM v3.0"
    page.bgcolor = BG_MAIN
    page.theme_mode = ft.ThemeMode.DARK
    page.window_width = 1000
    page.window_height = 800

    def mostrar_dashboard(user_name):
        page.clean()
        
        # Pestaña de Estadísticas (Equivalente a tu gráfico de barras)
        def build_stats():
            datos = obtener_resumen_db()
            total = sum(d['Total'] for d in datos)
            
            # Generamos las barras usando contenedores de Flet
            barras = []
            for d in datos:
                # n=1851
                altura = (d['Total'] / (max(i['Total'] for i in datos) or 1)) * 300
                barras.append(
                    ft.Column([
                        ft.Text(f"n={d['Total']}", color=ACCENT, weight="bold"),
                        ft.Container(bgcolor=ACCENT, width=80, height=altura, border_radius=5),
                        ft.Text(d['Tipo'], color=TEXT_MAIN, size=12)
                    ], horizontal_alignment="center", alignment="end")
                )

            return ft.Column([
                ft.Text("RESUMEN DE EQUIPOS POR TIPO", size=20, color=ACCENT, weight="bold"),
                ft.Text(f"TOTAL DISPOSITIVOS: {total}", color="#00ff00"),
                ft.Row(barras, alignment="center", spacing=50, vertical_alignment="end")
            ], horizontal_alignment="center", spacing=30)

        # Contenedor principal con Tabs (Equivalente a tu Notebook)
        tabs = ft.Tabs(
            selected_index=0,
            animation_duration=300,
            tabs=[
                ft.Tab(text="TERMINAL_POS", icon=ft.icons.COMPUTER, content=ft.Container(ft.Text("Aquí va la tabla de POS", color=TEXT_MAIN), padding=20)),
                ft.Tab(text="SCALE_NODES", icon=ft.icons.SETTINGS_INPUT_COMPONENT, content=ft.Container(ft.Text("Aquí va la tabla de Balanzas", color=TEXT_MAIN), padding=20)),
                ft.Tab(text="ESTADÍSTICAS", icon=ft.icons.BAR_CHART, content=ft.Container(build_stats(), padding=40)),
            ],
            expand=1
        )

        page.add(
            ft.Row([
                ft.Text(f"OPERATOR: {user_name.upper()}", color="#00ff00", size=12),
                ft.ElevatedButton("[ LOGOUT ]", color="white", bgcolor=DANGER, on_click=lambda _: page.go("/"))
            ], alignment="spaceBetween"),
            tabs
        )
        page.update()

    # --- PANTALLA DE LOGIN ---
    def login_click(e):
        u = user_input.value
        p = pass_input.value
        
        try:
            conn = conectar(); cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT password FROM usuarios WHERE usuario = %s", (u,))
            res = cursor.fetchone(); conn.close()
            
            # Verificación con bcrypt igual que en tu código
            if res and bcrypt.checkpw(p.encode('utf-8'), res['password'].encode('utf-8')):
                mostrar_dashboard(u)
            else:
                page.snack_bar = ft.SnackBar(ft.Text("ACCESO DENEGADO"))
                page.snack_bar.open = True
        except Exception as ex:
            print(f"Error: {ex}")
        page.update()

    user_input = ft.TextField(label="OPERATOR_ID", border_color=ACCENT, on_submit=login_click)
    pass_input = ft.TextField(label="SECURITY_KEY", password=True, can_reveal_password=True, border_color=ACCENT, on_submit=login_click)

    page.add(
        ft.Container(
            content=ft.Column([
                ft.Text("🔒 SYSTEM LOGIN", size=25, color=ACCENT, weight="bold"),
                user_input, pass_input,
                ft.ElevatedButton("[ AUTHORIZE ]", bgcolor=ACCENT, color=BG_MAIN, on_click=login_click, width=200)
            ], horizontal_alignment="center", spacing=20),
            padding=50, bgcolor=BG_CARD, border_radius=10, alignment=ft.alignment.center, width=400
        )
    )

# Importante para Cloud Run: escuchar en el puerto 8080
if __name__ == "__main__":
    ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=int(os.getenv("PORT", 8080)))