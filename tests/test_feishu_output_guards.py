from __future__ import annotations

import unittest

from src.daily_news_bot.main import _build_feishu_digest


class FeishuOutputGuardTest(unittest.TestCase):
    def test_digest_keeps_return_targets_as_discipline_and_requires_realtime_confirmation(self) -> None:
        digest = _build_feishu_digest(
            {
                "dashboard": {"public_url": "https://example.com/daily-news-bot/"},
                "clusters": [],
                "translations": {"items": {}},
                "market_snapshot": {
                    "items": [
                        {"name": "WTI原油", "change_pct": 1.2, "movement": "上涨"},
                        {"name": "黄金", "change_pct": -0.6, "movement": "下跌"},
                        {"name": "美元指数", "change_pct": 0.4, "movement": "上涨"},
                        {"name": "VIX", "change_pct": 3.0, "movement": "上涨"},
                    ]
                },
                "watchlist": {"triggered_count": 0},
                "signal_validation": {"signal_count": 0},
                "feishu_receipts": {"status": "not_run"},
                "portfolio": {
                    "annual_objective": {
                        "base_return_pct_range": [8, 12],
                        "stretch_return_pct_range": [12, 18],
                        "max_annual_drawdown_pct": 15,
                        "discipline": "目标收益不触发单笔交易。",
                    }
                },
                "macro_burst_risk": {
                    "enabled": True,
                    "level": "高",
                    "score": 9,
                    "posture": "暂停新增进攻仓，保留现金，等价格确认。",
                    "summary_lines": ["宏观爆破风险高：事实和推测分开，先看验证。"],
                    "rows": [
                        {
                            "name": "美元荒/被迫卖出",
                            "fact": "美元、VIX 上行，黄金短跌。",
                            "inference": "可能是换现金，而不是避险失效。",
                            "verify": "继续看美元、VIX、黄金和股指是否共振。",
                            "invalidate": "美元和VIX回落，黄金重新走强。",
                        }
                    ],
                },
            }
        )

        self.assertIn("不是收益承诺", digest)
        self.assertIn("数据可能延迟", digest)
        self.assertIn("实时价格", digest)
        self.assertLessEqual(len(digest.splitlines()), 44)
        self.assertIn("网页：https://example.com/daily-news-bot/", digest)

    def test_digest_is_short_action_market_news_and_web_only(self) -> None:
        digest = _build_feishu_digest(
            {
                "dashboard": {"public_url": "https://example.com/daily-news-bot/"},
                "clusters": [
                    {
                        "cluster_id": "1",
                        "theme": "能源成本上升",
                        "summary_zh": "油价上行推高通胀压力。",
                        "tags": ["energy", "macro"],
                        "direction": "分化",
                        "credibility_label": "高",
                        "confirmed_source_count": 2,
                    },
                    {
                        "cluster_id": "2",
                        "theme": "AI资本开支放缓",
                        "summary_zh": "市场开始复核高估值资产。",
                        "tags": ["ai", "markets"],
                        "direction": "中性",
                        "credibility_label": "中",
                        "confirmed_source_count": 1,
                    },
                ],
                "translations": {"items": {}},
                "market_snapshot": {
                    "items": [
                        {"name": "WTI原油", "change_pct": 1.2, "movement": "上涨"},
                        {"name": "黄金", "change_pct": -0.6, "movement": "下跌"},
                        {"name": "美元指数", "change_pct": 0.4, "movement": "上涨"},
                        {"name": "美国10Y国债收益率", "change_pct": 0.2, "movement": "震荡"},
                        {"name": "VIX", "change_pct": 3.0, "movement": "上涨"},
                        {"name": "纳斯达克100期货", "change_pct": -1.1, "movement": "下跌"},
                    ]
                },
                "watchlist": {"triggered_count": 0},
                "signal_validation": {"signal_count": 0, "rows": [{"theme": "AI"}]},
                "feishu_receipts": {"status": "not_run"},
                "portfolio": {
                    "enabled": True,
                    "action_slot_lines": ["继续持有｜没有明确纪律触发，等待价格确认。"],
                    "annual_objective": {
                        "base_return_pct_range": [8, 12],
                        "stretch_return_pct_range": [12, 18],
                    },
                },
                "macro_burst_risk": {
                    "enabled": True,
                    "level": "高",
                    "score": 9,
                    "posture": "暂停新增进攻仓，保留现金，等价格确认。",
                    "summary_lines": ["宏观爆破风险高：事实和推测分开，先看验证。"],
                },
            }
        )

        self.assertIn("**怎么调整**", digest)
        self.assertIn("**市场快照**", digest)
        self.assertIn("**当天新闻**", digest)
        self.assertIn("网页：https://example.com/daily-news-bot/", digest)
        self.assertNotIn("**宏观爆破风险**", digest)
        self.assertNotIn("**年度纪律**", digest)
        self.assertNotIn("**验算**", digest)
        self.assertNotIn("**回执/周报**", digest)
        self.assertNotIn("**状态**", digest)
        self.assertLessEqual(len(digest.splitlines()), 24)


if __name__ == "__main__":
    unittest.main()
