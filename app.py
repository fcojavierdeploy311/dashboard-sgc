import streamlit as st
import pandas as pd
import time

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Tablero SGC", layout="wide")
st.title("Tablero de Control SGC - Auditoría Interna 🚀")

# ==============================================================================
# 📝 SECCIÓN 1: ALTA Y MODIFICACIÓN
# ==============================================================================
st.sidebar.header("📝 Gestión de Personal")

with st.sidebar.form("formulario_gestion"):
    st.markdown("### Agregar o Actualizar")
    nombre_input = st.text_input("Nombre Completo")
    depto_input = st.selectbox("Departamento", ["Calidad", "RRHH", "Administracion", "Hematologia", "Inmunologia", "Santa Anita", "Mensajeria", "Recepcion", "Otro"])
    retardos_input = st.number_input("Retardos", min_value=0, step=1)
    faltas_input = st.number_input("Faltas", min_value=0, step=1)
    
    boton_guardar = st.form_submit_button("💾 Guardar / Actualizar")

    if boton_guardar:
        if nombre_input:
            try:
                df = pd.read_excel("empleados.xlsx", engine="openpyxl")
                nombre_limpio = nombre_input.strip()
                
                # Buscamos si ya existe
                filtro = df['Nombre'] == nombre_limpio
                
                if filtro.any():
                    # ACTUALIZAR
                    indice = df.index[filtro][0]
                    df.at[indice, 'Departamento'] = depto_input
                    df.at[indice, 'Retardos'] = retardos_input
                    df.at[indice, 'Faltas'] = faltas_input
                    mensaje = f"🔄 Datos de '{nombre_limpio}' actualizados."
                else:
                    # CREAR NUEVO
                    nuevo = {"Nombre": nombre_limpio, "Departamento": depto_input, "Retardos": retardos_input, "Faltas": faltas_input}
                    df = pd.concat([df, pd.DataFrame([nuevo])], ignore_index=True)
                    mensaje = f"✅ Nuevo empleado '{nombre_limpio}' creado."

                df.to_excel("empleados.xlsx", index=False, engine="openpyxl")
                st.success(mensaje)
                time.sleep(1)
                st.rerun()
            except PermissionError:
                st.error("⛔ ERROR: Cierra el Excel.")
            except Exception as e:
                st.error(f"❌ Error: {e}")

# ==============================================================================
# 🗑️ SECCIÓN 2: ELIMINAR CIRÚRGICO (POR ID)
# ==============================================================================
st.sidebar.markdown("---")
with st.sidebar.expander("🗑️ Zona de Peligro (Eliminar)"):
    st.warning("Selecciona el registro exacto a eliminar:")
    
    try:
        # Cargamos el DF para listar las opciones
        df_borrar = pd.read_excel("empleados.xlsx", engine="openpyxl")
        
        # Creamos una lista inteligente: "ID | Nombre (Depto)"
        # Esto permite diferenciar dos "Pacos" por su número de fila (Index)
        opciones_borrar = [f"{i} | {row['Nombre']} ({row['Departamento']})" for i, row in df_borrar.iterrows()]
        
        seleccion = st.selectbox("Selecciona registro:", opciones_borrar)
        
        if st.button("🔥 Eliminar Este Registro"):
            if seleccion:
                try:
                    # 1. Extraemos el ID (el número antes de la barra "|")
                    id_a_borrar = int(seleccion.split(" | ")[0])
                    nombre_borrado = seleccion.split(" | ")[1]
                    
                    # 2. Borramos esa fila específica usando el ID
                    df_limpio = df_borrar.drop(id_a_borrar)
                    
                    # 3. Guardamos
                    df_limpio.to_excel("empleados.xlsx", index=False, engine="openpyxl")
                    
                    st.success(f"👋 Registro eliminado: {nombre_borrado}")
                    time.sleep(1)
                    st.rerun()
                except PermissionError:
                    st.error("⛔ El Excel está abierto. Ciérralo.")
                except Exception as e:
                    st.error(f"❌ Error: {e}")
    except:
        st.error("No se pudo cargar la lista para borrar.")

# ==============================================================================
# 👀 SECCIÓN 3: MONITOR EN VIVO
# ==============================================================================
st.markdown("---")

@st.fragment(run_every=5)
def panel_en_vivo():
    try:
        df = pd.read_excel("empleados.xlsx", engine="openpyxl")
    except:
        return

    # Lógica
    def evaluar(fila):
        if fila['Faltas'] > 0 or fila['Retardos'] >= 3:
            return 'AUDITAR'
        else:
            return 'OK'

    df['Estatus'] = df.apply(evaluar, axis=1)

    # Métricas
    total = len(df)
    rojos = len(df[df['Estatus'] == 'AUDITAR'])
    cumplimiento = ((total - rojos) / total) * 100 if total > 0 else 0

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Personal", total)
    c2.metric("⚠️ A Auditar", rojos, delta_color="inverse")
    c3.metric("✅ Cumplimiento", f"{cumplimiento:.1f}%")

    # Tabla
    st.subheader("📋 Nómina Actualizada")
    def estilo(v):
        color = '#ffcccc' if v == 'AUDITAR' else '#ccffcc'
        return f'background-color: {color}; color: black'

    st.dataframe(
        df.style.applymap(estilo, subset=['Estatus']), 
        use_container_width=True,
        # AHORA NO OCULTAMOS EL ÍNDICE para que puedas ver qué número borrar
        hide_index=False 
    )

panel_en_vivo()