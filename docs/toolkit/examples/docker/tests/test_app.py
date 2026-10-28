from fastapi.testclient import TestClient

import app as service


def client(tmp_path, monkeypatch, greeting=None):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    if greeting:
        monkeypatch.setenv("GREETING", greeting)
    return TestClient(service.app)


def test_health(tmp_path, monkeypatch):
    assert client(tmp_path, monkeypatch).get("/health").json() == {"status": "ok"}


def test_ready_when_data_dir_writable(tmp_path, monkeypatch):
    assert client(tmp_path, monkeypatch).get("/ready").status_code == 200


def test_hello_counts_visits(tmp_path, monkeypatch):
    c = client(tmp_path, monkeypatch, greeting="Namaste")
    assert c.get("/hello/Asha").json() == {"message": "Namaste, Asha", "visits": 1}
    assert c.get("/hello/Asha").json()["visits"] == 2
