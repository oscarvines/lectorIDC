import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from extractor_idc import extraer_datos_idc

st.set_page_config(page_title="Auditoría V3.3", layout="wide")
st.title("📑 Auditoría Laboral (V3.3)")

with st.sidebar:
    h_conv = st.number_input("Horas Convenio Anual (100%):", value=1800.0)
    files = st.file_uploader("Subir PDFs", type="pdf", accept_multiple_files=True)
    if st.button("🚀 Calcular"):
        if files:
            st.session_state.raw = []
            for f in files: st.session_state.raw.extend(extraer_datos_idc(f))
            st.rerun()

if 'raw' in st.session_state and st.session_state.raw:
    anio = st.selectbox("Año:", [2024, 2023, 2022])
    dias_anio = 366 if (anio % 4 == 0 and anio % 100 != 0) or (anio % 400 == 0) else 365
    v_h_d = h_conv / dias_anio

    res = []
    # Obtenemos nombres únicos
    personas = {r['Nombre'] for r in st.session_state.raw}
    
    for p in personas:
        idcs = sorted([r for r in st.session_state.raw if r['Nombre'] == p], key=lambda x: x['Desde'])
        h_t, h_i = 0.0, 0.0
        
        fecha_inicio_anio = datetime(anio, 1, 1)
        for d in range(dias_anio):
            dia = fecha_inicio_anio + timedelta(days=d)
            # Buscar IDC vigente (el último que empezó antes o hoy)
            vig = None
            for idc in idcs:
                if idc['Desde'] <= dia <= idc['Hasta']:
                    vig = idc
            
            if vig:
                f_a = datetime.strptime(vig['Alta'], "%d-%m-%Y")
                f_b = datetime.strptime(vig['Baja'], "%d-%m-%Y") if vig['Baja'] != "ACTIVO" else datetime(2099,1,1)
                
                if f_a <= dia <= f_b:
                    factor = 1.0 if vig['CTP'] == 0 else vig['CTP'] / 1000.0
                    h_t += v_h_d * factor
                    # Check IT
                    if any(it[0] <= dia <= it[1] for it in vig['Tramos_IT']):
                        h_i += v_h_d * factor

        res.append({"Nombre": p, "Horas Teóricas": h_t, "Horas IT": h_i, "Horas Efectivas": h_t - h_i})

    # CORRECCIÓN DE FORMATO AQUÍ: Solo aplicamos decimales a las columnas numéricas
    df_final = pd.DataFrame(res)
    columnas_num = ["Horas Teóricas", "Horas IT", "Horas Efectivas"]
    
    st.subheader(f"✅ Resultados {anio}")
    st.dataframe(df_final.style.format("{:.2f}", subset=columnas_num))