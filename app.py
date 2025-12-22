import streamlit as st
import pandas as pd

# Configuración de la página en modo 'wide'
st.set_page_config(page_title="Tablero SGC", layout="wide")

# Título
st.title("Tablero de Control SGC - Auditoría Interna")

# Crear DataFrame simulado
data = {
    'Nombre': [
        'Juan Pérez', 'Ana Gómez', 'Carlos Ruiz', 'María López', 'Pedro Hernández',
        'Lucía Torres', 'Jorge Ramírez', 'Elena Díaz', 'Miguel Ángel', 'Sofía Castro'
    ],
    'Departamento': [
        'Ventas', 'RH', 'TI', 'Ventas', 'Operaciones',
        'Finanzas', 'TI', 'Marketing', 'Operaciones', 'Ventas'
    ],
    'Retardos': [0, 3, 1, 4, 0, 2, 5, 0, 1, 3],
    'Faltas': [0, 0, 1, 1, 0, 0, 0, 0, 0, 1]
}

df = pd.DataFrame(data)

# Lógica de Negocio: Columna 'Estatus'
def evaluar_auditoria(row):
    if row['Retardos'] >= 3 or row['Faltas'] >= 1:
        return 'AUDITAR'
    else:
        return 'OK'

df['Estatus'] = df.apply(evaluar_auditoria, axis=1)

# Métricas
total_empleados = len(df)
total_auditar = len(df[df['Estatus'] == 'AUDITAR'])
porcentaje_cumplimiento = ((total_empleados - total_auditar) / total_empleados) * 100

# Mostrar métricas en la parte superior
col1, col2, col3 = st.columns(3)
col1.metric("Total Empleados", total_empleados)
col2.metric("Total a Auditar", total_auditar, delta=total_auditar, delta_color="inverse")
col3.metric("% Cumplimiento", f"{porcentaje_cumplimiento:.1f}%", delta=f"{porcentaje_cumplimiento - 100:.1f}%")

# Función para aplicar estilos condicionales
def color_estatus(val):
    color = 'red' if val == 'AUDITAR' else 'green'
    return f'color: {color}; font-weight: bold'

# Mostrar DataFrame con estilos
st.subheader("Listado de Personal")
st.dataframe(
    df.style.applymap(color_estatus, subset=['Estatus']),
    use_container_width=True
)
