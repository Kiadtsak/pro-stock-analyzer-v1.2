#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════
# Pro Stock Analyzer — Launch Script
# ═══════════════════════════════════════════════════════════════════════════
set -e

cd "$(dirname "$0")"

# Create venv if it doesn't exist
if [ ! -d ".venv" ]; then
  echo "🔧 Creating virtual environment..."
  python3 -m venv .venv
fi

# Activate
source .venv/bin/activate

# Install deps if needed
if ! python3 -c "import fastapi" 2>/dev/null; then
  echo "📦 Installing dependencies..."
  pip install --upgrade pip -q
  pip install -r requirements.txt -q
fi

# Print info
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  Pro Stock Analyzer v1.0"
echo "═══════════════════════════════════════════════════════════════"
echo "  📊 200+ financial ratios · 18 categories"
echo "  🌐 Dashboard:  http://localhost:8300"
echo "  📖 API docs:   http://localhost:8300/docs"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Run
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
python -m uvicorn backend.app:app --host 0.0.0.0 --port 8300 --reload
