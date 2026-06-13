def test_get_languages_returns_200(client):
    response = client.get("/languages")
    assert response.status_code == 200


def test_get_languages_returns_seeded_data(client):
    response = client.get("/languages")
    data = response.json()
    codes = [lang["code"] for lang in data]
    assert "en" in codes
    assert "hu" in codes


def test_get_languages_has_expected_fields(client):
    response = client.get("/languages")
    data = response.json()
    for lang in data:
        assert "id" in lang
        assert "code" in lang
        assert "name" in lang
        assert "created_at" in lang


def test_get_parts_of_speech_returns_200(client):
    response = client.get("/parts-of-speech")
    assert response.status_code == 200


def test_get_parts_of_speech_returns_seeded_data(client):
    response = client.get("/parts-of-speech")
    data = response.json()
    codes = [pos["code"] for pos in data]
    assert "noun" in codes
    assert "verb" in codes
    assert "adj" in codes
    assert "adv" in codes
    assert "other" in codes


def test_get_parts_of_speech_has_expected_fields(client):
    response = client.get("/parts-of-speech")
    data = response.json()
    for pos in data:
        assert "id" in pos
        assert "code" in pos
        assert "label" in pos
        assert "created_at" in pos
