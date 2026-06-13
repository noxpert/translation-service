import pytest


WORD_ALMA = {
    "translations": [
        {"language_code": "hu", "text": "alma"},
        {"language_code": "en", "text": "apple"},
    ],
    "part_of_speech": "noun",
}

WORD_VARAKOZAS = {
    "translations": [
        {"language_code": "hu", "text": "várakozás"},
        {"language_code": "en", "text": "waiting"},
    ],
    "part_of_speech": "noun",
}

PHRASE_JO_REGGELT = {
    "translations": [
        {"language_code": "hu", "text": "Jó reggelt kívánok"},
        {"language_code": "en", "text": "Good morning"},
    ],
}


@pytest.fixture
def seeded_client(client):
    client.post("/words", json=WORD_ALMA)
    client.post("/words", json=WORD_VARAKOZAS)
    client.post("/phrases", json=PHRASE_JO_REGGELT)
    return client


def test_search_matches_word_by_substring(seeded_client):
    response = seeded_client.post(
        "/search", json={"text": "várakoz", "source_lang": "hu", "target_lang": "en"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["words"]) == 1
    texts = [t["text"] for t in data["words"][0]["translations"]]
    assert "várakozás" in texts
    assert data["phrases"] == []


def test_search_matches_phrase_by_substring(seeded_client):
    response = seeded_client.post(
        "/search", json={"text": "reggelt", "source_lang": "hu", "target_lang": "en"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["words"] == []
    assert len(data["phrases"]) == 1
    texts = [t["text"] for t in data["phrases"][0]["translations"]]
    assert "Jó reggelt kívánok" in texts


def test_search_returns_both_words_and_phrases(client):
    # seed a word and a phrase that share the substring "al"
    client.post("/words", json={
        "translations": [
            {"language_code": "hu", "text": "alma"},
            {"language_code": "en", "text": "apple"},
        ],
        "part_of_speech": "noun",
    })
    client.post("/phrases", json={
        "translations": [
            {"language_code": "hu", "text": "találkozunk"},
            {"language_code": "en", "text": "we will meet"},
        ],
    })
    response = client.post(
        "/search", json={"text": "al", "source_lang": "hu", "target_lang": "en"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["words"]) >= 1
    assert len(data["phrases"]) >= 1


def test_search_no_match_returns_empty_lists(seeded_client):
    response = seeded_client.post(
        "/search", json={"text": "xyznotfound", "source_lang": "hu", "target_lang": "en"}
    )
    assert response.status_code == 200
    assert response.json() == {"words": [], "phrases": []}


def test_search_is_case_insensitive(seeded_client):
    response = seeded_client.post(
        "/search", json={"text": "ALMA", "source_lang": "hu", "target_lang": "en"}
    )
    assert response.status_code == 200
    assert len(response.json()["words"]) == 1


def test_search_requires_target_lang_translation(client):
    # Word saved with only a Hungarian translation — no English translation
    client.post("/words", json={
        "translations": [{"language_code": "hu", "text": "titok"}],
        "part_of_speech": "noun",
    })
    response = client.post(
        "/search", json={"text": "titok", "source_lang": "hu", "target_lang": "en"}
    )
    assert response.status_code == 200
    assert response.json()["words"] == []


def test_search_invalid_source_lang_returns_400(client):
    response = client.post(
        "/search", json={"text": "hello", "source_lang": "xx", "target_lang": "en"}
    )
    assert response.status_code == 400


def test_search_invalid_target_lang_returns_400(client):
    response = client.post(
        "/search", json={"text": "hello", "source_lang": "hu", "target_lang": "xx"}
    )
    assert response.status_code == 400


def test_search_missing_field_returns_422(client):
    response = client.post(
        "/search", json={"text": "hello", "source_lang": "hu"}
    )
    assert response.status_code == 422
