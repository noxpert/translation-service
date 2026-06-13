from app.models.word import WordTranslation


def test_create_word_success(client):
    response = client.post("/words", json={
        "translations": [
            {"language_code": "hu", "text": "kutya"},
            {"language_code": "en", "text": "dog"},
        ],
        "part_of_speech": "noun",
    })
    assert response.status_code == 201
    body = response.json()
    assert body["id"] is not None
    assert len(body["translations"]) == 2


def test_create_word_unknown_pos_falls_back_to_other(client, db_session):
    response = client.post("/words", json={
        "translations": [{"language_code": "hu", "text": "valami"}],
        "part_of_speech": "pronoun",
    })
    assert response.status_code == 201
    word_id = response.json()["id"]
    from app.models.word import Word
    from app.models.part_of_speech import PartOfSpeech
    word = db_session.query(Word).filter(Word.id == word_id).first()
    pos = db_session.query(PartOfSpeech).filter(PartOfSpeech.id == word.part_of_speech_id).first()
    assert pos.code == "other"


def test_create_word_invalid_language_returns_400(client):
    response = client.post("/words", json={
        "translations": [{"language_code": "xx", "text": "test"}],
        "part_of_speech": "noun",
    })
    assert response.status_code == 400


def test_update_word_notes(client):
    create = client.post("/words", json={
        "translations": [{"language_code": "hu", "text": "ház"}],
        "part_of_speech": "noun",
    })
    word_id = create.json()["id"]

    response = client.patch(f"/words/{word_id}", json={"notes": "means house"})
    assert response.status_code == 200
    assert response.json()["notes"] == "means house"


def test_update_word_replaces_translations(client):
    create = client.post("/words", json={
        "translations": [{"language_code": "hu", "text": "alma"}],
        "part_of_speech": "noun",
    })
    word_id = create.json()["id"]

    response = client.patch(f"/words/{word_id}", json={
        "translations": [
            {"language_code": "hu", "text": "alma"},
            {"language_code": "en", "text": "apple"},
        ]
    })
    assert response.status_code == 200
    assert len(response.json()["translations"]) == 2


def test_update_word_not_found(client):
    response = client.patch("/words/99999", json={"notes": "test"})
    assert response.status_code == 404


def test_delete_word_success(client):
    create = client.post("/words", json={
        "translations": [{"language_code": "hu", "text": "fa"}],
        "part_of_speech": "noun",
    })
    word_id = create.json()["id"]

    response = client.delete(f"/words/{word_id}")
    assert response.status_code == 204


def test_delete_word_not_found(client):
    response = client.delete("/words/99999")
    assert response.status_code == 404


def test_delete_word_cascades_translations(client, db_session):
    create = client.post("/words", json={
        "translations": [
            {"language_code": "hu", "text": "víz"},
            {"language_code": "en", "text": "water"},
        ],
        "part_of_speech": "noun",
    })
    word_id = create.json()["id"]

    client.delete(f"/words/{word_id}")

    remaining = db_session.query(WordTranslation).filter(
        WordTranslation.word_id == word_id
    ).all()
    assert len(remaining) == 0
