"""Uji alat validasi ambang (perhitungan sensitivitas/spesifisitas/Youden) dengan data yang hasilnya diketahui."""
import os
import sys

os.environ.setdefault("MONGO_URL", "mongodb://127.0.0.1:27017")
os.environ.setdefault("DB_NAME", "cortexia_unit")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from threshold_validation import confusion, evaluate  # noqa: E402


def test_confusion_counts_and_rates():
    pairs = [(10, 0), (15, 0), (25, 1), (30, 1), (22, 0), (18, 1)]
    c = confusion(pairs, 20, ">")
    assert (c["tp"], c["fp"], c["tn"], c["fn"]) == (2, 1, 2, 1)
    assert c["sensitivity"] == round(2 / 3, 4) and c["specificity"] == round(2 / 3, 4) and c["youden"] == round(1 / 3, 4)


def test_evaluate_finds_separating_threshold_and_flags_small_samples():
    rows = [{"metrics": {"wpm": w}, "expert_fluency_issue": int(w < 50)} for w in (30, 40, 45, 55, 70, 90)]
    rep = evaluate(rows, min_sessions=30)["expert_fluency_issue"]
    assert rep["best_youden"]["youden"] == 1.0 and rep["best_youden"]["threshold"] == 55
    assert rep["current"]["threshold"] == 60 and rep["current"]["fp"] == 1
    assert rep["sufficient_data"] is False and "minimal 30" in rep["note"]


def test_reading_error_rate_falls_back_to_wer_and_skips_missing():
    rows = [{"metrics": {"wer": 30}, "expert_accuracy_issue": 1},
            {"metrics": {"reading_error_rate": 5, "wer": 50}, "expert_accuracy_issue": 0},
            {"metrics": {}, "expert_accuracy_issue": 1}]
    rep = evaluate(rows, min_sessions=1)["expert_accuracy_issue"]
    assert rep["sessions"] == 2 and rep["current"]["tp"] == 1 and rep["current"]["tn"] == 1


def test_nested_concordance_metric():
    rows = [{"metrics": {"multimodal": {"concordance": c}}, "expert_same_word": int(c >= 50)} for c in (0, 20, 50, 80)]
    rep = evaluate(rows, min_sessions=1)["expert_same_word"]
    assert rep["current"]["sensitivity"] == 1.0 and rep["current"]["specificity"] == 1.0
