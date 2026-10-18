"""
Consulta códigos en rematesjudiciales.com.co (búsqueda + ficha).

El login usa reCAPTCHA; la primera vez abre Chrome para que inicies sesión:

  python buscar_remates.py login

Se guardan cookies en remates_cookies.json (no lo subas a repos públicos).

Luego:

  python buscar_remates.py
  python buscar_remates.py 74499 74629
  python buscar_remates.py -o resultados.json 74499
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

BASE = "https://rematesjudiciales.com.co"
LOGIN_URL = f"{BASE}/mi-cuenta/"
COOKIE_FILE = Path(__file__).resolve().parent / "remates_cookies.json"
TXT_FILE = Path(__file__).resolve().parent / "resultados.txt"
PAGE_WAIT_SECONDS = 15


CODIGOS_DEFAULT = [
    "80494", "81180", "80807", "80726", "81250", "80967", "80847", "80290", "81130", "80948",
    "78038", "81040", "81140", "81089", "80095", "81217", "80933", "80748", "81252", "81068",
    "80860", "80468", "80920", "80907", "81262", "80935", "80859", "81163", "80940", "80464",
    "80732", "80759", "81046", "81000", "79817", "81218", "80744", "80093"
]


CLOUDFLARE_MARKERS = (
    "verifica su solicitud",
    "espere un momento",
    "just a moment",
    "checking your browser",
    "cf-browser-verification",
    "challenge-platform",
)


def _page_has_cloudflare(html: str) -> bool:
    lower = html.lower()
    return any(m in lower for m in CLOUDFLARE_MARKERS)


def _page_has_login_form(html: str) -> bool:
    lower = html.lower()
    return "woocommerce-form-login" in lower or "customer-logout" in lower


def _build_driver(headless: bool, *, for_login: bool = False) -> webdriver.Chrome:
    if for_login and not headless:
        try:
            import undetected_chromedriver as uc

            opts = uc.ChromeOptions()
            opts.add_argument("--window-size=1280,900")
            opts.add_argument("--lang=es-CO")
            return uc.Chrome(options=opts, use_subprocess=True)
        except ImportError:
            print(
                "Aviso: instala undetected-chromedriver para evitar el bloqueo de Cloudflare:\n"
                "  pip install undetected-chromedriver\n",
                file=sys.stderr,
            )
        except Exception as exc:
            print(
                f"Aviso: no se pudo usar undetected-chromedriver ({exc}). "
                "Se usará Chrome normal con opciones anti-detección.\n",
                file=sys.stderr,
            )

    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1280,900")
    opts.add_argument("--lang=es-CO")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    )
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=opts)
    try:
        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {
                "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            },
        )
    except Exception:
        pass
    return driver


def _wait_past_cloudflare(driver: webdriver.Chrome, timeout: float = 180) -> bool:
    """Espera solo a que termine el desafío de Cloudflare."""
    deadline = time.time() + timeout
    warned = False
    while time.time() < deadline:
        if not _page_has_cloudflare(driver.page_source):
            return True
        if not warned:
            print(
                "\nEl sitio muestra la verificación de Cloudflare "
                "(«Espere un momento…»).\n"
                "  • Espera en la ventana de Chrome hasta que desaparezca.\n"
                "  • Si aparece un captcha, resuélvelo.\n",
                flush=True,
            )
            warned = True
        time.sleep(2)
    return not _page_has_cloudflare(driver.page_source)


def _open_login_page(driver: webdriver.Chrome) -> None:
    """Abre directamente la página de acceso (mi-cuenta)."""
    print(f"Abriendo: {LOGIN_URL}\n", flush=True)
    driver.get(LOGIN_URL)
    _wait_past_cloudflare(driver)
    if "mi-cuenta" not in driver.current_url.lower():
        driver.get(LOGIN_URL)
        _wait_past_cloudflare(driver, timeout=60)


def _wait_for_login_form(driver: webdriver.Chrome, timeout: float = 120) -> bool:
    """Espera el formulario de usuario/contraseña en /mi-cuenta/."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if _page_has_cloudflare(driver.page_source):
            _wait_past_cloudflare(driver, timeout=30)
            continue
        if "mi-cuenta" not in driver.current_url.lower():
            driver.get(LOGIN_URL)
            time.sleep(1)
            continue
        if _page_has_login_form(driver.page_source):
            return True
        time.sleep(1)
    return _page_has_login_form(driver.page_source)


