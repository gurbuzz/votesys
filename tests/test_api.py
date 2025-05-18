# votesys/tests/test_api.py

import os
import shutil
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.xml_utils import DATA_DIR

client = TestClient(app)

@pytest.fixture(autouse=True)
def clear_data_dir():
    # Her testten önce data klasörünü temizle
    if os.path.exists(DATA_DIR):
        shutil.rmtree(DATA_DIR)
    os.makedirs(DATA_DIR)
    yield
    # (opsiyonel) Sonra tekrar temizle:
    shutil.rmtree(DATA_DIR)

def test_get_empty_polls():
    res = client.get("/api/polls")
    assert res.status_code == 200
    assert res.json() == []

def test_create_and_get_poll():
    payload = {
        "id": 1,
        "question": "Test sorusu?",
        "options": [
            {"id": 1, "text": "A şıkkı", "votes": 0},
            {"id": 2, "text": "B şıkkı", "votes": 0}
        ]
    }
    # Oluştur
    res = client.post("/api/polls", json=payload)
    assert res.status_code == 201
    assert res.json() == payload

    # Get
    res2 = client.get("/api/polls/1")
    assert res2.status_code == 200
    assert res2.json() == payload

def test_vote_increments():
    # Öncelikle anket yarat
    client.post("/api/polls", json={
        "id": 5,
        "question": "Oy testi?",
        "options": [
            {"id": 10, "text": "X", "votes": 0},
            {"id": 20, "text": "Y", "votes": 0}
        ]
    })

    # Oy ver
    res = client.post("/api/polls/5/vote", json={"option_id": 10})
    assert res.status_code == 200
    data = res.json()
    # 10 id’li seçeneğin oyu 1 artmış olmalı
    opt = next(o for o in data["options"] if o["id"] == 10)
    assert opt["votes"] == 1

def test_vote_on_nonexistent_poll():
    res = client.post("/api/polls/999/vote", json={"option_id": 1})
    assert res.status_code == 404

def test_invalid_option_vote():
    # Anket oluştur
    client.post("/api/polls", json={
        "id": 2,
        "question": "Hatalı oy?",
        "options": [{"id": 1, "text": "Evet", "votes": 0}]
    })
    # Geçersiz option_id
    res = client.post("/api/polls/2/vote", json={"option_id": 999})
    assert res.status_code == 400
