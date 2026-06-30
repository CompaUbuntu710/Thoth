import os
import re
import base64
import threading
from urllib.parse import urlparse

BROWSER_DIR = os.path.join(os.path.dirname(__file__), "..", ".browser_profile")
os.makedirs(BROWSER_DIR, exist_ok=True)

_lock = threading.Lock()
_context = None
_page = None


def _get_browser():
    global _context, _page
    if _page is not None:
        try:
            _page.title()
            return _context, _page
        except Exception:
            _context = None
            _page = None
    from playwright.sync_api import sync_playwright
    p = sync_playwright().start()
    browser = p.chromium.launch_persistent_context(
        BROWSER_DIR,
        headless=True,
        locale="es-MX",
        timezone_id="America/Mexico_City",
        viewport={"width": 1280, "height": 720},
        user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    )
    _context = browser
    _page = browser.pages[0] if browser.pages else browser.new_page()
    return _context, _page


def handle_browser_agent(action, url=None, selector=None, text=None, query=None):
    try:
        ctx, page = _get_browser()

        if action == "navigate":
            if not url:
                return "[Error: URL requerida]"
            if not url.startswith("http"):
                url = "https://" + url
            page.goto(url, wait_until="domcontentloaded", timeout=15000)
            title = page.title()
            return f"[Navegado a {url}] Título: {title}"

        elif action == "click":
            if not selector:
                return "[Error: selector requerido]"
            try:
                page.click(selector, timeout=5000)
                return f"[Click en '{selector}']"
            except Exception:
                try:
                    page.click(f"text={selector}", timeout=3000)
                    return f"[Click en texto '{selector}']"
                except Exception:
                    return f"[Error: no se encontró '{selector}']"

        elif action == "type":
            if not selector or text is None:
                return "[Error: selector y texto requeridos]"
            try:
                page.fill(selector, "", timeout=3000)
                page.type(selector, text, delay=20)
                return f"[Escrito '{text[:50]}' en '{selector}']"
            except Exception:
                try:
                    page.keyboard.type(text, delay=20)
                    return f"[Escrito '{text[:50]}' con teclado]"
                except Exception as e:
                    return f"[Error escribiendo: {e}]"

        elif action == "extract":
            tag = selector or "body"
            try:
                el = page.query_selector(tag)
                if not el:
                    return f"[Error: no se encontró '{tag}']"
                text = el.inner_text()
                text = re.sub(r'\s+', ' ', text).strip()
                if len(text) > 5000:
                    text = text[:5000] + "..."
                return text if text else "[Elemento vacío]"
            except Exception as e:
                return f"[Error extrayendo: {e}]"

        elif action == "screenshot":
            path = os.path.join(BROWSER_DIR, "last_screenshot.png")
            page.screenshot(path=path, full_page=False)
            with open(path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            return f"[Screenshot tomado ({len(b64)} bytes base64)]\ndata:image/png;base64,{b64[:100]}...]"

        elif action == "search":
            q = query or url
            if not q:
                return "[Error: query requerida]"
            page.goto(f"https://www.google.com/search?q={q.replace(' ', '+')}&hl=es", wait_until="domcontentloaded", timeout=15000)
            results = []
            items = page.query_selector_all("div.g")
            for item in items[:8]:
                try:
                    title_el = item.query_selector("h3")
                    link_el = item.query_selector("a")
                    snippet_el = item.query_selector("div[data-sncf], span.aCOpRe")
                    t = title_el.inner_text() if title_el else ""
                    href = link_el.get_attribute("href") if link_el else ""
                    s = snippet_el.inner_text() if snippet_el else ""
                    if t:
                        results.append(f"- {t}: {s[:200]}")
                except Exception:
                    pass
            if not results:
                results.append(f"Búsqueda: {q}")
            return "[Resultados de búsqueda]\n" + "\n".join(results)

        elif action == "current_url":
            return f"[URL actual: {page.url}]"

        elif action == "back":
            page.go_back()
            return f"[Volví atrás → {page.url}]"

        return "[Error: acción no válida. Usa: navigate, click, type, extract, screenshot, search, current_url, back]"

    except Exception as e:
        return f"[Error en browser: {e}]"


def close_browser():
    global _context, _page
    if _context:
        try:
            _context.close()
        except Exception:
            pass
    _context = None
    _page = None
