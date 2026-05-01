from __future__ import annotations

import unittest

from src.daily_news_bot.dashboard import render_dashboard_html


class DashboardWeeklyPriorityTest(unittest.TestCase):
    def test_weekly_review_is_shown_before_daily_news(self) -> None:
        html = render_dashboard_html(
            {
                "generated_at_utc": "2026-05-01T00:00:00",
                "mode": "evening",
                "selected_count": 0,
                "articles_count": 0,
                "clusters": [],
                "data_quality": {"generated_at_bjt": "2026-05-01 08:00"},
                "market_snapshot": {"items": []},
                "watchlist": {"triggered_count": 0, "new_count": 0, "active_count": 0},
                "feishu_receipts": {"status": "not_run"},
                "signal_validation": {"lines": ["- 30/60/90天成绩单继续积累。"], "rows": []},
                "weekly_review": {
                    "enabled": True,
                    "private_mode": True,
                    "public_note": "周复盘已生成，但不公开持仓细节。",
                    "signals": ["下周只看连续确认的主线。"],
                },
                "portfolio": {"enabled": False},
                "output_paths": {},
                "dashboard": {},
            }
        )

        self.assertIn("中长期周报", html)
        self.assertLess(html.index("中长期周报"), html.index("系统边界"))
        self.assertLess(html.index("中长期周报"), html.index("今日核心事件"))


if __name__ == "__main__":
    unittest.main()
