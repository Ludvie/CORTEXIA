"""Prioritas 5 — uji integrasi terhadap server lokal: idempotensi, data tatapan kotor, kontrak API, dashboard.

Jalankan: REACT_APP_BACKEND_URL=http://127.0.0.1:8001 pytest tests/test_hardening_integration.py -n 0
"""
import json
import os
import uuid

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def client():
    if not BASE_URL:
        pytest.skip("REACT_APP_BACKEND_URL not set")
    s = requests.Session()
    email = f"hard.teacher.{uuid.uuid4().hex[:10]}@example.com"
    r = s.post(f"{API}/auth/register", json={"name": "Hard Teacher", "email": email, "password": "HardPass123!", "role": "teacher"}, timeout=30)
    assert r.status_code == 200, r.text
    s.headers["Authorization"] = "Bearer " + r.json()["token"]
    return s


@pytest.fixture(scope="module")
def entities(client):
    student = client.post(f"{API}/students", json={"alias": "Hard Pembaca", "grade": 2}, timeout=30).json()
    text = client.get(f"{API}/texts", timeout=30).json()[0]
    yield student, text
    client.delete(f"{API}/students/{student['id']}", timeout=30)


def post(client, payload):
    return client.post(f"{API}/sessions", data={"payload": json.dumps(payload)}, timeout=120)


def base_payload(student, text, **extra):
    return {"student_id": student["id"], "text_id": text["id"], "consent": True, "mode": "gaze", "duration": 4,
            "gaze_points": [], "layouts": [], "calibration": {"median_error": 0.08, "validation_samples": 40, "passed": True}, **extra}


def test_retry_with_same_request_id_returns_same_session(client, entities):
    student, text = entities
    key = uuid.uuid4().hex
    a = post(client, base_payload(student, text, client_request_id=key))
    b = post(client, base_payload(student, text, client_request_id=key))
    assert a.status_code == 200 and b.status_code == 200
    assert a.json()["id"] == b.json()["id"]
    rows = [s for s in client.get(f"{API}/sessions", timeout=30).json() if s.get("client_request_id") == key]
    assert len(rows) == 1


def test_without_request_id_behaviour_unchanged(client, entities):
    student, text = entities
    a = post(client, base_payload(student, text))
    b = post(client, base_payload(student, text))
    assert a.json()["id"] != b.json()["id"]


def test_invalid_request_id_rejected(client, entities):
    student, text = entities
    assert post(client, base_payload(student, text, client_request_id="bad id!")).status_code == 422


def test_dirty_gaze_is_cleaned_and_reported(client, entities):
    student, text = entities
    pts = [{"x": 0.5, "y": 0.5, "t": round(i * 0.1, 3)} for i in range(40)]
    pts += [dict(p) for p in pts[:10]]                                   # duplikat
    pts += [{"x": 0.5, "y": 0.5, "t": 30 + i} for i in range(5)]         # setelah durasi sesi
    r = post(client, base_payload(student, text, gaze_points=pts))
    assert r.status_code == 200, r.text
    m = r.json()["metrics"]
    s = m["gaze_sampling"]
    assert s["received"] == 55 and s["valid"] == 40 and s["duplicates"] == 10 and s["out_of_range"] == 5
    assert m["gaze_samples"] == 40


def test_uncalibrated_flag_blocks_gaze_usable(client, entities):
    student, text = entities
    pts = [{"x": 0.5, "y": 0.5, "t": round(i * 0.1, 3)} for i in range(40)]
    cal = {"median_error": 0.08, "validation_samples": 40, "passed": False}
    m = post(client, base_payload(student, text, gaze_points=pts, calibration=cal)).json()["metrics"]
    assert m["calibration_valid"] is False and m["gaze_usable"] is False


def test_session_contract_and_dashboard_fields(client, entities):
    student, text = entities
    doc = post(client, base_payload(student, text)).json()
    for key in ["id", "metrics", "profile", "profile_reason", "quality", "quality_reasons", "recommendations", "limitations",
                "analysis_warnings", "transcript", "reviews"]:
        assert key in doc, key
    d = client.get(f"{API}/dashboard", timeout=30).json()
    for key in ["students", "session_count", "average_accuracy", "reading_minutes", "sessions", "accuracy_sessions", "accuracy_sessions_excluded"]:
        assert key in d, key


def test_concurrent_retries_create_one_session(client, entities):
    from concurrent.futures import ThreadPoolExecutor
    student, text = entities
    key = uuid.uuid4().hex
    payload = base_payload(student, text, client_request_id=key)
    headers = dict(client.headers)

    def send(_):
        return requests.post(f"{API}/sessions", data={"payload": json.dumps(payload)}, headers=headers, timeout=120)
    with ThreadPoolExecutor(6) as pool:
        results = list(pool.map(send, range(6)))
    assert all(r.status_code == 200 for r in results), [r.text for r in results if r.status_code != 200]
    assert len({r.json()["id"] for r in results}) == 1
    rows = [s for s in client.get(f"{API}/sessions", timeout=30).json() if s.get("client_request_id") == key]
    assert len(rows) == 1


def test_research_report_has_participant_level_and_reproducibility(client):
    r = client.post(f"{API}/research/train", json={"algorithm": "logistic"}, timeout=30)
    assert r.status_code in (202, 409)
    import time
    for _ in range(90):
        job = client.get(f"{API}/research", timeout=60).json()["job"]
        if job["status"] in ("complete", "failed"):
            break
        time.sleep(2)
    assert job["status"] == "complete", job
    report = client.get(f"{API}/research", timeout=60).json()["reports"][0]
    assert report["participant_level"]["participants"] == 70
    assert {"precision_macro", "recall_macro"} <= set(report)
    rep = report["reproducibility"]
    assert len(rep["dataset_sha256"]) == 64 and len(rep["model_sha256"]) == 64 and rep["environment"]["scikit_learn"]
