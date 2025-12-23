import streamlit as st
from supabase import create_client, Client

st.title("🕵️ Auditoría de Conexión: Supabase")

try:
    # 1. Intentamos leer las credenciales
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    st.write(f"📡 URL Configurada: `{url}`")

    # 2. Intentamos conectar
    supabase: Client = create_client(url, key)
    st.success("✅ ¡CONEXIÓN EXITOSA! Base de datos alcanzada.")

except Exception as e:
    st.error(f"❌ Error: {e}")
    st.info("Revisa que exista la carpeta .streamlit y el archivo secrets.toml")
