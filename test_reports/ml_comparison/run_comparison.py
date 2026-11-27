"""Evaluate the existing training entry point without changing application source.

Run from repository root:
backend/.venv/Scripts/python test_reports/ml_comparison/run_comparison.py
Outputs refuse to overwrite an earlier run. Full precision OOF values are captured
in memory from the existing cross_val_predict calls using unittest.mock.patch.
"""
import hashlib
import importlib.metadata
import json
import logging
import platform
import subprocess
import sys
import time
import traceback
import warnings
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.dummy import DummyClassifier
from sklearn.metrics import (
    accuracy_score, confusion_matrix, f1_score, precision_score, recall_score,
    roc_auc_score, roc_curve,
)
from sklearn.model_selection import StratifiedGroupKFold, cross_val_predict
from sklearn.pipeline import Pipeline

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
sys.path.insert(0, str(ROOT / "backend"))
import ml_pipeline as source

NAMES = {"logistic": "Logistic Regression", "forest": "Random Forest", "baseline": "Most frequent"}
METRICS = ["accuracy", "precision_macro", "recall_macro", "macro_f1", "roc_auc"]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def scores(y, pred, probability):
    return dict(
        accuracy=accuracy_score(y, pred),
        precision_macro=precision_score(y, pred, average="macro", zero_division=0),
        recall_macro=recall_score(y, pred, average="macro", zero_division=0),
        macro_f1=f1_score(y, pred, average="macro"),
        roc_auc=roc_auc_score(y, probability),
        precision_class_1=precision_score(y, pred, pos_label=1, zero_division=0),
        recall_class_1=recall_score(y, pred, pos_label=1, zero_division=0),
    )


def savefig(fig, name):
    fig.savefig(OUT / (name + ".png"), dpi=200, bbox_inches="tight")
    fig.savefig(OUT / (name + ".pdf"), bbox_inches="tight")
    plt.close(fig)


def charts(units, models):
    for unit, rows in units.items():
        fig, axes = plt.subplots(1, 2, figsize=(10, 4))
        for ax, key in zip(axes, ("logistic", "forest")):
            y, pred, prob = rows[key]
            matrix = confusion_matrix(y, pred, labels=[0, 1])
            pd.DataFrame(matrix, index=["actual_0", "actual_1"],
                         columns=["predicted_0", "predicted_1"]).to_csv(
                             OUT / f"confusion_matrix_{key}_{unit}.csv")
            ax.imshow(matrix, cmap="Blues", vmin=0, vmax=max(1, len(y)/2))
            for (i, j), value in np.ndenumerate(matrix):
                ax.text(j, i, str(value), ha="center", va="center",
                        color="white" if value > len(y)/4 else "black", fontsize=14)
            ax.set(xticks=[0, 1], yticks=[0, 1], xlabel="Predicted class",
                   ylabel="Actual class", title=NAMES[key])
        fig.suptitle("Out-of-fold confusion matrices — " + unit)
        fig.tight_layout()
        savefig(fig, "confusion_matrices_" + unit)

        fig, ax = plt.subplots(figsize=(10, 4.8))
        positions = np.arange(len(METRICS))
        for i, key in enumerate(NAMES):
            values = scores(*rows[key])
            bars = ax.bar(positions + (i-1)*.25, [values[m] for m in METRICS], .25,
                          label=NAMES[key])
            ax.bar_label(bars, fmt="%.3f", fontsize=8)
        ax.set(xticks=positions,
               xticklabels=["Accuracy", "Precision (macro)", "Recall (macro)", "Macro F1", "ROC-AUC"],
               ylim=(0, 1.15), ylabel="Score (0–1)", title="OOF model comparison — " + unit)
        ax.legend(loc="upper center", ncol=3)
        fig.tight_layout()
        savefig(fig, "comparison_" + unit)

        fig, ax = plt.subplots(figsize=(6.5, 5))
        for key in NAMES:
            y, pred, prob = rows[key]
            fpr, tpr, _ = roc_curve(y, prob)
            ax.plot(fpr, tpr, label=f"{NAMES[key]} (AUC={roc_auc_score(y, prob):.4f})")
        ax.plot([0, 1], [0, 1], "--", color="gray", label="Chance")
        ax.set(xlabel="False positive rate", ylabel="True positive rate",
               title="Out-of-fold ROC — " + unit)
        ax.legend(loc="lower right")
        fig.tight_layout()
        savefig(fig, "roc_curve_" + unit)

    for key, model in models.items():
        estimator = model.steps[-1][1]
        values = estimator.coef_[0] if key == "logistic" else estimator.feature_importances_
        frame = pd.DataFrame({"feature": model.feature_names_in_, "value": values})
        frame.to_csv(OUT / f"feature_values_{key}.csv", index=False)
        frame = frame.iloc[np.argsort(np.abs(values))]
        fig, ax = plt.subplots(figsize=(10, 7))
        ax.barh(frame.feature, frame.value, color=["#2563a6" if v >= 0 else "#cf6532" for v in frame.value])
        ax.axvline(0, color="black", linewidth=.7)
        ax.set(xlabel="Standardized coefficient toward class 1" if key == "logistic" else "Impurity-based importance",
               title=NAMES[key] + " — final full-data fit (descriptive)")
        fig.tight_layout()
        savefig(fig, "coefficients_lr" if key == "logistic" else "feature_importance_rf")


