import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from extractor_idc import extraer_datos_idc
import io

st.set_page_config(page_title="Auditoría V3.9 - Trazabilidad", layout="wide")
st.title("📑 Auditoría Laboral (V3.9 - Inicio de Contrato)")

# Función para exportar a Excel
def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Auditoria')
    return output.getvalue()

with st.sidebar:
    st.header("1. Configuración")
    h_conv = st.number_input("Horas Convenio Anual (100%):", value=1800.0)
    files = st.file_uploader("Subir PDFs", type="pdf", accept_multiple_files=True)
    if st.button("🚀 Calcular Auditoría"):
        if files:
            st.session_state.raw = []
            for f in files: st.session_state.raw.extend(extraer_datos_idc(f))
            st.rerun()

if 'raw' in st.session_state and st.session_state.raw:
    # Selector de años (ahora con 2025 y 2026)
    anio = st.selectbox("2. Seleccionar Año:", [2026, 2025, 2024, 2023, 2022])
    
    # Filtro de personas
    nombres_dis = sorted(list({r['Nombre'] for r in st.session_state.raw}))
    seleccion = st.multiselect("3. Filtrar Trabajadores:", options=nombres_dis, default=nombres_dis)

    dias_anio = 366 if (anio % 4 == 0 and (anio % 100 != 0 or anio % 400 == 0)) else 365
    v_h_d = h_conv / dias_anio
    
    f_limite_ini = datetime(anio, 1, 1)
    f_limite_fin = datetime(anio, 12, 31)

    res_final = []
    for p in seleccion:
        idcs_p = sorted([r for r in st.session_state.raw if r['Nombre'] == p], key=lambda x: x['Desde_Info'])
        h_t, h_i, d_it, d_alta = 0.0, 0.0, 0, 0
        
        primer_dia = None
        ultimo_dia = None
        hay_hueco = False
        
        # Fecha de contrato original detectada en el PDF
        f_contrato_orig = idcs_p[0]['Inicio_Contrato']
        
        for d in range(dias_anio):
            dia = f_limite_ini + timedelta(days=d)
            vig = next((i for i in reversed(idcs_p) if i['Desde_Info'] <= dia <= i['Hasta_Info']), None)
            
            deberia_haber_datos = f_contrato_orig <= dia
            
            if vig:
                f_a = datetime.strptime(vig['Alta'], "%d-%m-%Y")
                f_b = datetime.strptime(vig['Baja'], "%d-%m-%Y") if vig['Baja'] != "ACTIVO" else datetime(2099,1,1)
                
                if f_a <= dia <= f_b:
                    d_alta += 1
                    if primer_dia is None: primer_dia = dia
                    ultimo_dia = dia
                    factor = 1.0 if vig['CTP'] == 0 else vig['CTP'] / 1000.0
                    h_t += v_h_d * factor
                    if any(it[0] <= dia <= it[1] for it in vig['Tramos_IT']):
                        d_it += 1
                        h_i += v_h_d * factor
            elif deberia_haber_datos:
                hay_hueco = True

        if d_alta > 0:
            res_final.append({
                "Nombre": p,
                "Estado": "⚠️ INCOMPLETO" if hay_hueco else "✅ OK",
                "Inicio Contrato": f_contrato_orig.strftime("%d-%m-%Y"),
                "Inicio Auditado": primer_dia.strftime("%d-%m-%Y"),
                "Fin Auditado": ultimo_dia.strftime("%d-%m-%Y"),
                "Días IT": d_it,
                "Horas Teóricas": round(h_t, 2),
                "Horas IT": round(h_i, 2),
                "Horas Efectivas": round(h_t - h_i, 2)
            })

    if res_final:
        df_final = pd.DataFrame(res_final)
        st.subheader(f"✅ Informe Auditoría {anio}")
        st.dataframe(df_final, use_container_width=True)
        
        st.download_button(
            label="📥 Descargar Informe en Excel",
            data=to_excel(df_final),
            file_name=f"Auditoria_{anio}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )