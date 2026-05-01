from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import unittest

import json

from src.daily_news_bot.signal_validation import build_signal_validation, render_signal_validation_markdown


class SignalValidationLongTermTest(unittest.TestCase):
    def test_scorecard_uses_30_60_90_day_horizons(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "signal_validation.json"
            now = datetime(2026, 5, 1)
            created_at = now - timedelta(days=95)
            path.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "signals": [
                            {
                                "id": "old-semiconductor-signal",
                                "created_at_utc": created_at.isoformat(),
                                "source": "industry_radar",
                                "theme": "半导体材料",
                                "theme_key": "semiconductor_materials",
                                "priority": "今日关注",
                                "score": 12,
                                "code": "512480",
                                "name": "半导体ETF",
                                "start_price": 1.0,
                                "observations": {},
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            validation = build_signal_validation(
                generated_at=now,
                portfolio_payload={},
                execution_checks={"items": [{"code": "512480", "latest_price": 1.18}]},
                path=path,
            )
            row = validation["rows"][0]
            markdown = render_signal_validation_markdown(validation)

        self.assertEqual(row["t30"]["samples"], 1)
        self.assertEqual(row["t60"]["samples"], 1)
        self.assertEqual(row["t90"]["samples"], 1)
        self.assertIn("T+30", markdown)
        self.assertIn("T+60", markdown)
        self.assertIn("T+90", markdown)
        self.assertNotIn("T+5", markdown)


if __name__ == "__main__":
    unittest.main()
