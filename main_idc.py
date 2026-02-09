import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from extractor_idc import extraer_datos_idc

st.set_page_config(page_title="Auditoría V3.1", layout="wide")
st.title("📑 Auditoría Laboral (Versión Final Blindada)")

with st.sidebar:
    h_conv = st.number_input("Horas Convenio Anual:", value=1800.0)
    files = st.file_uploader("Subir PDFs", type="pdf", accept_multiple_files=True)
    if st.button("🚀 Calcular"):
        if files:
            st.session_state.raw = []
            for f in files: st.session_state.raw.extend(extraer_datos_idc(f))
            st.rerun()

if 'raw' in st.session_state and st.session_state.raw:
    anio = st.selectbox("Año a auditar:", [2024, 2023, 2022])
    dias_anio = 366 if (anio % 4 == 0 and anio % 100 != 0) or (anio % 400 == 0) else 365
    valor_hora_dia = h_conv / dias_anio

    res_final = []
    personas = {r['Nombre'] for r in st.session_state.raw}
    
    for p in personas:
        idcs_p = [r for r in st.session_state.raw if r['Nombre'] == p]
        idcs_p.sort(key=lambda x: x['Desde'])
        
        h_teoricas = 0.0
        h_it = 0.0
        d_it = 0
        d_alta = 0
        
        # Mapa de un solo barrido: día a día
        fecha_ini = datetime(anio, 1, 1)
        for d in range(dias_anio):
            dia = fecha_ini + timedelta(days=d)
            
            # Buscamos el IDC que manda hoy
            vigente = None
            for idc in idcs_p:
                if idc['Desde'] <= dia <= idc['Hasta']:
                    vigente = idc
            
            if vigente:
                f_a = datetime.strptime(vigente['Alta'], "%d-%m-%Y")
                f_b = datetime.strptime(vigente['Baja'], "%d-%m-%Y") if vigente['Baja'] != "ACTIVO" else datetime(2099,1,1)
                
                if f_a <= dia <= f_b:
                    d_alta += 1
                    # Factor de reducción: 500 -> 0.5
                    factor = 1.0 if vigente['CTP'] == 0 else vigente['CTP'] / 1000.0
                    h_teoricas += valor_hora_dia * factor
                    
                    # Verificamos si este día hay IT real
                    for it_i, it_f in vigente['Tramos_IT']:
                        if it_i <= dia <= it_f:
                            d_it += 1
                            h_it += valor_hora_dia * factor
                            break

        res_final.append({
            "Nombre": p, "Días Alta": d_alta, "Días IT": d_it,
            "Horas Teóricas": h_teoricas, "Horas IT": h_it, "Horas Efectivas": h_teoricas - h_it
        })

    st.subheader(f"✅ Informe Auditoría - Año {anio}")
    st.dataframe(pd.DataFrame(res_final).style.format("{:.2f}", subset=['Horas Teóricas', 'Horas IT', 'Horas Efectivas']))