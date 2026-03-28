import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

TEST_DB_PATH = Path(__file__).resolve().parents[1] / "test_farka.db"
if TEST_DB_PATH.exists():
    TEST_DB_PATH.unlink()

os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"

from fastapi.testclient import TestClient

from main import app


def test_chat_start():
    with TestClient(app) as client:
        response = client.post("/api/v1/chat/start", json={})
        assert response.status_code == 200
        payload = response.json()["data"]
        assert payload["session_id"]
        assert payload["stage"] == "initial"


def test_job_seeker_flow_and_matching():
    with TestClient(app) as client:
        session_id = client.post("/api/v1/chat/start", json={}).json()["data"]["session_id"]

        messages = [
            "I am in Qatar",
            "My name is Ram and I worked in construction",
            "I have 5 years experience",
            "I want a job",
            "formwork, concrete pouring, site supervision",
        ]

        last_response = None
        for message in messages:
            last_response = client.post("/api/v1/chat/message", json={"session_id": session_id, "content": message})
            assert last_response.status_code == 200

        data = last_response.json()["data"]
        assert data["redirect"] == "jobs"
        assert data["profile_id"]

        match_response = client.post("/api/v1/jobs/match", json={"profile_id": data["profile_id"]})
        assert match_response.status_code == 200
        assert len(match_response.json()["data"]) >= 1


def test_business_flow_and_toggle():
    with TestClient(app) as client:
        session_id = client.post("/api/v1/chat/start", json={}).json()["data"]["session_id"]

        messages = [
            "म कतारमा छु",
            "म होटलमा काम गर्थें",
            "४ वर्ष अनुभव छ",
            "म व्यवसाय सुरु गर्न चाहन्छु",
            "म पोखरामा फर्किन चाहन्छु, मसँग 5 to 20 बचत छ, म सानो रेस्टुरेन्ट खोल्न चाहन्छु",
        ]

        last_response = None
        for message in messages:
            last_response = client.post("/api/v1/chat/message", json={"session_id": session_id, "content": message})
            assert last_response.status_code == 200

        data = last_response.json()["data"]
        assert data["redirect"] == "checklist"
        assert data["profile_id"]

        checklist_response = client.post("/api/v1/business/checklist", json={"profile_id": data["profile_id"]})
        assert checklist_response.status_code == 200
        checklist = checklist_response.json()["data"]
        assert checklist["checklist_items"]

        toggle_response = client.patch(
            "/api/v1/business/checklist/item",
            json={"checklist_id": checklist["id"], "item_index": 0, "done": True},
        )
        assert toggle_response.status_code == 200
        assert toggle_response.json()["data"]["checklist_items"][0]["done"] is True
