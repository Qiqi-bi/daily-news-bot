from __future__ import annotations

from datetime import date, timedelta
import unittest
from unittest.mock import patch

from src.daily_news_bot.fixed_pool_history import build_fixed_pool_60d_panel


class FixedPoolHistoryTest(unittest.TestCase):
    def test_small_sample_first_mover_panel_hides_win_rate(self) -> None:
        start = date(2026, 5, 1)
        history = [
            {"date": (start + timedelta(days=offset)).isoformat(), "close": 1.0 + offset * 0.01}
            for offset in range(12)
        ]
        event_history = [
            {"generated_at_utc": "2026-05-01T00:00:00", "theme": "AI 算力主线", "tags": ["ai"]},
            {"generated_at_utc": "2026-05-05T00:00:00", "theme": "AI 订单继续发酵", "tags": ["ai"]},
        ]

        with patch("src.daily_news_bot.fixed_pool_history.load_event_history", return_value=event_history):
            panel = build_fixed_pool_60d_panel(
                {
                    "decision_cockpit": {
                        "fixed_buy_pool": [
                            {"theme_key": "ai_attack", "code": "588930", "name": "AI主题ETF", "type": "ETF"}
                        ]
                    }
                },
                [{"theme_key": "ai"}],
                {"items": [{"theme_key": "ai_attack", "code": "588930", "name": "AI主题ETF", "history": history}]},
            )

        text = "\n".join(panel["win_lines"])

        self.assertIn("样本仍偏少", text)
        self.assertIn("不展示胜率", text)
        self.assertNotIn("胜率 100", text)


if __name__ == "__main__":
    unittest.main()
