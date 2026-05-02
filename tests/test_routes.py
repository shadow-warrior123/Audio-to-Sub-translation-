from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_root_redirects_to_desktop_ui():
    response = client.get("/", follow_redirects=False)

    assert response.status_code in {307, 308}
    assert response.headers["location"] == "/app/"


def test_desktop_ui_served():
    response = client.get("/app/")

    assert response.status_code == 200
    assert "Anime Subtitle Studio" in response.text


def test_health_route_reports_runtime():
    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert "translation_model" in payload
    assert "large-v3" in payload["model_options"]["whisper"]
    assert "staka/fugumt-ja-en" in payload["model_options"]["translation"]


def test_create_job_rejects_unknown_model():
    response = client.post(
        "/jobs",
        data={"whisper_model_size": "not-real", "translation_model": "Helsinki-NLP/opus-mt-ja-en"},
        files={"file": ("sample.mp4", b"not video", "video/mp4")},
    )

    assert response.status_code == 400
    assert "Unsupported Whisper model" in response.text
