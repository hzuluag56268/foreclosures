from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

URL_NUMERO_RADICACION = "https://consultaprocesos.ramajudicial.gov.co/Procesos/NumeroRadicacion"
API_NUMERO_RADICACION = (
    "https://consultaprocesos.ramajudicial.gov.co:448/api/v2/Procesos/Consulta/NumeroRadicacion"
)
API_BASE = "https://consultaprocesos.ramajudicial.gov.co:448/api/v2"
OUT_DEFAULT = Path(__file__).resolve().parent / "resultados_rama_judicial.json"
IN_DEFAULT = Path(__file__).resolve().parent / "radicados.json"
WAIT_SECONDS = 25
RETRY_PER_RADICADO = 2
CAPTCHA_MARKERS = (
    "captcha",
    "reCAPTCHA",
    "no soy un robot",
    "valide que no es un robot",
)

# Radicados (23 dígitos) cuando no pasas códigos por la línea de comandos.
# Si esta lista está vacía, se intenta leer radicados.json (véase --input-file).
radicados: list[int | str]     = [
    "11001310301520240031800", # Código 80737 - Modelia (Fontibón)
    "11001310301420160075000", # Código 80724 - Villa Alsacia (Occidente)
    "11001310303120150055300", # Código 80325 - Castilla (Kennedy)
    "11001310300420210034000", # Código 81084 - Zapán de Castilla
    "11001400305720240110600", # Código 80729 - Res. San Agustín
    "11001310303120220035600", # Código 80772 - Colina 129 (Suba)
    "25175400300220160025100"  # Código 80770 - Chía (Av Chilacos)
]



def build_driver(headless: bool) -> webdriver.Chrome:
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1600,1000")
    options.add_argument("--lang=es-CO")
    options.add_argument("--no-sandbox")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    )
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)


