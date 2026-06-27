import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.services.ollama import get_synonyms, translate, validate

VALID_RESULT = {
    "source_text": "alma",
    "target_text": "apple",
    "part_of_speech": "noun",
    "root_source": "alma",
    "root_target": "apple",
    "notes": None,
}

VALID_SYNONYMS_RESULT = {"synonyms": ["körte", "szilva"]}


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
        result, timings = await translate("alma", "Hungarian", "English")
    assert result["source_text"] == "alma"
    assert result["target_text"] == "apple"
    assert result["part_of_speech"] == "noun"
    assert len(timings) == 1
    assert timings[0] >= 0


@pytest.mark.asyncio
async def test_translate_strips_json_code_fence():
    fenced = f"```json\n{json.dumps(VALID_RESULT)}\n```"
    mock_cls, _, _ = _make_mock_client({"response": fenced})
    with patch("app.services.ollama.httpx.AsyncClient", mock_cls):
        result, _ = await translate("alma", "Hungarian", "English")
    assert result["target_text"] == "apple"


@pytest.mark.asyncio
async def test_translate_strips_plain_code_fence():
    fenced = f"```\n{json.dumps(VALID_RESULT)}\n```"
    mock_cls, _, _ = _make_mock_client({"response": fenced})
    with patch("app.services.ollama.httpx.AsyncClient", mock_cls):
        result, _ = await translate("alma", "Hungarian", "English")
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


@pytest.mark.asyncio
async def test_translate_handles_null_root_without_error():
    result_with_null_root = {**VALID_RESULT, "root_source": None, "root_target": None}
    mock_cls, _, _ = _make_mock_client({"response": json.dumps(result_with_null_root)})
    with patch("app.services.ollama.httpx.AsyncClient", mock_cls):
        result, _ = await translate("alma", "Hungarian", "English")
    assert result["root_source"] is None


@pytest.mark.asyncio
async def test_translate_nulls_root_when_equal_to_input():
    result_with_same_root = {**VALID_RESULT, "root_source": "alma", "root_target": "apple"}
    mock_cls, _, _ = _make_mock_client({"response": json.dumps(result_with_same_root)})
    with patch("app.services.ollama.httpx.AsyncClient", mock_cls):
        result, _ = await translate("alma", "Hungarian", "English")
    assert result["root_source"] is None
    assert result["root_target"] is None


@pytest.mark.asyncio
async def test_translate_nulls_root_case_insensitive():
    result_with_same_root = {**VALID_RESULT, "root_source": "Alma", "root_target": "apple"}
    mock_cls, _, _ = _make_mock_client({"response": json.dumps(result_with_same_root)})
    with patch("app.services.ollama.httpx.AsyncClient", mock_cls):
        result, _ = await translate("alma", "Hungarian", "English")
    assert result["root_source"] is None


@pytest.mark.asyncio
async def test_translate_keeps_root_when_different_from_input():
    result_with_root = {**VALID_RESULT, "root_source": "almafa", "root_target": "apple tree"}
    mock_cls, _, _ = _make_mock_client({"response": json.dumps(result_with_root)})
    with patch("app.services.ollama.httpx.AsyncClient", mock_cls):
        result, _ = await translate("alma", "Hungarian", "English")
    assert result["root_source"] == "almafa"


@pytest.mark.asyncio
async def test_get_synonyms_returns_parsed_list():
    mock_cls, _, _ = _make_mock_client({"response": json.dumps(VALID_SYNONYMS_RESULT)})
    with patch("app.services.ollama.httpx.AsyncClient", mock_cls):
        synonyms, timings = await get_synonyms("alma", "apple", "noun", "Hungarian", "English")
    assert synonyms == ["körte", "szilva"]
    assert len(timings) == 1
    assert timings[0] >= 0


@pytest.mark.asyncio
async def test_get_synonyms_returns_none_when_null():
    mock_cls, _, _ = _make_mock_client({"response": json.dumps({"synonyms": None})})
    with patch("app.services.ollama.httpx.AsyncClient", mock_cls):
        synonyms, _ = await get_synonyms("alma", "apple", "noun", "Hungarian", "English")
    assert synonyms is None


@pytest.mark.asyncio
async def test_get_synonyms_filters_null_entries():
    mock_cls, _, _ = _make_mock_client(
        {"response": json.dumps({"synonyms": [None, "körte", None]})}
    )
    with patch("app.services.ollama.httpx.AsyncClient", mock_cls):
        synonyms, _ = await get_synonyms("alma", "apple", "noun", "Hungarian", "English")
    assert synonyms == ["körte"]


@pytest.mark.asyncio
async def test_get_synonyms_collapses_all_null_to_none():
    mock_cls, _, _ = _make_mock_client({"response": json.dumps({"synonyms": [None, None]})})
    with patch("app.services.ollama.httpx.AsyncClient", mock_cls):
        synonyms, _ = await get_synonyms("alma", "apple", "noun", "Hungarian", "English")
    assert synonyms is None


