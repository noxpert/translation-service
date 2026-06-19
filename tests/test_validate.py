from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

MOCK_VALID_RESULT = ({"is_valid": True, "corrections": None}, [456.78])
MOCK_INVALID_RESULT = (
    {"is_valid": False, "corrections": ["sietni", "sietek"]},
    [456.78],
)


@patch("app.services.ollama.validate", new_callable=AsyncMock)
def test_validate_valid_text(mock_validate, client):
    mock_validate.return_value = MOCK_VALID_RESULT

    response = client.post("/validate", json={"text": "sietni", "lang": "hu"})

    assert response.status_code == 200
    data = response.json()
    assert data["is_valid"] is True
    assert data["text"] == "sietni"
    assert data["corrections"] is None
    assert data["ollama_calls_ms"] == [456.78]


@patch("app.services.ollama.validate", new_callable=AsyncMock)
def test_validate_invalid_text_returns_corrections(mock_validate, client):
    mock_validate.return_value = MOCK_INVALID_RESULT

    response = client.post("/validate", json={"text": "siett", "lang": "hu"})

    assert response.status_code == 200
    data = response.json()
    assert data["is_valid"] is False
    assert data["text"] == "siett"
    assert data["corrections"] == ["sietni", "sietek"]
    assert data["ollama_calls_ms"] == [456.78]


def test_validate_unknown_lang_returns_400(client):
    response = client.post("/validate", json={"text": "hello", "lang": "xx"})
    assert response.status_code == 400
    assert "unknown language" in response.json()["detail"].lower()


def test_validate_missing_text_returns_422(client):
    response = client.post("/validate", json={"lang": "hu"})
    assert response.status_code == 422


def test_validate_missing_lang_returns_422(client):
    response = client.post("/validate", json={"text": "hello"})
    assert response.status_code == 422


@patch("app.services.ollama.validate", new_callable=AsyncMock)
def test_validate_ollama_failure(mock_validate, client):
    mock_validate.side_effect = HTTPException(
        status_code=502, detail="Ollama service unavailable"
    )

    response = client.post("/validate", json={"text": "hello", "lang": "en"})
    assert response.status_code == 502


@patch("app.services.ollama.validate", new_callable=AsyncMock)
def test_validate_echoes_original_text(mock_validate, client):
    mock_validate.return_value = MOCK_INVALID_RESULT

    response = client.post("/validate", json={"text": "siett", "lang": "hu"})

    assert response.json()["text"] == "siett"
