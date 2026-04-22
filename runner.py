"""
HakaBuddy — Runner de pruebas Playwright
Generado automáticamente. No editar manualmente.
"""
import subprocess, sys, os, json, re, tempfile, time, base64
from pathlib import Path
from datetime import datetime

SCRIPTS = [
    "Prueba_Rap\u00edda.py"
]

IS_CI = os.environ.get("CI", "") == "true" or not os.environ.get("DISPLAY", "")

def patch_headless(source):
    source = re.sub(r"headless\s*=\s*False", "headless=True", source)
    source = re.sub(r"slow_mo\s*=\s*\d+", "slow_mo=0", source)
    source = source.replace(
        "page = context.new_page()",
        "page = context.new_page()\n    page.set_default_timeout(60000)"
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

            # _build_instrumented_script retorna el código, no la ruta
            instrumented_code = sr._build_instrumented_script(
                str(path), str(ss_dir), steps_json,
                browser_config={"headless": True, "slow_mo": 0}
            )
            
            # Escribir el código instrumentado a un archivo temporal
            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as tmp:
                tmp.write(instrumented_code)
                instrumented_path = tmp.name
            
            t0 = time.time()
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
        "steps": steps
    })

# ── Resumen consola ───────────────────────────────────────────────
passed  = sum(1 for r in results if r["status"] == "PASS")
failed  = sum(1 for r in results if r["status"] == "FAIL")
skipped = sum(1 for r in results if r["status"] == "SKIP")
print(f"\n=== {passed} PASS / {failed} FAIL / {skipped} SKIP / {len(results)} total ===")

with open("results.json", "w") as f:
    json.dump(results, f, indent=2)

# ── Generar reporte HTML (mismo diseño que HakaBuddy local) ──────
all_ok     = failed == 0
ok_color   = "#28A745" if all_ok else "#DC3545"
ok_bg      = "#1B3A1F" if all_ok else "#3A1B1B"
icon       = "\u2713" if all_ok else "\u2717"
status_txt = "EXITOSO" if all_ok else "FALLIDO"
total_dur  = sum(r["duration"] for r in results)
fecha      = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
pct        = int(passed / len(results) * 100) if results else 0

# Construir acordeones por script
scripts_html = ""
for i, r in enumerate(results):
    s_ok    = r["status"] == "PASS"
    s_color = "#28A745" if s_ok else ("#DC3545" if r["status"] == "FAIL" else "#888888")
    s_bg    = "#1B3A1F" if s_ok else "#3A1B1B"
    s_icon  = "\u2713" if s_ok else ("\u2717" if r["status"] == "FAIL" else "\u2014")

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
                img_html = '<img src="data:image/png;base64,' + b64 + '" class="step-img">'

        err_html = '<div class="step-err">' + _esc(err) + '</div>' if err else ""
        has_body = bool(img_html or err_html)
        body     = '<div class="step-body">' + err_html + img_html + '</div>' if has_body else ""
        arrow    = '<span class="acc-arrow">&#9658;</span>' if has_body else '<span style="width:16px;display:inline-block"></span>'
        cursor   = "cursor:pointer;" if has_body else ""

        pasos_html += (
            '\n<div class="step-row' + (' step-fail' if not s_ok2 else '') + '">'
            '\n  <div class="step-head" style="' + cursor + '" onclick="toggleAcc(this)">'
            '\n    <span class="step-num">#' + str(num) + '</span>'
            '\n    <span class="step-desc">' + _esc(desc) + '</span>'
            '\n    <span class="step-status" style="color:' + sc2 + '">' + si2 + ' ' + ('Exitoso' if s_ok2 else 'Fallido') + '</span>'
            '\n    ' + arrow +
            '\n  </div>' + body +
            '\n</div>'
        )

    scripts_html += (
        '\n<div class="script-acc">'
        '\n  <div class="script-head" onclick="toggleScript(this)">'
        '\n    <span class="script-idx">' + str(i+1) + '</span>'
        '\n    <span class="script-name-lbl">' + _esc(r["script"]) + '</span>'
        '\n    <span class="script-badge" style="background:' + s_bg + ';color:' + s_color + ';border:1px solid ' + s_color + '">' + s_icon + ' ' + r["status"] + '</span>'
        '\n    <span class="script-dur">\u23f1 ' + _dur(r["duration"]) + '</span>'
        '\n    <span class="script-arrow">&#9658;</span>'
        '\n  </div>'
        '\n  <div class="script-body">' + err_script + '<div class="steps-wrap">' + pasos_html + '</div></div>'
        '\n</div>'
    )

CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',Calibri,sans-serif;background:#12132A;color:#E8E8F0;padding:32px;font-size:15px;line-height:1.6}
.main-header{background:#1E1F33;border-radius:12px;padding:24px 32px;margin-bottom:24px;border-left:5px solid #00D4FF}
.suite-title{font-size:24px;font-weight:700;color:#00D4FF;margin-bottom:12px}
.status-row{display:flex;align-items:center;gap:16px;flex-wrap:wrap;margin-bottom:12px}
.status-badge{padding:7px 22px;border-radius:22px;font-weight:700;font-size:16px;border:2px solid}
.stats-row{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:12px}
.stat-box{padding:6px 16px;border-radius:8px;font-weight:bold;font-size:14px}
.stat-box.green{background:#1B3A1F;color:#28A745;border:1px solid #28A745}
.stat-box.red{background:#3A1B1B;color:#DC3545;border:1px solid #DC3545}
.stat-box.blue{background:#1A2A3A;color:#00D4FF;border:1px solid #00D4FF}
.progress-wrap{background:#2A2B3E;border-radius:6px;height:8px;overflow:hidden;margin-bottom:6px}
.progress-bar{height:8px;border-radius:6px}
.scripts-title{font-size:18px;font-weight:700;color:#00D4FF;margin-bottom:16px}
.script-acc{background:#1E1F33;border-radius:10px;margin-bottom:12px;overflow:hidden}
.script-head{display:flex;align-items:center;gap:12px;padding:14px 18px;cursor:pointer;transition:background .15s}
.script-head:hover{background:#252640}
.script-idx{background:#252640;color:#8888AA;padding:2px 8px;border-radius:5px;font-size:13px;font-weight:700;min-width:30px;text-align:center;flex-shrink:0}
.script-name-lbl{font-weight:700;color:#FFF;font-size:16px;flex:1}
.script-badge{padding:3px 14px;border-radius:14px;font-size:13px;font-weight:700;flex-shrink:0}
.script-dur{color:#8888AA;font-size:13px;flex-shrink:0}
.script-arrow{color:#8888AA;font-size:12px;transition:transform .2s;display:inline-block;flex-shrink:0}
.script-body{display:none;padding:0 18px 16px 18px;border-top:1px solid #2E2F45}
.steps-wrap{margin-top:8px}
.step-row{background:#252640;border-radius:8px;margin-bottom:6px;overflow:hidden}
.step-row.step-fail{background:#2D1A1A}
.step-head{display:flex;align-items:center;gap:12px;padding:10px 14px;transition:background .15s}
.step-head:hover{background:rgba(255,255,255,.04);border-radius:8px}
.step-num{background:#1E1F33;color:#8888AA;padding:2px 8px;border-radius:4px;font-size:12px;font-weight:700;min-width:36px;text-align:center;flex-shrink:0}
.step-desc{font-weight:600;color:#FFF;font-size:14px;flex:1}
.step-status{font-weight:700;font-size:13px;white-space:nowrap;flex-shrink:0}
.acc-arrow{color:#8888AA;font-size:11px;transition:transform .2s;display:inline-block;flex-shrink:0}
.step-body{display:none;padding:0 14px 12px 14px}
.step-err{color:#FF6B6B;font-size:13px;font-family:Consolas,monospace;background:#3D1A1A;padding:6px 10px;border-radius:5px;margin-top:6px;white-space:pre-wrap}
.step-img{max-width:100%;border-radius:6px;border:1px solid #3A3B50;margin-top:8px;display:block}
.error-box{background:#2D1A1A;border:1px solid #DC3545;border-radius:8px;padding:14px;margin:10px 0}
.error-title{color:#DC3545;font-weight:700;margin-bottom:6px}
.error-content{color:#FFAAAA;font-size:12px;white-space:pre-wrap;font-family:Consolas,monospace}
.footer{text-align:center;color:#555577;font-size:12px;margin-top:24px}
"""

JS = """
function toggleScript(h){
  var b=h.nextElementSibling,a=h.querySelector('.script-arrow');
  if(!b)return;
  b.style.display=b.style.display==='block'?'none':'block';
  if(a)a.style.transform=b.style.display==='block'?'rotate(90deg)':'rotate(0deg)';
}
function toggleAcc(h){
  var b=h.nextElementSibling,a=h.querySelector('.acc-arrow');
  if(!b)return;
  b.style.display=b.style.display==='block'?'none':'block';
  if(a)a.style.transform=b.style.display==='block'?'rotate(90deg)':'rotate(0deg)';
}
document.addEventListener('DOMContentLoaded',function(){
  document.querySelectorAll('.script-acc').forEach(function(acc){
    var badge=acc.querySelector('.script-badge');
    if(badge&&badge.textContent.includes('FAIL')){
      toggleScript(acc.querySelector('.script-head'));
    }
  });
});
"""

html = (
    '<!DOCTYPE html><html lang="es"><head><meta charset="utf-8">'
    '<title>HakaBuddy CI &mdash; Reporte Suite</title>'
    '<style>' + CSS + '</style></head><body>'
    '<div class="main-header">'
    '<div class="suite-title">&#127917; HakaBuddy CI &mdash; Reporte de Suite</div>'
    '<div class="status-row">'
    '<span class="status-badge" style="background:' + ok_bg + ';color:' + ok_color + ';border-color:' + ok_color + '">' + icon + ' ' + status_txt + '</span>'
    '<span style="color:#9999BB">\u23f1 ' + _dur(total_dur) + '</span>'
    '<span style="color:#9999BB">&#128203; ' + str(len(results)) + ' scripts</span>'
    '<span style="color:#9999BB">&#128197; ' + fecha + '</span>'
    '</div>'
    '<div class="stats-row">'
    '<div class="stat-box green">&#10003; ' + str(passed) + ' exitosos</div>'
    '<div class="stat-box red">&#10007; ' + str(failed) + ' fallidos</div>'
    '<div class="stat-box blue">\u23f1 ' + _dur(total_dur) + '</div>'
    '</div>'
    '<div class="progress-wrap"><div class="progress-bar" style="width:' + str(pct) + '%;background:' + ok_color + '"></div></div>'
    '<div style="color:#8888AA;font-size:13px">' + str(pct) + '% exitoso</div>'
    '</div>'
    '<div class="scripts-title">&#128203; Scripts ejecutados</div>'
    + scripts_html +
    '<div class="footer">Generado por HakaBuddy CI Runner &bull; ' + fecha + '</div>'
    '<script>' + JS + '</script>'
    '</body></html>'
)

Path("report.html").write_text(html, encoding="utf-8")
print("\n[OK] Reporte HTML generado: report.html")

sys.exit(0 if failed == 0 else 1)
