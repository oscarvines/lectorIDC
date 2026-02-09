import pdfplumber
import re

def generar_auditoria_texto(pdf_path):
    archivo_salida = "analisis_claudia.txt"
    print(f"--- Iniciando análisis de: {pdf_path} ---")
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            # Extraemos el texto de la primera página
            texto = pdf.pages[0].extract_text()
            
            # Guardamos TODO el texto en un archivo TXT para que lo revises
            with open(archivo_salida, "w", encoding="utf-8") as f:
                f.write("=== EXTRACCIÓN COMPLETA DEL PDF (LO QUE VE LA MÁQUINA) ===\n\n")
                f.write(texto)
                f.write("\n\n" + "="*50 + "\n")
                f.write("=== ANÁLISIS DE PUNTOS CRÍTICOS ===\n")
                
                # Análisis de Coeficiente
                if "COEF TIEMPO PARCIAL" in texto:
                    pos = texto.find("COEF TIEMPO PARCIAL")
                    ventana = texto[pos:pos+100]
                    f.write(f"\n[!] COEFICIENTE DETECTADO:\n'{ventana}'\n")
                
                # Análisis de Bajas
                if "TIPO DE PECULIARIDAD" in texto:
                    pos_t = texto.find("TIPO DE PECULIARIDAD")
                    f.write(f"\n[!] SECCIÓN PECULIARIDADES:\n{texto[pos_t:pos_t+500]}\n")

        print(f"✅ ¡Hecho! Se ha creado el archivo '{archivo_salida}'.")
        print("Ábrelo con el Bloc de notas o TextEdit para ver el contenido real.")

    except Exception as e:
        print(f"❌ Error al procesar el PDF: {e}")

# Asegúrate de que este nombre coincide con tu archivo en la carpeta
generar_auditoria_texto("04. Claudia 3.pdf")