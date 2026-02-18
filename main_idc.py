import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from extractor_idc import extraer_datos_idc
import io

st.set_page_config(page_title="LECTOR IDCS", layout="wide")
st.title("📑 LECTOR IDCS")

def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Auditoria')
    return output.getvalue()

if "raw" not in st.session_state: st.session_state.raw = []

with st.sidebar:
    st.header("1. Configuración")
    h_conv = st.number_input("Horas Convenio Anual:", value=1800.0)
    st.markdown("---")
    st.subheader("👤 Datos Autónomos")
    emp_manual = st.text_input("Empresa Cliente:", value="")
    cif_manual = st.text_input("CIF Empresa Cliente:", value="")
    
    files = st.file_uploader("Subir PDFs", type="pdf", accept_multiple_files=True)
    if st.button("🚀 Procesar"):
        if files:
            st.session_state.raw = []
            errores_lectura = [] # Lista para capturar nombres de archivos fallidos
            
            for f in files: 
                datos, texto_completo = extraer_datos_idc(f)
                st.session_state.raw.extend(datos)
                
                # Si el primer dato devuelto tiene "DESCONOCIDO", lo guardamos como error
                if datos and "DESCONOCIDO" in datos[0]["Nombre"]:
                    errores_lectura.append(f.name)
            
            # --- ALERTA DE USABILIDAD ---
            if errores_lectura:
                st.warning(f"⚠️ Se han detectado {len(errores_lectura)} archivos que parecen ser escaneos o imágenes y no se han podido leer correctamente.")
                with st.expander("Ver lista de archivos no leídos"):
                    for err in errores_lectura:
                        st.write(f"❌ {err}")
            else:
                st.success("✅ Todos los archivos se han procesado correctamente.")
            
            # Eliminado: st.text(texto_completo) y st.rerun() para mantener la alerta visible

if st.session_state.raw:
    anio = st.selectbox("2. Seleccionar Año:", [2025, 2024, 2023, 2026])
    nombres_dis = sorted(list({r['Nombre'] for r in st.session_state.raw}))
    seleccion = st.multiselect("3. Filtrar Trabajadores:", options=nombres_dis, default=nombres_dis)

    dias_anio = 366 if (anio % 4 == 0 and (anio % 100 != 0 or anio % 400 == 0)) else 365
    v_h_d = h_conv / dias_anio
    f_limite_ini = datetime(anio, 1, 1)

    res_final = []
    for p in seleccion:
        idcs_p = sorted([r for r in st.session_state.raw if r['Nombre'] == p], key=lambda x: x['Desde_Info'])
        h_t, h_i, d_it, d_alta = 0.0, 0.0, 0, 0
        primer_dia, ultimo_dia = None, None
        hay_hueco = False
        
        es_aut = idcs_p[0].get('Es_Autonomo', False)
        f_contrato_orig = idcs_p[0]['Inicio_Contrato']

        # LÓGICA DE PRODUCCIÓN V3.9: Recorrido diario para trazabilidad
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
                    
                    # CTP: 0 o 1000 = 100%
                    ctp_val = vig.get('CTP', 0)
                    factor = 1.0 if (es_aut or ctp_val in [0, 1000]) else ctp_val / 1000.0
                    
                    h_t += v_h_d * factor
                    if not es_aut and any(it[0] <= dia <= it[1] for it in vig['Tramos_IT']):
                        d_it += 1
                        h_i += v_h_d * factor
            elif deberia_haber_datos:
                hay_hueco = True

        if d_alta > 0:
            # Dedicación: Recuperamos lógica de producción
            ultimo_ctp = idcs_p[-1].get('CTP', 0)
            dedicacion_texto = "100%" if (es_aut or ultimo_ctp in [0, 1000]) else f"{(ultimo_ctp/10):.2f}%"
            
            res_final.append({
                "Nombre": p,
                "DNI": idcs_p[0]['DNI_Trabajador'],
                "CIF Empresa": cif_manual if es_aut else idcs_p[0]['NIF_Empresa'],
                "Empresa": emp_manual if es_aut else idcs_p[0]['Empresa'],
                "Estado": "⚠️ INCOMPLETO" if hay_hueco else "✅ OK",
                "Inicio Contrato": f_contrato_orig.strftime("%d-%m-%Y"),
                "Inicio Auditado": primer_dia.strftime("%d-%m-%Y") if primer_dia else "N/A",
                "Fin Auditado": ultimo_dia.strftime("%d-%m-%Y") if ultimo_dia else "N/A",
                "Días IT": d_it,
                "Horas Teóricas": round(h_t, 2),
                "Horas IT": round(h_i, 2),
                "Horas Efectivas": round(h_t - h_i, 2),
                "Dedicación": dedicacion_texto,
                "Cotización IT": idcs_p[0].get('Cotizacion_IT', 0.0),
                "Cotización IMS": idcs_p[0].get('Cotizacion_IMS', 0.0),
                "Cotización Desempleo": idcs_p[0].get('Cotizacion_Desempleo', 0.0)
            })

    if res_final:
        df_final = pd.DataFrame(res_final)
        st.subheader(f"✅ Informe Auditoría {anio}")
        st.dataframe(df_final, use_container_width=True)
        st.download_button("📥 Descargar Informe en Excel", data=to_excel(df_final), file_name=f"Auditoria_{anio}.xlsx")