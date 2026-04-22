"""
HakaBuddy — Runner de pruebas Playwright
Generado automáticamente. No editar manualmente.
"""
import subprocess, sys, os, json, re, tempfile
from pathlib import Path

SCRIPTS = [
    "hol123456.py",
    "pool.py",
]

# En CI (sin display) forzar headless=True
IS_CI = os.environ.get('CI', '') == 'true' or not os.environ.get('DISPLAY', '')

def patch_headless(source: str) -> str:
    """Reemplaza headless=False por headless=True en el script."""
    return re.sub(r'headless\s*=\s*False', 'headless=True', source)

results = []
base = Path(__file__).parent / 'scripts'

for name in SCRIPTS:
    path = base / name
    if not path.exists():
        print(f'[SKIP] {name} no encontrado')
        results.append({'script': name, 'status': 'SKIP'})
        continue
    print(f'[RUN]  {name}')

    # Si estamos en CI, parchear headless antes de ejecutar
    if IS_CI:
        source = path.read_text(encoding='utf-8')
        patched = patch_headless(source)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py',
                                         delete=False, encoding='utf-8') as tmp:
            tmp.write(patched)
            run_path = tmp.name
    else:
        run_path = str(path)

    r = subprocess.run([sys.executable, run_path], capture_output=True, text=True)

    if IS_CI and run_path != str(path):
        os.unlink(run_path)  # limpiar temporal

    ok = r.returncode == 0
    status = 'PASS' if ok else 'FAIL'
    print(f'[{status}] {name}')
    if not ok:
        print(r.stderr[-800:])
    results.append({'script': name, 'status': status})

# Resumen
passed = sum(1 for r in results if r['status'] == 'PASS')
failed = sum(1 for r in results if r['status'] == 'FAIL')
print(f'\n=== Resultado: {passed} PASS / {failed} FAIL / {len(results)} total ===')

with open('results.json', 'w') as f:
    json.dump(results, f, indent=2)

sys.exit(0 if failed == 0 else 1)