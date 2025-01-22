import pytest
from unittest.mock import patch, MagicMock
from decimal import Decimal


class TestRunScenario:
    @patch("analysis.pricing.get_session")
    def test_product_not_found(self, mock_session):
        session = MagicMock()
        mock_session.return_value.__enter__ = MagicMock(return_value=session)
        mock_session.return_value.__exit__ = MagicMock(return_value=False)

        session.query.return_value.filter.return_value.first.return_value = None

        from analysis.pricing import run_scenario
        result = run_scenario("Nonexistent Product", 5.0)

        assert "error" in result

    @patch("analysis.pricing.get_session")
    def test_price_increase_scenario(self, mock_session):
        session = MagicMock()
        mock_session.return_value.__enter__ = MagicMock(return_value=session)
        mock_session.return_value.__exit__ = MagicMock(return_value=False)

        product = MagicMock(
            id=1,
            name="Tax Returns",
            unit_price=Decimal("150"),
            cost=Decimal("20"),
        )
        session.query.return_value.filter.return_value.first.side_effect = [
            product,
            (Decimal("30000"), Decimal("200"), 200),
        ]

        from analysis.pricing import run_scenario
        result = run_scenario("Tax Returns", 5.0)

        assert result["product"] == "Tax Returns"
        assert result["current_price"] == 150.0
        assert result["new_price"] == 155.0
        assert result["profit_change"] > 0

    @patch("analysis.pricing.get_session")
    def test_no_sales_data(self, mock_session):
        session = MagicMock()
        mock_session.return_value.__enter__ = MagicMock(return_value=session)
        mock_session.return_value.__exit__ = MagicMock(return_value=False)

        product = MagicMock(
            id=1,
            name="New Service",
            unit_price=Decimal("100"),
            cost=Decimal("10"),
        )
        session.query.return_value.filter.return_value.first.side_effect = [
            product,
            (None, Decimal("0"), 0),
        ]

        from analysis.pricing import run_scenario
        result = run_scenario("New Service", 10.0)

        assert "error" in result


class TestFindSafeIncreases:
    @patch("analysis.pricing.get_session")
    @patch("analysis.pricing.run_scenario")
    def test_filters_by_margin(self, mock_scenario, mock_session):
        session = MagicMock()
        mock_session.return_value.__enter__ = MagicMock(return_value=session)
        mock_session.return_value.__exit__ = MagicMock(return_value=False)

        product = MagicMock(
            id=1,
            name="Tax Returns",
            unit_price=Decimal("150"),
            cost=Decimal("20"),
            is_active=True,
        )
        session.query.return_value.filter_by.return_value.all.return_value = [product]
        session.query.return_value.filter.return_value.first.return_value = (
            Decimal("30000"), Decimal("200")
        )

        mock_scenario.return_value = {"profit_change": 500.0}

        from analysis.pricing import find_safe_increases
        result = find_safe_increases(min_margin=40)

        assert len(result) > 0
        assert result[0]["current_margin"] >= 40
