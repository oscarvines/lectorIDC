import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from extractor_idc import extraer_datos_idc
import io
from st_supabase_connection import SupabaseConnection

st.set_page_config(page_title="Auditoría V4.9 - Registro CIF", layout="wide")
st.title("📑 Auditoría Laboral (V4.9 - Trazabilidad CIF)")

# --- CONEXIÓN A SUPABASE ---
conn = st.connection("supabase", type=SupabaseConnection)

# --- FUNCIONES DE APOYO ---

def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Auditoria')
    return output.getvalue()

def sincronizar_historial_supabase(datos_raw, h_conv):
    anios_a_procesar = [2022, 2023, 2024, 2025, 2026]
    registros_totales = []
    
    progreso_bar = st.progress(0)
    status_text = st.empty()
    
    for idx, anio_proc in enumerate(anios_a_procesar):
        status_text.text(f"⏳ Procesando ejercicio {anio_proc}...")
        
        dias_anio = 366 if (anio_proc % 4 == 0 and (anio_proc % 100 != 0 or anio_proc % 400 == 0)) else 365
        v_h_d = h_conv / dias_anio
        f_limite_ini = datetime(anio_proc, 1, 1)
        
        nombres = {r['Nombre'] for r in datos_raw}
        for p in nombres:
            idcs_p = sorted([r for r in datos_raw if r['Nombre'] == p], key=lambda x: x['Desde_Info'])
            h_t, h_i, d_it, d_alta = 0.0, 0.0, 0, 0
            primer_dia, ultimo_dia, hay_hueco = None, None, False
            f_contrato_orig = idcs_p[0]['Inicio_Contrato']
            
            for d in range(dias_anio):
                dia = f_limite_ini + timedelta(days=d)
                vig = next((i for i in reversed(idcs_p) if i['Desde_Info'] <= dia <= i['Hasta_Info']), None)
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
                elif f_contrato_orig <= dia:
                    hay_hueco = True

            if d_alta > 0:
                # Calculamos el CTP medio o tomamos el del último registro vigente
                ultimo_ctp = idcs_p[-1]['CTP'] 
                registros_totales.append({
                    "ejercicio": anio_proc,
                    "nif": idcs_p[0]['DNI_Trabajador'],
                    "nombre": p,
                    "nif_empresa": idcs_p[0]['NIF_Empresa'],
                    "cliente": idcs_p[0]['Empresa'],
                    "ctp": ultimo_ctp, # <--- AÑADE ESTO PARA SUPABASE
                    "estado": "⚠️ INCOMPLETO" if hay_hueco else "✅ OK",
                    "inicio_contrato": f_contrato_orig.strftime("%Y-%m-%d"),
                    "inicio_auditado": primer_dia.strftime("%Y-%m-%d"),
                    "fin_auditado": ultimo_dia.strftime("%Y-%m-%d"),
                    "dias_it": d_it,
                    "horas_teoricas": round(h_t, 2),
                    "horas_it": round(h_i, 2),
                    "horas_efectivas": round(h_t - h_i, 2)
                })
        progreso_bar.progress((idx + 1) / len(anios_a_procesar))

    if registros_totales:
        try:
            conn.table("resumen_idcs_central").upsert(
                registros_totales, 
                on_conflict='nif,ejercicio'
            ).execute()
            status_text.text(f"✅ ¡Éxito! {len(registros_totales)} registros sincronizados (2022-2026).")
            st.balloons()
        except Exception as e:
            st.error(f"❌ Error al guardar en Supabase: {e}")

# --- BARRA LATERAL ---

with st.sidebar:
    st.header("1. Configuración")
    h_conv = st.number_input("Horas Convenio Anual (100%):", value=1800.0)
    files = st.file_uploader("Subir PDFs", type="pdf", accept_multiple_files=True)
    if st.button("🚀 Calcular Auditoría"):
        if files:
            st.session_state.raw = []
            for f in files: st.session_state.raw.extend(extraer_datos_idc(f))
            st.rerun()

# --- LÓGICA PRINCIPAL ---

if 'raw' in st.session_state and st.session_state.raw:
    anio = st.selectbox("2. Seleccionar Año para Visualizar:", [2026, 2025, 2024, 2023, 2022])
    
    nombres_dis = sorted(list({r['Nombre'] for r in st.session_state.raw}))
    seleccion = st.multiselect("3. Filtrar Trabajadores:", options=nombres_dis, default=nombres_dis)

    dias_anio = 366 if (anio % 4 == 0 and (anio % 100 != 0 or anio % 400 == 0)) else 365
    v_h_d = h_conv / dias_anio
    f_limite_ini = datetime(anio, 1, 1)

    res_final = []
    for p in seleccion:
        idcs_p = sorted([r for r in st.session_state.raw if r['Nombre'] == p], key=lambda x: x['Desde_Info'])
        h_t, h_i, d_it, d_alta = 0.0, 0.0, 0, 0
        primer_dia, ultimo_dia, hay_hueco = None, None, False
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
            # Extraemos el CTP del último IDC de este trabajador para mostrarlo
            ctp_valor = idcs_p[-1]['CTP']
            dedicacion_texto = f"{ctp_valor / 10}%" if ctp_valor > 0 else "100%"
            res_final.append({
                "Nombre": p,
                "DNI": idcs_p[0]['DNI_Trabajador'],
                "CIF Empresa": idcs_p[0]['NIF_Empresa'],
                "Empresa": idcs_p[0]['Empresa'],
                "Estado": "⚠️ INCOMPLETO" if hay_hueco else "✅ OK",
                "Inicio Contrato": f_contrato_orig.strftime("%d-%m-%Y"),
                "Inicio Auditado": primer_dia.strftime("%d-%m-%Y"),
                "Fin Auditado": ultimo_dia.strftime("%d-%m-%Y"),
                "Días IT": d_it,
                "Horas Teóricas": round(h_t, 2),
                "Horas IT": round(h_i, 2),
                "Horas Efectivas": round(h_t - h_i, 2),
                "Dedicación": dedicacion_texto  # <--- ESTA ES LA LÍNEA NUEVA
            })
    if res_final:
        df_final = pd.DataFrame(res_final)
        st.subheader(f"✅ Vista Previa Auditoría {anio}")
        st.dataframe(df_final, use_container_width=True)
        
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                label="📥 Descargar Excel (Año Actual)",
                data=to_excel(df_final),
                file_name=f"Auditoria_{anio}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        with col2:
            if st.button("📤 Sincronizar Histórico 2022-2026 en Supabase"):
                sincronizar_historial_supabase(st.session_state.raw, h_conv)