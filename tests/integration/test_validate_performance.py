"""Live-Ollama integration & performance tests for POST /validate.

Source language is Hungarian. For each case we verify that ``is_valid`` matches
the expectation, and for misspelled inputs that the correctly-spelled text is
among the returned corrections. Every call is recorded (input, output, timings)
to the session report whether it passes or fails.
"""

import time

import pytest

from tests.integration.cases import SOURCE_LANG, VALIDATE_CASES
from tests.integration.conftest import normalize_correction

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("case", VALIDATE_CASES, ids=[c["id"] for c in VALIDATE_CASES])
def test_validate(case, warm_validate_client, recorder):
    body = {"text": case["text"], "lang": SOURCE_LANG}

    t0 = time.perf_counter()
    response = warm_validate_client.post("/validate", json=body)
    wall_ms = round((time.perf_counter() - t0) * 1000, 2)

    data = response.json() if response.status_code == 200 else {}
    corrections = data.get("corrections") or []

    checks: list[dict] = []

    ok_status = response.status_code == 200
    checks.append({
        "name": "http_200",
        "passed": ok_status,
        "detail": f"status={response.status_code}",
    })

    ok_valid = data.get("is_valid") is case["expected_valid"]
    checks.append({
        "name": "is_valid_matches",
        "passed": ok_valid,
        "detail": f"expected is_valid={case['expected_valid']}, got {data.get('is_valid')}",
    })

    # For misspelled inputs, the correct spelling must be offered as a correction.
    # correct_texts (list) is checked when present; falls back to correct_text (single string).
    ok_correction = True
    correct_text = case.get("correct_text")
    correct_texts = case.get("correct_texts")
    if correct_texts is not None:
        wanted_set = {normalize_correction(t) for t in correct_texts}
        found = [c for c in corrections if normalize_correction(c) in wanted_set]
        ok_correction = bool(found)
        checks.append({
            "name": "correct_text_in_corrections",
            "passed": ok_correction,
            "detail": (
                f"expected one of {correct_texts!r} among corrections; "
                f"got {corrections!r}"
            ),
        })
    elif correct_text is not None:
        wanted = normalize_correction(correct_text)
        found = [c for c in corrections if normalize_correction(c) == wanted]
        ok_correction = bool(found)
        checks.append({
            "name": "correct_text_in_corrections",
            "passed": ok_correction,
            "detail": (
                f"expected {correct_text!r} among corrections; "
                f"got {corrections!r}"
            ),
        })

    passed = ok_status and ok_valid and ok_correction
    recorder.add(
        endpoint="/validate",
        case_id=case["id"],
        input=case["text"],
        status_code=response.status_code,
        response=data,
        wall_ms=wall_ms,
        ollama_calls_ms=data.get("ollama_calls_ms"),
        expected={
            "is_valid": case["expected_valid"],
            "correct_text": case.get("correct_texts") or case.get("correct_text"),
        },
        checks=checks,
        passed=passed,
    )

    assert ok_status, f"/validate returned {response.status_code}: {data}"
    assert ok_valid, (
        f"is_valid mismatch for {case['text']!r}: "
        f"expected {case['expected_valid']}, got {data.get('is_valid')}"
    )
    if correct_texts is not None or correct_text is not None:
        assert ok_correction, (
            f"no expected correction found in {corrections!r}"
        )
