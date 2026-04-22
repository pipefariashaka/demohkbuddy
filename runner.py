"""
HakaBuddy — Runner de pruebas Playwright
Generado automáticamente. No editar manualmente.
"""
import subprocess, sys, os, json, re, tempfile, time
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
    s = int(s)
    return f"{s//60}m {s%60}s" if s >= 60 else f"{s}s"

# ── Ejecutar scripts ──────────────────────────────────────────────
results = []
base = Path(__file__).parent / "scripts"

for name in SCRIPTS:
    path = base / name
    if not path.exists():
        print(f"[SKIP] {name}")
        results.append({"script": name, "status": "SKIP", "duration": 0, "error": "Archivo no encontrado"})
        continue
    print(f"[RUN]  {name}")
    if IS_CI:
        source = path.read_text(encoding="utf-8")
        patched = patch_headless(source)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as tmp:
            tmp.write(patched)
            run_path = tmp.name
    else:
        run_path = str(path)
    t0 = time.time()
    r = subprocess.run([sys.executable, run_path], capture_output=True, text=True)
    duration = round(time.time() - t0, 1)
    if IS_CI and run_path != str(path):
        os.unlink(run_path)
    ok = r.returncode == 0
    status = "PASS" if ok else "FAIL"
    print(f"[{status}] {name} ({duration}s)")
    stderr_lines = [l for l in r.stderr.splitlines() if l.strip()]
    relevant = [l for l in stderr_lines if any(x in l for x in ["Error", "Timeout", "assert"])]
    error_msg = "\n".join(relevant[-5:]) if relevant else (r.stderr[-400:] if not ok else "")
    if not ok:
        print(error_msg)
    results.append({"script": name, "status": status, "duration": duration, "error": error_msg})

# ── Resumen consola ───────────────────────────────────────────────
passed  = sum(1 for r in results if r["status"] == "PASS")
failed  = sum(1 for r in results if r["status"] == "FAIL")
skipped = sum(1 for r in results if r["status"] == "SKIP")
print(f"\n=== {passed} PASS / {failed} FAIL / {skipped} SKIP / {len(results)} total ===")

with open("results.json", "w") as f:
    json.dump(results, f, indent=2)

# ── Generar reporte HTML ──────────────────────────────────────────
all_ok     = failed == 0
ok_color   = "#28A745" if all_ok else "#DC3545"
ok_bg      = "#1B3A1F" if all_ok else "#3A1B1B"
icon       = "\u2713" if all_ok else "\u2717"
status_txt = "EXITOSO" if all_ok else "FALLIDO"
total_dur  = sum(r["duration"] for r in results)
fecha      = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
pct        = int(passed / len(results) * 100) if results else 0

rows = ""
for i, r in enumerate(results):
    sc  = "#28A745" if r["status"]=="PASS" else ("#DC3545" if r["status"]=="FAIL" else "#888888")
    si  = "\u2713" if r["status"]=="PASS" else ("\u2717" if r["status"]=="FAIL" else "\u2014")
    err = f'<div class="step-err">{_esc(r["error"])}</div>' if r["error"] else ""
    has = bool(r["error"])
    arrow  = '<span class="acc-arrow">&#9658;</span>' if has else ""
    cursor = "cursor:pointer;" if has else ""
    body   = f'<div class="acc-body">{err}</div>' if has else ""
    rows += f"""
    <div class="acc">
      <div class="acc-head" style="{cursor}border-color:{sc}" onclick="toggleAcc(this)">
        <span class="step-num">#{i+1}</span>
        <span class="step-desc">{_esc(r["script"])}</span>
        <span class="step-status" style="color:{sc}">{si} {r["status"]}</span>
        <span class="step-dur">{_dur(r["duration"])}</span>
        {arrow}
      </div>
      {body}
    </div>"""

