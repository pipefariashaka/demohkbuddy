"""
Step Runner — Ejecuta scripts de Playwright capturando steps del código fuente.
Transforma el script insertando page.screenshot() después de cada acción.
"""
import os
import sys
import time
import subprocess
import re
import json
from dataclasses import dataclass, field

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import DATA_DIR


@dataclass
class StepResult:
    num: int = 0
    action: str = ""
    selector: str = ""
    value: str = ""
    screenshot_path: str = ""
    success: bool = True
    error: str = ""


@dataclass
class DetailedPlaybackResult:
    success: bool = False
    duration_seconds: float = 0.0
    error_output: str = ""
    steps: list = field(default_factory=list)
    script_name: str = ""


def _extract_steps_from_script(script_code: str) -> list:
    """Extrae pasos del script parseando el código fuente."""
    steps = []
    num = 0
    for line in script_code.split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        selector = ""
        m = re.search(r'get_by_role\(["\']([^"\']+)["\'](?:,\s*name=["\']([^"\']+)["\'])?', stripped)
        if m:
            selector = f"{m.group(1)}: {m.group(2)}" if m.group(2) else m.group(1)
        else:
            m = re.search(r'get_by_(?:label|text|placeholder|title)\(["\']([^"\']+)["\']', stripped)
            if m:
                selector = m.group(1)
            else:
                m = re.search(r'locator\(["\']([^"\']+)["\']', stripped)
                if m:
                    selector = m.group(1)[:50]

        action, value = "", ""
        if "page.goto(" in stripped:
            m = re.search(r'page\.goto\(["\']([^"\']+)["\']', stripped)
            action, value = "goto", (m.group(1) if m else "")
        elif ".fill(" in stripped:
            m = re.search(r'\.fill\(["\']([^"\']*)["\']', stripped)
            action, value = "fill", (m.group(1) if m else "")
        elif ".click()" in stripped:
            action = "click"
        elif ".press(" in stripped:
            m = re.search(r'\.press\(["\']([^"\']+)["\']', stripped)
            action, value = "press", (m.group(1) if m else "")
        elif ".select_option(" in stripped:
            m = re.search(r'\.select_option\(["\']([^"\']+)["\']', stripped)
            action, value = "select_option", (m.group(1) if m else "")
        elif ".check()" in stripped:
            action = "check"
        elif ".uncheck()" in stripped:
            action = "uncheck"
        elif "expect(" in stripped and "to_have_url" in stripped:
            action = "assert_url"
        elif "expect(" in stripped and "to_be_visible" in stripped:
            action = "assert_visible"
        elif "expect(" in stripped and "to_have_text" in stripped:
            action = "assert_text"

        if action:
            num += 1
            steps.append(StepResult(num=num, action=action, selector=selector, value=value))

    return steps