@pytest.mark.asyncio
async def test_get_synonyms_sends_source_target_and_pos_in_prompt():
    mock_cls, _, mock_client = _make_mock_client(
        {"response": json.dumps(VALID_SYNONYMS_RESULT)}
    )
    with patch("app.services.ollama.httpx.AsyncClient", mock_cls):
        await get_synonyms("alma", "apple", "noun", "Hungarian", "English")
    call_kwargs = mock_client.post.call_args
    payload = call_kwargs.kwargs["json"] if call_kwargs.kwargs else call_kwargs[1]["json"]
    assert "alma" in payload["prompt"]
    assert "apple" in payload["prompt"]
    assert "noun" in payload["prompt"]
    assert payload["stream"] is False


@pytest.mark.asyncio
async def test_get_synonyms_invalid_json_raises_502():
    mock_cls, _, _ = _make_mock_client({"response": "not valid json {"})
    with patch("app.services.ollama.httpx.AsyncClient", mock_cls):
        with pytest.raises(HTTPException) as exc_info:
            await get_synonyms("alma", "apple", "noun", "Hungarian", "English")
    assert exc_info.value.status_code == 502


# --- validate() tests ---

VALID_VALIDATE_RESULT = {"is_valid": True, "corrections": None}
INVALID_VALIDATE_RESULT = {"is_valid": False, "corrections": ["alma", "almák"]}


@pytest.mark.asyncio
async def test_validate_returns_valid_result():
    mock_cls, _, _ = _make_mock_client({"response": json.dumps(VALID_VALIDATE_RESULT)})
    with patch("app.services.ollama.httpx.AsyncClient", mock_cls):
        result, timings = await validate("alma", "Hungarian")
    assert result["is_valid"] is True
    assert result["corrections"] is None
    assert len(timings) == 1
    assert timings[0] >= 0


@pytest.mark.asyncio
async def test_validate_returns_corrections_when_invalid():
    mock_cls, _, _ = _make_mock_client({"response": json.dumps(INVALID_VALIDATE_RESULT)})
    with patch("app.services.ollama.httpx.AsyncClient", mock_cls):
        result, _ = await validate("alme", "Hungarian")
    assert result["is_valid"] is False
    assert result["corrections"] == ["alma", "almák"]


@pytest.mark.asyncio
async def test_validate_filters_null_entries_from_corrections():
    raw = {"is_valid": False, "corrections": [None, "alma", None]}
    mock_cls, _, _ = _make_mock_client({"response": json.dumps(raw)})
    with patch("app.services.ollama.httpx.AsyncClient", mock_cls):
        result, _ = await validate("alme", "Hungarian")
    assert result["corrections"] == ["alma"]


@pytest.mark.asyncio
async def test_validate_collapses_all_null_corrections_to_none():
    raw = {"is_valid": False, "corrections": [None, None]}
    mock_cls, _, _ = _make_mock_client({"response": json.dumps(raw)})
    with patch("app.services.ollama.httpx.AsyncClient", mock_cls):
        result, _ = await validate("alme", "Hungarian")
    assert result["corrections"] is None


@pytest.mark.asyncio
async def test_validate_sends_text_and_lang_in_prompt():
    mock_cls, _, mock_client = _make_mock_client({"response": json.dumps(VALID_VALIDATE_RESULT)})
    with patch("app.services.ollama.httpx.AsyncClient", mock_cls):
        await validate("alma", "Hungarian")
    call_kwargs = mock_client.post.call_args
    payload = call_kwargs.kwargs["json"] if call_kwargs.kwargs else call_kwargs[1]["json"]
    assert "alma" in payload["prompt"]
    assert "Hungarian" in payload["prompt"]
    assert payload["stream"] is False


@pytest.mark.asyncio
async def test_validate_degenerate_correction_flips_to_valid():
    """Model returns is_valid=false with corrections identical to input -> reconcile to valid."""
    raw = {"is_valid": False, "corrections": ["alma"]}
    mock_cls, _, _ = _make_mock_client({"response": json.dumps(raw)})
    with patch("app.services.ollama.httpx.AsyncClient", mock_cls):
        result, _ = await validate("alma", "Hungarian")
    assert result["is_valid"] is True
    assert result["corrections"] is None


@pytest.mark.asyncio
async def test_validate_degenerate_correction_case_insensitive():
    """Degenerate-correction guard uses casefold comparison."""
    raw = {"is_valid": False, "corrections": ["Alma"]}
    mock_cls, _, _ = _make_mock_client({"response": json.dumps(raw)})
    with patch("app.services.ollama.httpx.AsyncClient", mock_cls):
        result, _ = await validate("alma", "Hungarian")
    assert result["is_valid"] is True
    assert result["corrections"] is None


@pytest.mark.asyncio
async def test_validate_degenerate_correction_keeps_genuinely_different_ones():
    """Only corrections equal to the input are dropped; others are kept."""
    raw = {"is_valid": False, "corrections": ["alma", "almák"]}
    mock_cls, _, _ = _make_mock_client({"response": json.dumps(raw)})
    with patch("app.services.ollama.httpx.AsyncClient", mock_cls):
        result, _ = await validate("alma", "Hungarian")
    # "almák" is different from "alma", so the result stays invalid
    assert result["is_valid"] is False
    assert result["corrections"] == ["almák"]