html = f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8"><title>HakaBuddy CI Report</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',sans-serif;background:#12132A;color:#E8E8F0;padding:32px;font-size:16px}
.main-header{background:#1E1F33;border-radius:12px;padding:24px 32px;margin-bottom:24px;border-left:5px solid #00D4FF}
.suite-title{font-size:24px;font-weight:700;color:#00D4FF;margin-bottom:12px}
.status-row{display:flex;align-items:center;gap:16px;flex-wrap:wrap;margin-bottom:12px}
.status-badge{padding:7px 22px;border-radius:22px;font-weight:700;font-size:16px;border:2px solid}
.stats-row{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:10px}
.stat-box{padding:6px 16px;border-radius:8px;font-weight:bold;font-size:14px}
.stat-box.green{background:#1B3A1F;color:#28A745;border:1px solid #28A745}
.stat-box.red{background:#3A1B1B;color:#DC3545;border:1px solid #DC3545}
.stat-box.blue{background:#1A2A3A;color:#00D4FF;border:1px solid #00D4FF}
.progress-wrap{background:#2A2B3E;border-radius:6px;height:8px;overflow:hidden;margin-bottom:6px}
.progress-bar{height:8px;border-radius:6px}
.scripts-title{font-size:18px;font-weight:700;color:#00D4FF;margin:20px 0 12px}
.acc{background:#1E1F33;border-radius:10px;margin-bottom:8px;overflow:hidden}
.acc-head{display:flex;align-items:center;gap:12px;padding:14px 18px;border:1px solid #3A3B50;border-radius:10px;transition:background .15s}
.acc-head:hover{background:#252640}
.step-num{background:#252640;color:#8888AA;padding:2px 8px;border-radius:5px;font-size:13px;font-weight:700;min-width:36px;text-align:center}
.step-desc{font-weight:600;color:#FFF;font-size:15px;flex:1}
.step-status{font-weight:700;font-size:14px;white-space:nowrap}
.step-dur{color:#8888AA;font-size:13px;white-space:nowrap}
.acc-arrow{color:#8888AA;font-size:12px;transition:transform .2s;display:inline-block}
.acc-body{display:none;padding:10px 18px 14px}
.step-err{color:#FF6B6B;font-size:13px;font-family:Consolas,monospace;background:#3D1A1A;padding:8px 12px;border-radius:6px;white-space:pre-wrap}
.footer{text-align:center;color:#555577;font-size:12px;margin-top:24px}
</style></head><body>
<div class="main-header">
  <div class="suite-title">&#127917; HakaBuddy CI &mdash; Reporte de Suite</div>
  <div class="status-row">
    <span class="status-badge" style="background:{ok_bg};color:{ok_color};border-color:{ok_color}">{icon} {status_txt}</span>
    <span style="color:#9999BB">&#9201; {_dur(total_dur)}</span>
    <span style="color:#9999BB">&#128203; {len(results)} scripts</span>
    <span style="color:#9999BB">&#128197; {fecha}</span>
  </div>
  <div class="stats-row">
    <div class="stat-box green">&#10003; {passed} exitosos</div>
    <div class="stat-box red">&#10007; {failed} fallidos</div>
    <div class="stat-box blue">&#9201; {_dur(total_dur)}</div>
  </div>
  <div class="progress-wrap"><div class="progress-bar" style="width:{pct}%;background:{ok_color}"></div></div>
  <div style="color:#8888AA;font-size:13px">{pct}% exitoso</div>
</div>
<div class="scripts-title">&#128203; Scripts ejecutados</div>
{rows}
<div class="footer">Generado por HakaBuddy CI Runner &bull; {fecha}</div>
<script>
function toggleAcc(h){var b=h.nextElementSibling,a=h.querySelector('.acc-arrow');if(!b)return;
b.style.display=b.style.display==='block'?'none':'block';
if(a)a.style.transform=b.style.display==='block'?'rotate(90deg)':'rotate(0deg)';}
document.addEventListener('DOMContentLoaded',function(){
document.querySelectorAll('.acc').forEach(function(a){
var s=a.querySelector('.step-status');
if(s&&s.textContent.includes('FAIL')){var h=a.querySelector('.acc-head');if(h)toggleAcc(h);}
});});
</script>
</body></html>"""

Path("report.html").write_text(html, encoding="utf-8")
print(f"\n\U0001f4c4 Reporte HTML generado: report.html")

sys.exit(0 if failed == 0 else 1)
