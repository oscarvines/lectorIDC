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
        dni = re.search(r"NUM:\s*(\d+[A-Z]?)", texto).group(1).strip()
        alta = re.search(r"ALTA:\s*(\d{2}-\d{2}-\d{4})", texto).group(1).strip()
        baja_m = re.search(r"BAJA:\s*(\d{2}-\d{2}-\d{4})", texto)
        baja = baja_m.group(1).strip() if baja_m else "ACTIVO"
        
        # 2. CTP (COEFICIENTE) - Ahora acepta "COEF." con punto opcional
        ctp = 0
        ctp_match = re.search(r"COEF\.?\s*TIEMPO\s*PARCIAL:\s*(\d+)", texto, re.IGNORECASE)
        if ctp_match:
            ctp = int(ctp_match.group(1))

        # 3. Periodo
        per_m = re.search(r"PERIODO:\s*DESDE\s*(\d{2}-\d{2}-\d{4})(?:\s*HASTA\s*(\d{2}-\d{2}-\d{4}))?", texto)
        if per_m:
            f_desde = datetime.strptime(per_m.group(1), "%d-%m-%Y")
            f_hasta = datetime.strptime(per_m.group(2), "%d-%m-%Y") if per_m.group(2) else datetime(2099, 12, 31)
        else:
            f_desde = datetime.strptime(alta, "%d-%m-%Y")
            f_hasta = datetime(2099, 12, 31)

        # 4. Tramos de IT (Bajas reales)
        tramos_it = []
        if "TIPO DE PECULIARIDAD" in texto:
            bloque = texto.split("TIPO DE PECULIARIDAD")[1].split("***FIN DE PECULIARIDADES***")[0]
            
            for linea in bloque.split("\n"):
                linea_up = linea.upper()
                # FILTRO RIGUROSO:
                # 1. Buscamos códigos de IT real (Suelen empezar por 22 o tener "IT.")
                # 2. Excluimos explícitamente BONIFICACIONES
                es_it_real = "IT." in linea_up or "22 " in linea_up or "ENFERMEDAD" in linea_up
                es_bonif = "BONIFICACION" in linea_up or "INEM" in linea_up
                
                if es_it_real and not es_bonif:
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