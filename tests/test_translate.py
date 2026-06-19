from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

MOCK_TRANSLATE_RESULT = {
    "source_text": "várakozás",
    "target_text": "waiting",
    "part_of_speech": "noun",
    "root_source": "várakozás",
    "root_target": "waiting",
    "synonyms": None,
    "notes": "Nominalized form of várakozni (to wait).",
}


@patch("app.services.ollama.translate", new_callable=AsyncMock)
def test_translate_valid_request(mock_translate, client):
    mock_translate.return_value = MOCK_TRANSLATE_RESULT

    response = client.post(
        "/translate",
        json={"text": "várakozás", "source_lang": "hu", "target_lang": "en"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["source_text"] == "várakozás"
    assert data["target_text"] == "waiting"
    assert data["source_lang"] == "hu"
    assert data["target_lang"] == "en"
    assert data["part_of_speech"] == "noun"
    assert data["root_source"] == "várakozás"
    assert data["root_target"] == "waiting"
    assert data["notes"] is not None


def test_translate_invalid_source_lang(client):
    response = client.post(
        "/translate",
        json={"text": "hello", "source_lang": "xx", "target_lang": "en"},
    )
    assert response.status_code == 400
    assert "source language" in response.json()["detail"].lower()


def test_translate_invalid_target_lang(client):
    response = client.post(
        "/translate",
        json={"text": "hello", "source_lang": "en", "target_lang": "xx"},
    )
    assert response.status_code == 400
    assert "target language" in response.json()["detail"].lower()


@patch("app.services.ollama.translate", new_callable=AsyncMock)
def test_translate_ollama_failure(mock_translate, client):
    mock_translate.side_effect = HTTPException(
        status_code=502, detail="Ollama service unavailable"
    )

    response = client.post(
        "/translate",
        json={"text": "hello", "source_lang": "hu", "target_lang": "en"},
    )
    assert response.status_code == 502


@patch("app.services.ollama.translate", new_callable=AsyncMock)
def test_translate_unknown_pos_normalized_to_other(mock_translate, client):
    result = MOCK_TRANSLATE_RESULT.copy()
    result["part_of_speech"] = "pronoun"
    mock_translate.return_value = result

    response = client.post(
        "/translate",
        json={"text": "ő", "source_lang": "hu", "target_lang": "en"},
    )

    assert response.status_code == 200
    assert response.json()["part_of_speech"] == "other"


@patch("app.services.ollama.translate", new_callable=AsyncMock)
def test_translate_null_pos_stays_null(mock_translate, client):
    result = MOCK_TRANSLATE_RESULT.copy()
    result["part_of_speech"] = None
    mock_translate.return_value = result

    response = client.post(
        "/translate",
        json={"text": "Jó reggelt kívánok", "source_lang": "hu", "target_lang": "en"},
    )

    assert response.status_code == 200
    assert response.json()["part_of_speech"] is None


@patch("app.services.ollama.translate", new_callable=AsyncMock)
def test_translate_missing_text_returns_422(mock_translate, client):
    response = client.post(
        "/translate",
        json={"source_lang": "hu", "target_lang": "en"},
    )
    assert response.status_code == 422


@patch("app.services.ollama.translate", new_callable=AsyncMock)
def test_translate_returns_synonyms(mock_translate, client):
    result = {**MOCK_TRANSLATE_RESULT, "synonyms": ["várakoztatás", "türelem"]}
    mock_translate.return_value = result

    response = client.post(
        "/translate",
        json={"text": "várakozás", "source_lang": "hu", "target_lang": "en"},
    )

    assert response.status_code == 200
    assert response.json()["synonyms"] == ["várakoztatás", "türelem"]


@patch("app.services.ollama.translate", new_callable=AsyncMock)
def test_translate_null_synonyms_for_phrase(mock_translate, client):
    result = {**MOCK_TRANSLATE_RESULT, "synonyms": None}
    mock_translate.return_value = result

    response = client.post(
        "/translate",
        json={"text": "Jó reggelt kívánok", "source_lang": "hu", "target_lang": "en"},
    )

    assert response.status_code == 200
    assert response.json()["synonyms"] is None