def main():
    marker = OUT / "RUN_STARTED.json"
    with marker.open("x", encoding="utf8") as handle:
        json.dump({"started_utc": datetime.now(timezone.utc).isoformat()}, handle)
    logging.basicConfig(filename=OUT / "execution.log", level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))
    logging.captureWarnings(True)
    started = time.perf_counter()
    files = [source.DATA / "dyslexia_class_label.csv",
             *sorted((source.DATA / "data" / "data").glob("*_metrics.csv"))]
    digest_before = source._sha256(files)
    source_hash = sha(Path(source.__file__))
    previous = {str(p.relative_to(ROOT)): sha(p) for p in source.MODELS.rglob("*") if p.is_file()}
    frame = source.dataset_frame()
    features = [c for c in frame if c not in ("subject_id", "task", "label")]
    X, y, groups = frame[features].astype(float), frame.label.astype(int), frame.subject_id.astype(str)
    assert len(frame) == 210 and groups.nunique() == 70 and len(features) == 16
    assert not frame.duplicated(["subject_id", "task"]).any()
    assert frame.groupby("subject_id").label.nunique().eq(1).all()
    assert frame.groupby("subject_id").size().eq(3).all()
    assert y.value_counts().to_dict() == {0: 105, 1: 105}
    assert not set(features) & {"subject_id", "task", "label"}
    cv = list(StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42).split(X, y, groups))
    fold_ids = np.zeros(len(frame), dtype=int)
    audit = []
    for number, (tr, te) in enumerate(cv, 1):
        overlap = set(groups.iloc[tr]) & set(groups.iloc[te])
        assert not overlap
        assert set(y.iloc[tr]) == set(y.iloc[te]) == {0, 1}
        assert not fold_ids[te].any()
        fold_ids[te] = number
        audit.append(dict(fold=number, train_rows=len(tr), test_rows=len(te),
                          train_participants=groups.iloc[tr].nunique(),
                          test_participants=groups.iloc[te].nunique(), participant_overlap=len(overlap),
                          train_index_sha256=hashlib.sha256(tr.astype("<i8").tobytes()).hexdigest(),
                          test_index_sha256=hashlib.sha256(te.astype("<i8").tobytes()).hexdigest()))
    assert (fold_ids > 0).all()
    aliases = {sid: f"P{i+1:03d}" for i, sid in enumerate(sorted(groups.unique()))}
    metadata = pd.DataFrame(dict(row_number=np.arange(len(frame)), participant=groups.map(aliases),
                                 task=frame.task, label=y, fold=fold_ids))
    metadata.to_csv(OUT / "fold_assignments.csv", index=False)
    pd.DataFrame(audit).to_csv(OUT / "leakage_audit.csv", index=False)
    logging.info("Validated 210 records, 70 participants, 16 features; no participant overlap")
    captures, models, parameters = {}, {}, {}
    times = {}
    for key in ("logistic", "forest"):
        collected = {}
        def capture(estimator, x, target, *, cv, method="predict"):
            assert len(cv) == 5
            for (tr, te), (expected_tr, expected_te) in zip(cv, expected_cv):
                assert np.array_equal(tr, expected_tr) and np.array_equal(te, expected_te)
            if isinstance(estimator, Pipeline):
                assert [type(step).__name__ for _, step in estimator.steps[:2]] == ["SimpleImputer", "StandardScaler"]
                assert estimator.steps[0][1].strategy == "median"
                assert not hasattr(estimator.steps[0][1], "statistics_")
                assert not hasattr(estimator.steps[1][1], "mean_")
            output = cross_val_predict(estimator, x, target, cv=expected_cv, method=method)
            collected[("baseline_" if isinstance(estimator, DummyClassifier) else "") + method] = output.copy()
            return output

        expected_cv = cv
        logging.info("Running existing ml_pipeline.train(%s)", key)
        begin = time.perf_counter()
        with patch.object(source, "cross_val_predict", capture):
            report = source.train(algorithm=key, output_dir=OUT / "models" / key)
        times[key] = time.perf_counter() - begin
        model_path = OUT / "models" / key / (report["id"] + ".joblib")
        models[key] = joblib.load(model_path)
        parameters[key] = models[key].steps[-1][1].get_params()
        captures[key] = (collected["predict"], collected["predict_proba"][:, 1])
        baseline = cross_val_predict(DummyClassifier(strategy="most_frequent"), X, y, cv=cv, method="predict_proba")[:, 1]
        if "baseline" in captures:
            assert np.array_equal(captures["baseline"][0], collected["baseline_predict"])
            assert np.array_equal(captures["baseline"][1], baseline)
        captures["baseline"] = (collected["baseline_predict"], baseline)
        assert np.isclose(report["accuracy"], accuracy_score(y, captures[key][0]), atol=.00005)
        assert np.isclose(report["macro_f1"], f1_score(y, captures[key][0], average="macro"), atol=.00005)
        # Retain aggregate report, remove original participant identifiers.
        report.pop("oof")
        (model_path.with_suffix(".json")).write_text(json.dumps(report, indent=2), encoding="utf8")

    record_rows, participant_rows, fold_rows, units = [], [], [], {"recording": {}, "participant": {}}
    for key, (prediction, probability) in captures.items():
        assert len(prediction) == 210 and np.isfinite(probability).all()
        assert ((probability >= 0) & (probability <= 1)).all()
        record_rows.append(dict(model=NAMES[key], unit="recording", n=210,
                                **scores(y, prediction, probability)))
        pd.DataFrame({**metadata.to_dict("series"), "prediction": prediction, "probability": probability}).to_csv(
            OUT / f"oof_{key}.csv", index=False)
        aggregate = metadata.assign(probability=probability).groupby("participant").agg(
            label=("label", "first"), probability=("probability", "mean"),
            recordings=("row_number", "size"), fold=("fold", "first"))
        assert metadata.groupby("participant").fold.nunique().eq(1).all()
        aggregate["prediction"] = (aggregate.probability >= .5).astype(int)
        # Dummy most_frequent emits a one-hot probability for its training majority.
        participant_prediction = aggregate.prediction
        aggregate.to_csv(OUT / f"participant_oof_{key}.csv")
        participant_rows.append(dict(model=NAMES[key], unit="participant", n=70,
                                    **scores(aggregate.label, participant_prediction, aggregate.probability)))
        units["recording"][key] = (y, prediction, probability)
        units["participant"][key] = (aggregate.label, participant_prediction, aggregate.probability)
        for number, (tr, te) in enumerate(cv, 1):
            fold_rows.append(dict(model=NAMES[key], unit="recording", **audit[number-1],
                                  **scores(y.iloc[te], prediction[te], probability[te])))
            part = aggregate[aggregate.fold == number]
            fold_rows.append(dict(model=NAMES[key], unit="participant", **audit[number-1],
                                  **scores(part.label, part.prediction, part.probability)))

    recordings = pd.DataFrame(record_rows)
    participants = pd.DataFrame(participant_rows)
    recordings.to_csv(OUT / "comparison_metrics.csv", index=False)
    participants.to_csv(OUT / "participant_metrics.csv", index=False)
    pd.DataFrame(fold_rows).to_csv(OUT / "fold_metrics.csv", index=False)
    baseline_rows = []
    for table in (recordings, participants):
        base = table[table.model == NAMES["baseline"]].iloc[0]
        for _, row in table[table.model != NAMES["baseline"]].iterrows():
            baseline_rows.append(dict(model=row.model, unit=row.unit,
                                      **{f"delta_{metric}": row[metric]-base[metric] for metric in METRICS}))
    pd.DataFrame(baseline_rows).to_csv(OUT / "baseline_comparison.csv", index=False)
    charts(units, models)
    assert digest_before == source._sha256(files)
    assert source_hash == sha(Path(source.__file__))
    assert previous == {str(p.relative_to(ROOT)): sha(p) for p in source.MODELS.rglob("*") if p.is_file()}
    configuration = dict(
        started_utc=json.loads(marker.read_text())["started_utc"],
        finished_utc=datetime.now(timezone.utc).isoformat(),
        library_versions={p: importlib.metadata.version(p) for p in
                          ["scikit-learn", "numpy", "pandas", "scipy", "joblib", "matplotlib"]},
        python=platform.python_version(), platform=platform.platform(),
        git_head=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        features=features, feature_version=source.FEATURE_VERSION,
        missing_values=X.isna().sum().to_dict(), estimator_parameters=parameters,
        cv=dict(type="StratifiedGroupKFold", n_splits=5, shuffle=True, random_state=42, group="subject_id"),
        preprocessing=["SimpleImputer(strategy=median)", "StandardScaler"],
        dataset_sha256=digest_before, dataset_hash_definition="ml_pipeline._sha256 over sorted source paths; filename bytes then file bytes",
        pipeline_sha256=source_hash, evaluator_sha256=sha(Path(__file__)),
        source_files=[dict(file=str(p.relative_to(source.DATA)), sha256=sha(p)) for p in files],
        participant_aggregation="Mean OOF probability per participant; threshold >=0.5",
        positive_class=1, precision_recall_average="macro", timings_seconds=times,
        total_seconds=time.perf_counter()-started,
        checks=dict(identical_folds=True, participant_overlap_zero=True, all_rows_tested_once=True,
                    preprocessing_inside_cv=True, raw_dataset_unchanged=True,
                    application_pipeline_unchanged=True, previous_model_artifacts_unchanged=True))
    (OUT / "experiment_config.json").write_text(json.dumps(configuration, indent=2), encoding="utf8")
    def table_markdown(table):
        lines = ["| Model | Accuracy | Precision macro | Recall macro | Macro F1 | ROC-AUC |",
                 "|---|---:|---:|---:|---:|---:|"]
        for _, row in table.iterrows():
            lines.append("| " + row.model + " | " + " | ".join(f"{row[m]:.6f}" for m in METRICS) + " |")
        return "\n".join(lines)

    winners = {}
    for unit, table in (("rekaman", recordings), ("peserta", participants)):
        eligible = table[table.model != NAMES["baseline"]].sort_values("macro_f1", ascending=False)
        winners[unit] = (eligible.iloc[0].model, eligible.iloc[0].macro_f1, eligible.iloc[0].macro_f1-eligible.iloc[1].macro_f1)
    report = f"""# Perbandingan Logistic Regression dan Random Forest CORTEXIA

Eksperimen dijalankan langsung pada dataset ETDD70 v2 melalui fungsi backend/ml_pipeline.py train.
Tanggal mulai UTC {configuration['started_utc']}. HEAD {configuration['git_head']}.

## Metode

Dataset terdiri atas 210 rekaman, 70 peserta, dan 16 fitur aktual pipeline. Tiap peserta mempunyai tiga rekaman.
Labels pada tingkat rekaman berimbang 105/105. Label 1 adalah kelas dyslexic pada dataset.
Pembagian StratifiedGroupKFold lima fold, shuffle=True, random_state=42, dan group subject_id dipakai identik
untuk LR, RF, serta baseline. Setiap rekaman masuk test tepat sekali. Seluruh fold memiliki overlap peserta nol.
Imputasi median dan StandardScaler berada di dalam pipeline yang di-clone dan di-fit hanya pada training fold.
Tidak ada cleaning tambahan atau pencarian hyperparameter.

Script memanggil train dua kali. Wrapper in-memory memverifikasi fold yang diberikan pipeline dan menangkap
keluaran cross_val_predict pada presisi penuh sebelum JSON aplikasi membulatkan probabilitas.
Kode aplikasi tetap identik menurut SHA256. Dataset dan artefak riset sebelumnya juga diperiksa hash-nya
sebelum dan setelah eksperimen. File baru disimpan dalam folder eksperimen ini.
Laporan model baru mempertahankan metrik agregat. OOF terpisah memakai alias peserta P001 dan seterusnya.

LR memakai C=0.1, max_iter=3000, class_weight=balanced, random_state=42.
RF memakai 160 pohon, max_depth=5, min_samples_leaf=3, n_jobs=2, class_weight=balanced, random_state=42.
Parameter lengkap termasuk default versi terpasang tercantum di experiment_config.json.
Baseline adalah DummyClassifier most_frequent yang di-fit pada training fold.

## Evaluasi per rekaman

{table_markdown(recordings)}

## Evaluasi per peserta

Probabilitas OOF tiga rekaman dirata-ratakan per peserta, lalu kelas ditentukan pada ambang >=0.5.
Precision dan recall tabel memakai macro average dengan zero_division=0. ROC-AUC memakai probabilitas kelas 1.
Probabilitas baseline berasal dari training fold, termasuk pada agregasi peserta.

{table_markdown(participants)}

## Model dengan Macro F1 tertinggi

Per rekaman, {winners['rekaman'][0]} memperoleh Macro F1 {winners['rekaman'][1]:.6f},
selisih {winners['rekaman'][2]:.6f} terhadap model pembanding.
Per peserta, {winners['peserta'][0]} memperoleh Macro F1 {winners['peserta'][1]:.6f},
selisih {winners['peserta'][2]:.6f}.
Penetapan pemenang ini berlaku untuk pembagian fold dan dataset eksperimen ini.
Selisih terhadap baseline untuk masing-masing unit disimpan di baseline_comparison.csv.

## Grafik dan tabel

- comparison_metrics.csv berisi pooled OOF per rekaman.
- participant_metrics.csv berisi pooled OOF per peserta.
- fold_metrics.csv memuat kedua unit, jumlah training/testing, overlap, dan hash indeks fold.
- leakage_audit.csv serta fold_assignments.csv memungkinkan pemeriksaan pemisahan peserta.
- confusion_matrices_recording.png dan confusion_matrices_participant.png memuat matriks LR/RF.
- comparison_recording.png dan comparison_participant.png membandingkan lima metrik.
- roc_curve_recording.png dan roc_curve_participant.png memuat kurva OOF dan baseline.
- feature_importance_rf.png berisi impurity-based importance dari fit akhir seluruh data.
- coefficients_lr.png berisi koefisien bertanda, pada fitur yang distandardisasi, menuju kelas 1.
- Semua grafik juga diekspor ke PDF; nilai numerik matriks dan fitur disimpan dalam CSV.

Grafik fitur menjelaskan model akhir yang dilatih pipeline setelah CV. Seluruh angka performa dan kurva ROC
dihitung dari OOF. Magnitudo koefisien bergantung pada standardisasi dan korelasi fitur. Importance RF dapat
bias pada karakteristik fitur; kedua grafik belum menunjukkan hubungan sebab-akibat.

## Keterbatasan dan leakage

Pemeriksaan ini membuktikan tidak ada overlap peserta dalam train/test pada data yang diberikan, fitur identitas
tidak masuk X, dan preprocessing dipelajari di dalam CV. Pemeriksaan tidak dapat menyingkirkan seluruh bias
pada proses pengumpulan sumber atau ketergantungan fitur terhadap target secara substantif.
Peserta uji berbeda, tetapi stimulus/tugas dapat berulang antar peserta.
Tiga rekaman satu peserta saling berkaitan, sehingga metrik peserta perlu dilaporkan bersama metrik rekaman.
Tidak dilakukan uji signifikansi, confidence interval, tuning, external test, atau validasi webcam Indonesia.
Memilih model terbaik dari CV yang sama belum memberikan estimasi generalisasi independen setelah seleksi.
Eksperimen tidak mengubah model yang dipakai assessment dan tidak menghasilkan probabilitas klinis pengguna.

## Reproduksi dan error

Library aktual, konfigurasi lengkap, hash setiap file dataset, hash agregat, hash pipeline, dan hash evaluator
ada di experiment_config.json. Execution.log mencatat eksekusi dan warning. ERRORS.md mencatat error persiapan.
Jalankan dari root dengan backend/.venv/Scripts/python test_reports/ml_comparison/run_comparison.py.
Script menolak overwrite ketika RUN_STARTED.json sudah ada; gunakan folder baru untuk eksperimen berikutnya.
Diperlukan dependensi backend serta matplotlib. Durasi total {configuration['total_seconds']:.2f} detik.
"""
    (OUT / "ML_COMPARISON_REPORT.md").write_text(report, encoding="utf8")
    (OUT / "artifact_manifest.json").write_text(json.dumps(
        {str(p.relative_to(OUT)): sha(p) for p in sorted(OUT.rglob("*")) if p.is_file() and p.name not in
         ("artifact_manifest.json", "execution.log")}, indent=2), encoding="utf8")
    logging.info("Completed. Winners: %s", winners)


if __name__ == "__main__":
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        main()
    except Exception:
        with (OUT / "ERRORS.md").open("a", encoding="utf8") as handle:
            handle.write("\n\nExecution failure\n\n" + traceback.format_exc())
        raise
