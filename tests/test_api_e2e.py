"""
tests/test_api_e2e.py — End-to-end API tests.

ทดสอบ HTTP endpoints ทั้งหมด — เหมือน user จริงเรียกใช้

Usage:
    pytest tests/test_api_e2e.py
    pytest -m e2e
"""
from __future__ import annotations

import pytest


@pytest.mark.e2e
class TestHealthEndpoints:
    def test_health_returns_ok(self, api_client):
        response = api_client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["categories"] == 18

    def test_categories_endpoint(self, api_client):
        response = api_client.get("/api/categories")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 18
        # Every category has required fields
        for cat in data["categories"]:
            assert "id" in cat
            assert "label_en" in cat
            assert "label_th" in cat
            assert "description" in cat

    def test_symbols_endpoint(self, api_client):
        response = api_client.get("/api/symbols")
        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        assert "symbols" in data
        assert isinstance(data["symbols"], list)


@pytest.mark.e2e
@pytest.mark.real_data
class TestAnalyzeEndpoints:
    def test_analyze_full(self, api_client):
        """Full analysis of a symbol via HTTP."""
        response = api_client.get("/api/analyze/AAPL")
        if response.status_code == 404:
            pytest.skip("AAPL data not available")

        assert response.status_code == 200
        data = response.json()

        # Check all expected fields
        expected_fields = [
            "symbol", "name", "sector", "signal", "signal_th",
            "composite_score", "sub_scores", "narrative_en", "narrative_th",
            "total_ratios", "categories_computed", "years", "latest_by_category",
        ]
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"

        # Sanity checks
        assert data["symbol"] == "AAPL"
        assert data["total_ratios"] > 200
        assert 0 <= data["composite_score"] <= 100

    def test_analyze_summary(self, api_client):
        """Fast summary endpoint."""
        response = api_client.get("/api/analyze/AAPL/summary")
        if response.status_code == 404:
            pytest.skip("AAPL data not available")

        data = response.json()
        assert "signal" in data
        assert "composite_score" in data
        # Summary should NOT have full ratio data
        assert "latest_by_category" not in data

    def test_analyze_single_category(self, api_client):
        """Fetch one category across years."""
        response = api_client.get("/api/analyze/AAPL/category/profitability")
        if response.status_code == 404:
            pytest.skip("AAPL data not available")

        data = response.json()
        assert data["symbol"] == "AAPL"
        assert data["category"] == "profitability"
        assert "years" in data

    def test_analyze_with_category_filter(self, api_client):
        """Only compute requested categories."""
        response = api_client.get(
            "/api/analyze/AAPL?categories=profitability,valuation"
        )
        if response.status_code == 404:
            pytest.skip("AAPL data not available")

        data = response.json()
        assert set(data["categories_computed"]) == {"profitability", "valuation"}


@pytest.mark.e2e
class TestErrorHandling:
    def test_unknown_symbol_returns_404(self, api_client):
        response = api_client.get("/api/analyze/DOESNOTEXIST")
        assert response.status_code == 404

    def test_unknown_category_returns_400(self, api_client):
        response = api_client.get("/api/analyze/AAPL?categories=nonexistent")
        assert response.status_code in (400, 404)

    def test_invalid_symbol_format_returns_error(self, api_client):
        response = api_client.get("/api/analyze/  ")
        # Should either be 404 or 422 (validation error)
        assert response.status_code >= 400


@pytest.mark.e2e
@pytest.mark.real_data
class TestDeepAnalysis:
    def test_deep_analysis_endpoint(self, api_client):
        response = api_client.get("/api/analyze/AAPL/deep")
        if response.status_code == 404:
            pytest.skip("AAPL data not available")

        data = response.json()
        assert "sections" in data
        assert len(data["sections"]) >= 10
        assert "markdown_th" in data
        assert "markdown_en" in data
        assert len(data["markdown_th"]) > 3000
        assert data["ratios_used_in_analysis"] > 40


@pytest.mark.e2e
class TestStaticFiles:
    def test_root_returns_html_or_json(self, api_client):
        response = api_client.get("/")
        assert response.status_code == 200
        # Either HTML (if frontend exists) or JSON info

    def test_static_css_available(self, api_client):
        response = api_client.get("/static/style.css")
        if response.status_code == 404:
            pytest.skip("Frontend not deployed")
        assert response.status_code == 200
        assert "text/css" in response.headers.get("content-type", "")
