import pytest
import numpy as np
from analysis.forecast import _linear_forecast


class TestLinearForecast:
    def test_basic_upward_trend(self):
        data = [
            (2024, 1, 1000),
            (2024, 2, 1100),
            (2024, 3, 1200),
            (2024, 4, 1300),
            (2024, 5, 1400),
            (2024, 6, 1500),
        ]
        result = _linear_forecast(data, 3)

        assert len(result) == 3
        assert result[0]["value"] > 1500
        assert result[0]["trend"] == "up"

    def test_flat_trend(self):
        data = [
            (2024, 1, 1000),
            (2024, 2, 1000),
            (2024, 3, 1000),
            (2024, 4, 1000),
        ]
        result = _linear_forecast(data, 3)

        assert len(result) == 3
        for f in result:
            assert abs(f["value"] - 1000) < 10

    def test_insufficient_data_uses_average(self):
        data = [
            (2024, 1, 500),
            (2024, 2, 700),
        ]
        result = _linear_forecast(data, 3)

        assert len(result) == 3
        for f in result:
            assert f["value"] == 600.0

    def test_empty_data(self):
        result = _linear_forecast([], 3)

        assert len(result) == 3
        for f in result:
            assert f["value"] == 0

    def test_values_never_negative(self):
        data = [
            (2024, 1, 100),
            (2024, 2, 80),
            (2024, 3, 60),
            (2024, 4, 40),
            (2024, 5, 20),
            (2024, 6, 5),
        ]
        result = _linear_forecast(data, 12)

        for f in result:
            assert f["value"] >= 0
