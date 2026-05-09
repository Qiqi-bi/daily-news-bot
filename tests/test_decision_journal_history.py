from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from src.daily_news_bot.decision_journal import build_event_etf_history


class DecisionJournalHistoryTest(unittest.TestCase):
    def test_event_etf_history_hides_small_sample_win_rate(self) -> None:
        records = [
            {
                "generated_at_utc": "2026-05-01T00:00:00",
                "top_events": [{"theme_keys": ["ai"]}],
                "top_candidates": [
                    {
                        "theme_key": "semiconductor",
                        "instruments": [{"code": "512480", "name": "半导体ETF", "latest_price": 1.0}],
                    }
                ],
            },
            {
                "generated_at_utc": "2026-05-02T00:00:00",
                "top_candidates": [
                    {
                        "theme_key": "semiconductor",
                        "instruments": [{"code": "512480", "name": "半导体ETF", "latest_price": 1.1}],
                    }
                ],
            },
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "decision_journal.json"
            path.write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")

            panel = build_event_etf_history([{"theme_key": "ai"}], path=path)

        text = "\n".join(panel["lines"])

        self.assertIn("样本偏少", text)
        self.assertIn("不展示均值/胜率", text)
        self.assertNotIn("胜率 100", text)
        self.assertNotIn("+10.00%", text)


if __name__ == "__main__":
    unittest.main()
