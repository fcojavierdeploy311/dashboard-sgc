import streamlit as st
import pandas as pd
from supabase import create_client, Client
import time
from datetime import datetime, timedelta

# --- 1. CONFIGURACIÓN VISUAL ---
st.set_page_config(page_title="SGC Auditor", page_icon="🛡️", layout="wide", initial_sidebar_state="expanded")

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

# --- 2. CONEXIÓN ---
@st.cache_resource
def init_connection():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception:
        return None

supabase = init_connection()

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

# --- 4. LÓGICA PRINCIPAL ---
if supabase:
    # Traer datos
    response = supabase.table("documentos_sgc").select("*").execute()
    
    if response.data:
        df = pd.DataFrame(response.data)
        
        # ⚠️ AQUÍ ESTÁ EL ARREGLO (FIX) ⚠️
        # Convertimos el TEXTO de Supabase a FECHA real de Python
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
            st.markdown("### 📥 Actualización Masiva")
            uploaded_file = st.file_uploader("Sube tu CSV", type=['csv'])
            if uploaded_file and st.button("🚀 Procesar"):
                try:
                    df_raw = pd.read_csv(uploaded_file)
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
        st.info("Sube tu primer archivo en la pestaña de Configuración.")