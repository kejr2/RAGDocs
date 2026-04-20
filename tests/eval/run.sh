#!/usr/bin/env bash
# Run the RAGDocs eval harness against http://localhost:8000
# Usage: bash tests/eval/run.sh
set -euo pipefail
cd "$(dirname "$0")/../.."
pytest tests/eval/test_eval_battery.py -v --tb=short "$@"
