"""Prioritas 3 — uji unit penilaian pelafalan dengan Vosk di-mock (deterministik, tanpa model)."""
import os
import sys

import pytest

os.environ.setdefault("MONGO_URL", "mongodb://127.0.0.1:27017")
os.environ.setdefault("DB_NAME", "cortexia_unit")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pronunciation as pr  # noqa: E402

PCM = b"\x10\x00" * 16000  # 1 detik, tidak hening


def w(word, conf):
    return {"word": word, "conf": conf, "start": 0.0, "end": 0.5}


@pytest.fixture
def fake_vosk(monkeypatch):
    """Ganti decode/recognize/kosakata; `state` mengatur hasil dekode bebas dan pilihan-paksa."""
    state = {"free": [], "forced": [], "competitors": ["apek", "apes"], "pcm": PCM, "grammars": []}
    monkeypatch.setattr(pr, "decode_pcm", lambda path: state["pcm"])
    monkeypatch.setattr(pr, "_load", lambda: None)
    monkeypatch.setattr(pr, "_vocab", ["apel", "apek", "apes", "kupu", "mawar"])
    monkeypatch.setattr(pr, "competitors", lambda target, limit=12: list(state["competitors"]))

    def recognize(pcm, grammar=None):
        if grammar:
            state["grammars"].append(grammar)
            return state["forced"]
        return state["free"]
    monkeypatch.setattr(pr, "recognize", recognize)
    return state


def test_verdict_boundaries():
    assert pr.verdict_for(None) is None
    assert pr.verdict_for(85) == "tepat" and pr.verdict_for(100) == "tepat"
    assert pr.verdict_for(84.9) == "hampir" and pr.verdict_for(60) == "hampir"
    assert pr.verdict_for(59.9) == "latihan" and pr.verdict_for(0) == "latihan"


def test_conf_is_clamped_and_finite():
    assert pr._conf(1.4) == 1.0 and pr._conf(-0.2) == 0.0
    assert pr._conf(float("nan")) == 0.0 and pr._conf(None) == 0.0 and pr._conf("x") == 0.0


def test_forced_choice_target_wins(fake_vosk):
    fake_vosk["free"] = [w("apel", 0.9)]
    fake_vosk["forced"] = [w("apel", 0.8)]
    r = pr.assess("x", "Apel")
    # 0,35 x 100 (ejaan sama) + 0,65 x 80 = 87
    assert r["score"] == 87.0 and r["verdict"] == "tepat" and r["score_method"] == "kemiripan_ejaan+pilihan_paksa"
    assert r["forced_choice"]["target_won"] and fake_vosk["grammars"][0][0] == "apel"


def test_forced_choice_competitor_wins_scores_low(fake_vosk):
    fake_vosk["free"] = [w("apek", 0.9)]
    fake_vosk["forced"] = [w("apek", 0.9)]
    r = pr.assess("x", "apel")
    assert r["similarity"] == 75.0 and r["score"] == round(0.35 * 75.0, 1) and r["verdict"] == "latihan"


def test_no_competitors_skips_forced_choice(fake_vosk):
    fake_vosk["competitors"] = []
    fake_vosk["free"] = [w("apel", 0.4)]
    fake_vosk["forced"] = [w("apel", 0.99)]  # akan "menang" bila grammar hanya berisi target
    r = pr.assess("x", "apel")
    assert fake_vosk["grammars"] == [] and r["forced_choice"] is None
    assert r["forced_choice_skipped"] == "tanpa kata pesaing"
    assert r["score_method"] == "kemiripan_ejaan" and r["score"] == r["similarity"] == 100.0


def test_out_of_vocabulary_uses_similarity_only(fake_vosk):
    fake_vosk["free"] = [w("zebra", 0.9)]
    r = pr.assess("x", "zebra")
    assert not r["in_vocabulary"] and r["forced_choice"] is None and r["score_method"] == "kemiripan_ejaan"


def test_nothing_heard_gives_no_score(fake_vosk):
    fake_vosk["free"] = []
    r = pr.assess("x", "apel")
    assert r["score"] is None and r["verdict"] is None and r["similarity"] is None and r["score_method"] is None
    assert all(not s["ok"] for s in r["syllables"])


def test_empty_or_silent_audio_rejected(fake_vosk):
    for pcm in (b"", b"\x00\x00" * 16000):
        fake_vosk["pcm"] = pcm
        with pytest.raises(ValueError):
            pr.assess("x", "apel")