def normalize_radicado(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", "", str(value))


def validate_radicado(radicado: str) -> str | None:
    if not radicado:
        return "radicado vacío"
    if not radicado.isdigit():
        return "el radicado debe contener solo dígitos"
    if len(radicado) != 23:
        return "el radicado debe tener exactamente 23 dígitos"
    return None


def load_radicados(args: argparse.Namespace) -> list[str]:
    if args.radicados:
        return [normalize_radicado(item) for item in args.radicados]

    if radicados:
        return [normalize_radicado(item) for item in radicados]

    source = Path(args.input_file) if args.input_file else IN_DEFAULT
    if not source.is_file():
        return []

    data = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("El archivo de entrada debe contener un arreglo JSON.")
    return [normalize_radicado(item) for item in data]


def detect_captcha(page_source: str) -> bool:
    lower_text = page_source.lower()
    return any(marker.lower() in lower_text for marker in CAPTCHA_MARKERS)


def wait_manual_captcha_resolution(driver: webdriver.Chrome, radicado: str) -> None:
    print(
        "\nSe detectó posible CAPTCHA o validación visual.\n"
        f"Radicado: {radicado}\n"
        "Resuélvelo manualmente en la ventana de Chrome y luego pulsa ENTER para continuar..."
    )
    try:
        input()
    except EOFError:
        print("No se recibió ENTER. Continuando de todas formas...", file=sys.stderr)
    driver.switch_to.default_content()


def visible_text(tag: Any) -> str:
    return " ".join(tag.get_text(" ", strip=True).split())


def extract_tables(soup: BeautifulSoup) -> list[dict[str, Any]]:
    tables: list[dict[str, Any]] = []
    for table in soup.select("table"):
        rows = []
        for tr in table.select("tr"):
            cells = tr.select("th, td")
            row = [visible_text(cell) for cell in cells if visible_text(cell)]
            if row:
                rows.append(row)
        if rows:
            tables.append({"rows": rows})
    return tables


def extract_key_values(soup: BeautifulSoup) -> dict[str, str]:
    key_values: dict[str, str] = {}
    for row in soup.select("div.row, li, p"):
        text = visible_text(row)
        if ":" not in text:
            continue
        key, value = text.split(":", 1)
        key = key.strip()
        value = value.strip()
        if key and value and len(key) <= 60 and len(value) <= 250:
            if key not in key_values:
                key_values[key] = value
    return key_values


def extract_sections(soup: BeautifulSoup) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    section_candidates = soup.select("section, .card, .panel, .accordion-item")
    for idx, node in enumerate(section_candidates):
        title_node = node.select_one("h1, h2, h3, h4, .card-title, .panel-title")
        title = visible_text(title_node) if title_node else f"seccion_{idx + 1}"
        text = visible_text(node)
        if not text:
            continue
        sections.append(
            {
                "titulo": title,
                "texto": text[:3000],
            }
        )
    return sections


def parse_result_page(driver: webdriver.Chrome, radicado: str) -> dict[str, Any]:
    soup = BeautifulSoup(driver.page_source, "html.parser")
    try:
        body_text = driver.find_element(By.TAG_NAME, "body").text.strip()
    except Exception:
        body_text = visible_text(soup.body) if soup.body else ""
    lower_body_text = body_text.lower()
    has_empty_message = any(
        marker in lower_body_text
        for marker in (
            "no se encontraron resultados",
            "no existe información",
            "sin resultados",
        )
    )
    # El texto del bloque noscript puede existir en el HTML aunque JS sí esté activo.
    # Solo marcamos error si no hay señales de interfaz interactiva cargada.
    has_js_disabled_page = (
        "no funciona correctamente sin javascript habilitado" in lower_body_text
        and "consultar" not in lower_body_text
    )
    data = {
        "url": driver.current_url,
        "titulo_pagina": visible_text(soup.title) if soup.title else "",
        "resumen": body_text[:2000],
        "campos": extract_key_values(soup),
        "tablas": extract_tables(soup),
        "secciones": extract_sections(soup),
    }
    state = "ok"
    message = "consulta exitosa"
    if has_js_disabled_page:
        state = "error_consulta"
        message = (
            "la página devolvió el mensaje de JavaScript deshabilitado; "
            "intenta de nuevo en modo visible con --headed"
        )
    if has_empty_message and not data["tablas"] and not data["campos"]:
        state = "no_encontrado"
        message = "no se encontró información para el radicado"

    return {
        "radicado": radicado,
        "estado": state,
        "mensaje": message,
        "datos": data,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }


def _clean_proceso_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "idProceso": row.get("idProceso"),
        "idConexion": row.get("idConexion"),
        "llaveProceso": row.get("llaveProceso"),
        "fechaProceso": row.get("fechaProceso"),
        "fechaUltimaActuacion": row.get("fechaUltimaActuacion"),
        "despacho": row.get("despacho"),
        "departamento": row.get("departamento"),
        "sujetosProcesales": row.get("sujetosProcesales"),
        "esPrivado": row.get("esPrivado"),
    }


def parse_api_payload(payload: Any, include_payload: bool) -> dict[str, Any]:
    if isinstance(payload, list):
        clean_rows = [item for item in payload if isinstance(item, dict)]
        return {
            "cantidad": len(clean_rows),
            "registros": [_clean_proceso_row(item) for item in clean_rows],
        }
    if isinstance(payload, dict):
        records = None
        for key in ("procesos", "resultado", "data", "items", "registros"):
            value = payload.get(key)
            if isinstance(value, list):
                records = value
                break
        normalized = records if isinstance(records, list) else [payload]
        clean_rows = [item for item in normalized if isinstance(item, dict)]
        response = {
            "cantidad": len(clean_rows),
            "registros": [_clean_proceso_row(item) for item in clean_rows],
        }
        if include_payload:
            response["payload"] = payload
        return {
            **response
        }
    base = {"cantidad": 0, "registros": []}
    if include_payload:
        base["payload"] = payload
    return base


