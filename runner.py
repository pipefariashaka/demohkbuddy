"""
HakaBuddy — Runner de pruebas Playwright
Generado automáticamente. No editar manualmente.
"""
import subprocess, sys, os, json, re, tempfile, time, base64
from pathlib import Path
from datetime import datetime

SCRIPTS = [
    "script_test60_20260427_215225.py",
    "Prueba_hakalab_2.py",
    "Prueba_1111.py"
]
SUITE_NAME = "Suit web haka"

IS_CI = os.environ.get("CI", "") == "true" or not os.environ.get("DISPLAY", "")

def patch_headless(source):
    # 1. Quitar channel="chrome" / channel='chrome' — en CI solo hay Chromium
    source = re.sub(r',?\s*channel\s*=\s*["\']chrome["\']', "", source)
    source = re.sub(r'channel\s*=\s*["\']chrome["\'],?\s*', "", source)

    # 2. headless=True y slow_mo=0
    source = re.sub(r"headless\s*=\s*False", "headless=True", source)
    source = re.sub(r"slow_mo\s*=\s*\d+", "slow_mo=0", source)

    # 3. Inyectar args de CI en chromium.launch(...)
    ci_args = ("['--no-sandbox','--disable-dev-shm-usage','--disable-gpu',"
               "'--disable-setuid-sandbox','--window-size=1280,720',"
               "'--disable-blink-features=AutomationControlled']")
    def _inject_args(m):
        call = m.group(0)
        if "args=" in call:
            return call
        call = call.rstrip()
        if call.endswith(")"):
            return call[:-1] + f", args={ci_args})"
        return call + f", args={ci_args}"
    source = re.sub(r'\.launch\([^)]*\)', _inject_args, source)

    # 4. Forzar viewport 1280x720 y user-agent en new_context()
    def _inject_viewport(m):
        call = m.group(0)
        ua = "user_agent='Haka2026'"
        if "viewport" in call and "user_agent" in call:
            return call
        call = call.rstrip()
        if "viewport" not in call and "user_agent" not in call:
            if call.endswith(")"):
                return call[:-1] + f", viewport={{'width':1280,'height':720}}, {ua})"
        elif "viewport" in call and "user_agent" not in call:
            if call.endswith(")"):
                return call[:-1] + f", {ua})"
        elif "user_agent" not in call:
            if call.endswith(")"):
                return call[:-1] + f", {ua})"
        return call
    source = re.sub(r'\.new_context\([^)]*\)', _inject_viewport, source)

    # 5. Después de new_page(): timeout 90s + wait_for_load_state
    source = re.sub(
        r'(\bpage\s*=\s*(?:context|browser)\.new_page\(\))',
        r'\1\n    page.set_default_timeout(90000)',
        source
    )

    # 6. Después de cada goto(): esperar que la red esté idle
    source = re.sub(
        r'(page\.goto\([^)]+\))',
        r'\1\n    page.wait_for_load_state("networkidle")\n    page.screenshot(path="ci_debug_goto.png")',
        source
    )

    return source

def _esc(t):
    return str(t).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

def _dur(s):
    s = int(float(s))
    return f"{s//60}m {s%60}s" if s >= 60 else f"{s}s"

def _img_b64(path):
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception:
        return ""

def _substitute_fills(source, variables, data_set):
    """Replace .fill() values in source with data_set values (for outline)."""
    lines = source.split('\n')
    # Build line_number -> (default_value, new_value) map
    for var in variables:
        name = var.get("name", "")
        default_val = var.get("default_value", "")
        new_val = data_set.get(name, default_val)
        if default_val != new_val:
            # Replace in all lines that have .fill("default_val")
            old_escaped = re.escape(default_val)
            for i, line in enumerate(lines):
                if '.fill(' in line and default_val in line:
                    lines[i] = re.sub(
                        r'(\.fill\(\s*["\'])' + old_escaped + r'(["\'])',
                        lambda m: m.group(1) + new_val + m.group(2),
                        line, count=1
                    )
    return '\n'.join(lines)

