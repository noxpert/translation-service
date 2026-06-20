"""Live-Ollama integration & performance tests for POST /translate.

Source language is Hungarian, target English. The primary verification is the
root form (``root_source``): phrases and lemmas should return a null root, while
inflected words should return the expected lemma. The translation text itself is
non-deterministic, so it is checked last and only loosely (an expected English
keyword must appear). Every call is recorded — passing or failing — to the
session report.
"""

import time

import pytest

from tests.integration.cases import SOURCE_LANG, TARGET_LANG, TRANSLATE_CASES
from tests.integration.conftest import normalize

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("case", TRANSLATE_CASES, ids=[c["id"] for c in TRANSLATE_CASES])
def test_translate(case, warm_translate_client, recorder):
    body = {
        "text": case["text"],
        "source_lang": SOURCE_LANG,
        "target_lang": TARGET_LANG,
    }

    t0 = time.perf_counter()
    response = warm_translate_client.post("/translate", json=body)
    wall_ms = round((time.perf_counter() - t0) * 1000, 2)

    data = response.json() if response.status_code == 200 else {}
    root_source = data.get("root_source")
    target_text = data.get("target_text") or ""

    checks: list[dict] = []

    ok_status = response.status_code == 200
    checks.append({
        "name": "http_200",
        "passed": ok_status,
        "detail": f"status={response.status_code}",
    })

    # Root verification (the main assertion).
    if case["expected_root"] is None:
        ok_root = root_source is None
        checks.append({
            "name": "root_is_null",
            "passed": ok_root,
            "detail": (
                f"expected null root (phrase/lemma), got {root_source!r}"
            ),
        })
    else:
        ok_root = root_source is not None and normalize(root_source) == normalize(
            case["expected_root"]
        )
        checks.append({
            "name": "root_matches",
            "passed": ok_root,
            "detail": f"expected root {case['expected_root']!r}, got {root_source!r}",
        })

    # Translation match — non-deterministic, checked last and loosely.
    hay = normalize(target_text)
    matched = [kw for kw in case["keywords"] if normalize(kw) in hay]
    ok_translation = bool(matched)
    checks.append({
        "name": "translation_keyword_present",
        "passed": ok_translation,
        "detail": (
            f"expected any of {case['keywords']} in target_text {target_text!r}; "
            f"matched {matched}"
        ),
    })

    passed = ok_status and ok_root and ok_translation
    recorder.add(
        endpoint="/translate",
        case_id=case["id"],
        input=case["text"],
        status_code=response.status_code,
        response=data,
        wall_ms=wall_ms,
        ollama_calls_ms=data.get("ollama_calls_ms"),
        expected={
            "root_source": case["expected_root"],
            "keywords": case["keywords"],
        },
        checks=checks,
        passed=passed,
    )

    assert ok_status, f"/translate returned {response.status_code}: {data}"
    # Root form first — this is the deterministic part we care about.
    assert ok_root, (
        f"root mismatch for {case['text']!r}: "
        f"expected {case['expected_root']!r}, got {root_source!r}"
    )
    # Translation match last (loose, may be brittle by nature).
    assert ok_translation, (
        f"none of {case['keywords']} found in target_text {target_text!r}"
    )
