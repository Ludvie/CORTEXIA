"""Prioritas 2 — uji unit deterministik eye-tracking: timestamp, sampling, I-DT, pemetaan kata, regresi, quality gate."""
import os
import sys

os.environ.setdefault("MONGO_URL", "mongodb://127.0.0.1:27017")
os.environ.setdefault("DB_NAME", "cortexia_unit")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analytics import (  # noqa: E402
    MIN_FIX_S, assign_word, calibration_ok, classify_transitions, clean_gaze, clean_layouts,
    fixations_idt, gaze_metrics, layout_at,
)

CAL_OK = {"median_error": 0.08, "validation_samples": 40, "passed": True}
W, H = 800, 400


def run(t0, n, dt, x=0.5, y=0.5, jitter=0.0):
    return [{"x": x + (jitter if i % 2 else 0), "y": y, "t": round(t0 + i * dt, 3)} for i in range(n)]


# ---------- kalibrasi ----------

def test_calibration_requires_passed_flag_and_limits():
    assert calibration_ok(CAL_OK)
    assert not calibration_ok({**CAL_OK, "passed": False})
    assert not calibration_ok({"median_error": 0.08, "validation_samples": 40})  # payload lama tanpa passed
    assert not calibration_ok({**CAL_OK, "median_error": 0.17})
    assert calibration_ok({**CAL_OK, "median_error": 0.16})  # batas inklusif
    assert not calibration_ok({**CAL_OK, "validation_samples": 14})
    assert not calibration_ok({**CAL_OK, "median_error": None})
    assert not calibration_ok({**CAL_OK, "median_error": float("nan")})
    assert not calibration_ok(None)


# ---------- timestamp & sampling ----------

def test_clean_gaze_reports_duplicates_order_range_and_invalid():
    pts = [{"x": .5, "y": .5, "t": 0.2}, {"x": .5, "y": .5, "t": 0.1}, {"x": .5, "y": .5, "t": 0.1},
           {"x": float("nan"), "y": .5, "t": 0.3}, {"x": .5, "y": .5, "t": -1}, {"x": .5, "y": .5, "t": 9.0}]
    valid, s = clean_gaze(pts, duration=1.0)
    assert [p["t"] for p in valid] == [0.1, 0.2]
    assert s == {**s, "received": 6, "valid": 2, "invalid": 2, "duplicates": 1, "out_of_range": 1, "out_of_order": 1}


def test_tolerance_keeps_points_just_after_duration():
    valid, s = clean_gaze([{"x": .5, "y": .5, "t": 1.2}, {"x": .5, "y": .5, "t": 1.3}], duration=1.0)
    assert [p["t"] for p in valid] == [1.2] and s["out_of_range"] == 1


def test_interval_statistics():
    pts = run(0, 5, 0.1) + [{"x": .5, "y": .5, "t": 1.5}]  # 4 interval 100 ms + 1 celah 1,1 s
    _, s = clean_gaze(pts, duration=2)
    assert s["interval_median_ms"] == 100.0 and s["large_gaps"] == 1
    assert s["effective_rate_hz"] == round(5 / 1.5, 1)


def test_duplicates_and_out_of_range_do_not_inflate_coverage():
    good = run(0, 24, 0.125)                     # 8 Hz selama 3 detik -> cakupan 100%
    m = gaze_metrics(good, 10, CAL_OK)            # durasi 10 s -> 24/80 = 30%
    assert m["gaze_coverage"] == 30.0 and m["gaze_usable"]
    padded = good + [dict(p) for p in good] + run(20, 30, 0.1)  # duplikat + 30 titik setelah sesi
    m2 = gaze_metrics(padded, 10, CAL_OK)
    assert m2["gaze_samples"] == 24 and m2["gaze_coverage"] == 30.0
    assert m2["gaze_sampling"]["duplicates"] == 24 and m2["gaze_sampling"]["out_of_range"] == 30


def test_quality_gate_uses_named_thresholds():
    assert not gaze_metrics(run(0, 19, 0.1), 2, CAL_OK)["gaze_usable"]   # 19 < 20 sampel
    assert gaze_metrics(run(0, 20, 0.1), 2, CAL_OK)["gaze_usable"]        # 20 sampel, cakupan 100%
    low = gaze_metrics(run(0, 20, 0.1), 9, CAL_OK)                        # 20/72 = 27,8% < 30%
    assert low["gaze_analyzable"] and not low["gaze_usable"]
    assert not gaze_metrics(run(0, 20, 0.1), 2, {**CAL_OK, "passed": False})["gaze_usable"]


def test_empty_or_zero_duration_gaze_is_safe():
    m = gaze_metrics([], 0, CAL_OK)
    assert m["gaze_samples"] == 0 and m["gaze_coverage"] == 0.0 and m["gaze_rate_hz"] == 0.0 and not m["gaze_usable"]
    m = gaze_metrics(run(0, 25, 0.1), float("nan"), CAL_OK)
    assert m["gaze_rate_hz"] == 0.0 and not m["gaze_usable"]


# ---------- I-DT ----------

def test_idt_accepts_exactly_120ms():
    f = fixations_idt(run(0, 4, 0.04), W, H)      # 0,00 .. 0,12 s
    assert len(f) == 1 and f[0]["d"] == 120.0 and f[0]["n"] == 4


def test_idt_rejects_window_shorter_than_120ms_even_when_cut_by_gap():
    # 0,00-0,08 s lalu celah 0,6 s (> MAX_GAP_S): dulu lolos karena toleransi 0,6 x 120 ms = 72 ms.
    pts = run(0, 3, 0.04) + run(0.68, 2, 0.04, x=0.9)
    assert fixations_idt(pts, W, H) == []
    assert MIN_FIX_S == 0.12