# ── Ejecutar scripts ──────────────────────────────────────────────
results = []
base = Path(__file__).parent / "scripts"

for name in SCRIPTS:
    path = base / name
    if not path.exists():
        print(f"[SKIP] {name}")
        results.append({"script": name, "status": "SKIP", "duration": 0, "error": "", "steps": []})
        continue
    print(f"[RUN]  {name}")

    steps = []
    source = path.read_text(encoding="utf-8")
    if IS_CI:
        source = patch_headless(source)

    # Check for outline data (data-driven testing)
    outline_json_path = base / (name + ".outline.json")
    outline_data_sets = []
    outline_variables = []
    if outline_json_path.exists():
        try:
            with open(outline_json_path, "r", encoding="utf-8") as _of:
                _odata = json.load(_of)
            outline_data_sets = _odata.get("data_sets", [])
            outline_variables = _odata.get("variables", [])
            if outline_data_sets:
                print(f"[OUTLINE] {name}: {len(outline_data_sets)} data set(s) found")
        except Exception as e:
            print(f"[OUTLINE] Error loading {outline_json_path}: {e}")

    # Intentar usar step_runner para capturar pasos y screenshots
    step_runner_path = Path(__file__).parent / "step_runner.py"
    if step_runner_path.exists():
        try:
            import importlib.util, tempfile as _tf
            spec = importlib.util.spec_from_file_location("step_runner", step_runner_path)
            sr = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(sr)

            ss_dir = Path(__file__).parent / "screenshots" / name.replace(".py", "")
            ss_dir.mkdir(parents=True, exist_ok=True)
            steps_json = str(ss_dir / "steps.json")

            # Escribir el source ya patcheado a un archivo temporal para instrumentar
            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as tmp_src:
                tmp_src.write(source)
                patched_path = tmp_src.name

            # _build_instrumented_script recibe el archivo patcheado
            instrumented_code = sr._build_instrumented_script(
                patched_path, str(ss_dir), steps_json,
                browser_config={
                    "headless": True,
                    "slow_mo": 0,
                    "args": ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu", "--disable-setuid-sandbox"],
                    "timeout": 90000,
                }
            )
            try:
                os.unlink(patched_path)
            except Exception:
                pass
            
            # Escribir el código instrumentado a un archivo temporal
            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as tmp:
                tmp.write(instrumented_code)
                instrumented_path = tmp.name
            
            t0 = time.time()
            if IS_CI:
                print(f"[DEBUG] Script instrumentado para {name}:")
                print(instrumented_code[:1500])
                print("---")
            r = subprocess.run([sys.executable, instrumented_path], capture_output=True, text=True)
            duration = round(time.time() - t0, 1)
            try:
                os.unlink(instrumented_path)
            except Exception:
                pass

            # Leer steps capturados
            if os.path.exists(steps_json):
                with open(steps_json) as f:
                    raw_steps = json.load(f)
                # El formato del JSON es {"screenshots": {num: path}}
                screenshots_map = raw_steps.get("screenshots", {})
                # Extraer steps del código original
                parsed_steps = sr._extract_steps_from_script(source)
                for i, ps in enumerate(parsed_steps):
                    is_last = (i == len(parsed_steps) - 1)
                    # Si el script falló, marcar el último step como fallido
                    step_success = r.returncode == 0 or not is_last
                    
                    # Construir descripción legible del paso
                    action_desc = ps.action
                    if ps.value:
                        action_desc += f": {ps.value}"
                    if ps.selector:
                        action_desc += f" [{ps.selector}]"
                    
                    steps.append({
                        "num":             ps.num,
                        "action":          action_desc,
                        "success":         step_success,
                        "error":           "" if step_success else "Error en este paso",
                        "screenshot_path": screenshots_map.get(str(ps.num), ""),
                    })
            else:
                # Si no hay steps.json, extraer pasos del código sin screenshots
                parsed_steps = sr._extract_steps_from_script(source)
                for i, ps in enumerate(parsed_steps):
                    is_last = (i == len(parsed_steps) - 1)
                    step_success = r.returncode == 0 or not is_last
                    
                    action_desc = ps.action
                    if ps.value:
                        action_desc += f": {ps.value}"
                    if ps.selector:
                        action_desc += f" [{ps.selector}]"
                    
                    steps.append({
                        "num":             ps.num,
                        "action":          action_desc,
                        "success":         step_success,
                        "error":           "" if step_success else "Error en este paso",
                        "screenshot_path": "",
                    })
        except Exception as e:
            print(f"[step_runner] Error: {e} — ejecutando sin instrumentación")
            instrumented_path = None
            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as tmp:
                tmp.write(source)
                run_path = tmp.name
            t0 = time.time()
            r = subprocess.run([sys.executable, run_path], capture_output=True, text=True)
            duration = round(time.time() - t0, 1)
            try:
                os.unlink(run_path)
            except Exception:
                pass
    else:
        # Sin step_runner — ejecución simple
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as tmp:
            tmp.write(source)
            run_path = tmp.name
        t0 = time.time()
        r = subprocess.run([sys.executable, run_path], capture_output=True, text=True)
        duration = round(time.time() - t0, 1)
        try:
            os.unlink(run_path)
        except Exception:
            pass

    ok = r.returncode == 0
    status = "PASS" if ok else "FAIL"
    print(f"[{status}] {name} ({duration}s)")

    stderr_lines = [l for l in r.stderr.splitlines() if l.strip()]
    relevant = [l for l in stderr_lines if any(x in l for x in ["Error", "Timeout", "assert", "Assert"])]
    error_msg = "\n".join(relevant[-5:]) if relevant else (r.stderr[-400:] if not ok else "")
    if not ok:
        print(error_msg)

    results.append({
        "script": name,
        "status": status,
        "duration": duration,
        "error": error_msg,
        "steps": steps,
        "outline_iterations": [],  # Will be populated for outline scripts
    })

    # If outline data exists, re-execute for remaining data sets
    if outline_data_sets and len(outline_data_sets) > 0:
        all_iterations = []

        # Iteración 0: la ejecución original (ya ejecutada arriba)
        original_ds = {}
        for v in outline_variables:
            original_ds[v.get("name", "")] = v.get("default_value", "")
        all_iterations.append({
            "iteration": 1,
            "data_set": original_ds,
            "status": status,
            "duration": duration,
            "error": error_msg,
            "steps": steps,
        })

        # Iteraciones adicionales con data sets
        for ds_idx, ds in enumerate(outline_data_sets):
            ds_label = ", ".join(f"{k}={v}" for k, v in ds.items())
            print(f"[OUTLINE] {name} — Iteración {ds_idx+1}/{len(outline_data_sets)}: {ds_label}")

            modified_source = _substitute_fills(source, outline_variables, ds)
            if IS_CI:
                modified_source = patch_headless(modified_source)

            iter_steps = []

            # Intentar instrumentar con step_runner para capturar pasos
            if step_runner_path.exists():
                try:
                    iter_ss_dir = Path(__file__).parent / "screenshots" / (name.replace(".py", "") + f"_iter{ds_idx+2}")
                    iter_ss_dir.mkdir(parents=True, exist_ok=True)
                    iter_steps_json = str(iter_ss_dir / "steps.json")

                    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as tmp_src:
                        tmp_src.write(modified_source)
                        iter_patched_path = tmp_src.name

                    iter_instrumented_code = sr._build_instrumented_script(
                        iter_patched_path, str(iter_ss_dir), iter_steps_json,
                        browser_config={
                            "headless": True,
                            "slow_mo": 0,
                            "args": ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu", "--disable-setuid-sandbox"],
                            "timeout": 90000,
                        }
                    )
                    try:
                        os.unlink(iter_patched_path)
                    except Exception:
                        pass

                    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as tmp:
                        tmp.write(iter_instrumented_code)
                        iter_path = tmp.name

                    t0_iter = time.time()
                    r_iter = subprocess.run([sys.executable, iter_path], capture_output=True, text=True, timeout=300)
                    dur_iter = round(time.time() - t0_iter, 1)
                    try:
                        os.unlink(iter_path)
                    except Exception:
                        pass

                    # Leer steps capturados
                    if os.path.exists(iter_steps_json):
                        with open(iter_steps_json) as f:
                            raw_iter_steps = json.load(f)
                        iter_screenshots_map = raw_iter_steps.get("screenshots", {})
                        parsed_iter_steps = sr._extract_steps_from_script(modified_source)
                        for si, ps in enumerate(parsed_iter_steps):
                            is_last = (si == len(parsed_iter_steps) - 1)
                            step_success = r_iter.returncode == 0 or not is_last
                            action_desc = ps.action
                            if ps.value:
                                action_desc += f": {ps.value}"
                            if ps.selector:
                                action_desc += f" [{ps.selector}]"
                            iter_steps.append({
                                "num":             ps.num,
                                "action":          action_desc,
                                "success":         step_success,
                                "error":           "" if step_success else "Error en este paso",
                                "screenshot_path": iter_screenshots_map.get(str(ps.num), ""),
                            })
                    else:
                        parsed_iter_steps = sr._extract_steps_from_script(modified_source)
                        for si, ps in enumerate(parsed_iter_steps):
                            is_last = (si == len(parsed_iter_steps) - 1)
                            step_success = r_iter.returncode == 0 or not is_last
                            action_desc = ps.action
                            if ps.value:
                                action_desc += f": {ps.value}"
                            if ps.selector:
                                action_desc += f" [{ps.selector}]"
                            iter_steps.append({
                                "num":             ps.num,
                                "action":          action_desc,
                                "success":         step_success,
                                "error":           "" if step_success else "Error en este paso",
                                "screenshot_path": "",
                            })
                except Exception as e:
                    print(f"[OUTLINE] step_runner error iter {ds_idx+1}: {e} — ejecutando sin instrumentación")
                    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as tmp:
                        tmp.write(modified_source)
                        iter_path = tmp.name
                    t0_iter = time.time()
                    r_iter = subprocess.run([sys.executable, iter_path], capture_output=True, text=True, timeout=300)
                    dur_iter = round(time.time() - t0_iter, 1)
                    try:
                        os.unlink(iter_path)
                    except Exception:
                        pass
            else:
                with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as tmp:
                    tmp.write(modified_source)
                    iter_path = tmp.name
                t0_iter = time.time()
                r_iter = subprocess.run([sys.executable, iter_path], capture_output=True, text=True, timeout=300)
                dur_iter = round(time.time() - t0_iter, 1)
                try:
                    os.unlink(iter_path)
                except Exception:
                    pass

            iter_ok = r_iter.returncode == 0
            iter_status = "PASS" if iter_ok else "FAIL"
            iter_error = ""
            if not iter_ok:
                stderr_lines_iter = [l for l in r_iter.stderr.splitlines() if l.strip()]
                relevant_iter = [l for l in stderr_lines_iter if any(x in l for x in ["Error", "Timeout", "assert"])]
                iter_error = "\n".join(relevant_iter[-3:]) if relevant_iter else r_iter.stderr[-300:]

            print(f"[OUTLINE] [{iter_status}] Iteración {ds_idx+1} ({dur_iter}s)")

            all_iterations.append({
                "iteration": ds_idx + 2,
                "data_set": ds,
                "status": iter_status,
                "duration": dur_iter,
                "error": iter_error,
                "steps": iter_steps,
            })

        # Update the main result with outline data
        results[-1]["outline_iterations"] = all_iterations
        iter_passed = sum(1 for it in all_iterations if it["status"] == "PASS")
        iter_failed = sum(1 for it in all_iterations if it["status"] == "FAIL")
        results[-1]["status"] = "PASS" if iter_failed == 0 else "FAIL"
        results[-1]["duration"] = sum(it["duration"] for it in all_iterations)
        if iter_failed > 0:
            results[-1]["error"] = f"{iter_failed} de {len(all_iterations)} iteraciones fallaron"
        print(f"[OUTLINE] {name}: {iter_passed} PASS / {iter_failed} FAIL")

