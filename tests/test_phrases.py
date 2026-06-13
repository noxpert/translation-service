from app.models.phrase import PhraseTranslation


def test_create_phrase_success(client):
    response = client.post("/phrases", json={
        "translations": [
            {"language_code": "hu", "text": "Jó reggelt"},
            {"language_code": "en", "text": "Good morning"},
        ],
    })
    assert response.status_code == 201
    body = response.json()
    assert body["id"] is not None
    assert len(body["translations"]) == 2


def test_create_phrase_invalid_language_returns_400(client):
    response = client.post("/phrases", json={
        "translations": [{"language_code": "xx", "text": "test"}],
    })
    assert response.status_code == 400


def test_update_phrase_notes(client):
    create = client.post("/phrases", json={
        "translations": [{"language_code": "hu", "text": "Hogy vagy?"}],
    })
    phrase_id = create.json()["id"]

    response = client.patch(f"/phrases/{phrase_id}", json={"notes": "informal greeting"})
    assert response.status_code == 200
    assert response.json()["notes"] == "informal greeting"


def test_update_phrase_replaces_translations(client):
    create = client.post("/phrases", json={
        "translations": [{"language_code": "hu", "text": "Köszönöm"}],
    })
    phrase_id = create.json()["id"]

    response = client.patch(f"/phrases/{phrase_id}", json={
        "translations": [
            {"language_code": "hu", "text": "Köszönöm"},
            {"language_code": "en", "text": "Thank you"},
        ]
    })
    assert response.status_code == 200
    assert len(response.json()["translations"]) == 2


def test_update_phrase_not_found(client):
    response = client.patch("/phrases/99999", json={"notes": "test"})
    assert response.status_code == 404


def test_delete_phrase_success(client):
    create = client.post("/phrases", json={
        "translations": [{"language_code": "hu", "text": "Viszlát"}],
    })
    phrase_id = create.json()["id"]

    response = client.delete(f"/phrases/{phrase_id}")
    assert response.status_code == 204


def test_delete_phrase_not_found(client):
    response = client.delete("/phrases/99999")
    assert response.status_code == 404


def test_delete_phrase_cascades_translations(client, db_session):
    create = client.post("/phrases", json={
        "translations": [
            {"language_code": "hu", "text": "Jó éjszakát"},
            {"language_code": "en", "text": "Good night"},
        ],
    })
    phrase_id = create.json()["id"]

    client.delete(f"/phrases/{phrase_id}")

    remaining = db_session.query(PhraseTranslation).filter(
        PhraseTranslation.phrase_id == phrase_id
    ).all()
    assert len(remaining) == 0
