from __future__ import annotations

import unittest

from src.daily_news_bot.dashboard import render_dashboard_html
from src.daily_news_bot.main import _public_payload_without_private_portfolio


class DashboardWeeklyPriorityTest(unittest.TestCase):
    def test_dashboard_uses_cluster_level_chinese_news_without_showing_english_original(self) -> None:
        html = render_dashboard_html(
            {
                "generated_at_utc": "2026-05-01T00:00:00",
                "mode": "evening",
                "selected_count": 1,
                "articles_count": 1,
                "clusters": [
                    {
                        "cluster_id": "energy-1",
                        "title_zh": "美国制裁扰动能源价格",
                        "summary_zh": "能源价格可能继续波动，先看油价、美元和运费是否同步确认。",
                        "representative": {
                            "title": "U.S. Sanctions Zigzag in New World of Economic Warfare",
                            "summary": "Oil markets face a new sanctions shock.",
                            "source": "Foreign Wire",
                        },
                        "tags": ["energy", "macro"],
                        "direction": "分化",
                        "credibility_label": "中",
                        "confirmed_source_count": 1,
                    }
                ],
                "translations": {"items": {}},
                "data_quality": {"generated_at_bjt": "2026-05-01 08:00"},
                "market_snapshot": {"items": []},
                "watchlist": {"triggered_count": 0, "new_count": 0, "active_count": 0},
                "feishu_receipts": {"status": "not_run"},
                "signal_validation": {"lines": [], "rows": []},
                "weekly_review": {"enabled": False},
                "portfolio": {"enabled": False},
                "output_paths": {},
                "dashboard": {},
            }
        )

        self.assertIn("美国制裁扰动能源价格", html)
        self.assertIn("能源价格可能继续波动", html)
        self.assertNotIn("U.S. Sanctions", html)
        self.assertNotIn("Oil markets face", html)

    def test_dashboard_watchlist_uses_chinese_translation_without_english_original(self) -> None:
        html = render_dashboard_html(
            {
                "generated_at_utc": "2026-05-01T00:00:00",
                "mode": "evening",
                "selected_count": 1,
                "articles_count": 1,
                "clusters": [
                    {
                        "cluster_id": "energy-1",
                        "title_zh": "美国制裁扰动能源价格",
                        "summary_zh": "能源价格可能继续波动。",
                        "representative": {
                            "title": "U.S. Sanctions Zigzag in New World of Economic Warfare",
                            "summary": "Oil markets face a new sanctions shock.",
                        },
                    }
                ],
                "translations": {
                    "enabled": True,
                    "items": {
                        "energy-1": {
                            "title_zh": "美国制裁扰动能源价格",
                            "summary_zh": "能源价格可能继续波动。",
                        }
                    },
                },
                "data_quality": {"generated_at_bjt": "2026-05-01 08:00"},
                "market_snapshot": {"items": []},
                "watchlist": {
                    "triggered_count": 0,
                    "new_count": 0,
                    "active_count": 1,
                    "active_items": [
                        {
                            "title": "跟踪：U.S. Sanctions Zigzag in New World of Economic Warfare",
                            "condition_text": "再次出现或价格确认",
                            "action": "继续观察",
                        }
                    ],
                },
                "feishu_receipts": {"status": "not_run"},
                "signal_validation": {"lines": [], "rows": []},
                "weekly_review": {"enabled": False},
                "portfolio": {"enabled": False},
                "output_paths": {},
                "dashboard": {},
            }
        )

        self.assertIn("跟踪：美国制裁扰动能源价格", html)
        self.assertNotIn("原文：", html)
        self.assertNotIn("U.S. Sanctions", html)

    def test_dashboard_hides_english_event_text_when_translation_is_missing(self) -> None:
        html = render_dashboard_html(
            {
                "generated_at_utc": "2026-05-01T00:00:00",
                "mode": "evening",
                "selected_count": 1,
                "articles_count": 1,
                "clusters": [
                    {
                        "cluster_id": "energy-1",
                        "representative": {
                            "title": "U.S. Sanctions Zigzag in New World of Economic Warfare",
                            "summary": "Oil markets face a new sanctions shock and traders are watching shipping costs.",
                            "source": "Foreign Wire",
                        },
                        "tags": ["energy", "macro"],
                    }
                ],
                "translations": {"enabled": False, "items": {}},
                "data_quality": {"generated_at_bjt": "2026-05-01 08:00"},
                "market_snapshot": {"items": []},
                "watchlist": {"triggered_count": 0, "new_count": 0, "active_count": 0},
                "feishu_receipts": {"status": "not_run"},
                "signal_validation": {"lines": [], "rows": []},
                "weekly_review": {"enabled": False},
                "portfolio": {"enabled": False},
                "output_paths": {},
                "dashboard": {},
            }
        )

        self.assertIn("外文事件待翻译", html)
        self.assertIn("外文摘要待翻译", html)
        self.assertNotIn("U.S. Sanctions", html)
        self.assertNotIn("Oil markets face", html)

    def test_dashboard_translation_error_metric_matches_hidden_english_policy(self) -> None:
        html = render_dashboard_html(
            {
                "generated_at_utc": "2026-05-01T00:00:00",
                "mode": "evening",
                "selected_count": 0,
                "articles_count": 0,
                "clusters": [],
                "translations": {"enabled": False, "error": "timeout", "items": {}},
                "data_quality": {"generated_at_bjt": "2026-05-01 08:00"},
                "market_snapshot": {"items": []},
                "watchlist": {"triggered_count": 0, "new_count": 0, "active_count": 0},
                "feishu_receipts": {"status": "not_run"},
                "signal_validation": {"lines": [], "rows": []},
                "weekly_review": {"enabled": False},
                "portfolio": {"enabled": False},
                "output_paths": {},
                "dashboard": {},
            }
        )

        self.assertIn("外文速译", html)
        self.assertIn("长英文已隐藏", html)
        self.assertNotIn("翻译失败时保留原文", html)

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

    def test_weekly_entry_surfaces_industry_review_gates(self) -> None:
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
                                "name": "AI电力底座",
                                "base_position_gate": "周报评估",
                                "price_confirmation_status": "价格确认",
                                "hit_streak": 4,
                            },
                            {
                                "name": "黄金保险仓",
                                "base_position_gate": "冷却中",
                                "price_confirmation_status": "价格确认",
                                "hit_streak": 5,
                            },
                            {
                                "name": "半导体材料",
                                "base_position_gate": "继续观察",
                                "price_confirmation_status": "价格未确认",
                                "hit_streak": 4,
                            },
                            {
                                "name": "风电设备",
                                "base_position_gate": "继续观察",
                                "price_confirmation_status": "价格确认",
                                "hit_streak": 1,
                            },
                        ],
                    },
                },
                "output_paths": {},
                "dashboard": {},
            }
        )

        weekly_html = html[: html.index("系统边界")]
        self.assertIn("本周评估", weekly_html)
        self.assertIn("AI电力底座", weekly_html)
        self.assertIn("冷却观察", weekly_html)
        self.assertIn("黄金保险仓", weekly_html)
        self.assertIn("只观察", weekly_html)
        self.assertIn("2 条", weekly_html)
        self.assertIn("先周报评估，不自动交易", weekly_html)

    def test_weekly_entry_starts_with_action_conclusion(self) -> None:
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
                    "annual_objective": {
                        "base_return_pct_range": [8, 12],
                        "stretch_return_pct_range": [12, 18],
                        "max_annual_drawdown_pct": 12,
                    },
                    "industry_radar": {
                        "rows": [
                            {
                                "name": "AI电力底座",
                                "base_position_gate": "周报评估",
                                "price_confirmation_status": "价格确认",
                                "hit_streak": 4,
                            },
                            {
                                "name": "黄金保险仓",
                                "base_position_gate": "冷却中",
                                "price_confirmation_status": "价格确认",
                                "hit_streak": 5,
                            },
                        ],
                    },
                },
                "output_paths": {},
                "dashboard": {},
            }
        )

        weekly_html = html[: html.index("系统边界")]
        self.assertIn("本周动作", weekly_html)
        self.assertIn("周报复核", weekly_html)
        self.assertIn("AI电力底座", weekly_html)
        self.assertIn("不自动买卖", weekly_html)
        self.assertIn("年度纪律", weekly_html)
        self.assertIn("8.00%~12.00%", weekly_html)
        self.assertLess(weekly_html.index("本周动作"), weekly_html.index("周报状态"))

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

    def test_private_portfolio_still_shows_public_research_sections(self) -> None:
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
                    "private_mode": True,
                    "trade_sync_status": {"label": "操作回执", "value": "已同步", "note": "按账本运行。"},
                    "industry_radar": {
                        "enabled": True,
                        "rows": [
                            {
                                "layer_label": "长期主线",
                                "name": "AI电力底座",
                                "horizon": "1-3年",
                                "score_card_text": "政策 4 / 供需 5",
                                "status": "持仓复核",
                                "base_position_gate": "周报评估",
                                "price_confirmation_status": "价格确认",
                                "fact_summary": "算电协同继续推进。",
                                "watch": "绿电和算力订单。",
                                "binding_summary": "连续4次；价格闸门：价格确认，周报评估",
                                "verify": "等周报评估。",
                                "action": "只进周报评估，不自动交易。",
                            }
                        ],
                    },
                    "fixed_buy_pool_rows": [
                        {
                            "name": "电力ETF",
                            "code": "561560",
                            "state": "观察",
                            "market_confirmation": {"summary": "价格确认，等待周报。"},
                            "odds_label": "中",
                            "amount_text": "按纪律表",
                            "change_text": "+1.20%",
                            "role": "AI电力底座",
                            "reason": "观察，不自动买。",
                        }
                    ],
                },
                "output_paths": {},
                "dashboard": {},
            }
        )

        self.assertIn("组合配置（私密）", html)
        self.assertIn("行业雷达", html)
        self.assertIn('href="#industry"', html)
        self.assertIn("行业闸门", html)
        self.assertIn("周报评估：AI电力底座", html)
        self.assertIn("固定候选池", html)
        self.assertIn('href="#fixed-pool"', html)
        self.assertIn("电力ETF", html)
        self.assertIn("价格确认，等待周报", html)
        self.assertIn("按纪律表", html)
        self.assertIn("+1.20%", html)
        self.assertNotIn("组合偏离面板", html)
        self.assertNotIn("年度收益拆账", html)

    def test_redacted_public_payload_keeps_public_research_sections(self) -> None:
        payload = {
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
                "holdings": [{"code": "SECRET", "cost": 1.23, "shares": 1000}],
                "cash_cny": 99999,
                "action_slot_lines": ["私密动作：买入 SECRET 10000"],
                "allocation_deviation": {"rows": [{"label": "私密仓位"}], "conclusion": "私密仓位"},
                "annual_objective": {"return_budget": {"rows": []}},
                "trade_sync_status": {"value": "已同步", "note": "私密组合已接入。"},
                "industry_radar": {
                    "enabled": True,
                    "rows": [
                        {
                            "layer_label": "长期主线",
                            "name": "AI电力底座",
                            "horizon": "1-3年",
                            "score_card_text": "政策 4 / 供需 5",
                            "status": "持仓复核",
                            "base_position_gate": "周报评估",
                            "price_confirmation_status": "价格确认",
                            "fact_summary": "算电协同继续推进。",
                            "watch": "绿电和算力订单。",
                            "binding_summary": "连续4次；价格闸门：价格确认，周报评估",
                            "verify": "等周报评估。",
                            "action": "只进周报评估，不自动交易。",
                        }
                    ],
                },
                "fixed_buy_pool_rows": [
                    {
                        "name": "电力ETF",
                        "code": "561560",
                        "state": "观察",
                        "market_confirmation": {"summary": "价格确认，等待周报。"},
                        "amount_text": "按纪律表",
                        "change_text": "+1.20%",
                        "role": "AI电力底座",
                        "reason": "观察，不自动买。",
                    }
                ],
            },
            "output_paths": {},
            "dashboard": {},
        }

        public_payload = _public_payload_without_private_portfolio(payload)
        html = render_dashboard_html(public_payload)

        self.assertIn("本周评估", html)
        self.assertIn("行业雷达", html)
        self.assertIn("AI电力底座", html)
        self.assertIn("固定候选池", html)
        self.assertIn("电力ETF", html)
        self.assertNotIn("SECRET", html)
        self.assertNotIn("99999", html)
        self.assertNotIn("私密动作", html)
        self.assertNotIn("组合偏离面板", html)

    def test_dashboard_validation_leaderboard_hides_small_sample_win_rate(self) -> None:
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
                "signal_validation": {
                    "lines": [],
                    "rows": [],
                    "industry_leaderboard": {
                        "rows": [
                            {
                                "theme": "算电协同",
                                "basis": "T+30",
                                "samples": 2,
                                "win_rate_pct": 100.0,
                                "avg_return_pct": 8.8,
                                "avg_relative_return_pct": 5.2,
                                "action": "继续观察",
                            }
                        ]
                    },
                },
                "weekly_review": {"enabled": False},
                "portfolio": {"enabled": False},
                "output_paths": {},
                "dashboard": {},
            }
        )

        self.assertIn("算电协同", html)
        self.assertIn("样本不足", html)
        self.assertIn("不展示胜率", html)
        self.assertNotIn("100.00%", html)

    def test_dashboard_validation_rows_hide_small_sample_win_rate(self) -> None:
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
                "signal_validation": {
                    "lines": [],
                    "rows": [
                        {
                            "theme": "算电协同",
                            "signals": 2,
                            "t30": {"samples": 2, "win_rate_pct": 100.0, "avg_return_pct": 8.0},
                            "t60": {"samples": 0, "win_rate_pct": None, "avg_return_pct": None},
                            "t90": {"samples": 0, "win_rate_pct": None, "avg_return_pct": None},
                            "verdict": "继续积累",
                            "adjustment": "不调整",
                        }
                    ],
                    "industry_leaderboard": {"rows": []},
                },
                "weekly_review": {"enabled": False},
                "portfolio": {"enabled": False},
                "output_paths": {},
                "dashboard": {},
            }
        )

        self.assertIn("算电协同", html)
        self.assertIn("样本不足，不展示胜率", html)
        self.assertNotIn("100.00%", html)

    def test_dashboard_fixed_pool_win_table_hides_small_sample_win_rate(self) -> None:
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
                    "fixed_pool_win_rows": [
                        {
                            "theme_key": "ai_attack",
                            "sample_days": {"d60": 2, "d120": 2, "d250": 2},
                            "selected_window": 60,
                            "selected_leaders": {
                                "t1": {
                                    "name": "AI主题ETF",
                                    "code": "588930",
                                    "samples": 2,
                                    "win_rate_pct": 100.0,
                                    "avg_return_pct": 5.5,
                                }
                            },
                        }
                    ],
                },
                "output_paths": {},
                "dashboard": {},
            }
        )

        self.assertIn("AI主题ETF", html)
        self.assertIn("样本不足", html)
        self.assertIn("不展示胜率", html)
        self.assertNotIn("+100.00%", html)


if __name__ == "__main__":
    unittest.main()
