from __future__ import annotations

from datetime import datetime
import unittest

from src.daily_news_bot.dashboard import render_dashboard_html
from src.daily_news_bot.macro_burst_risk import build_macro_burst_risk
from src.daily_news_bot.main import _build_feishu_digest
from src.daily_news_bot.models import Article, EventCluster


def _cluster(title: str, summary: str, tags: list[str]) -> EventCluster:
    article = Article(
        title=title,
        url="https://example.com/macro",
        source="Macro Wire",
        category="macro",
        region="US",
        source_weight=1.0,
        published_at=datetime(2026, 5, 9),
        summary=summary,
    )
    return EventCluster(
        cluster_id="macro-1",
        theme=title,
        articles=[article],
        score=12,
        tags=tags,
        credibility_label="高",
        confirmed_source_count=3,
    )


def _stressed_market() -> dict:
    return {
        "items": [
            {"name": "WTI原油", "group": "energy", "change_pct": 2.1, "movement": "上涨"},
            {"name": "美元指数", "group": "fx", "change_pct": 0.8, "movement": "上涨"},
            {"name": "美国10Y国债收益率", "group": "rates", "change_pct": 1.1, "movement": "上涨"},
            {"name": "VIX", "group": "volatility", "change_pct": 9.2, "movement": "上涨"},
            {"name": "纳斯达克100期货", "group": "equity", "change_pct": -1.6, "movement": "下跌"},
            {"name": "黄金", "group": "safe_haven", "change_pct": -1.1, "movement": "下跌"},
        ]
    }


class MacroBurstRiskTest(unittest.TestCase):
    def test_macro_burst_risk_detects_forced_selling_setup(self) -> None:
        lens = build_macro_burst_risk(
            [
                _cluster(
                    "Warsh Fed chair shift revives QT and rate cut debate",
                    "Oil shock, dollar shortage, margin pressure, AI capex and Buffett cash raise forced selling risk.",
                    ["macro", "energy", "markets"],
                )
            ],
            _stressed_market(),
        )

        self.assertTrue(lens["enabled"])
        self.assertIn(lens["level"], {"高", "极高"})
        self.assertGreaterEqual(lens["score"], 8)
        self.assertIn("被迫交易", " ".join(lens["summary_lines"]))
        self.assertIn("暂停新增进攻", lens["posture"])
        self.assertTrue(any(row["key"] == "liquidity_squeeze" for row in lens["rows"]))
        self.assertTrue(any("VIX" in row["evidence"] for row in lens["rows"]))

    def test_feishu_digest_surfaces_macro_risk_without_turning_it_into_buy_signal(self) -> None:
        digest = _build_feishu_digest(
            {
                "dashboard": {"public_url": "https://example.com/daily-news-bot/"},
                "clusters": [],
                "translations": {"items": {}},
                "market_snapshot": {"items": []},
                "watchlist": {"triggered_count": 0},
                "signal_validation": {"signal_count": 0},
                "feishu_receipts": {"status": "not_run"},
                "macro_burst_risk": {
                    "enabled": True,
                    "level": "高",
                    "score": 9,
                    "posture": "暂停新增进攻仓，保留现金，等价格确认。",
                    "summary_lines": [
                        "宏观爆破风险高：谁被迫交易、谁有现金等打折、谁承担油价和美元压力。",
                        "用途：只做风险闸门，不自动买卖。",
                    ],
                },
            }
        )

        self.assertIn("宏观爆破风险", digest)
        self.assertIn("暂停新增进攻仓", digest)
        self.assertIn("不自动买卖", digest)
        self.assertNotIn("马上买入", digest)

    def test_dashboard_shows_macro_burst_risk_panel(self) -> None:
        html = render_dashboard_html(
            {
                "generated_at_utc": "2026-05-09T12:00:00",
                "mode": "evening",
                "selected_count": 0,
                "articles_count": 0,
                "clusters": [],
                "translations": {"items": {}},
                "data_quality": {"generated_at_bjt": "2026-05-09 20:00"},
                "market_snapshot": {"items": []},
                "watchlist": {"triggered_count": 0, "new_count": 0, "active_count": 0},
                "feishu_receipts": {"status": "not_run"},
                "signal_validation": {"lines": [], "rows": []},
                "weekly_review": {"enabled": False},
                "portfolio": {"enabled": False},
                "output_paths": {},
                "dashboard": {},
                "macro_burst_risk": {
                    "enabled": True,
                    "level": "高",
                    "score": 9,
                    "posture": "暂停新增进攻仓，保留现金，等价格确认。",
                    "summary_lines": ["谁被迫交易，谁有现金等打折。"],
                    "rows": [
                        {
                            "name": "美元荒/被迫卖出",
                            "evidence": "美元指数上涨；黄金下跌；VIX上涨",
                            "read": "先看流动性，不把黄金短跌误判成主线失效。",
                        }
                    ],
                },
            }
        )

        self.assertIn("宏观爆破风险", html)
        self.assertIn("暂停新增进攻仓", html)
        self.assertIn("美元荒/被迫卖出", html)


if __name__ == "__main__":
    unittest.main()
