"""
Tests for report API endpoints.
"""
import pytest


class TestReportEndpoints:
    """Test suite for quarterly and monthly report endpoints."""

    def test_get_quarterly_reports(self, client):
        """Test getting quarterly reports."""
        response = client.get("/api/reports/quarterly")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        for quarter in data:
            assert "quarter" in quarter
            assert "total_orders" in quarter
            assert "total_revenue" in quarter
            assert "fulfillment_rate" in quarter

    def test_get_monthly_trends(self, client):
        """Test getting monthly trends sorted by month."""
        response = client.get("/api/reports/monthly-trends")
        assert response.status_code == 200

        data = response.json()
        months = [m["month"] for m in data]
        assert months == sorted(months)

    @pytest.mark.parametrize("endpoint", ["/api/reports/quarterly", "/api/reports/monthly-trends"])
    def test_reports_respect_warehouse_filter(self, client, endpoint):
        """Test that the warehouse filter narrows report totals to that warehouse's orders."""
        count_key = "total_orders" if "quarterly" in endpoint else "order_count"
        expected = len(client.get("/api/orders?warehouse=Tokyo").json())

        all_data = client.get(endpoint).json()
        filtered = client.get(f"{endpoint}?warehouse=Tokyo").json()

        assert sum(r[count_key] for r in filtered) == expected
        assert sum(r[count_key] for r in filtered) < sum(r[count_key] for r in all_data)

    def test_monthly_trends_month_filter(self, client):
        """Test that a month filter returns only that month."""
        response = client.get("/api/reports/monthly-trends?month=2025-03")
        assert response.status_code == 200

        data = response.json()
        assert [m["month"] for m in data] == ["2025-03"]

    def test_quarterly_reports_quarter_filter(self, client):
        """Test that a quarter filter returns only that quarter."""
        data = client.get("/api/reports/quarterly?month=Q2-2025").json()
        assert [q["quarter"] for q in data] == ["Q2-2025"]

    def test_reports_status_filter(self, client):
        """Test that filtering by Delivered gives a 100% fulfillment rate."""
        data = client.get("/api/reports/quarterly?status=Delivered").json()
        assert len(data) > 0
        for quarter in data:
            assert quarter["fulfillment_rate"] == 100.0