def fetch_api_with_browser_session(
    driver: webdriver.Chrome, radicado: str, solo_activos: bool = True, pagina: int = 1
) -> dict[str, Any]:
    return fetch_api_path_with_browser_session(
        driver=driver,
        api_path="/Procesos/Consulta/NumeroRadicacion",
        params={
            "numero": radicado,
            "SoloActivos": "true" if solo_activos else "false",
            "pagina": str(pagina),
        },
    )


def fetch_api_path_with_browser_session(
    driver: webdriver.Chrome, api_path: str, params: dict[str, str] | None = None
) -> dict[str, Any]:
    cookies = {item["name"]: item["value"] for item in driver.get_cookies() if "name" in item and "value" in item}
    user_agent = driver.execute_script("return navigator.userAgent")
    headers = {
        "User-Agent": user_agent,
        "Referer": URL_NUMERO_RADICACION,
        "Origin": "https://consultaprocesos.ramajudicial.gov.co",
        "Accept": "application/json, text/plain, */*",
    }
    target_url = f"{API_BASE}{api_path}"
    try:
        response = requests.get(
            target_url,
            params=params,
            headers=headers,
            cookies=cookies,
            timeout=30,
        )
    except Exception as exc:
        return {
            "ok": False,
            "status": 0,
            "url": target_url,
            "text": "",
            "json": None,
            "error": str(exc),
        }

    json_data = None
    try:
        json_data = response.json()
    except Exception:
        json_data = None
    return {
        "ok": response.ok,
        "status": response.status_code,
        "url": response.url,
        "text": response.text,
        "json": json_data,
    }


def clean_actuacion_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "idRegActuacion": row.get("idRegActuacion"),
        "consActuacion": row.get("consActuacion"),
        "fechaActuacion": row.get("fechaActuacion"),
        "actuacion": row.get("actuacion"),
        "anotacion": row.get("anotacion"),
        "fechaInicial": row.get("fechaInicial"),
        "fechaFinal": row.get("fechaFinal"),
        "fechaRegistro": row.get("fechaRegistro"),
        "conDocumentos": row.get("conDocumentos"),
    }


def fetch_actuaciones_for_proceso(
    driver: webdriver.Chrome, id_proceso: int | None, max_paginas_actuaciones: int
) -> dict[str, Any]:
    if not id_proceso:
        return {"cantidad": 0, "actuaciones": [], "paginacion": {}}

    actuaciones: list[dict[str, Any]] = []
    paginacion: dict[str, Any] = {}
    total_paginas = 1
    pagina = 1
    while pagina <= total_paginas and pagina <= max_paginas_actuaciones:
        result = fetch_api_path_with_browser_session(
            driver=driver,
            api_path=f"/Proceso/Actuaciones/{id_proceso}",
            params={"pagina": str(pagina)},
        )
        if not result.get("ok") or not isinstance(result.get("json"), dict):
            break
        payload = result["json"]
        rows = payload.get("actuaciones") if isinstance(payload.get("actuaciones"), list) else []
        actuaciones.extend(clean_actuacion_row(item) for item in rows if isinstance(item, dict))
        paginacion = payload.get("paginacion", {}) if isinstance(payload.get("paginacion"), dict) else {}
        total_paginas = int(paginacion.get("cantidadPaginas") or 1)
        pagina += 1

    return {"cantidad": len(actuaciones), "actuaciones": actuaciones, "paginacion": paginacion}


