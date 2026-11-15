"""Validasi ambang profil terhadap label pendamping/ahli.

Ambang aturan v1 (WER 20%, 60 kata/menit, cakupan tatapan 30%, concordance 40%) belum tervalidasi untuk
anak Indonesia. Modul ini mengukur seberapa baik setiap ambang memisahkan label ahli, menyapu nilai ambang
alternatif, lalu melaporkan sensitivitas, spesifisitas, dan indeks Youden. Hasilnya bahan keputusan:
ambang TIDAK diubah otomatis.

Pemakaian (setelah ada sesi nyata + label ahli):
    python threshold_validation.py labels.csv [--min-sessions 30]
labels.csv: session_id, lalu satu atau lebih kolom label 0/1:
    expert_accuracy_issue  -> diuji terhadap metrics.reading_error_rate (atau wer bila belum ditinjau), arah '>'
    expert_fluency_issue   -> metrics.wpm, arah '<'
    expert_gaze_issue      -> metrics.on_text_percent, arah '<'
    expert_gaze_reliable   -> metrics.gaze_coverage, arah '>='  (apakah tatapan layak dibaca menurut ahli)
    expert_same_word       -> metrics.multimodal.concordance, arah '>='
"""
import argparse
import asyncio
import json
import math

TARGETS = {
    'expert_accuracy_issue': {'metric': 'reading_error_rate', 'fallback': 'wer', 'direction': '>', 'current': 20},
    'expert_fluency_issue': {'metric': 'wpm', 'direction': '<', 'current': 60},
    'expert_gaze_issue': {'metric': 'on_text_percent', 'direction': '<', 'current': 65},
    'expert_gaze_reliable': {'metric': 'gaze_coverage', 'direction': '>=', 'current': 30},
    'expert_same_word': {'metric': 'multimodal.concordance', 'direction': '>=', 'current': 40},
}


def _get(metrics, path):
    v = metrics
    for k in path.split('.'):
        v = v.get(k) if isinstance(v, dict) else None
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) else None


def _flag(value, threshold, direction):
    return {'>': value > threshold, '<': value < threshold, '>=': value >= threshold}[direction]


def confusion(pairs, threshold, direction):
    tp = fp = tn = fn = 0
    for value, label in pairs:
        pred = _flag(value, threshold, direction)
        if pred and label: tp += 1
        elif pred: fp += 1
        elif label: fn += 1
        else: tn += 1
    sens = tp / (tp + fn) if tp + fn else None
    spec = tn / (tn + fp) if tn + fp else None
    youden = sens + spec - 1 if sens is not None and spec is not None else None
    r = lambda x: round(x, 4) if x is not None else None
    return {'threshold': threshold, 'tp': tp, 'fp': fp, 'tn': tn, 'fn': fn, 'sensitivity': r(sens), 'specificity': r(spec), 'youden': r(youden)}


def evaluate(rows, min_sessions=30):
    """rows: list of {'metrics': {...}, '<label>': 0/1}. Mengembalikan laporan per ambang."""
    report = {}
    for label, spec in TARGETS.items():
        pairs = []
        for row in rows:
            if row.get(label) not in (0, 1):
                continue
            value = _get(row['metrics'], spec['metric'])
            if value is None and spec.get('fallback'):
                value = _get(row['metrics'], spec['fallback'])
            if value is not None:
                pairs.append((value, int(row[label])))
        if not pairs:
            continue
        positives = sum(l for _, l in pairs)
        candidates = sorted({v for v, _ in pairs} | {spec['current']})
        sweep = [confusion(pairs, t, spec['direction']) for t in candidates]
        valid = [s for s in sweep if s['youden'] is not None]
        best = max(valid, key=lambda s: (s['youden'], -abs(s['threshold'] - spec['current']))) if valid else None
        report[label] = {
            'metric': spec['metric'], 'direction': spec['direction'], 'sessions': len(pairs), 'positives': positives,
            'current': confusion(pairs, spec['current'], spec['direction']), 'best_youden': best,
            'sufficient_data': len(pairs) >= min_sessions and 0 < positives < len(pairs),
            'note': None if len(pairs) >= min_sessions else f'Hanya {len(pairs)} sesi berlabel; minimal {min_sessions} sebelum ambang dipertimbangkan untuk diubah.',
        }
    return report


async def _load_sessions(ids):
    from core import db
    docs = await db.sessions.find({'id': {'$in': ids}}, {'_id': 0, 'id': 1, 'metrics': 1}).to_list(len(ids))
    return {d['id']: d['metrics'] for d in docs}


def main():
    import pandas as pd
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('labels'); ap.add_argument('--min-sessions', type=int, default=30)
    args = ap.parse_args()
    labels = pd.read_csv(args.labels)
    metrics = asyncio.run(_load_sessions(labels['session_id'].astype(str).tolist()))
    rows = [{**r, 'metrics': metrics[str(r['session_id'])]} for r in labels.to_dict('records') if str(r['session_id']) in metrics]
    print(json.dumps({'matched_sessions': len(rows), 'report': evaluate(rows, args.min_sessions)}, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
