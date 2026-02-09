import pdfplumber
import re
from datetime import datetime

def extraer_datos_idc(file_object):
    resultados = []
    with pdfplumber.open(file_object) as pdf:
        texto = ""
        for page in pdf.pages: texto += page.extract_text() + "\n"

        # 1. Identificación básica
        nombre_m = re.search(r"NOMBRE Y APELLIDOS:\s*(.*)", texto)
        nombre = nombre_m.group(1).strip() if nombre_m else "DESCONOCIDO"
        
        dni_m = re.search(r"NUM:\s*(\d+[A-Z]?)", texto)
        dni = dni_m.group(1).strip() if dni_m else "N/A"
        
        alta_m = re.search(r"ALTA:\s*(\d{2}-\d{2}-\d{4})", texto)
        alta = alta_m.group(1).strip() if alta_m else "01-01-1900"
        
        baja_m = re.search(r"BAJA:\s*(\d{2}-\d{2}-\d{4})", texto)
        baja = baja_m.group(1).strip() if baja_m else "ACTIVO"
        
        # 2. CTP (COEFICIENTE) - Flexible
        ctp = 0
        ctp_match = re.search(r"COEF\.?\s*TIEMPO\s*PARCIAL:\s*(\d+)", texto, re.IGNORECASE)
        if ctp_match:
            ctp = int(ctp_match.group(1))

        # 3. Periodo
        per_m = re.search(r"PERIODO:\s*DESDE\s*(\d{2}-\d{2}-\d{4})(?:\s*HASTA\s*(\d{2}-\d{2}-\d{4}))?", texto)
        f_desde = datetime.strptime(per_m.group(1), "%d-%m-%Y") if per_m else datetime.strptime(alta, "%d-%m-%Y")
        f_hasta = datetime.strptime(per_m.group(2), "%d-%m-%Y") if (per_m and per_m.group(2)) else datetime(2099, 12, 31)

        # 4. Tramos de IT (Sólo bajas reales)
        tramos_it = []
        if "TIPO DE PECULIARIDAD" in texto:
            partes = texto.split("TIPO DE PECULIARIDAD")
            if len(partes) > 1:
                bloque = partes[1].split("***")[0]
                for linea in bloque.split("\n"):
                    linea_up = linea.upper()
                    if "BONIFICACION" in linea_up or "INEM" in linea_up: continue
                    if any(x in linea_up for x in ["IT.", "ENFERMEDAD", "ACCIDENTE", "22 "]):
                        fechas = re.findall(r"(\d{2}-\d{2}-\d{4})", linea)
                        if len(fechas) >= 2:
                            try:
                                f_i = datetime.strptime(fechas[-2], "%d-%m-%Y")
                                f_f = datetime.strptime(fechas[-1], "%d-%m-%Y")
                                tramos_it.append((f_i, f_f))
                            except: continue

        resultados.append({
            "Nombre": nombre, "DNI": dni, "CTP": ctp,
            "Desde": f_desde, "Hasta": f_hasta, 
            "Tramos_IT": tramos_it, "Alta": alta, "Baja": baja
        })
    return resultados