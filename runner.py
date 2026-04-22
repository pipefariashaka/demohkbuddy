"""
HakaBuddy — Runner de pruebas Playwright
Generado automáticamente. No editar manualmente.
"""
import subprocess, sys, os, json
from pathlib import Path

SCRIPTS = [
    "hol123456.py",
    "pool.py",
]

results = []
base = Path(__file__).parent / 'scripts'

for name in SCRIPTS:
    path = base / name
    if not path.exists():
        print(f'[SKIP] {name} no encontrado')
        results.append({'script': name, 'status': 'SKIP'})
        continue
    print(f'[RUN]  {name}')
    r = subprocess.run([sys.executable, str(path)], capture_output=True, text=True)
    ok = r.returncode == 0
    status = 'PASS' if ok else 'FAIL'
    print(f'[{status}] {name}')
    if not ok:
        print(r.stderr[-500:])
    results.append({'script': name, 'status': status})

# Resumen
passed = sum(1 for r in results if r['status'] == 'PASS')
failed = sum(1 for r in results if r['status'] == 'FAIL')
print(f'\n=== Resultado: {passed} PASS / {failed} FAIL / {len(results)} total ===')

with open('results.json', 'w') as f:
    json.dump(results, f, indent=2)

sys.exit(0 if failed == 0 else 1)