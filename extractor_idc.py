import pdfplumber
import re
import pandas as pd
from datetime import datetime

def extraer_datos_idc(file_object):
    resultados = []
    with pdfplumber.open(file_object) as pdf:
        texto_completo = ""
        for page in pdf.pages:
            texto_completo += page.extract_text() + "\n"

        # --- 1. CABECERA ---
        nombre = (re.search(r"NOMBRE Y APELLIDOS:\s*(.*)", texto_completo).group(1).strip() if re.search(r"NOMBRE Y APELLIDOS:\s*(.*)", texto_completo) else "N/A")
        dni = (re.search(r"NUM:\s*(\d+[A-Z]?)", texto_completo).group(1).strip() if re.search(r"NUM:\s*(\d+[A-Z]?)", texto_completo) else "N/A")
        alta = (re.search(r"ALTA:\s*(\d{2}-\d{2}-\d{4})", texto_completo).group(1).strip() if re.search(r"ALTA:\s*(\d{2}-\d{2}-\d{4})", texto_completo) else "N/A")
        baja = (re.search(r"BAJA:\s*(\d{2}-\d{2}-\d{4})", texto_completo).group(1).strip() if re.search(r"BAJA:\s*(\d{2}-\d{2}-\d{4})", texto_completo) else "TRABAJADOR EN ACTIVO")
        contrato = (re.search(r"T\.CONTRATO:\s*(\d+)", texto_completo).group(1).strip() if re.search(r"T\.CONTRATO:\s*(\d+)", texto_completo) else "N/A")
        gc = (re.search(r"GC/M\s*(\d+)", texto_completo).group(1).strip() if re.search(r"GC/M\s*(\d+)", texto_completo) else "N/A")

        # --- 2. TIPOS DE COTIZACIÓN (Corrección I.M.S / L.M.S) ---
        tipo_it = (re.search(r"IT:\s*([\d,]+)", texto_completo).group(1) if re.search(r"IT:\s*([\d,]+)", texto_completo) else "0,00")
        
        # Buscamos tanto I.M.S. como L.M.S. por si el lector de PDF confunde la letra
        ims_match = re.search(r"(?:I|L)\.?\s*M\.?\s*S\.?:\s*([\d,]+)", texto_completo)
        tipo_ims = ims_match.group(1) if ims_match else "0,00"
        
        tipo_des = (re.search(r"DESEMPLEO:\s*([\d,]+)", texto_completo).group(1) if re.search(r"DESEMPLEO:\s*([\d,]+)", texto_completo) else "0,00")

        # --- 3. PECULIARIDADES ---
        tramos_encontrados = False
        lineas = texto_completo.split('\n')
        for line in lineas:
            fechas = re.findall(r"(\d{2}-\d{2}-\d{2,4})", line)
            if len(fechas) >= 2:
                try:
                    if "REFERENCIA" in line or "Tesorería" in line: continue
                    f_ini_str, f_fin_str = fechas[-2], fechas[-1]
                    fmt_ini = "%d-%m-%y" if len(f_ini_str.split('-')[-1]) == 2 else "%d-%m-%Y"
                    fmt_fin = "%d-%m-%y" if len(f_fin_str.split('-')[-1]) == 2 else "%d-%m-%Y"
                    f_ini = datetime.strptime(f_ini_str, fmt_ini)
                    f_fin = datetime.strptime(f_fin_str, fmt_fin)
                    valor_m = re.search(r"(\d+,\d{2})", line)
                    valor = valor_m.group(1) if valor_m else "0,00"

                    # Limpieza de concepto
                    con = line
                    for f in fechas: con = con.replace(f, "")
                    con = re.sub(r"^\d+\s+", "", con)
                    con = re.sub(r"\s+[A-Z0-9]{3}$", "", con).strip()
                    if not con or "***" in con or "TIPO DE" in con: continue

                    for anio in range(f_ini.year, f_fin.year + 1):
                        tramos_encontrados = True
                        resultados.append({
                            "DNI": dni, "Nombre": nombre, "Alta": alta, "Baja": baja,
                            "Contrato": contrato, "GC": gc, "Peculiaridad": con,
                            "Inicio": max(f_ini, datetime(anio, 1, 1)).strftime("%d-%m-%Y"),
                            "Fin": min(f_fin, datetime(anio, 12, 31)).strftime("%d-%m-%Y"),
                            "Días": (min(f_fin, datetime(anio, 12, 31)) - max(f_ini, datetime(anio, 1, 1))).days + 1,
                            "Año": anio, "Valor %": valor, "Tipo IT": tipo_it, "Tipo IMS": tipo_ims, "Tipo Desempleo": tipo_des
                        })
                except: continue

        if not tramos_encontrados:
            resultados.append({
                "DNI": dni, "Nombre": nombre, "Alta": alta, "Baja": baja,
                "Contrato": contrato, "GC": gc, "Peculiaridad": "SITUACIÓN NORMAL",
                "Inicio": alta, "Fin": "-", "Días": 0, "Año": 2025, "Valor %": "0,00",
                "Tipo IT": tipo_it, "Tipo IMS": tipo_ims, "Tipo Desempleo": tipo_des
            })
    return resultados