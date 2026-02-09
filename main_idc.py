import streamlit as st
import pandas as pd
import io
from extractor_idc import extraer_datos_idc

st.set_page_config(page_title="Lector IDC", layout="wide")
st.title("📑 Panel de Gestión IDC")

if 'datos' not in st.session_state: st.session_state.datos = []

with st.sidebar:
    st.header("Carga")
    files = st.file_uploader("PDFs", type="pdf", accept_multiple_files=True)
    if st.button("Procesar"):
        if files:
            res = []
            for f in files:
                try: res.extend(extraer_datos_idc(f))
                except Exception as e: st.error(f"Error: {e}")
            st.session_state.datos = res
            st.rerun()
    if st.button("Limpiar"):
        st.session_state.datos = []
        st.rerun()

if st.session_state.datos:
    df = pd.DataFrame(st.session_state.datos)
    df['Año'] = df['Año'].astype(int)
    
    # Filtros
    año_sel = st.selectbox("📅 Año:", sorted(df['Año'].unique(), reverse=True))
    nombres = sorted(df['Nombre'].unique())
    nombres_sel = st.multiselect("👥 Trabajadores:", nombres, default=nombres)

    df_f = df[(df['Año'] == año_sel) & (df['Nombre'].isin(nombres_sel))]

    # Resumen (Consolidado)
    df_res = df_f.groupby(['DNI', 'Nombre', 'Alta', 'Baja', 'Contrato', 'GC', 'Tipo IT', 'Tipo IMS', 'Tipo Desempleo']).apply(
        lambda x: x[x['Peculiaridad'].str.contains("IT|COLAB|DELEGADO", case=False, na=False)]['Días'].sum()
    ).reset_index(name='Total Días IT')

    st.subheader(f"📊 Resumen de Plantilla - {año_sel}")
    st.dataframe(df_res, use_container_width=True)

    # Detalle Individual
    st.divider()
    p_sel = st.selectbox("🔎 Ver desglose de:", nombres_sel)
    df_p = df_f[df_f['Nombre'] == p_sel]
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Trabajador", p_sel)
    m2.metric("IMS", f"{df_p.iloc[0]['Tipo IMS']}%")
    m3.metric("Desempleo", f"{df_p.iloc[0]['Tipo Desempleo']}%")

    with st.expander("📂 Tramos Detallados"):
        df_p_v = df_p[~df_p['Peculiaridad'].isin(["SITUACIÓN NORMAL"])]
        if not df_p_v.empty:
            st.dataframe(df_p_v[['Inicio', 'Fin', 'Días', 'Peculiaridad', 'Valor %']], use_container_width=True)
        else:
            st.info("Sin peculiaridades (Situación normal).")

    # Descarga
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine='openpyxl') as writer:
        df_res.to_excel(writer, index=False)
    st.download_button("📥 Descargar Excel Resumen", out.getvalue(), "resumen.xlsx", type="primary")