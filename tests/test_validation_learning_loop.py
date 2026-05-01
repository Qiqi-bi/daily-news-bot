from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
import json
import tempfile
import unittest

from src.daily_news_bot.signal_validation import build_signal_validation, render_signal_validation_markdown


def _signal(
    *,
    now: datetime,
    theme_key: str,
    theme: str,
    code: str,
    return_pct: float,
    priority: str = "watch",
    source: str = "industry_radar",
) -> dict[str, object]:
    created_at = now - timedelta(days=95)
    price = round(1 + return_pct / 100, 4)
    return {
        "id": f"{theme_key}-{code}",
        "created_at_utc": created_at.isoformat(),
        "source": source,
        "theme": theme,
        "theme_key": theme_key,
        "priority": priority,
        "score": 12,
        "code": code,
        "name": code,
        "start_price": 1.0,
        "observations": {
            "t30": {"return_pct": return_pct, "hit": return_pct > 0, "price": price},
            "t60": {"return_pct": return_pct, "hit": return_pct > 0, "price": price},
            "t90": {"return_pct": return_pct, "hit": return_pct > 0, "price": price},
        },
    }


class ValidationLearningLoopTest(unittest.TestCase):
    def test_builds_industry_hit_rate_leaderboard_and_mistake_reviews(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "signal_validation.json"
            now = datetime(2026, 5, 1)
            path.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "signals": [
                            _signal(now=now, theme_key="energy_power", theme="energy power", code="A", return_pct=6.0),
                            _signal(now=now, theme_key="energy_power", theme="energy power", code="B", return_pct=4.0),
                            _signal(now=now, theme_key="energy_power", theme="energy power", code="C", return_pct=8.0),
                            _signal(now=now, theme_key="story_only", theme="story only", code="D", return_pct=-5.0),
                            _signal(now=now, theme_key="story_only", theme="story only", code="E", return_pct=-3.0),
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            validation = build_signal_validation(
                generated_at=now,
                portfolio_payload={},
                execution_checks={"items": []},
                path=path,
            )

        leaderboard = validation["industry_leaderboard"]["rows"]
        self.assertEqual(leaderboard[0]["theme_key"], "energy_power")
        self.assertEqual(leaderboard[0]["win_rate_pct"], 100.0)
        self.assertGreater(leaderboard[0]["rank_score"], 0)
        self.assertTrue(any(item["theme_key"] == "story_only" for item in validation["mistake_reviews"]))
        self.assertTrue(validation["mistake_summary"]["lines"])

    def test_markdown_surfaces_learning_loop_sections(self) -> None:
        validation = {
            "lines": ["- daily signal validation"],
            "rows": [],
            "industry_leaderboard": {
                "lines": ["- energy power: keep"],
                "rows": [
                    {
                        "theme_key": "energy_power",
                        "theme": "energy power",
                        "signals": 3,
                        "basis": "T90",
                        "samples": 3,
                        "win_rate_pct": 100.0,
                        "avg_return_pct": 6.0,
                        "rank_score": 7.6,
                        "action": "keep",
                    }
                ],
            },
            "mistake_reviews": [
                {
                    "theme": "story only",
                    "name": "D",
                    "code": "D",
                    "horizon": "T90",
                    "return_pct": -5.0,
                    "reason": "signal upgraded too early",
                    "lesson": "wait for price confirmation",
                }
            ],
            "mistake_summary": {"lines": ["- one mistake"]},
        }

        markdown = render_signal_validation_markdown(validation)

        self.assertIn("\u884c\u4e1a\u96f7\u8fbe\u547d\u4e2d\u7387\u699c", markdown)
        self.assertIn("\u9519\u8bef\u590d\u76d8\u5e93", markdown)


if __name__ == "__main__":
    unittest.main()
