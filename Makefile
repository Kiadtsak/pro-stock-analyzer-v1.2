# ═══════════════════════════════════════════════════════════════════════
# Pro Stock Analyzer — Makefile (enhanced with QA)
# ═══════════════════════════════════════════════════════════════════════
.PHONY: help setup run test test-unit test-integration test-e2e coverage \
        lint format type-check qa benchmark profile clean import-data \
        install-hooks

# Default: show help
help:
	@echo "═══════════════════════════════════════════════════════════════"
	@echo "  Pro Stock Analyzer — Available Commands"
	@echo "═══════════════════════════════════════════════════════════════"
	@echo ""
	@echo "  📦 Setup:"
	@echo "    make setup            Install project + dev dependencies"
	@echo "    make install-hooks    Install pre-commit hooks (once)"
	@echo ""
	@echo "  🚀 Run:"
	@echo "    make run              Start server on :8300"
	@echo ""
	@echo "  🧪 Testing:"
	@echo "    make test             Run ALL tests"
	@echo "    make test-unit        Run unit tests only (fast)"
	@echo "    make test-integration Run integration tests"
	@echo "    make test-e2e         Run E2E API tests"
	@echo "    make coverage         Run tests + coverage report"
	@echo "    make benchmark        Run performance benchmarks"
	@echo ""
	@echo "  🎨 Code Quality:"
	@echo "    make lint             Check code style (ruff)"
	@echo "    make format           Auto-format code (ruff + black)"
	@echo "    make type-check       Static type check (mypy)"
	@echo "    make qa               Run ALL QA checks (lint+format+type+test)"
	@echo ""
	@echo "  📊 Performance:"
	@echo "    make profile          Profile execution (find bottlenecks)"
	@echo ""
	@echo "  🧹 Maintenance:"
	@echo "    make clean            Remove caches"
	@echo "    make import-data      Copy JSONs from ../System_Stock/data/"

# ═══════════════════════════════════════════════════════════════════════
# Setup
# ═══════════════════════════════════════════════════════════════════════
setup:
	@echo "🔧 Creating virtual environment..."
	python3 -m venv .venv
	@echo "📦 Installing project + dev dependencies..."
	. .venv/bin/activate && pip install --upgrade pip -q && pip install -e ".[dev]"

install-hooks:
	@echo "🪝 Installing pre-commit hooks..."
	. .venv/bin/activate && pre-commit install
	@echo "✓ Hooks installed. Every 'git commit' now runs QA checks."

# ═══════════════════════════════════════════════════════════════════════
# Run
# ═══════════════════════════════════════════════════════════════════════
run:
	@bash run.sh

# ═══════════════════════════════════════════════════════════════════════
# Testing
# ═══════════════════════════════════════════════════════════════════════
test:
	@echo "🧪 Running ALL tests..."
	PYTHONPATH=$$(pwd) pytest

test-unit:
	@echo "🧪 Running unit tests..."
	PYTHONPATH=$$(pwd) pytest -m unit

test-integration:
	@echo "🧪 Running integration tests..."
	PYTHONPATH=$$(pwd) pytest -m integration

test-e2e:
	@echo "🧪 Running E2E tests..."
	PYTHONPATH=$$(pwd) pytest -m e2e

test-fast:
	@echo "⚡ Running fast tests (unit only, stop at first failure)..."
	PYTHONPATH=$$(pwd) pytest -m unit -x

coverage:
	@echo "📊 Running tests with coverage..."
	PYTHONPATH=$$(pwd) pytest --cov=backend --cov-report=term-missing --cov-report=html
	@echo ""
	@echo "📄 HTML report: open htmlcov/index.html"

benchmark:
	@echo "⚡ Running benchmarks..."
	PYTHONPATH=$$(pwd) pytest tests/test_benchmarks.py --benchmark-only

# ═══════════════════════════════════════════════════════════════════════
# Code Quality
# ═══════════════════════════════════════════════════════════════════════
lint:
	@echo "🔍 Linting..."
	ruff check backend/ tests/

format:
	@echo "🎨 Formatting..."
	ruff check --fix backend/ tests/
	ruff format backend/ tests/

type-check:
	@echo "📝 Type checking..."
	mypy backend/

qa: lint type-check test-unit
	@echo ""
	@echo "═══════════════════════════════════════════════════════════════"
	@echo "  ✅ All QA checks passed"
	@echo "═══════════════════════════════════════════════════════════════"

# ═══════════════════════════════════════════════════════════════════════
# Performance profiling
# ═══════════════════════════════════════════════════════════════════════
profile:
	@echo "📊 Profiling analysis..."
	PYTHONPATH=$$(pwd) python3 -m cProfile -s cumulative -o profile.stats \
		-c "from backend import load_financials, analyze_financials; \
		    data = load_financials('AAPL'); \
		    [analyze_financials(data) for _ in range(10)]"
	@echo ""
	@echo "📄 Profile saved to profile.stats"
	@echo "View with: python3 -m pstats profile.stats"

# ═══════════════════════════════════════════════════════════════════════
# Maintenance
# ═══════════════════════════════════════════════════════════════════════
clean:
	@echo "🧹 Cleaning caches..."
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov/ .coverage profile.stats
	@echo "✓ Clean"

import-data:
	@if [ -d "../System_Stock/data" ]; then \
		echo "📥 Copying data from ../System_Stock/data/ ..."; \
		cp ../System_Stock/data/*.json data/ 2>/dev/null || true; \
		ls data/*.json 2>/dev/null | wc -l | xargs echo "   Files imported:"; \
	else \
		echo "❌ ../System_Stock/data/ not found"; \
	fi
