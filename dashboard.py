import streamlit as st
import pandas as pd
from supabase import create_client, Client
import time
from datetime import datetime, timedelta

# --- 1. CONFIGURACIÓN VISUAL ---
st.set_page_config(page_title="SGC Auditor", page_icon="🛡️", layout="wide", initial_sidebar_state="expanded")

# --- LOGIN SYSTEM ---
def check_password():
    """Retorna True si el usuario se loguea correctamente."""
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if st.session_state["password_correct"]:
        return True

    st.markdown("## 🔐 Acceso Restringido")
    st.markdown("Por favor, inicia sesión para acceder al tablero.")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.image("https://cdn-icons-png.flaticon.com/512/6195/6195699.png", width=100)
    
    with col2:
        user_input = st.text_input("Usuario", key="login_user")
        password_input = st.text_input("Contraseña", type="password", key="login_password")

        if st.button("Iniciar Sesión"):
            # Verificar si existe la sección [passwords] en secrets
            secrets_passwords = st.secrets.get("passwords", {})
            
            if user_input in secrets_passwords and password_input == secrets_passwords[user_input]:
                st.session_state["password_correct"] = True
                st.success("✅ Acceso concedido")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("❌ Usuario o contraseña incorrectos")

    return False

# --- 2. CONEXIÓN ---
@st.cache_resource
def init_connection():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception:
        return None

# --- 3. LIMPIEZA PARA SUBIDA (Upload) ---
def clean_data_for_upload(df):
    rename_map = {
        'Código del Documento': 'codigo',
        'Título del Documento': 'titulo',
        'Versión Actual': 'revision',
        'Fecha de Emisión': 'fecha_emision',
        'Próxima Revisión': 'proxima_revision',
        'Área Aplicable': 'area',
        'Estado': 'estatus',
        'Tipo de Documento': 'tipo_documento',
        'Enlace al Documento Controlado': 'link_documento',
        'Puesto Responsable': 'responsable'
    }
    available_cols = {k: v for k, v in rename_map.items() if k in df.columns}
    df = df[list(available_cols.keys())].rename(columns=available_cols)
    
    # Formatear fechas para que Supabase las entienda (YYYY-MM-DD)
    for date_col in ['fecha_emision', 'proxima_revision']:
        if date_col in df.columns:
            df[date_col] = pd.to_datetime(df[date_col], dayfirst=True, errors='coerce')
            df[date_col] = df[date_col].dt.strftime('%Y-%m-%d').replace('NaT', None)
            
    if 'revision' in df.columns:
        df['revision'] = df['revision'].fillna('0').astype(str)
    return df

