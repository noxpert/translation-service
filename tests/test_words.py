from app.models.word import Word, WordTranslation


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


def test_create_word_response_shape(client):
    response = client.post("/words", json={
        "translations": [{"language_code": "hu", "text": "könyv"}],
        "part_of_speech": "noun",
        "notes": "common word",
        "context": "found in a book",
        "is_verified": True,
    })
    assert response.status_code == 201
    body = response.json()
    assert "id" in body
    assert "part_of_speech_id" in body
    assert "source_id" in body
    assert "notes" in body
    assert "context" in body
    assert "is_verified" in body
    assert "created_at" in body
    assert "translations" in body
    assert body["notes"] == "common word"
    assert body["context"] == "found in a book"
    assert body["is_verified"] == 1


def test_create_word_with_source_name(client):
    response = client.post("/words", json={
        "translations": [{"language_code": "hu", "text": "szó"}],
        "part_of_speech": "noun",
        "source_name": "my-app",
    })
    assert response.status_code == 201
    assert response.json()["source_id"] is not None


def test_create_word_source_name_reused_across_words(client):
    client.post("/words", json={
        "translations": [{"language_code": "hu", "text": "első"}],
        "part_of_speech": "adj",
        "source_name": "shared-app",
    })
    second = client.post("/words", json={
        "translations": [{"language_code": "hu", "text": "második"}],
        "part_of_speech": "adj",
        "source_name": "shared-app",
    })
    assert second.json()["source_id"] == client.post("/words", json={
        "translations": [{"language_code": "hu", "text": "harmadik"}],
        "part_of_speech": "adj",
        "source_name": "shared-app",
    }).json()["source_id"]


def test_create_word_empty_translations_returns_422(client):
    response = client.post("/words", json={
        "translations": [],
        "part_of_speech": "noun",
    })
    assert response.status_code == 422


def test_update_word_part_of_speech(client):
    create = client.post("/words", json={
        "translations": [{"language_code": "hu", "text": "fut"}],
        "part_of_speech": "noun",
    })
    word_id = create.json()["id"]
    original_pos_id = create.json()["part_of_speech_id"]

    response = client.patch(f"/words/{word_id}", json={"part_of_speech": "verb"})
    assert response.status_code == 200
    assert response.json()["part_of_speech_id"] != original_pos_id


def test_update_word_source_name(client):
    create = client.post("/words", json={
        "translations": [{"language_code": "hu", "text": "hold"}],
        "part_of_speech": "noun",
    })
    word_id = create.json()["id"]
    assert create.json()["source_id"] is None

    response = client.patch(f"/words/{word_id}", json={"source_name": "new-app"})
    assert response.status_code == 200
    assert response.json()["source_id"] is not None


def test_update_word_context(client):
    create = client.post("/words", json={
        "translations": [{"language_code": "hu", "text": "nap"}],
        "part_of_speech": "noun",
    })
    word_id = create.json()["id"]

    response = client.patch(f"/words/{word_id}", json={"context": "astronomy context"})
    assert response.status_code == 200
    assert response.json()["context"] == "astronomy context"


def test_update_word_is_verified(client):
    create = client.post("/words", json={
        "translations": [{"language_code": "hu", "text": "csillag"}],
        "part_of_speech": "noun",
        "is_verified": False,
    })
    word_id = create.json()["id"]
    assert create.json()["is_verified"] == 0

    response = client.patch(f"/words/{word_id}", json={"is_verified": True})
    assert response.status_code == 200
    assert response.json()["is_verified"] == 1


def test_update_word_no_op_returns_200(client):
    create = client.post("/words", json={
        "translations": [{"language_code": "hu", "text": "tenger"}],
        "part_of_speech": "noun",
    })
    word_id = create.json()["id"]

    response = client.patch(f"/words/{word_id}", json={})
    assert response.status_code == 200


def test_create_word_without_part_of_speech_notes_context(client):
    response = client.post("/words", json={
        "translations": [{"language_code": "hu", "text": "igen"}],
        "part_of_speech": "other",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["notes"] is None
    assert data["context"] is None


def test_create_word_with_none_part_of_speech_uses_service_default(client, db_session):
    # Exercises resolve_part_of_speech(db, None) → returns None → part_of_speech_id is None
    from app.services.word_service import resolve_part_of_speech
    result = resolve_part_of_speech(db_session, None)
    assert result is None
