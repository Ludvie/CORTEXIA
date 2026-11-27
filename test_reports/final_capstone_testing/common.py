"""Shared helpers for isolated final testing. No production mutations."""
import csv, hashlib, json, os, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(OUT / '_test_dependencies'))
sys.path.insert(0, str(ROOT / 'backend'))
os.environ['MONGO_URL'] = os.environ.get('CORTEXIA_TEST_MONGO_URL','mongodb://127.0.0.1:27017')
os.environ['DB_NAME'] = 'cortexia_finaltest_20261127'
os.environ['CORS_ORIGINS'] = 'http://127.0.0.1:3000'
os.environ['MPLCONFIGDIR'] = str(OUT / '_matplotlib')
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
SECTIONS = ['01_whitebox','02_vad','03_eye_tracking','04_speech_recognition','05_pronunciation','06_fluency','07_multimodal_fusion','08_nonfunctional','09_integration','10_existing_ml_results','11_existing_turead_results']
for section in SECTIONS: (OUT / section).mkdir(exist_ok=True)
def dump(path, obj):
    (OUT / path).write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False, default=str), encoding='utf-8')
def write(path, text): (OUT / path).write_text(text, encoding='utf-8')
def csvout(path, rows, fields=None):
    with (OUT / path).open('w', newline='', encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f, fieldnames=fields or list(dict.fromkeys(k for row in rows for k in row)))
        writer.writeheader(); writer.writerows(rows)
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for part in iter(lambda:f.read(2**20), b''):h.update(part)
    return h.hexdigest()
def snapshot():
    files=list((ROOT/'backend').glob('*.py'))+list((ROOT/'frontend/src').rglob('*'))
    files += list((ROOT/'backend/models').rglob('*'))+list((ROOT/'test_reports/ml_comparison').rglob('*'))
    files += [ROOT/'backend/requirements.txt',ROOT/'frontend/package.json',ROOT/'scripts/run-backend.cmd']
    return {str(p.relative_to(ROOT)):sha(p) for p in sorted(set(files)) if p.is_file() and '__pycache__' not in p.parts}
def log(text):
    with (OUT/'EXECUTION.log').open('a',encoding='utf-8') as f:f.write(time.strftime('%Y-%m-%dT%H:%M:%S')+' '+text+'\n')
    print(text,flush=True)