def _build_instrumented_script(original_path: str, screenshots_dir: str,
                               steps_json_path: str,
                               browser_config: dict | None = None) -> str:
    """
    Transforma el script original insertando page.screenshot() después de cada acción.
    Inyecta opciones del navegador (viewport, slow_mo, etc.) en launch() y new_context().
    """
    with open(original_path, "r", encoding="utf-8") as f:
        original_lines = f.readlines()

    cfg = browser_config or {}

    # Kwargs para new_context()
    ctx_kwargs = {}
    if cfg.get("custom_size") and cfg.get("width") and cfg.get("height"):
        ctx_kwargs["viewport"] = f"{{'width': {cfg['width']}, 'height': {cfg['height']}}}"
    if cfg.get("ignore_https_errors"):
        ctx_kwargs["ignore_https_errors"] = "True"
    if cfg.get("locale"):
        ctx_kwargs["locale"] = f"'{cfg['locale']}'"
    if cfg.get("timezone"):
        ctx_kwargs["timezone_id"] = f"'{cfg['timezone']}'"

    # Kwargs para launch() — reemplazamos headless y agregamos slow_mo
    # slow_mo va en launch(), no en codegen
    launch_overrides = {}
    if cfg.get("headless"):
        launch_overrides["headless"] = "True"
    else:
        launch_overrides["headless"] = "False"
    if cfg.get("slow_mo", 0) > 0:
        launch_overrides["slow_mo"] = str(cfg["slow_mo"])

    action_patterns = [
        r'\.goto\(', r'\.click\(', r'\.fill\(', r'\.press\(',
        r'\.select_option\(', r'\.check\(', r'\.uncheck\(',
        r'expect\(.*\)\.to_have_url\(', r'expect\(.*\)\.to_be_visible\(',
        r'expect\(.*\)\.to_have_text\(', r'expect\(.*\)\.to_be_enabled\(',
        r'expect\(.*\)\.to_be_checked\(', r'expect\(.*\)\.to_have_value\(',
        r'expect\(.*\)\.to_contain_text\(', r'expect\(.*\)\.to_have_count\(',
    ]

    instrumented = []
    step_num = [0]

    ss_dir_repr = repr(screenshots_dir)
    sj_repr = repr(steps_json_path)
    instrumented.append(f"import os as _os, json as _json\n")
    instrumented.append(f"_ss_dir = {ss_dir_repr}\n")
    instrumented.append(f"_sj_path = {sj_repr}\n")
    instrumented.append(f"_os.makedirs(_ss_dir, exist_ok=True)\n")
    instrumented.append(f"_ss_map = {{}}\n\n")

    for line in original_lines:
        # Reemplazar launch() completo con nuestros kwargs
        if re.search(r'\.launch\(', line):
            # Extraer la variable del browser (ej: playwright.chromium, playwright.firefox)
            m = re.search(r'(\w+\.\w+)\.launch\(', line)
            browser_obj = m.group(1) if m else "playwright.chromium"
            indent = len(line) - len(line.lstrip())
            sp = " " * indent
            # Detectar si hay asignación (browser = ...)
            assign_m = re.match(r'(\s*)(\w+\s*=\s*)', line)
            assign = assign_m.group(2) if assign_m else ""
            kwargs_str = ", ".join(f"{k}={v}" for k, v in launch_overrides.items())
            line = f"{sp}{assign}{browser_obj}.launch({kwargs_str})\n"

        # Reemplazar new_context() con nuestros kwargs
        if ctx_kwargs and re.search(r'\.new_context\(\)', line):
            kwargs_str = ", ".join(f"{k}={v}" for k, v in ctx_kwargs.items())
            line = line.replace(".new_context()", f".new_context({kwargs_str})")

        # Insertar page.close() ANTES de context.close()
        stripped_check = line.strip()
        if re.match(r'context\.close\(\)', stripped_check):
            indent = len(line) - len(line.lstrip())
            sp = " " * indent
            instrumented.append(f"{sp}try:\n{sp}    page.close()\n{sp}except Exception: pass\n")
        
        # Asegurar que browser.close() siempre se ejecute
        if re.match(r'browser\.close\(\)', stripped_check):
            indent = len(line) - len(line.lstrip())
            sp = " " * indent
            # Reemplazar con un try-except para asegurar que se cierre
            instrumented.append(f"{sp}try:\n{sp}    browser.close()\n{sp}except Exception: pass\n")
            continue  # No agregar la línea original

        instrumented.append(line)

        # Agregar viewport fullscreen después de new_page
        if cfg.get("fullscreen") and re.search(r'\bpage\s*=.*\.new_page\(\)', line):
            indent = len(line) - len(line.lstrip())
            sp = " " * indent
            instrumented.append(f"{sp}page.set_viewport_size({{'width': 1920, 'height': 1080}})\n")

        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        is_action = any(re.search(p, stripped) for p in action_patterns)
        if not is_action:
            continue

        step_num[0] += 1
        n = step_num[0]
        indent = len(line) - len(line.lstrip())
        sp = " " * indent
        ss_path = f"_os.path.join(_ss_dir, f'step_{n:03d}.png')"
        instrumented.append(
            f"{sp}try:\n"
            f"{sp}    _p = {ss_path}\n"
            f"{sp}    page.screenshot(path=_p)\n"
            f"{sp}    _ss_map[{n}] = _p\n"
            f"{sp}except Exception: pass\n"
        )

    instrumented.append(f"\nwith open(_sj_path, 'w', encoding='utf-8') as _f:\n")
    instrumented.append(f"    _json.dump({{'screenshots': _ss_map}}, _f)\n")

    return "".join(instrumented)


def execute_with_steps(script_path, script_name="Script", script_id=None,
                       browser_config=None):
    """Ejecuta el script instrumentado y retorna DetailedPlaybackResult con steps y screenshots."""
    result = DetailedPlaybackResult(script_name=script_name)

    if not os.path.exists(script_path):
        result.error_output = f"Script no encontrado: {script_path}"
        return result

    try:
        with open(script_path, "r", encoding="utf-8") as f:
            script_code = f.read()
    except Exception as e:
        result.error_output = str(e)
        return result

    parsed_steps = _extract_steps_from_script(script_code)

    ts = int(time.time())
    run_dir = os.path.join(DATA_DIR, "playwright_runs", f"run_{ts}")
    screenshots_dir = os.path.join(run_dir, "screenshots")
    steps_json_path = os.path.join(run_dir, "steps.json")
    os.makedirs(run_dir, exist_ok=True)

    instrumented_code = _build_instrumented_script(
        script_path, screenshots_dir, steps_json_path, browser_config)
    instrumented_path = os.path.join(run_dir, "instrumented.py")
    with open(instrumented_path, "w", encoding="utf-8") as f:
        f.write(instrumented_code)

    start = time.time()
    try:
        proc = subprocess.run(
            [sys.executable, instrumented_path],
            capture_output=True, text=True, timeout=300)
        result.duration_seconds = time.time() - start
        result.success = proc.returncode == 0
        if not result.success:
            result.error_output = proc.stderr or proc.stdout or "Error desconocido"
    except subprocess.TimeoutExpired:
        result.duration_seconds = time.time() - start
        result.error_output = "Timeout: el script excedió 5 minutos"
    except Exception as e:
        result.duration_seconds = time.time() - start
        result.error_output = str(e)

    # Leer mapa de screenshots
    screenshots_map = {}
    if os.path.exists(steps_json_path):
        try:
            with open(steps_json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            screenshots_map = {int(k): v for k, v in data.get("screenshots", {}).items()}
        except Exception as e:
            print(f"Error leyendo screenshots: {e}")

    # Combinar pasos con screenshots
    for ps in parsed_steps:
        n = ps.num
        ps.screenshot_path = screenshots_map.get(n, "")
        is_last = (n == len(parsed_steps))
        ps.success = result.success or not is_last
        if not result.success and is_last:
            ps.error = result.error_output[:200]
        result.steps.append(ps)

    return result