def locate_input_and_search(driver: webdriver.Chrome, radicado: str) -> None:
    wait = WebDriverWait(driver, WAIT_SECONDS)
    candidates = (
        (By.CSS_SELECTOR, "input[maxlength='23']"),
        (By.CSS_SELECTOR, "input[formcontrolname*='radicacion']"),
        (By.CSS_SELECTOR, "input[placeholder*='Radicaci']"),
        (By.CSS_SELECTOR, "input[placeholder*='radicaci']"),
        (By.CSS_SELECTOR, "input[type='text']"),
    )
    last_error: Exception | None = None
    search_input = None
    for selector in candidates:
        try:
            search_input = wait.until(EC.visibility_of_element_located(selector))
            if search_input:
                break
        except Exception as exc:
            last_error = exc
    if not search_input:
        raise TimeoutException("No fue posible ubicar el campo de radicación.") from last_error

    search_input.clear()
    search_input.send_keys(radicado)

    button_selectors = (
        (By.CSS_SELECTOR, "button.success"),
        (By.CSS_SELECTOR, "button[type='submit']"),
        (By.XPATH, "//button[contains(., 'Consultar')]"),
        (By.XPATH, "//button[contains(., 'CONSULTAR')]"),
        (By.XPATH, "//button[contains(., 'Buscar')]"),
        (By.CSS_SELECTOR, "input[type='submit']"),
    )
    last_button_error: Exception | None = None
    for selector in button_selectors:
        try:
            button = wait.until(EC.element_to_be_clickable(selector))
            button.click()
            return
        except Exception as exc:
            last_button_error = exc
    raise TimeoutException("No fue posible ubicar el botón de búsqueda.") from last_button_error


def wait_for_results_or_captcha(driver: webdriver.Chrome, radicado: str) -> None:
    deadline = time.time() + WAIT_SECONDS
    while time.time() < deadline:
        html = driver.page_source
        if detect_captcha(html):
            wait_manual_captcha_resolution(driver, radicado)
            deadline = time.time() + WAIT_SECONDS
            continue

        try:
            visible_lower = driver.find_element(By.TAG_NAME, "body").text.lower()
        except Exception:
            visible_lower = html.lower()
        if any(
            marker in visible_lower
            for marker in (
                "actuaciones",
                "sujetos procesales",
                "detalle del proceso",
                "no se encontraron resultados",
                "resultado de la consulta",
                "clase de proceso",
                "despacho",
            )
        ):
            return
        time.sleep(1)


