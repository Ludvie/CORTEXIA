"""Uji transkripsi pada rekaman suara manusia nyata (bukan TTS). Dilewati bila model Whisper belum ada."""
import os
import sys

import pytest

os.environ.setdefault("MONGO_URL", "mongodb://127.0.0.1:27017")
os.environ.setdefault("DB_NAME", "cortexia_unit")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analytics import analyze, asr_ready, transcribe  # noqa: E402

SAMPLE = os.path.join(os.path.dirname(__file__), "fixtures", "bookbot_sample.wav")
REF = "Sepulang sekolah Fitri sangat lapar."


@pytest.mark.skipif(not asr_ready(), reason="Model Whisper belum tersedia")
def test_whisper_transcribes_real_recording():
    r = transcribe(SAMPLE)
    assert 3.5 < r["audio_duration"] < 4.0
    words = r["words"]
    assert len(words) == 5 and all(0 <= w["start"] <= w["end"] <= r["audio_duration"] + 0.1 for w in words)
    assert [w["start"] for w in words] == sorted(w["start"] for w in words)
    out = analyze(REF, r["transcript"], r["audio_duration"], [], {}, words)
    m = out["metrics"]
    assert m["wer"] == 0.0 and m["wer_source"] == "transkrip_otomatis"
    # 3,7 detik < MIN_SPEECH_S (5 detik): tidak cukup untuk dinilai, sehingga suara tidak boleh dianggap andal
    assert not m["speech_reliable"] and out["quality"] == "tidak_cukup"
    assert "terlalu pendek" in out["quality_reasons"][0]