# ── Resumen consola ───────────────────────────────────────────────
passed  = sum(1 for r in results if r["status"] == "PASS")
failed  = sum(1 for r in results if r["status"] == "FAIL")
skipped = sum(1 for r in results if r["status"] == "SKIP")
print(f"\n=== {passed} PASS / {failed} FAIL / {skipped} SKIP / {len(results)} total ===")

with open("results.json", "w") as f:
    json.dump(results, f, indent=2)

# ── Generar reporte HTML (mismo formato que reporte local) ────────
all_ok     = failed == 0
ok_color   = "#28A745" if all_ok else "#DC3545"
icon       = "\u2713" if all_ok else "\u2717"
status_txt = "EXITOSO" if all_ok else "FALLIDO"
total_dur  = sum(r["duration"] for r in results)
fecha      = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
pct        = int(passed / len(results) * 100) if results else 0

# Construir acordeones por script (formato local)
scripts_html = ""
for i, r in enumerate(results):
    s_ok    = r["status"] == "PASS"
    s_color = "#28A745" if s_ok else ("#DC3545" if r["status"] == "FAIL" else "#888888")
    s_dur   = _dur(r["duration"])

    # Error del script
    err_script = ""
    if r["error"]:
        err_script = (
            '<div class="error-box">'
            '<div class="error-title">\u26a0\ufe0f Error</div>'
            '<pre class="error-content">' + _esc(r["error"]) + '</pre>'
            '</div>'
        )

    # Pasos (si los hay)
    pasos_html = ""
    for step in r.get("steps", []):
        num   = step.get("num", "")
        s_ok2 = step.get("success", True)
        desc  = step.get("action", "")
        err   = step.get("error", "")
        ss    = step.get("screenshot_path", "")
        sc2   = "#28A745" if s_ok2 else "#DC3545"
        si2   = "\u2713" if s_ok2 else "\u2717"

        img_html = ""
        if ss and os.path.exists(ss):
            b64 = _img_b64(ss)
            if b64:
                img_html = '<img src="data:image/png;base64,' + b64 + '" class="paso-img">'

        err_html = '<div class="paso-err">' + _esc(err) + '</div>' if err else ""
        has_body = bool(img_html or err_html)
        body     = '<div class="paso-body">' + err_html + img_html + '</div>' if has_body else ""
        arrow    = '<span class="acc-arrow">&#9658;</span>' if has_body else '<span style="width:16px;display:inline-block"></span>'
        cursor   = "cursor:pointer;" if has_body else ""

        pasos_html += (
            '\n<div class="paso-acc' + (' fail' if not s_ok2 else '') + '">'
            '\n  <div class="paso-head" style="' + cursor + '" onclick="toggleAcc(this)">'
            '\n    <span class="paso-num">#' + str(num) + '</span>'
            '\n    <span class="paso-titulo">' + _esc(desc) + '</span>'
            '\n    <span class="paso-estado" style="color:' + sc2 + '">' + si2 + ' ' + ('Exitoso' if s_ok2 else 'Fallido') + '</span>'
            '\n    ' + arrow +
            '\n  </div>' + body +
            '\n</div>'
        )

    # Build outline iterations HTML if present
    outline_iters_html = ""
    hide_top_steps = False
    if r.get("outline_iterations"):
        iters = r["outline_iterations"]
        hide_top_steps = True
        outline_iters_html = '<div style="margin-top:10px">'
        outline_iters_html += '<div class="section-title">\U0001f4ca Iteraciones (' + str(len(iters)) + ')</div>'
        for it in iters:
            it_ok = it["status"] == "PASS"
            it_color = "#28A745" if it_ok else "#DC3545"
            it_icon = "\u2713" if it_ok else "\u2717"
            it_label = ", ".join(f"{k}={v}" for k, v in it.get("data_set", {}).items())
            it_err = ""
            if it.get("error"):
                it_err = '<div class="paso-err">' + _esc(it["error"]) + '</div>'

            # Pasos de esta iteración
            it_steps_html = ""
            for st in it.get("steps", []):
                st_num = st.get("num", "")
                st_ok = st.get("success", True)
                st_desc = st.get("action", "")
                st_err = st.get("error", "")
                st_ss = st.get("screenshot_path", "")
                st_c = "#28A745" if st_ok else "#DC3545"
                st_i = "\u2713" if st_ok else "\u2717"
                st_img = ""
                if st_ss and os.path.exists(st_ss):
                    b64 = _img_b64(st_ss)
                    if b64:
                        st_img = '<img src="data:image/png;base64,' + b64 + '" class="paso-img">'
                st_err_h = '<div class="paso-err">' + _esc(st_err) + '</div>' if st_err else ""
                st_body = bool(st_img or st_err_h)
                st_body_h = '<div class="paso-body">' + st_err_h + st_img + '</div>' if st_body else ""
                st_arrow = '<span class="acc-arrow">\u25b6</span>' if st_body else '<span style="width:16px;display:inline-block"></span>'
                st_cursor = "cursor:pointer;" if st_body else ""
                it_steps_html += (
                    '\n<div class="paso-acc' + (' fail' if not st_ok else '') + '">'
                    '\n  <div class="paso-head" style="' + st_cursor + '" onclick="toggleAcc(this)">'
                    '\n    <span class="paso-num">#' + str(st_num) + '</span>'
                    '\n    <span class="paso-titulo">' + _esc(st_desc) + '</span>'
                    '\n    <span class="paso-estado" style="color:' + st_c + '">' + st_i + ' ' + ('Exitoso' if st_ok else 'Fallido') + '</span>'
                    '\n    ' + st_arrow +
                    '\n  </div>' + st_body_h +
                    '\n</div>'
                )

            it_fail = " fail" if not it_ok else ""
            outline_iters_html += (
                '<div class="script-acc' + it_fail + '" style="margin:6px 0">'
                '<div class="script-head" onclick="toggleScript(this)" style="padding:10px 14px">'
                '<span class="script-idx">#' + str(it["iteration"]) + '</span>'
                '<span class="script-name" style="font-size:13px">' + _esc(it_label[:60]) + '</span>'
                '<span class="badge ' + ('badge-ok' if it_ok else 'badge-fail') + '" style="font-size:11px;padding:2px 10px">' + it_icon + ' ' + ('Exitoso' if it_ok else 'Fallido') + '</span>'
                '<span class="script-dur">\u23f1 ' + _dur(it["duration"]) + '</span>'
                '<span class="script-arrow">&#9658;</span>'
                '</div>'
                '<div class="script-body" style="padding:0 14px 12px 14px">' + it_err + '<div style="margin-top:6px">' + it_steps_html + '</div></div>'
                '</div>'
            )
        outline_iters_html += '</div>'

    # Build script body — hide top-level steps for outline scripts
    top_steps = '' if hide_top_steps else '<div style="margin-top:8px">' + pasos_html + '</div>'

    # Outline stats
    outline_stats = ''
    if r.get("outline_iterations"):
        iter_count = len(r["outline_iterations"])
        outline_stats = '<span class="stats" style="color:#F5A623">\U0001f4ca ' + str(iter_count) + ' iteraciones</span>'

    fail_class = " fail" if not s_ok else ""
    scripts_html += (
        '\n<div class="script-acc' + fail_class + '">'
        '\n  <div class="script-head" onclick="toggleScript(this)">'
        '\n    <span class="script-idx">' + str(i+1) + '</span>'
        '\n    <span class="script-name">' + _esc(r["script"]) + '</span>'
        '\n    <span class="badge ' + ('badge-ok' if s_ok else 'badge-fail') + '" style="font-size:12px;padding:3px 12px">' + ('\u2713' if s_ok else '\u2717') + ' ' + ('Exitoso' if s_ok else 'Fallido') + '</span>'
        '\n    <span class="script-dur">\u23f1 ' + s_dur + '</span>'
        '\n    ' + outline_stats +
        '\n    <span class="script-arrow">&#9658;</span>'
        '\n  </div>'
        '\n  <div class="script-body">' + err_script + top_steps + outline_iters_html + '</div>'
        '\n</div>'
    )

CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:Calibri,sans-serif;background:#140323;color:#FFF;padding:24px;min-height:100vh}
.wrap{max-width:1100px;margin:0 auto}
.card{background:#1A2A4A;border-radius:10px;padding:20px 24px;margin-bottom:16px;border-left:4px solid #00D4FF}
.section-title{font-size:15px;font-weight:bold;color:#00D4FF;margin-bottom:12px;letter-spacing:.5px}
.info-label{color:#7EB8D4;font-size:11px;text-transform:uppercase}
.info-value{color:#FFF;font-size:13px;font-weight:bold}
.info-item{margin-right:24px;margin-top:6px;display:inline-block}
.badge{padding:5px 18px;border-radius:20px;font-weight:bold;font-size:14px;display:inline-block}
.badge-ok{background:#0D3320;color:#28A745;border:2px solid #28A745}
.badge-fail{background:#3A1B1B;color:#DC3545;border:2px solid #DC3545}
.stats{color:#7EB8D4;font-size:13px}
.paso-acc{background:#1A2A4A;border:1px solid #2A4A6A;border-radius:8px;margin-bottom:8px;overflow:hidden}
.paso-acc.fail{border-color:#DC3545}
.paso-head{padding:14px 16px;display:flex;align-items:center;gap:12px}
.paso-head:hover{background:rgba(255,255,255,.03)}
.paso-num{background:#2A2B3E;color:#8888AA;padding:2px 8px;border-radius:4px;font-size:12px;font-weight:bold;min-width:36px;text-align:center;flex-shrink:0}
.paso-titulo{font-weight:bold;color:#FFF;font-size:14px;flex:1}
.paso-estado{font-weight:bold;font-size:13px;flex-shrink:0}
.acc-arrow{color:#7EB8D4;font-size:11px;transition:transform .2s;display:inline-block;flex-shrink:0}
.paso-body{display:none;padding:0 16px 14px 16px}
.paso-err{color:#FF6B6B;font-size:13px;font-family:Consolas,monospace;background:#3D1A1A;padding:6px 10px;border-radius:5px;margin-top:6px;white-space:pre-wrap}
.paso-img{max-width:100%;border-radius:6px;border:1px solid #3A3B50;margin-top:8px;display:block}
.error-box{background:#2D1A1A;border:1px solid #DC3545;border-radius:8px;padding:14px;margin:10px 0}
.error-title{color:#DC3545;font-weight:700;margin-bottom:6px}
.error-content{color:#FFAAAA;font-size:12px;white-space:pre-wrap;font-family:Consolas,monospace}
.script-acc{background:#1A2A4A;border-radius:10px;margin-bottom:12px;overflow:hidden;border:1px solid #2A4A6A}
.script-acc.fail{border-color:#DC3545}
.script-head{display:flex;align-items:center;gap:12px;padding:14px 18px;cursor:pointer;transition:background .15s}
.script-head:hover{background:#1E3355}
.script-idx{background:#252640;color:#8888AA;padding:2px 8px;border-radius:5px;font-size:13px;font-weight:700;min-width:30px;text-align:center;flex-shrink:0}
.script-name{font-weight:700;color:#FFF;font-size:16px;flex:1}
.script-dur{color:#7EB8D4;font-size:13px;flex-shrink:0}
.script-arrow{color:#7EB8D4;font-size:12px;transition:transform .2s;display:inline-block;flex-shrink:0}
.script-body{display:none;padding:0 18px 16px 18px;border-top:1px solid #2A4A6A}
.footer{text-align:center;padding:20px;color:#7EB8D4;font-size:11px}
"""

JS = """
function toggleAcc(h){
  var b=h.nextElementSibling,a=h.querySelector('.acc-arrow');
  if(!b)return;
  b.style.display=b.style.display==='block'?'none':'block';
  if(a)a.style.transform=b.style.display==='block'?'rotate(90deg)':'rotate(0deg)';
}
function toggleScript(h){
  var b=h.nextElementSibling,a=h.querySelector('.script-arrow');
  if(!b)return;
  b.style.display=b.style.display==='block'?'none':'block';
  if(a)a.style.transform=b.style.display==='block'?'rotate(90deg)':'rotate(0deg)';
}
document.addEventListener('DOMContentLoaded',function(){
  document.querySelectorAll('.paso-acc.fail,.script-acc.fail').forEach(function(el){
    var h=el.querySelector('.paso-head,.script-head');
    if(h){
      if(el.classList.contains('script-acc'))toggleScript(h);
      else toggleAcc(h);
    }
  });
});
"""

# Barra de progreso
progress_html = (
    '<div style="background:#2A2B3E;border-radius:6px;height:8px;overflow:hidden;margin-bottom:6px">'
    '<div style="height:8px;border-radius:6px;width:' + str(pct) + '%;background:' + ok_color + '"></div>'
    '</div>'
    '<div style="color:#7EB8D4;font-size:12px">' + str(pct) + '% exitoso</div>'
)

# Info items helper
def _info(label, value):
    if not value:
        return ""
    return '<div class="info-item"><span class="info-label">' + label + '</span><br><span class="info-value">' + _esc(str(value)) + '</span></div>'

html = (
    '<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">'
    '<title>' + _esc(SUITE_NAME) + ' &mdash; HakaBuddy CI</title>'
    '<style>' + CSS + '</style></head><body>'
    '<div class="wrap">'

    # ── HEADER card ──
    '<div class="card" style="border-left:4px solid #00D4FF">'
    '<div style="font-size:22px;font-weight:bold;color:#00D4FF;text-align:center;margin-bottom:10px">Reporte de prueba automatizada</div>'
    '<div style="display:flex;flex-wrap:wrap;padding-top:10px;border-top:1px solid #2A4A6A">'
    + _info("Fecha", fecha)
    + _info("Duraci\u00f3n", _dur(total_dur))
    + _info("Scripts", str(len(results)))
    + '</div></div>'

    # ── RESULTADO card ──
    '<div class="card" style="border-left:4px solid ' + ok_color + '">'
    '<div class="section-title" style="color:' + ok_color + '">Resultado</div>'
    '<div style="display:flex;align-items:center;gap:16px;flex-wrap:wrap;margin-bottom:10px">'
    '<span class="badge ' + ('badge-ok' if all_ok else 'badge-fail') + '">' + icon + ' ' + status_txt + '</span>'
    '<span class="stats">\u2705 ' + str(passed) + ' exitosos &nbsp;\u00b7&nbsp; \u274c ' + str(failed) + ' fallidos &nbsp;\u00b7&nbsp; \u23f1 ' + _dur(total_dur) + '</span>'
    '</div>'
    + progress_html +
    '</div>'

    # ── SCRIPTS ──
    '<div class="section-title">\U0001f4cb Scripts ejecutados</div>'
    + scripts_html +

    '</div>'
    '<div class="footer">Generado por HakaBuddy CI Runner &bull; ' + fecha + '</div>'
    '<script>' + JS + '</script>'
    '</body></html>'
)

Path("report.html").write_text(html, encoding="utf-8")
print("\n[OK] Reporte HTML generado: report.html")

sys.exit(0 if failed == 0 else 1)
