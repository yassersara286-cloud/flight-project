from __future__ import annotations

import unittest

import pandas as pd

from backend.app.analytics import build_analytics


class AnalyticsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.frame = pd.DataFrame(
            {
                "Month": [1, 1, 2],
                "Origin": ["JFK", "LGA", "JFK"],
                "Dest": ["LAX", "ORD", "LAX"],
                "DepDel15": [1, 0, 1],
                "DepDelayMinutes": [30.0, 0.0, 45.0],
            }
        )

    def test_summary_counts_flights_and_positive_delays(self) -> None:
        result = build_analytics(self.frame)

        self.assertEqual(result["total_flights"], 3)
        self.assertEqual(result["delayed_flights"], 2)
        self.assertEqual(result["delay_rate"], 66.67)
        self.assertEqual(result["average_delay_minutes"], 37.5)
        self.assertEqual(len(result["monthly"]), 2)

    def test_origin_filter_is_case_insensitive(self) -> None:
        result = build_analytics(self.frame, "jfk")

        self.assertEqual(result["total_flights"], 2)
        self.assertEqual(result["delayed_flights"], 2)
        self.assertEqual(result["top_routes"][0]["route"], "JFK - LAX")

    def test_unknown_origin_returns_empty_summary(self) -> None:
        result = build_analytics(self.frame, "BOS")

        self.assertEqual(result["total_flights"], 0)
        self.assertEqual(result["monthly"], [])


if __name__ == "__main__":
    unittest.main()
