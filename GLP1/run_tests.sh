#!/usr/bin/env bash
# Run all test suites in the repo: backend auth tests + consequence-model tests.
# Usage: ./run_tests.sh   (from the repo root, e.g. ~/Documents/GLP-1_Adherence)

set -e
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "===================================="
echo " Backend auth tests"
echo "===================================="
cd "$REPO_ROOT/Backend"
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi
pytest tests/ -v

echo ""
echo "===================================="
echo " Consequence model tests"
echo "===================================="
cd "$REPO_ROOT"
python -m pytest Model/consequence/tests/ -q

echo ""
echo "All test suites passed."