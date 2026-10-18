import re

def procesar_remates_masivo(archivo_entrada, archivo_salida):
    print("Iniciando la extracción de los más de 400 códigos... Por favor espera.")
    
    # Leer el archivo de texto completo
    with open(archivo_entrada, 'r', encoding='utf-8', errors='ignore') as f:
        contenido_total = f.read()
    
    # Dividir el archivo por cada bloque de aviso de remate
    bloques = contenido_total.split('===== CODIGO')
    
    resultados = []
    
    for bloque in bloques:
        if not bloque.strip():
            continue
            
        lineas = bloque.strip().split('\n')
        primera_linea = lineas[0]
        
        # Extraer el número identificador del remate (ej. 76868)
        match_codigo = re.search(r'(\d+)\s*=====', primera_linea)
        if not match_codigo:
            continue
        codigo_remate = match_codigo.group(1)
        
        radicado_23 = None
        
        # Buscar el radicado de 23 dígitos inspeccionando línea por línea
        for linea in lineas:
            # Eliminar todos los espacios, guiones y tabulaciones para unir el número
            linea_limpia = re.sub(r'[\s\-]+', '', linea)
            
            # Buscar una secuencia exacta de 23 números continuos (Radicado de la Rama Judicial)
            match_radicado = re.search(r'\d{23}', linea_limpia)
            if match_radicado:
                radicado_23 = match_radicado.group(0)
                break # Pasa al siguiente bloque al encontrar el radicado válido
                
        resultados.append((codigo_remate, radicado_23))
        
    # Generar el archivo final .py con el formato que solicitaste
    with open(archivo_salida, 'w', encoding='utf-8') as f_out:
        f_out.write("# ==========================================================\n")
        f_out.write(f"# LISTA COMPLETA GENERADA AUTOMÁTICAMENTE ({len(resultados)} REGISTROS)\n")
        f_out.write("# ==========================================================\n\n")
        f_out.write("codigos_rama_judicial = [\n")
        
        for codigo_remate, radicado in resultados:
            if radicado:
                f_out.write(f'    "{radicado}",  # {codigo_remate}\n')
            else:
                f_out.write(f'    None,                       # {codigo_remate} (Proceso especial / Sin radicado de 23 dígitos)\n')
                
        f_out.write("]\n")
        
    print(f"¡Proceso finalizado con éxito!")
    print(f"Se analizaron {len(resultados)} avisos y se guardó la lista completa en '{archivo_salida}'.")

# Ejecución del script en tu equipo
# Asegúrate de que el nombre del archivo de entrada coincida exactamente
procesar_remates_masivo("20 mayo todos.txt", "lista_sencilla_remates.py")