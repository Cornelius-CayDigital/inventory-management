"""
Tests for restocking order API endpoints.
"""
import pytest


class TestRestockOrderEndpoints:
    """Test suite for restocking order endpoints."""

    def test_demand_forecasts_include_cost_and_lead_time(self, client):
        """Test that every forecast carries pricing data for restocking."""
        response = client.get("/api/demand")
        assert response.status_code == 200

        for forecast in response.json():
            assert forecast["unit_cost"] > 0
            assert forecast["lead_time_days"] > 0

    def test_create_restock_order(self, client):
        """Test submitting a restocking order prices lines from server data."""
        response = client.post("/api/restock-orders", json={
            "items": [
                {"sku": "WDG-001", "quantity": 10},
                {"sku": "GSK-203", "quantity": 4}
            ],
            "budget": 1000
        })
        assert response.status_code == 201

        order = response.json()
        assert order["status"] == "Submitted"
        assert order["order_number"].startswith("RST-")
        assert len(order["items"]) == 2

        widget = order["items"][0]
        assert widget["name"] == "Industrial Widget Type A"
        assert widget["unit_cost"] == 42.50
        assert widget["line_total"] == 425.00
        assert order["total_cost"] == 452.00

        # Lead time is the slowest line (widget 10 days vs gasket 7 days)
        assert order["lead_time_days"] == 10

    def test_created_order_is_listed(self, client):
        """Test that submitted orders appear in the list, newest first."""
        created = client.post("/api/restock-orders", json={
            "items": [{"sku": "FLT-405", "quantity": 1}]
        }).json()

        response = client.get("/api/restock-orders")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert data[0]["id"] == created["id"]

    def test_unknown_sku_rejected(self, client):
        """Test that SKUs outside the demand forecast return 400."""
        response = client.post("/api/restock-orders", json={
            "items": [{"sku": "NOPE-999", "quantity": 1}]
        })
        assert response.status_code == 400
        assert "NOPE-999" in response.json()["detail"]

    def test_over_budget_rejected(self, client):
        """Test that an order costing more than its budget returns 400."""
        response = client.post("/api/restock-orders", json={
            "items": [{"sku": "MTR-304", "quantity": 10}],
            "budget": 100
        })
        assert response.status_code == 400

    @pytest.mark.parametrize("payload", [
        {"items": []},
        {"items": [{"sku": "WDG-001", "quantity": 0}]},
        {"items": [{"sku": "WDG-001", "quantity": -5}]},
    ])
    def test_invalid_payload_rejected(self, client, payload):
        """Test that empty orders and non-positive quantities fail validation."""
        response = client.post("/api/restock-orders", json=payload)
        assert response.status_code == 422
