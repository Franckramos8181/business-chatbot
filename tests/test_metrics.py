import pytest
from unittest.mock import patch, MagicMock
from decimal import Decimal


def _mock_revenue_query(total_amount=10000, total_quantity=100):
    mock_result = MagicMock()
    mock_result.scalar.return_value = Decimal(str(total_amount))
    return mock_result


class TestSummaryMetrics:
    @patch("analysis.metrics.get_session")
    def test_returns_expected_keys(self, mock_session):
        session = MagicMock()
        mock_session.return_value.__enter__ = MagicMock(return_value=session)
        mock_session.return_value.__exit__ = MagicMock(return_value=False)

        session.query.return_value.filter.return_value.scalar.side_effect = [
            Decimal("50000"),
            Decimal("30000"),
            Decimal("10000"),
        ]

        from analysis.metrics import summary_metrics
        result = summary_metrics("2024-01-01", "2024-12-31")

        assert "total_revenue" in result
        assert "total_expenses" in result
        assert "net_profit" in result
        assert "profit_margin" in result
        assert "total_liabilities" in result

    @patch("analysis.metrics.get_session")
    def test_calculates_net_profit(self, mock_session):
        session = MagicMock()
        mock_session.return_value.__enter__ = MagicMock(return_value=session)
        mock_session.return_value.__exit__ = MagicMock(return_value=False)

        session.query.return_value.filter.return_value.scalar.side_effect = [
            Decimal("50000"),
            Decimal("30000"),
            Decimal("10000"),
        ]

        from analysis.metrics import summary_metrics
        result = summary_metrics("2024-01-01", "2024-12-31")

        assert result["net_profit"] == 20000.0
        assert result["profit_margin"] == 40.0


class TestProductMetrics:
    @patch("analysis.metrics.get_session")
    def test_returns_sorted_by_revenue(self, mock_session):
        session = MagicMock()
        mock_session.return_value.__enter__ = MagicMock(return_value=session)
        mock_session.return_value.__exit__ = MagicMock(return_value=False)

        product1 = MagicMock(id=1, name="Tax Returns", type="Service", unit_price=Decimal("150"), cost=Decimal("20"), is_active=True)
        product2 = MagicMock(id=2, name="Bookkeeping", type="Service", unit_price=Decimal("100"), cost=Decimal("15"), is_active=True)

        session.query.return_value.filter_by.return_value.all.return_value = [product1, product2]

        session.query.return_value.filter.return_value.first.side_effect = [
            (Decimal("30000"), Decimal("200")),
            Decimal("5000"),
            (Decimal("10000"), Decimal("100")),
            Decimal("2000"),
        ]
        session.query.return_value.filter.return_value.scalar.side_effect = [
            Decimal("5000"),
            Decimal("2000"),
        ]

        from analysis.metrics import product_metrics
        result = product_metrics("2024-01-01", "2024-12-31")

        assert len(result) == 2
        assert result[0]["total_revenue"] >= result[1]["total_revenue"]


class TestIdentifyOpportunities:
    @patch("analysis.metrics.product_metrics")
    @patch("analysis.metrics.get_session")
    def test_flags_low_margin_products(self, mock_session, mock_product_metrics):
        session = MagicMock()
        mock_session.return_value.__enter__ = MagicMock(return_value=session)
        mock_session.return_value.__exit__ = MagicMock(return_value=False)

        mock_product_metrics.return_value = [
            {
                "product_id": 1,
                "name": "Basic Filing",
                "type": "Service",
                "unit_price": 50.0,
                "unit_cost": 40.0,
                "total_revenue": 5000.0,
                "total_expenses": 4000.0,
                "total_quantity": 100.0,
                "avg_price": 50.0,
                "margin_pct": 20.0,
                "net_profit": 1000.0,
            },
        ]

        session.query.return_value.filter.return_value.group_by.return_value.order_by.return_value.limit.return_value.all.return_value = []

        from analysis.metrics import identify_opportunities
        result = identify_opportunities("2024-01-01", "2024-12-31")

        low_margin = [o for o in result if o["type"] == "low_margin"]
        assert len(low_margin) > 0
        assert low_margin[0]["product"] == "Basic Filing"
