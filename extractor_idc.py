import pdfplumber
import re
from datetime import datetime

def extraer_datos_idc(file_object):
    resultados = []
    with pdfplumber.open(file_object) as pdf:
        texto = ""
        for page in pdf.pages: texto += page.extract_text() + "\n"

        # 1. Identificación
        nombre = re.search(r"NOMBRE Y APELLIDOS:\s*(.*)", texto).group(1).strip()
        # Fecha ALTA (campo administrativo)
        alta = re.search(r"ALTA:\s*(\d{2}-\d{2}-\d{4})", texto).group(1).strip()
        
        # 2. Fecha Inicio Contrato Real (Buscamos el patrón FECHA: que mencionas)
        # Priorizamos el campo "FECHA:" que suele ser el inicio de la relación
        fecha_con_m = re.search(r"FECHA:\s*(\d{2}-\d{2}-\d{4})", texto)
        inicio_contrato = fecha_con_m.group(1).strip() if fecha_con_m else alta

        baja_m = re.search(r"BAJA:\s*(\d{2}-\d{2}-\d{4})", texto)
        baja = baja_m.group(1).strip() if baja_m else "ACTIVO"
        
        # 3. CTP y Periodo IDC
        ctp = 0
        ctp_match = re.search(r"COEF\.?\s*TIEMPO\s*PARCIAL:\s*(\d+)", texto, re.IGNORECASE)
        if ctp_match: ctp = int(ctp_match.group(1))

        per_m = re.search(r"PERIODO:\s*DESDE\s*(\d{2}-\d{2}-\d{4})(?:\s*HASTA\s*(\d{2}-\d{2}-\d{4}))?", texto)
        f_desde_info = datetime.strptime(per_m.group(1), "%d-%m-%Y") if per_m else datetime.strptime(alta, "%d-%m-%Y")
        f_hasta_info = datetime.strptime(per_m.group(2), "%d-%m-%Y") if (per_m and per_m.group(2)) else datetime(2099, 12, 31)

        # 4. Tramos de IT
        tramos_it = []
        if "TIPO DE PECULIARIDAD" in texto:
            bloque = texto.split("TIPO DE PECULIARIDAD")[1].split("***")[0]
            for linea in bloque.split("\n"):
                if any(x in linea.upper() for x in ["IT.", "ENFERMEDAD", "ACCIDENTE", "22 "]) and "BONIF" not in linea.upper():
                    fechas = re.findall(r"(\d{2}-\d{2}-\d{4})", linea)
                    if len(fechas) >= 2:
                        tramos_it.append((datetime.strptime(fechas[-2], "%d-%m-%Y"), datetime.strptime(fechas[-1], "%d-%m-%Y")))

        resultados.append({
            "Nombre": nombre, "CTP": ctp,
            "Desde_Info": f_desde_info, "Hasta_Info": f_hasta_info, 
            "Inicio_Contrato": datetime.strptime(inicio_contrato, "%d-%m-%Y"),
            "Tramos_IT": tramos_it, "Alta": alta, "Baja": baja
        })
    return resultados