def consultar_radicado(
    driver: webdriver.Chrome,
    radicado: str,
    solo_activos: bool,
    include_payload: bool,
    include_actuaciones: bool,
    max_paginas_actuaciones: int,
) -> dict[str, Any]:
    for attempt in range(1, RETRY_PER_RADICADO + 1):
        try:
            driver.get(URL_NUMERO_RADICACION)
            
            # --- MODIFICACIÓN: Lógica de doble intento en la API ---
            # Si solo_activos es True (comportamiento por defecto), intentamos [True, False].
            # Si el usuario ejecutó con --todos (False), solo intentamos [False].
            intentos_activos = [True, False] if solo_activos else [False]
            
            for flag_activo in intentos_activos:
                api_result = fetch_api_with_browser_session(
                    driver, radicado, solo_activos=flag_activo
                )
                
                if api_result.get("ok") and api_result.get("json") is not None:
                    parsed = parse_api_payload(api_result["json"], include_payload=include_payload)
                    
                    # Si no encontró resultados en "actuaciones recientes" (True), 
                    # evitamos retornar "no_encontrado" y saltamos a buscar en "Todos los procesos" (False)
                    if parsed["cantidad"] == 0 and flag_activo is True:
                        print(f"  > Sin resultados recientes para {radicado}. Reintentando búsqueda en 'Todos los procesos'...")
                        continue 
                    
                    # Si encontró información o si ya estamos en la búsqueda de "Todos los procesos", 
                    # procesamos las actuaciones como de costumbre.
                    if include_actuaciones:
                        for registro in parsed.get("registros", []):
                            if not isinstance(registro, dict):
                                continue
                            registro["actuaciones"] = fetch_actuaciones_for_proceso(
                                driver,
                                registro.get("idProceso"),
                                max_paginas_actuaciones=max_paginas_actuaciones,
                            )
                            
                    if parsed["cantidad"] == 0:
                        return {
                            "radicado": radicado,
                            "estado": "no_encontrado",
                            "mensaje": "no se encontró información para el radicado en ninguna de las opciones",
                            "datos": {
                                "url": api_result.get("url", API_NUMERO_RADICACION),
                                "api_status": api_result.get("status"),
                                "api_response": parsed,
                            },
                            "timestamp": datetime.now().isoformat(timespec="seconds"),
                        }
                        
                    return {
                        "radicado": radicado,
                        "estado": "ok",
                        "mensaje": "consulta exitosa",
                        "datos": {
                            "url": api_result.get("url", API_NUMERO_RADICACION),
                            "api_status": api_result.get("status"),
                            "api_response": parsed,
                        },
                        "timestamp": datetime.now().isoformat(timespec="seconds"),
                    }

            # Fallback al flujo de UI si la API no responde/deniega.
            locate_input_and_search(driver, radicado)
            wait_for_results_or_captcha(driver, radicado)
            parsed_ui = parse_result_page(driver, radicado)
            if parsed_ui.get("datos", {}).get("tablas") or parsed_ui.get("datos", {}).get("campos"):
                return parsed_ui
            return {
                "radicado": radicado,
                "estado": "error_consulta",
                "mensaje": (
                    "la API devolvió estado "
                    f"{api_result.get('status')} y la UI no mostró datos extraíbles"
                ),
                "datos": {
                    "url": parsed_ui.get("datos", {}).get("url", URL_NUMERO_RADICACION),
                    "api_status": api_result.get("status"),
                    "api_error": api_result.get("error"),
                    "api_preview": (api_result.get("text") or "")[:500],
                    "ui_preview": (parsed_ui.get("datos", {}).get("resumen") or "")[:1000],
                },
                "timestamp": datetime.now().isoformat(timespec="seconds"),
            }
        except Exception as exc:
            if attempt >= RETRY_PER_RADICADO:
                return {
                    "radicado": radicado,
                    "estado": "error_consulta",
                    "mensaje": f"falló la consulta tras {attempt} intento(s): {exc}",
                    "datos": {},
                    "timestamp": datetime.now().isoformat(timespec="seconds"),
                }
            time.sleep(1.5)
    return {
        "radicado": radicado,
        "estado": "error_consulta",
        "mensaje": "error inesperado",
        "datos": {},
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }


