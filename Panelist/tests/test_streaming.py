from __future__ import annotations


def _collect_sse(client, path: str) -> str:
    response = client.post(
        path,
        json={
            "conversation_id": "conv-stream",
            "user_id": "user-1",
            "message": "stream please",
            "stream": True,
        },
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    return response.text


def test_chat_stream_via_flag(client):
    body = _collect_sse(client, "/v1/chat")
    assert "event: message_start" in body
    assert "event: message_delta" in body
    assert "event: message_completed" in body


def test_chat_stream_via_dedicated_route(client):
    body = _collect_sse(client, "/v1/chat/stream")
    assert "event: message_start" in body
    assert "event: message_completed" in body


def test_chat_stream_accept_header(client):
    response = client.post(
        "/v1/chat",
        headers={"Accept": "text/event-stream"},
        json={
            "conversation_id": "conv-accept",
            "user_id": "user-1",
            "message": "via header",
        },
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: message_completed" in response.text