def test_idt_dispersion_boundary():
    # dispersi = (max x - min x) + (max y - min y) dalam piksel; 80 px lolos, 81 px ditolak
    ok = [{"x": 0.5 + (80 / W if i == 1 else 0), "y": 0.5, "t": i * 0.06} for i in range(3)]
    bad = [{"x": 0.5 + (81 / W if i == 1 else 0), "y": 0.5, "t": i * 0.06} for i in range(3)]
    assert len(fixations_idt(ok, W, H)) == 1
    assert fixations_idt(bad, W, H) == []


def test_idt_splits_on_gap_and_extends_while_stable():
    pts = run(0, 6, 0.05) + run(1.0, 6, 0.05)
    f = fixations_idt(pts, W, H)
    assert [round(x["start"], 2) for x in f] == [0.0, 1.0] and all(x["d"] == 250.0 for x in f)


def test_idt_uses_dimensions_of_layout_active_at_each_point():
    words = [{"i": 0, "text": "a", "x": 0.1, "y": 0.4, "w": 0.2, "h": 0.2, "line": 0}]
    # jitter 0,05 lebar: 40 px pada 800 px (lolos), 100 px pada 2000 px (ditolak)
    pts = run(0, 25, 0.05, jitter=0.05)
    narrow = gaze_metrics(pts, 1.25, CAL_OK, [{"t": 0, "width": 800, "height": 400, "words": words}])
    wide = gaze_metrics(pts, 1.25, CAL_OK, [{"t": 0, "width": 800, "height": 400, "words": words},
                                            {"t": 0.0001, "width": 2000, "height": 400, "words": words}])
    assert narrow["fixations"] == 1 and wide["fixations"] == 0


# ---------- layout & pemetaan kata ----------

def box(i, x, line, w=0.1, h=0.1):
    return {"i": i, "text": f"w{i}", "x": x, "y": 0.1 + line * 0.3, "w": w, "h": h, "line": line}


def test_clean_layouts_drops_bad_boxes_and_sorts():
    layouts = [{"t": 5, "width": 800, "height": 400, "words": [box(0, 0.1, 0)]},
               {"t": 1, "width": 800, "height": 400, "words": [box(0, 0.1, 0), box(0, 0.3, 0), box(1, 0.3, 0, w=0), box(2, 0.5, 0, h=0)]}]
    out, dropped = clean_layouts(layouts)
    assert [l["t"] for l in out] == [1, 5] and dropped == 3 and len(out[0]["words"]) == 1


def test_layout_at_is_order_independent():
    a, b = {"t": 0, "id": "a"}, {"t": 2, "id": "b"}
    assert layout_at([b, a], 1)["id"] == "a" and layout_at([b, a], 3)["id"] == "b"


def test_assign_word_nearest_line_and_word_and_rejections():
    layout = {"words": [box(0, 0.1, 0), box(1, 0.3, 0), box(2, 0.1, 1)]}
    assert assign_word({"x": 0.35, "y": 0.15}, layout)[1]["i"] == 1
    assert assign_word({"x": 0.12, "y": 0.45}, layout)[1]["i"] == 2
    assert assign_word({"x": 0.35, "y": 0.95}, layout) == (None, None)        # terlalu jauh dari baris mana pun
    assert assign_word({"x": 0.95, "y": 0.15}, layout) == (0, None)           # baris cocok, kata terlalu jauh
    assert assign_word({"x": 0.5, "y": 0.5}, {"words": [box(0, 0.1, 0, w=0)]}) == (None, None)


# ---------- regresi & return sweep ----------

def seq(*pairs):
    return [{"word": w, "line": l} for w, l in pairs]


def test_transition_classification():
    #   maju, maju, regresi-dalam-baris, return sweep, regresi-antar-baris, lompat 2 baris (progresi)
    s = seq((0, 0), (1, 0), (2, 0), (1, 0), (3, 1), (0, 0), (5, 2))
    within, between, forward, sweeps = classify_transitions(s)
    assert (within, between, forward, sweeps) == (1, 1, 3, 1)


def test_gaze_metrics_end_to_end_reading_two_lines():
    words = [box(0, 0.05, 0), box(1, 0.4, 0), box(2, 0.05, 1), box(3, 0.4, 1)]
    layout = [{"t": 0, "width": 800, "height": 400, "words": words}]
    pts = (run(0.0, 4, 0.05, x=0.10, y=0.15) + run(0.3, 4, 0.05, x=0.45, y=0.15)   # w0 -> w1
           + run(0.6, 4, 0.05, x=0.10, y=0.15)                                        # regresi ke w0
           + run(0.9, 4, 0.05, x=0.10, y=0.45) + run(1.2, 4, 0.05, x=0.45, y=0.45)    # return sweep -> w2 -> w3
           + run(1.5, 4, 0.05, x=0.45, y=0.15))                                       # regresi antar baris -> w1
    m = gaze_metrics(pts, 2, CAL_OK, layout)
    g = m["gaze"]
    assert m["fixations"] == 6 and g["words_fixated"] == 4 and g["skipped_words_percent"] == 0.0
    assert (g["regressions_within_line"], g["regressions_between_line"], g["return_sweeps"], g["progressions"]) == (1, 1, 1, 2)
    assert g["regression_rate"] == 40.0 and m["regressions"] == 2
    assert {w["index"]: w["visits"] for w in g["words"]} == {0: 2, 1: 2, 2: 1, 3: 1} and g["revisited_words"] == 2