def run(
    radicados: list[str],
    out_file: Path,
    headless: bool,
    solo_activos: bool,
    include_payload: bool,
    include_actuaciones: bool,
    max_paginas_actuaciones: int,
) -> int:
    resultados: list[dict[str, Any]] = []
    driver = build_driver(headless=headless)
    try:
        for radicado in radicados:
            error = validate_radicado(radicado)
            if error:
                resultados.append(
                    {
                        "radicado": radicado,
                        "estado": "error_validacion",
                        "mensaje": error,
                        "datos": {},
                        "timestamp": datetime.now().isoformat(timespec="seconds"),
                    }
                )
                continue

            print(f"Consultando radicado: {radicado}")
            resultados.append(
                consultar_radicado(
                    driver,
                    radicado,
                    solo_activos=solo_activos,
                    include_payload=include_payload,
                    include_actuaciones=include_actuaciones,
                    max_paginas_actuaciones=max_paginas_actuaciones,
                )
            )
    finally:
        driver.quit()

    json_data = json.dumps(resultados, ensure_ascii=False, indent=2)
    try:
        out_file.write_text(json_data, encoding="utf-8")
    except PermissionError:
        # Crea un nombre de archivo alternativo usando la fecha y hora actual
        fallback_file = out_file.with_name(f"resultados_backup_{int(time.time())}.json")
        fallback_file.write_text(json_data, encoding="utf-8")
        print(f"\n⚠️ Advertencia: No se pudo escribir en {out_file.name} porque está bloqueado.")
        print(f"✅ Los datos se guardaron a salvo en: {fallback_file.name}")

    # Agrupamos los radicados según su estado
    radicados_ok = [r["radicado"] for r in resultados if r.get("estado") == "ok"]
    radicados_no_encontrados = [r["radicado"] for r in resultados if r.get("estado") == "no_encontrado"]
    radicados_errores = [r for r in resultados if r.get("estado") not in ("ok", "no_encontrado")]
    
    total = len(resultados)
    ok = len(radicados_ok)
    not_found = len(radicados_no_encontrados)
    errors = len(radicados_errores)
    
    # Imprimimos el reporte detallado
    print("\n" + "="*50)
    print("📋 RESUMEN DEL PROCESO")
    print("="*50)
    print(f"Total consultados: {total}\n")
    
    print(f"✅ OK: {ok}")
    for rad in radicados_ok:
        print(f"   - {rad}")
        
    print(f"\n🔎 No encontrados: {not_found}")
    for rad in radicados_no_encontrados:
        print(f"   - {rad}")
        
    print(f"\n❌ Errores: {errors}")
    for err in radicados_errores:
        estado = err.get("estado", "error_desconocido")
        mensaje = err.get("mensaje", "Sin detalles")
        print(f"   - Radicado: {err.get('radicado')}")
        print(f"     Tipo: {estado} | Detalle: {mensaje}")
        
    print("\n" + "-" * 50)
    print(f"📁 Archivo JSON guardado en: {out_file}")
    
    return 0 if errors == 0 else 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Consulta procesos judiciales por número de radicación (23 dígitos) "
            "en la Rama Judicial y exporta resultados a JSON."
        )
    )
    parser.add_argument(
        "radicados",
        nargs="*",
        help="Lista de radicados de 23 dígitos. Si no se envían, usa la lista `radicados` "
        "en este archivo; si está vacía, --input-file.",
    )
    parser.add_argument(
        "-i",
        "--input-file",
        type=Path,
        default=IN_DEFAULT,
        help=(
            f"Archivo JSON con arreglo de radicados si no hay argumentos CLI "
            f"y la lista `radicados` en el script está vacía (por defecto: {IN_DEFAULT.name})."
        ),
    )
    parser.add_argument(
        "-o",
        "--out",
        type=Path,
        default=OUT_DEFAULT,
        help=f"Ruta del JSON de salida (por defecto: {OUT_DEFAULT.name}).",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Ejecuta con navegador visible (recomendado para resolución manual de CAPTCHA).",
    )
    parser.add_argument(
        "--todos",
        action="store_true",
        help="Consulta todos los procesos (equivale a SoloActivos=false).",
    )
    parser.add_argument(
        "--full-payload",
        action="store_true",
        help="Incluye el payload completo de la API en el JSON de salida.",
    )
    parser.add_argument(
        "--sin-actuaciones",
        action="store_true",
        help="No consulta actuaciones por proceso.",
    )
    parser.add_argument(
        "--max-paginas-actuaciones",
        type=int,
        default=15,
        help="Número máximo de páginas de actuaciones por proceso (por defecto: 3).",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        radicados = load_radicados(args)
    except Exception as exc:
        print(f"Error al leer la entrada: {exc}", file=sys.stderr)
        return 1

    if not radicados:
        print(
            "No hay radicados para consultar. Rellena la lista `radicados` en el script, "
            "pásalos por CLI o crea radicados.json.",
            file=sys.stderr,
        )
        return 1

    return run(
        radicados=radicados,
        out_file=args.out,
        headless=not args.headed,
        solo_activos=not args.todos,
        include_payload=args.full_payload,
        include_actuaciones=not args.sin_actuaciones,
        max_paginas_actuaciones=max(1, args.max_paginas_actuaciones),
    )


if __name__ == "__main__":
    raise SystemExit(main())