def _save_cookies(driver: webdriver.Chrome) -> None:
    COOKIE_FILE.write_text(
        json.dumps(driver.get_cookies(), indent=2),
        encoding="utf-8",
    )


def _wait_css(driver: webdriver.Chrome, selector: str, timeout: float = PAGE_WAIT_SECONDS) -> bool:
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
        )
        return True
    except Exception:
        return False


def _codigo_url(codigo: str) -> str:
    return f"{BASE}/codigo/{codigo}/"


def _load_cookies(driver: webdriver.Chrome) -> bool:
    if not COOKIE_FILE.is_file():
        return False
    raw = json.loads(COOKIE_FILE.read_text(encoding="utf-8"))
    driver.get(BASE + "/")
    time.sleep(0.5)
    for c in raw:
        item = {k: c[k] for k in ("name", "value", "domain", "path") if k in c}
        if "expiry" in c:
            item["expiry"] = int(c["expiry"])
        try:
            driver.add_cookie(item)
        except Exception:
            pass
    driver.refresh()
    _wait_past_cloudflare(driver, timeout=30)
    return True


def _find_search_href(soup: BeautifulSoup, codigo: str) -> str | None:
    for a in soup.select("a.entry-title-link"):
        h = a.get("href") or ""
        if f"/codigo/{codigo}/" in h or h.rstrip("/").endswith(f"/codigo/{codigo}"):
            return h
    first = soup.select_one("a.entry-title-link")
    return first.get("href") if first else None


def _parse_ficha_page(driver: webdriver.Chrome, codigo: str, url: str) -> dict:
    if _page_has_cloudflare(driver.page_source):
        _wait_past_cloudflare(driver, timeout=30)
    soup = BeautifulSoup(driver.page_source, "html.parser")
    if _page_has_cloudflare(str(soup)):
        return {
            "codigo": codigo,
            "url": url,
            "error": "bloqueado por Cloudflare; ejecuta de nuevo: python buscar_remates.py login",
        }
    div = soup.select_one("div.entry-content")
    if not div:
        return {"codigo": codigo, "url": url, "error": "no se encontró el contenido"}

    texto = div.get_text("\n", strip=True)
    restringido = "contenido restringido" in texto.lower()

    return {
        "codigo": codigo,
        "url": url,
        "contenido_restringido": restringido,
        "texto": texto,
    }


def login_interactivo() -> None:
    print(
        "\n"
        "=== PASO 1: guardar sesión (solo la primera vez) ===\n"
        "\n"
        f"Se abrirá Chrome en: {LOGIN_URL}\n"
        "\n"
        "Si ves «Espere un momento mientras se verifica su solicitud…», es Cloudflare:\n"
        "  espera en Chrome hasta que aparezca el formulario de acceso (puede tardar ~30 s).\n"
        "\n"
        "En esa ventana:\n"
        "  • Escribe tu correo o usuario y la contraseña.\n"
        "  • Marca el reCAPTCHA (la casilla de \"No soy un robot\").\n"
        "  • Pulsa el botón \"Acceso\" (o equivalente).\n"
        "\n"
        "Comprueba que ya NO ves solo el formulario de login: deberías ver\n"
        "el panel de tu cuenta (pedidos, datos, etc.).\n"
        "\n"
        "Importante: no cierres Chrome tú mismo; vuelve aquí y pulsa ENTER\n"
        "para que el programa guarde las cookies y cierre el navegador.\n"
        "\n"
        f"Archivo que se creará: {COOKIE_FILE}\n"
    )
    driver = _build_driver(headless=False, for_login=True)
    try:
        _open_login_page(driver)
        if not _wait_for_login_form(driver):
            print(
                "\nNo apareció el formulario de acceso en /mi-cuenta/ tras varios minutos.\n"
                "Si Chrome quedó en la portada, abre manualmente:\n"
                f"  {LOGIN_URL}\n"
                "Cierra Chrome, ejecuta: pip install undetected-chromedriver\n"
                "y vuelve a intentar: python buscar_remates.py login\n",
                file=sys.stderr,
            )
        try:
            input("Cuando hayas iniciado sesión correctamente, pulsa ENTER aquí… ")
        except EOFError:
            print("Entrada cancelada.", file=sys.stderr)
            sys.exit(1)
        html = driver.page_source.lower()
        if "woocommerce-form-login login" in html and "customer-logout" not in html:
            print(
                "\nAdvertencia: la página sigue mostrando el formulario de acceso.\n"
                "Si no habías entrado, vuelve a Chrome, corrige datos/captcha e intenta de nuevo;\n"
                "luego ejecuta otra vez: python buscar_remates.py login\n",
                file=sys.stderr,
            )
        _save_cookies(driver)
    finally:
        driver.quit()
    print(f"\nListo. Cookies guardadas en:\n  {COOKIE_FILE}\n")
    print("Siguiente paso en la misma carpeta:\n  python buscar_remates.py\n")