# --- 4. LÓGICA PRINCIPAL DEL DASHBOARD ---
def main_dashboard():
    st.markdown("""
    <style>
        .stMetric {
            background-color: #f0f2f6;
            padding: 15px;
            border-radius: 10px;
            border-left: 5px solid #ff4b4b;
        }
    </style>
    """, unsafe_allow_html=True)

    st.title("🛡️ Centro de Comando SGC")
    
    # --- LOGO SIDEBAR ---
    try:
        st.sidebar.image("logo.png", width=200)
    except Exception:
        pass

    # Botón de Logout en el sidebar
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state["password_correct"] = False
        st.rerun()

    supabase = init_connection()

    if supabase:
        # Traer datos
        response = supabase.table("documentos_sgc").select("*").execute()
        
        if response.data:
            df = pd.DataFrame(response.data)
            
            # Convirtiendo fechas
            if "proxima_revision" in df.columns:
                df["proxima_revision"] = pd.to_datetime(df["proxima_revision"]).dt.date
            if "fecha_emision" in df.columns:
                df["fecha_emision"] = pd.to_datetime(df["fecha_emision"]).dt.date
            
            # --- CALCULAR HEALTH SCORE ---
            total_docs = len(df)
            vigentes = len(df[df["estatus"] == "Vigente"])
            score = int((vigentes / total_docs) * 100) if total_docs > 0 else 0
            
            # --- PESTAÑAS ---
            tab1, tab2, tab3 = st.tabs(["📊 Tablero Gerencial", "🔎 Explorador", "⚙️ Carga"])
            
            # === TAB 1: GRÁFICOS ===
            with tab1:
                st.markdown("### 🏥 Salud del Sistema")
                bar_color = "green" if score > 80 else "orange" if score > 50 else "red"
                st.progress(score, text=f"Índice de Cumplimiento: {score}%")
                
                k1, k2, k3, k4 = st.columns(4)
                k1.metric("Documentos", total_docs)
                k2.metric("Vigentes", vigentes)
                pendientes = len(df[df["estatus"] != "Vigente"])
                k3.metric("Atención Requerida", pendientes, delta_color="inverse")
                k4.metric("Áreas", df["area"].nunique())

                c1, c2 = st.columns(2)
                c1.bar_chart(df["estatus"].value_counts(), color="#ff4b4b")
                c2.bar_chart(df["area"].value_counts())

            # === TAB 2: TABLA EXPLORADOR ===
            with tab2:
                with st.expander("🔍 Filtros", expanded=True):
                    c1, c2 = st.columns(2)
                    search = c1.text_input("Buscar", "")
                    f_status = c2.selectbox("Filtrar Estatus", ["Todos", "Vigente", "Obsoleto"])

                df_view = df.copy()
                if search:
                    df_view = df_view[df_view["titulo"].str.contains(search, case=False) | df_view["codigo"].str.contains(search, case=False)]
                if f_status != "Todos":
                    df_view = df_view[df_view["estatus"] == f_status]

                # Tabla Interactiva
                st.data_editor(
                    df_view,
                    column_order=("estatus", "codigo", "titulo", "revision", "area", "link_documento", "proxima_revision"),
                    column_config={
                        "estatus": st.column_config.TextColumn("Estado", width="medium"),
                        "link_documento": st.column_config.LinkColumn("Enlace", display_text="Abrir 🔗"),
                        "proxima_revision": st.column_config.DateColumn("Vencimiento", format="DD MMM YYYY"),
                        "revision": st.column_config.TextColumn("Rev.", width="small")
                    },
                    hide_index=True,
                    use_container_width=True,
                    disabled=True
                )

            # === TAB 3: CARGA ===
            with tab3:
                st.markdown("### 📤 Carga de Documentos")
                
                tab_single, tab_bulk = st.tabs(["📄 Documento Único", "📦 Carga Masiva (CSV)"])
                
                # --- SUBIDA ÚNICA ---
                with tab_single:
                    st.info("Sube un documento PDF o imagen para registrarlo en el sistema.")
                    
                    with st.form("form_subida_unica"):
                        # Fila 1: Básicos
                        c1, c2, c3 = st.columns(3)
                        nombre_doc = c1.text_input("Nombre del Documento")
                        codigo_doc = c2.text_input("Código")
                        area_doc = c3.selectbox("Área", ["Calidad", "RRHH", "Operaciones", "Ventas", "Dirección", "Otro"])

                        # Fila 2: Detalles
                        c4, c5, c6 = st.columns(3)
                        tipo_doc = c4.selectbox("Tipo de Documento", ['Procedimiento', 'Formato', 'Manual', 'Instructivo', 'Registro', 'Externo'])
                        estado_doc = c5.selectbox("Estado", ['Vigente', 'En Revisión', 'Obsoleto'])
                        revision_doc = c6.text_input("No. de Revisión", value="1.0")

                        # Fila 3: Responsables y Fechas
                        c7, c8, c9 = st.columns(3)
                        responsable_doc = c7.text_input("Responsable del Documento")
                        fecha_emision_doc = c8.date_input("Fecha de Emisión", value=datetime.now())
                        vencimiento_doc = c9.date_input("Fecha de Vencimiento / Revisión", value=datetime.now() + timedelta(days=365))
                        
                        uploaded_file = st.file_uploader("Seleccionar Archivo (PDF, PNG, JPG)")
                        
                        btn_subir = st.form_submit_button("Subir Documento 🚀")
                        
                        if btn_subir:
                            if uploaded_file and nombre_doc and codigo_doc:
                                try:
                                    # 1. Preparar archivo
                                    file_content = uploaded_file.read()
                                    file_ext = uploaded_file.name.split('.')[-1]
                                    file_name = f"{codigo_doc}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{file_ext}"
                                    bucket_name = "documentos"
                                    
                                    # 2. Subir a Storage
                                    supabase.storage.from_(bucket_name).upload(
                                        path=file_name,
                                        file=file_content,
                                        file_options={"content-type": uploaded_file.type}
                                    )
                                    
                                    # 3. Obtener URL Pública
                                    public_url = supabase.storage.from_(bucket_name).get_public_url(file_name)
                                    
                                    # 4. Insertar en Base de Datos
                                    nuevo_registro = {
                                        # Campos básicos
                                        "titulo": nombre_doc,
                                        "codigo": codigo_doc,
                                        "area": area_doc,
                                        "link_documento": public_url,
                                        
                                        # Campos nuevos mapeados
                                        "tipo_documento": tipo_doc,
                                        "estatus": estado_doc,       # 'Estado' -> estatus
                                        "revision": revision_doc,    # 'rev' -> revision
                                        "responsable": responsable_doc,
                                        "fecha_emision": fecha_emision_doc.strftime('%Y-%m-%d'),
                                        "proxima_revision": vencimiento_doc.strftime('%Y-%m-%d') # 'vencimiento' -> proxima_revision
                                    }
                                    
                                    supabase.table("documentos_sgc").insert(nuevo_registro).execute()
                                    
                                    st.success("✅ Documento cargado exitosamente")
                                    st.balloons()
                                    time.sleep(2)
                                    st.rerun()
                                    
                                except Exception as e:
                                    st.error(f"❌ Error durante la carga: {e}")
                            else:
                                st.warning("⚠️ Completa todos los campos obligatorios.")

                # --- CARGA MASIVA (Lógica Anterior) ---
                with tab_bulk:
                     st.markdown("### 📥 Actualización Masiva")
                     csv_file = st.file_uploader("Sube tu CSV", type=['csv'], key="csv_upload")
                     if csv_file and st.button("🚀 Procesar CSV"):
                        try:
                            df_raw = pd.read_csv(csv_file)
                            df_clean = clean_data_for_upload(df_raw)
                            data = df_clean.where(pd.notnull(df_clean), None).to_dict(orient='records')
                            supabase.table("documentos_sgc").delete().neq("id", 0).execute()
                            supabase.table("documentos_sgc").insert(data).execute()
                            st.success("✅ Actualizado")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")
        else:
            st.info("No hay datos en la base de datos.")
    else:
        st.error("No se pudo conectar a Supabase. Revisa tus secretos.")

    # --- CRÉDITOS SIDEBAR ---
    st.sidebar.divider()
    st.sidebar.markdown("""
    👨‍💻 **Desarrollado por:** Francisco Javier García Santos
    """)
    st.sidebar.markdown('[📧 Contactar Soporte](https://tally.so/r/QKMXrX)', unsafe_allow_html=True)

# --- EJECUCIÓN ---
if __name__ == "__main__":
    if check_password():
        main_dashboard()