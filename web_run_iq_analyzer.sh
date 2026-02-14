#!/bin/bash
# Run IQ Data Web Viewer for _logs/iq_data/session_* structure
# Run from directory containing iq_web.py: ./web_run_iq_analyzer.sh
# On first run, creates venv and installs dependencies.

set -e
cd "$(dirname "$0")"
SCRIPT="iq_web.py"
VENV_DIR=".venv_iq"
PYTHON="$(pwd)/$VENV_DIR/bin/python"
PIP="$(pwd)/$VENV_DIR/bin/pip"

if [ ! -f "$SCRIPT" ]; then
    echo "✗ Not found: $SCRIPT"
    exit 1
fi

# Create venv if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment in $VENV_DIR ..."
    python3 -m venv "$VENV_DIR"
fi

# Always check that dependencies are installed (fixes broken/empty venv)
if ! "$PYTHON" -c "import pandas, numpy, plotly, dash" 2>/dev/null; then
    echo "Installing dependencies (pandas, numpy, plotly, dash) ..."
    "$PIP" install --upgrade pip -q
    "$PIP" install pandas numpy plotly dash -q
    echo "✓ Done."
fi

echo "Data dir: $(pwd)/_logs/iq_data"
echo "✓ Data path found: $(pwd)/_logs/iq_data/"
echo "============================================================"
echo "             RTL-SDR IQ Data Web Viewer"
echo "============================================================"
echo "Data path: .../_logs/iq_data/"
exec "$PYTHON" "$SCRIPT"
