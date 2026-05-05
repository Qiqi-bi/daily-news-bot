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

    def test_portfolio_stress_test_is_visible_on_dashboard(self) -> None:
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
                "signal_validation": {"lines": [], "rows": []},
                "weekly_review": {"enabled": False},
                "portfolio": {
                    "enabled": True,
                    "action_slot_lines": [],
                    "allocation_deviation": {"rows": [], "conclusion": "维持。"},
                    "annual_objective": {"return_budget": {"rows": []}},
                    "stress_test": {
                        "conclusion": "压力超过预算，先控进攻仓。",
                        "rows": [
                            {
                                "name": "A股系统回撤",
                                "estimated_impact_pct": -13.7,
                                "severity": "超过预算",
                                "shock_text": "稳底仓 -12.00%；成长底仓 -18.00%；进攻仓 -22.00%",
                                "action": "暂停新增进攻仓，先复核AI重叠。",
                            }
                        ],
                    },
                },
                "output_paths": {},
                "dashboard": {},
            }
        )

        self.assertIn("风险压力测试", html)
        self.assertIn("A股系统回撤", html)
        self.assertIn("暂停新增进攻仓", html)

    def test_industry_radar_surfaces_review_gate_summary(self) -> None:
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
                "signal_validation": {"lines": [], "rows": []},
                "weekly_review": {"enabled": False},
                "portfolio": {
                    "enabled": True,
                    "action_slot_lines": [],
                    "allocation_deviation": {"rows": [], "conclusion": "维持。"},
                    "annual_objective": {"return_budget": {"rows": []}},
                    "stress_test": {"rows": []},
                    "industry_radar": {
                        "enabled": True,
                        "rows": [
                            {
                                "layer_label": "长期主线",
                                "name": "AI电力底座",
                                "horizon": "1-3年",
                                "score_card_text": "政策 4 / 供需 5",
                                "status": "今日关注",
                                "base_position_gate": "周报评估",
                                "price_confirmation_status": "价格确认",
                                "price_confirmation_note": "连续命中叠加价格确认，可以进入周报底仓评估，但不自动交易。",
                                "fact_summary": "算电协同继续推进。",
                                "watch": "绿电和算力订单。",
                                "binding_summary": "连续4次；价格闸门：价格确认，周报评估",
                                "verify": "等周报评估。",
                                "action": "只进周报评估，不自动交易。",
                            },
                            {
                                "layer_label": "保险仓",
                                "name": "黄金保险仓",
                                "horizon": "长期",
                                "score_card_text": "政策 2 / 供需 3",
                                "status": "今日关注",
                                "base_position_gate": "冷却中",
                                "price_confirmation_status": "价格确认",
                                "price_confirmation_note": "冷却期到 2026-05-09；等周报或新回执后再重新评估。",
                                "fact_summary": "避险仍在。",
                                "watch": "美元和实际利率。",
                                "binding_summary": "价格闸门：价格确认，冷却中",
                                "verify": "等新回执。",
                                "action": "本周已提醒。",
                            },
                        ],
                    },
                },
                "output_paths": {},
                "dashboard": {},
            }
        )

        self.assertIn("行业闸门", html)
        self.assertIn("周报评估：AI电力底座", html)
        self.assertIn("冷却中：黄金保险仓", html)
        self.assertIn("只进周报评估，不自动交易", html)


if __name__ == "__main__":
    unittest.main()
