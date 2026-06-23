"""Fixtures for the live-Ollama integration / performance suite.

These tests hit a real Ollama instance through the FastAPI endpoints, so they are
opt-in: they only run when ``RUN_OLLAMA_INTEGRATION`` is set (and Ollama is
reachable). This keeps the default mocked unit suite — and CI — untouched.

All results (inputs, outputs, per-call Ollama timings and pass/fail checks) are
collected by the session-scoped ``recorder`` and written to
``tests/integration/results/`` on teardown, regardless of whether the assertions
passed, so a failing run still leaves a full report behind.
"""

import json
import os
import re
import statistics
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest

from app.services import ollama

OPT_IN_ENV = "RUN_OLLAMA_INTEGRATION"
# Overridable so the report can be written to a mounted volume when the suite
# runs inside the container (the source tree itself is not mounted).
RESULTS_DIR = Path(os.getenv("INTEGRATION_RESULTS_DIR", Path(__file__).parent / "results"))


def pytest_configure(config):
    # Registered here as well as in pyproject.toml because the container image
    # does not copy pyproject.toml, so the marker would otherwise be unknown.
    config.addinivalue_line(
        "markers",
        "integration: live-Ollama integration/performance tests "
        "(opt-in via RUN_OLLAMA_INTEGRATION)",
    )


def _ollama_reachable() -> bool:
    try:
        resp = httpx.get(f"{ollama.OLLAMA_BASE_URL}/api/tags", timeout=5.0)
        return resp.status_code == 200
    except httpx.HTTPError:
        return False


@pytest.fixture(scope="session", autouse=True)
def _require_ollama():
    """Skip the whole suite unless explicitly opted in and Ollama is up."""
    if not os.getenv(OPT_IN_ENV):
        pytest.skip(
            f"set {OPT_IN_ENV}=1 (and run with a live Ollama) to run integration tests",
            allow_module_level=True,
        )
    if not _ollama_reachable():
        pytest.skip(
            f"Ollama not reachable at {ollama.OLLAMA_BASE_URL}",
            allow_module_level=True,
        )


def normalize(text: str | None) -> str:
    """Lower-case, trim and collapse whitespace for tolerant text comparison."""
    if text is None:
        return ""
    return re.sub(r"\s+", " ", text).strip().casefold()


# Punctuation that models routinely add/drop at the end of a correction without
# changing its meaning (full stop, comma, ellipsis, closing quotes, etc.).
_TRAILING_PUNCT = ".,;:!?…\"'’”)]}-– \t"


def normalize_correction(text: str | None) -> str:
    """Like :func:`normalize` but also ignores trailing punctuation.

    Models frequently re-punctuate a correction (e.g. add a closing period or
    capitalize the first word) without changing the substance of the fix, so
    correction matching tolerates those trailing differences.
    """
    return normalize(text).rstrip(_TRAILING_PUNCT)


# --- Result recording --------------------------------------------------------


class Recorder:
    """Accumulates one record per endpoint call for the end-of-session report."""

    def __init__(self) -> None:
        self.records: list[dict] = []

    def add(self, **record) -> None:
        self.records.append(record)


def _ollama_total_ms(calls) -> float:
    """Sum the per-call Ollama timings, whether a list (/validate) or dict (/translate)."""
    if isinstance(calls, dict):
        return round(sum(calls.values()), 2)
    if isinstance(calls, list):
        return round(sum(calls), 2)
    return 0.0


def _render_markdown(records: list[dict]) -> str:
    lines = ["# Translation Service — Integration & Performance Results", ""]
    lines.append(f"Generated: {datetime.now(timezone.utc).isoformat()}")
    lines.append(f"Model: `{ollama.OLLAMA_MODEL}`  ·  Endpoint: `{ollama.OLLAMA_BASE_URL}`")
    lines.append("")

    for endpoint in sorted({r["endpoint"] for r in records}):
        group = [r for r in records if r["endpoint"] == endpoint]
        passed = sum(1 for r in group if r["passed"])
        lines.append(f"## `{endpoint}` — {passed}/{len(group)} passed")
        lines.append("")

        ollama_totals = [_ollama_total_ms(r["ollama_calls_ms"]) for r in group]
        walls = [r["wall_ms"] for r in group]
        if ollama_totals:
            lines.append(
                "Ollama time (ms): "
                f"min {min(ollama_totals):.0f} · "
                f"mean {statistics.mean(ollama_totals):.0f} · "
                f"max {max(ollama_totals):.0f}  |  "
                "Request wall time (ms): "
                f"min {min(walls):.0f} · "
                f"mean {statistics.mean(walls):.0f} · "
                f"max {max(walls):.0f}"
            )
            lines.append("")

        lines.append("| case | result | wall ms | ollama ms |")
        lines.append("|---|---|---|---|")
        for r in group:
            mark = "✅ pass" if r["passed"] else "❌ FAIL"
            lines.append(
                f"| {r['case_id']} | {mark} | {r['wall_ms']:.0f} | "
                f"{_ollama_total_ms(r['ollama_calls_ms']):.0f} |"
            )
        lines.append("")

        for r in group:
            lines.append(f"### `{endpoint}` — {r['case_id']}")
            lines.append("")
            lines.append(f"- **input:** `{r['input']}`")
            lines.append(f"- **status:** {r['status_code']}")
            lines.append(f"- **ollama_calls_ms:** {r['ollama_calls_ms']}")
            lines.append(f"- **wall_ms:** {r['wall_ms']:.2f}")
            lines.append(f"- **output:** `{json.dumps(r['response'], ensure_ascii=False)}`")
            lines.append("- **checks:**")
            for c in r["checks"]:
                cmark = "✅" if c["passed"] else "❌"
                lines.append(f"  - {cmark} {c['name']} — {c['detail']}")
            lines.append("")

    return "\n".join(lines)


@pytest.fixture(scope="session")
def recorder():
    rec = Recorder()
    yield rec

    if not rec.records:
        return

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe_model = re.sub(r"[^A-Za-z0-9._-]", "-", ollama.OLLAMA_MODEL)
    stem = f"results_{safe_model}_{ts}"
    json_path = RESULTS_DIR / f"{stem}.json"
    md_path = RESULTS_DIR / f"{stem}.md"

    json_path.write_text(
        json.dumps(
            {
                "generated": datetime.now(timezone.utc).isoformat(),
                "model": ollama.OLLAMA_MODEL,
                "ollama_base_url": ollama.OLLAMA_BASE_URL,
                "records": rec.records,
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    md_path.write_text(_render_markdown(rec.records))
    print(f"\nIntegration results written to:\n  {json_path}\n  {md_path}")


# --- Warm-up -----------------------------------------------------------------
#
# The first request to a model pays the load cost; we make one untimed call per
# endpoint up front so it is excluded from the measured cases.


@pytest.fixture(scope="session")
def _warmed():
    return {"validate": False, "translate": False}


@pytest.fixture
def warm_validate_client(client, _warmed):
    if not _warmed["validate"]:
        client.post("/validate", json={"text": "alma", "lang": "hu"})
        _warmed["validate"] = True
    return client


@pytest.fixture
def warm_translate_client(client, _warmed):
    if not _warmed["translate"]:
        client.post(
            "/translate",
            json={"text": "alma", "source_lang": "hu", "target_lang": "en"},
        )
        _warmed["translate"] = True
    return client
