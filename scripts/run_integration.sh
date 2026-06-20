#!/usr/bin/env bash
#
# Run the live-Ollama integration/performance suite for one or more models.
#
# Usage:
#   scripts/run_integration.sh [model ...]
#
# With no arguments the three supported models are used. Each model writes its
# own timestamped report (results_<model>_<UTC>.json/.md) into
# tests/integration/results/ so successive runs never overwrite each other.
#
# Env:
#   OLLAMA_TIMEOUT   per-call timeout in seconds (default 300)
set -uo pipefail
cd "$(dirname "$0")/.."

MODELS=("$@")
if [ ${#MODELS[@]} -eq 0 ]; then
    MODELS=(translategemma:12b translategemma:27b qwen3.6:35b-a3b)
fi

RESULTS_DIR="tests/integration/results"
mkdir -p "$RESULTS_DIR"

echo "Building image..."
docker compose build

for M in "${MODELS[@]}"; do
    echo "================ ${M} ================"
    # Don't abort the loop when a model has failing cases (pytest exits non-zero);
    # the full report is still written for every run.
    docker compose run --rm \
        -e DATABASE_URL=sqlite:// \
        -e PYTHONPATH=/app \
        -e RUN_OLLAMA_INTEGRATION=1 \
        -e OLLAMA_MODEL="$M" \
        -e OLLAMA_TIMEOUT="${OLLAMA_TIMEOUT:-300}" \
        -e INTEGRATION_RESULTS_DIR=/results \
        -v "$PWD/$RESULTS_DIR:/results" \
        translation-service \
        pytest tests/integration -v -s || true
done

echo "Reports written to $RESULTS_DIR/"