def extraer_ficha(driver: webdriver.Chrome, codigo: str) -> dict:
    codigo = codigo.strip()
    if not codigo.isdigit():
        return {"codigo": codigo, "error": "el código debe ser numérico"}

    url = _codigo_url(codigo)
    driver.get(url)
    if _wait_css(driver, "div.entry-content"):
        return _parse_ficha_page(driver, codigo, url)

    driver.get(f"{BASE}/?s={codigo}")
    _wait_css(driver, "a.entry-title-link")
    soup = BeautifulSoup(driver.page_source, "html.parser")
    href = _find_search_href(soup, codigo)
    if not href:
        lower = driver.page_source.lower()
        if "woocommerce-form-login" in lower and "customer-logout" not in lower:
            return {
                "codigo": codigo,
                "error": "sesión no válida; ejecuta: python buscar_remates.py login",
            }
        return {"codigo": codigo, "error": "sin resultados en la búsqueda"}

    driver.get(href)
    _wait_css(driver, "div.entry-content")
    return _parse_ficha_page(driver, codigo, href)


def formatear_resultado_txt(resultado: dict) -> str:
    codigo = resultado.get("codigo", "N/A")
    url = resultado.get("url", "N/A")
    if resultado.get("error"):
        estado = f"ERROR: {resultado['error']}"
    elif resultado.get("contenido_restringido"):
        estado = "CONTENIDO RESTRINGIDO"
    else:
        estado = "OK"
    texto = (resultado.get("texto") or "").strip()
    if not texto:
        texto = "(sin texto extraido)"
    return (
        f"===== CODIGO {codigo} =====\n"
        f"URL: {url}\n"
        f"ESTADO: {estado}\n"
        "CONTENIDO:\n"
        f"{texto}\n\n"
    ) 


def buscar_codigos(codigos: list[str], salida_json: Path | None, salida_txt: Path) -> int:
    if not COOKIE_FILE.is_file():
        print(
            "No existe remates_cookies.json. Ejecuta primero:\n  python buscar_remates.py login",
            file=sys.stderr,
        )
        return 1

    resultados = []
    salida_txt.write_text("", encoding="utf-8")
    driver = _build_driver(headless=True)
    try:
        if not _load_cookies(driver):
            print("No se pudieron cargar cookies.", file=sys.stderr)
            return 1
        for c in codigos:
            resultado = extraer_ficha(driver, c)
            resultados.append(resultado)
            with salida_txt.open("a", encoding="utf-8") as f:
                f.write(formatear_resultado_txt(resultado))
    finally:
        driver.quit()

    for r in resultados:
        print("---")
        print(json.dumps(r, ensure_ascii=False, indent=2))

    if salida_json:
        salida_json.write_text(
            json.dumps(resultados, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"\nGuardado: {salida_json}", file=sys.stderr)
    print(f"\nTXT final listo en: {salida_txt}", file=sys.stderr)

    if any(r.get("contenido_restringido") or r.get("error") for r in resultados):
        return 2
    return 0


def main() -> int:
    if len(sys.argv) >= 2 and sys.argv[1] == "login":
        login_interactivo()
        return 0

    ap = argparse.ArgumentParser(
        description="Buscar remates por código (requiere cookies guardadas con 'login')."
    )
    ap.add_argument(
        "codigos",
        nargs="*",
        help=f"Códigos a consultar (por defecto: {' '.join(CODIGOS_DEFAULT)})",
    )
    ap.add_argument(
        "-o",
        "--out",
        type=Path,
        default=None,
        help="Archivo JSON con todos los resultados",
    )
    args = ap.parse_args()

    codigos = args.codigos if args.codigos else CODIGOS_DEFAULT
    return buscar_codigos(codigos, args.out, TXT_FILE)


if __name__ == "__main__":
    raise SystemExit(main())
