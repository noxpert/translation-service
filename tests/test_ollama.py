import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.services.ollama import translate

VALID_RESULT = {
    "source_text": "alma",
    "target_text": "apple",
    "part_of_speech": "noun",
    "root_source": "alma",
    "root_target": "apple",
    "notes": None,
}


def _make_mock_client(response_payload: dict) -> tuple:
    """Return (mock_cls patcher target, mock_response) for httpx.AsyncClient."""
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = response_payload

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response

    mock_cls = MagicMock()
    mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
    mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

    return mock_cls, mock_response, mock_client


@pytest.mark.asyncio
async def test_translate_returns_parsed_result():
    mock_cls, _, _ = _make_mock_client({"response": json.dumps(VALID_RESULT)})
    with patch("app.services.ollama.httpx.AsyncClient", mock_cls):
        result = await translate("alma", "Hungarian", "English")
    assert result["source_text"] == "alma"
    assert result["target_text"] == "apple"
    assert result["part_of_speech"] == "noun"


@pytest.mark.asyncio
async def test_translate_strips_json_code_fence():
    fenced = f"```json\n{json.dumps(VALID_RESULT)}\n```"
    mock_cls, _, _ = _make_mock_client({"response": fenced})
    with patch("app.services.ollama.httpx.AsyncClient", mock_cls):
        result = await translate("alma", "Hungarian", "English")
    assert result["target_text"] == "apple"


@pytest.mark.asyncio
async def test_translate_strips_plain_code_fence():
    fenced = f"```\n{json.dumps(VALID_RESULT)}\n```"
    mock_cls, _, _ = _make_mock_client({"response": fenced})
    with patch("app.services.ollama.httpx.AsyncClient", mock_cls):
        result = await translate("alma", "Hungarian", "English")
    assert result["target_text"] == "apple"


@pytest.mark.asyncio
async def test_translate_connect_error_raises_502():
    import httpx

    mock_client = AsyncMock()
    mock_client.post.side_effect = httpx.ConnectError("Connection refused")

    mock_cls = MagicMock()
    mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
    mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

    with patch("app.services.ollama.httpx.AsyncClient", mock_cls):
        with pytest.raises(HTTPException) as exc_info:
            await translate("alma", "Hungarian", "English")
    assert exc_info.value.status_code == 502


@pytest.mark.asyncio
async def test_translate_http_error_raises_502():
    import httpx

    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "500", request=MagicMock(), response=MagicMock()
    )

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response

    mock_cls = MagicMock()
    mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
    mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

    with patch("app.services.ollama.httpx.AsyncClient", mock_cls):
        with pytest.raises(HTTPException) as exc_info:
            await translate("alma", "Hungarian", "English")
    assert exc_info.value.status_code == 502


@pytest.mark.asyncio
async def test_translate_invalid_json_raises_502():
    mock_cls, _, _ = _make_mock_client({"response": "not valid json {"})
    with patch("app.services.ollama.httpx.AsyncClient", mock_cls):
        with pytest.raises(HTTPException) as exc_info:
            await translate("alma", "Hungarian", "English")
    assert exc_info.value.status_code == 502


@pytest.mark.asyncio
async def test_translate_missing_response_key_raises_502():
    mock_cls, _, _ = _make_mock_client({"unexpected_key": "value"})
    with patch("app.services.ollama.httpx.AsyncClient", mock_cls):
        with pytest.raises(HTTPException) as exc_info:
            await translate("alma", "Hungarian", "English")
    assert exc_info.value.status_code == 502


@pytest.mark.asyncio
async def test_translate_sends_correct_payload():
    mock_cls, _, mock_client = _make_mock_client({"response": json.dumps(VALID_RESULT)})
    with patch("app.services.ollama.httpx.AsyncClient", mock_cls):
        await translate("alma", "Hungarian", "English")

    call_kwargs = mock_client.post.call_args
    payload = call_kwargs.kwargs["json"] if call_kwargs.kwargs else call_kwargs[1]["json"]
    assert payload["stream"] is False
    assert "alma" in payload["prompt"]
    assert "Hungarian" in payload["prompt"]
    assert "English" in payload["prompt"]
