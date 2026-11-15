"""Prioritas 1 — uji unit deterministik analisis suara (tanpa server, tanpa model)."""
import math
import os
import sys

import pytest

os.environ.setdefault("MONGO_URL", "mongodb://127.0.0.1:27017")
os.environ.setdefault("DB_NAME", "cortexia_unit")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analytics import align, analyze, clean_words, normalize, speech_metrics, validate_pcm, word_error_rate  # noqa: E402

REF = "Rani pergi ke taman bunga, lalu duduk di bangku."  # 9 kata


def words(text, prob=0.9, step=0.6):
    return [{"word": w, "start": i * step, "end": i * step + 0.4, "probability": prob} for i, w in enumerate(text.split())]


# ---------- normalisasi & WER ----------

def test_normalize_strips_punctuation_keeps_hyphenated_words():
    assert normalize("Kupu-kupu, TERBANG!  ke taman.") == "kupu-kupu terbang ke taman"
    assert normalize(None) == "" and normalize("— ... ,") == ""


def test_wer_zero_for_identical_after_normalization():
    a = align(REF, "rani pergi ke taman bunga lalu duduk di bangku")
    assert a["wer"] == 0.0 and a["accuracy"] == 100.0
    assert (a["substitutions"], a["deletions"], a["insertions"], a["correct_words"]) == (0, 0, 0, 9)


def test_wer_substitution():
    a = align(REF, "Rani pergi ke taman bunga lalu duduk di bantal")
    assert a["substitutions"] == 1 and a["deletions"] == 0 and a["insertions"] == 0
    assert a["wer"] == round(1 / 9 * 100, 2)
    assert [x for x in a["annotations"] if x["type"] == "substitute"] == [{"index": 8, "word": "bangku", "type": "substitute", "spoken": "bantal"}]


def test_wer_deletion():
    a = align(REF, "Rani pergi ke taman lalu duduk di bangku")
    assert a["deletions"] == 1 and a["substitutions"] == 0
    assert a["wer"] == round(1 / 9 * 100, 2)
    assert any(x["type"] == "delete" and x["word"] == "bunga" for x in a["annotations"])


def test_wer_insertion_can_exceed_100_but_accuracy_floor_zero():
    a = align("ke taman", "ke ke ke taman taman taman")
    assert a["insertions"] == 4 and a["wer"] == 200.0 and a["accuracy"] == 0


def test_empty_reference_returns_complete_structure():
    a = align("", "apa saja")
    assert a["wer"] is None and a["accuracy"] is None and a["annotations"] == []
    assert word_error_rate("", "x") is None


def test_empty_hypothesis_is_all_deletions():
    a = align(REF, "...")
    assert a["wer"] == 100.0 and a["deletions"] == 9 and a["accuracy"] == 0.0
    assert word_error_rate("a b", "") == 100.0


# ---------- validasi audio & timestamp ----------

def test_validate_pcm_rejects_empty_short_and_digital_silence():
    with pytest.raises(ValueError):
        validate_pcm(b"")
    with pytest.raises(ValueError):
        validate_pcm(b"\x01\x00" * 100)  # 100 sampel = 6 ms
    with pytest.raises(ValueError):
        validate_pcm(b"\x00\x00" * 16000)
    validate_pcm(b"\x01\x00" * 16000)  # 1 detik non-hening: lolos


def test_clean_words_drops_invalid_and_sorts():
    raw = [
        {"word": "b", "start": 1.0, "end": 1.4, "probability": 0.8},
        {"word": "a", "start": 0.0, "end": 0.4, "probability": 1.7},
        {"word": "x", "start": float("nan"), "end": 1.0, "probability": 0.5},
        {"word": "y", "start": -0.2, "end": 0.1, "probability": 0.5},
        {"word": "z", "start": 2.0, "end": 1.5, "probability": 0.5},
        {"word": " ", "start": 2.0, "end": 2.5, "probability": 0.5},
        {"word": "c", "start": 2.0, "end": 2.5, "probability": float("inf")},
    ]
    out, dropped = clean_words(raw)
    assert dropped == 4
    assert [w["word"] for w in out] == ["a", "b", "c"]
    assert out[0]["probability"] == 1.0 and out[2]["probability"] is None


def test_pauses_use_sorted_valid_timestamps():
    w = [{"word": "b", "start": 1.5, "end": 2.0, "probability": 0.9}, {"word": "a", "start": 0.0, "end": 0.5, "probability": 0.9}]
    m, *_ = speech_metrics("a b", "a b", 6, w)
    assert m["pauses"] == 1 and m["pause_seconds"] == 1.0


# ---------- WPM ----------

def test_wpm_formula_and_invalid_duration():
    m, *_ = speech_metrics(REF, REF, 9, words(REF))
    assert m["wpm"] == 60.0
    for bad in (0, -3, float("nan"), float("inf"), None):
        m, *_ = speech_metrics(REF, REF, bad, words(REF))
        assert m["wpm"] is None


# ---------- keandalan & sumber galat ----------

def test_unknown_confidence_is_not_reliable_until_reviewed():
    no_prob = [{"word": w, "start": i * 0.6, "end": i * 0.6 + 0.4} for i, w in enumerate(REF.split())]
    r = analyze(REF, REF, 8, [], {}, no_prob)
    assert r["metrics"]["asr_confidence"] is None and not r["metrics"]["speech_reliable"]
    assert "tidak tersedia" in r["quality_reasons"][0]
    r = analyze(REF, REF, 8, [], {}, no_prob, reviewed=True)
    assert r["metrics"]["speech_reliable"]


def test_automatic_wer_is_not_labelled_as_reading_error():
    r = analyze(REF, "Rani pergi ke taman bunga lalu duduk di bantal", 8, [], {}, words(REF))
    m = r["metrics"]
    assert m["wer_source"] == "transkrip_otomatis"
    assert m["reading_error_rate"] is None and m["asr_wer"] is None


def test_review_separates_asr_wer_from_reading_error_rate():
    automatic = "Rani pergi ke taman bunga lalu duduk di bantal"   # ASR salah dengar 1 kata
    manual = "Rani pergi ke taman lalu duduk di bangku"            # anak melewatkan 'bunga'
    r = analyze(REF, manual, 8, [], {}, words(automatic), reviewed=True, asr_transcript=automatic)
    m = r["metrics"]
    assert m["wer_source"] == "transkrip_manual"
    assert m["reading_error_rate"] == m["wer"] == round(1 / 9 * 100, 2)
    # manual (8 kata) vs otomatis: 1 substitusi (bangku->bantal) + 1 sisipan (bunga) = 2/8
    assert m["asr_wer"] == 25.0


def test_review_without_automatic_transcript_has_no_asr_wer():
    r = analyze(REF, REF, 8, [], {}, [], reviewed=True, asr_transcript=None)
    assert r["metrics"]["asr_wer"] is None and r["metrics"]["reading_error_rate"] == 0.0


def test_no_nan_in_speech_metrics():
    m, *_ = speech_metrics(REF, REF, 8, words(REF))
    for k, v in m.items():
        if isinstance(v, float):
            assert math.isfinite(v), k
