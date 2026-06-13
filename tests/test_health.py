def test_health_check_returns_200(client):
    response = client.get("/")
    assert response.status_code == 200


def test_health_check_response_shape(client):
    response = client.get("/")
    body = response.json()
    assert "status" in body
    assert body["status"] == "ok"
