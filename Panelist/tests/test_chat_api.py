from __future__ import annotations


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["panelist_id"] == "fake-panelist"
    assert body["provider"] == "fake"


def test_current_model(client):
    response = client.get("/v1/models/current")
    assert response.status_code == 200
    body = response.json()
    assert body["model"] == "fake-1"
    assert body["panelist_type"] == "fake"


def test_chat_non_streaming(client):
    response = client.post(
        "/v1/chat",
        json={
            "conversation_id": "conv-api",
            "user_id": "user-api",
            "message": "hello api",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert "echo: hello api" in body["content"]
    assert body["provider"] == "fake"


def test_conversation_lifecycle(client):
    # Create
    created = client.post(
        "/v1/conversations",
        json={"conversation_id": "conv-life", "user_id": "user-1", "title": "T"},
    )
    assert created.status_code == 201
    assert created.json()["conversation_id"] == "conv-life"

    # Chat into it
    client.post(
        "/v1/chat",
        json={
            "conversation_id": "conv-life",
            "user_id": "user-1",
            "message": "remember this",
        },
    )

    # Messages reflect the exchange
    messages = client.get("/v1/conversations/conv-life/messages")
    assert messages.status_code == 200
    roles = [m["role"] for m in messages.json()["messages"]]
    assert roles == ["user", "assistant"]

    # Listed
    listing = client.get("/v1/conversations")
    ids = [c["conversation_id"] for c in listing.json()["conversations"]]
    assert "conv-life" in ids

    # Deleted
    deleted = client.delete("/v1/conversations/conv-life")
    assert deleted.status_code == 204

    # Gone
    missing = client.get("/v1/conversations/conv-life")
    assert missing.status_code == 404


def test_get_missing_conversation_returns_404(client):
    response = client.get("/v1/conversations/does-not-exist")
    assert response.status_code == 404