def test_invalid_target_rejected(fake_vosk):
    with pytest.raises(ValueError):
        pr.assess("x", "123 !!")


def test_syllables_basic_cases():
    assert pr.syllables("bunga") == ["bu", "nga"]
    assert pr.syllables("taman") == ["ta", "man"]
    assert pr.syllables("nyanyi") == ["nya", "nyi"]
    assert pr.syllables("a") == ["a"] and pr.syllables("") == []


def test_word_confidence_reports_coverage(monkeypatch):
    monkeypatch.setattr(pr, "decode_pcm", lambda path: PCM)
    # bacaan 4 kata, hanya 2 yang terdengar cocok -> rerata atas 2 kata, cakupan 50%
    monkeypatch.setattr(pr, "recognize", lambda pcm, grammar=None: [w("rani", 0.9), w("taman", 0.5)])
    r = pr.word_confidence("x", "Rani pergi ke taman")
    assert r["mean_confidence"] == 70.0 and r["words_matched"] == 2 and r["words_total"] == 4 and r["coverage_percent"] == 50.0
    assert [x["word"] for x in r["weak_words"]] == ["taman"]


def test_word_confidence_reduplicated_word_takes_min_part(monkeypatch):
    monkeypatch.setattr(pr, "decode_pcm", lambda path: PCM)
    monkeypatch.setattr(pr, "recognize", lambda pcm, grammar=None: [w("kupu", 0.9), w("kupu", 0.3)])
    r = pr.word_confidence("x", "kupu-kupu")
    assert r["words"] == [{"index": 0, "word": "kupu-kupu", "conf": 0.3}] and r["coverage_percent"] == 100.0


def test_word_confidence_empty_audio(monkeypatch):
    monkeypatch.setattr(pr, "decode_pcm", lambda path: b"")
    r = pr.word_confidence("x", "Rani pergi")
    assert r["mean_confidence"] is None and r["words_matched"] == 0 and r["coverage_percent"] == 0.0


# ---------- kemiripan fonetik ----------

def test_g2p_indonesian_rules():
    assert pr.phonemes("nyanyi") == ["ɲ", "a", "ɲ", "i"]
    assert pr.phonemes("bangun") == ["b", "a", "ŋ", "u", "n"]
    assert pr.phonemes("cinta") == ["C", "i", "n", "t", "a"]
    assert pr.phonemes("syukur") == ["ʃ", "u", "k", "u", "r"]
    assert pr.phonemes("anak")[-1] == "ʔ"  # /k/ akhir -> glotal
    assert pr.phonemes("pantai")[-1] == "A"  # diftong ai


def test_phonetic_distance_orders_by_sound_not_spelling():
    # sama-sama 1 huruf beda, tetapi p/b hanya beda bersuara sedangkan p/s beda tempat & cara
    assert pr.phonetic_distance("baku", "paku") < pr.phonetic_distance("baku", "saku")
    assert pr.phonetic_distance("lari", "lali") < pr.phonetic_distance("lari", "laki")      # r/l cair
    assert pr.phonetic_distance("akil", "aqil") == 0.0                                      # q = k
    assert pr.phonetic_distance("sapi", "sapi") == 0.0
    assert pr.phonetic_distance("ban", "bang") == pr.phonetic_distance("ban", "bam") == 0.5  # nasal


def test_competitors_ranked_phonetically(monkeypatch):
    monkeypatch.setattr(pr, "_load", lambda: None)
    monkeypatch.setattr(pr, "_vocab", ["paku", "saku", "baku", "bakul", "zebra"])
    assert pr.competitors("baku") == ["paku", "bakul", "saku"]


# ---------- rekaman suara nyata (bukan TTS) ----------

SAMPLE = os.path.join(os.path.dirname(__file__), "fixtures", "bookbot_sample.wav")


def test_real_recording_pronunciation_and_confidence():
    if not pr.vosk_ready():
        pytest.skip("Model Vosk belum tersedia")
    r = pr.word_confidence(SAMPLE, "Sepulang sekolah Fitri sangat lapar.")
    assert r["words_matched"] == 5 and r["coverage_percent"] == 100.0 and r["mean_confidence"] > 60
    good = pr.assess(SAMPLE, "sepulang sekolah fitri sangat lapar")
    bad = pr.assess(SAMPLE, "kucing makan ikan")
    assert good["verdict"] in ("tepat", "hampir") and bad["verdict"] == "latihan" and good["score"] > bad["score"]
