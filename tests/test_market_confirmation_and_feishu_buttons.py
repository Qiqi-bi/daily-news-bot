from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
import tempfile
import unittest

from src.daily_news_bot.portfolio import _apply_industry_price_confirmation, _evaluate_fixed_buy_pool, _execution_check_lines
from src.daily_news_bot.main import _build_feishu_action_tendency, _build_feishu_digest, _build_feishu_objective_lines
from src.daily_news_bot.senders import _build_card_payload


class MarketConfirmationAndFeishuButtonsTest(unittest.TestCase):
    def test_execution_check_lines_prioritize_holding_risks(self) -> None:
        lines = _execution_check_lines(
            {
                "items": [
                    {
                        "code": "510300",
                        "name": "沪深300ETF",
                        "source": "holding",
                        "latest_price": 4.0,
                        "change_pct": 0.2,
                        "turnover_cny": 300_000_000,
                        "liquidity_level": "好",
                        "chase_risk": "低",
                    },
                    {
                        "code": "588930",
                        "name": "AI主题ETF",
                        "source": "holding",
                        "latest_price": 1.2,
                        "change_pct": 3.2,
                        "turnover_cny": 10_000_000,
                        "liquidity_level": "偏弱",
                        "chase_risk": "高",
                    },
                ]
            }
        )

        first_data_row = lines[2]

        self.assertIn("AI主题ETF", first_data_row)
        self.assertIn("偏弱", first_data_row)
        self.assertIn("高", first_data_row)

    def test_industry_price_gate_blocks_three_hit_streak_when_relative_strength_is_weak(self) -> None:
        radar = {
            "enabled": True,
            "rows": [
                {
                    "id": "ai_power_base",
                    "name": "AI电力底座",
                    "layer": "secular",
                    "status": "今日关注",
                    "hit_streak": 3,
                    "theme_keys": ["ai_power_base"],
                    "instruments": ["561560"],
                    "binding_summary": "参考代码：561560；连续3次：连续确认",
                }
            ],
            "summary_lines": [],
        }

        enriched = _apply_industry_price_confirmation(
            radar,
            portfolio_quotes=None,
            execution_checks={
                "items": [
                    {
                        "code": "561560",
                        "change_pct": -0.2,
                        "turnover_cny": 150_000_000,
                        "chase_risk": "低",
                    }
                ]
            },
            local_market_payload={"broad_change_pct": 0.8, "risk_avg_pct": 0.1, "high_chase_count": 0},
            candidate_scores=[],
        )

        row = enriched["rows"][0]

        self.assertEqual(row["price_confirmation_status"], "价格未确认")
        self.assertEqual(row["base_position_gate"], "继续观察")
        self.assertIn("相对强弱落后", "；".join(row["price_confirmation"]["blockers"]))
        self.assertIn("价格未确认", row["binding_summary"])

    def test_industry_price_gate_allows_weekly_review_only_after_streak_and_price_confirmation(self) -> None:
        radar = {
            "enabled": True,
            "rows": [
                {
                    "id": "ai_power_base",
                    "name": "AI电力底座",
                    "layer": "secular",
                    "status": "今日关注",
                    "hit_streak": 3,
                    "theme_keys": ["ai_power_base"],
                    "instruments": ["561560"],
                    "binding_summary": "参考代码：561560；连续3次：连续确认",
                }
            ],
            "summary_lines": [],
        }

        enriched = _apply_industry_price_confirmation(
            radar,
            portfolio_quotes=None,
            execution_checks={
                "items": [
                    {
                        "code": "561560",
                        "change_pct": 1.4,
                        "turnover_cny": 150_000_000,
                        "chase_risk": "低",
                    }
                ]
            },
            local_market_payload={"broad_change_pct": 0.2, "risk_avg_pct": 0.1, "high_chase_count": 0},
            candidate_scores=[],
        )

        row = enriched["rows"][0]

        self.assertEqual(row["price_confirmation_status"], "价格确认")
        self.assertEqual(row["base_position_gate"], "周报评估")
        self.assertIn("周报评估", row["binding_summary"])
        self.assertIn("不自动交易", row["price_confirmation_note"])

    def test_industry_weekly_review_enters_cooldown_after_first_prompt(self) -> None:
        radar = {
            "enabled": True,
            "rows": [
                {
                    "id": "ai_power_base",
                    "name": "AI电力底座",
                    "layer": "secular",
                    "status": "今日关注",
                    "hit_streak": 4,
                    "theme_keys": ["ai_power_base"],
                    "instruments": ["561560"],
                    "binding_summary": "参考代码：561560；连续4次：连续确认",
                }
            ],
            "summary_lines": [],
        }
        checks = {
            "items": [
                {
                    "code": "561560",
                    "change_pct": 1.4,
                    "turnover_cny": 150_000_000,
                    "chase_risk": "低",
                }
            ]
        }

        with tempfile.TemporaryDirectory() as tmp:
            state_path = Path(tmp) / "industry_radar_state.json"
            first = _apply_industry_price_confirmation(
                radar,
                portfolio_quotes=None,
                execution_checks=checks,
                local_market_payload={"broad_change_pct": 0.2, "risk_avg_pct": 0.1, "high_chase_count": 0},
                candidate_scores=[],
                generated_at=datetime(2026, 5, 3, 13),
                state_path=state_path,
            )
            second = _apply_industry_price_confirmation(
                radar,
                portfolio_quotes=None,
                execution_checks=checks,
                local_market_payload={"broad_change_pct": 0.2, "risk_avg_pct": 0.1, "high_chase_count": 0},
                candidate_scores=[],
                generated_at=datetime(2026, 5, 4, 13),
                state_path=state_path,
            )
            state_payload = json.loads(state_path.read_text(encoding="utf-8"))

        first_row = first["rows"][0]
        second_row = second["rows"][0]

        self.assertEqual(first_row["base_position_gate"], "周报评估")
        self.assertEqual(second_row["base_position_gate"], "冷却中")
        self.assertIn("冷却", second_row["price_confirmation_note"])
        self.assertIn("冷却中", second_row["binding_summary"])
        self.assertIn("已进入冷却期", "\n".join(second["summary_lines"]))
        self.assertEqual(state_payload["updated_at_utc"], "2026-05-03T13:00:00")

    def test_fixed_pool_rows_include_market_confirmation_detail(self) -> None:
        rows = _evaluate_fixed_buy_pool(
            {
                "profile": {"monthly_contribution_cny": 10000},
                "allocation_framework": {
                    "stable_core_target_pct": [35, 45],
                    "growth_core_target_pct": [15, 20],
                    "attack_target_pct": [20, 30],
                    "insurance_target_pct": [10, 15],
                },
                "risk_controls": {
                    "direct_ai_cap_pct": 35,
                    "growth_tech_cap_pct": 55,
                    "single_attack_holding_cap_pct": 15,
                    "hard_gates": {"max_monthly_action_count": 2},
                },
                "decision_cockpit": {
                    "action_amount_bands": {"buy_probe_cny": [800, 1500]},
                    "fixed_buy_pool": [
                        {
                            "code": "588930",
                            "name": "AI ETF",
                            "type": "ETF",
                            "role": "AI attack ETF",
                            "theme_key": "ai_attack",
                        }
                    ],
                },
                "holdings": [],
            },
            {
                "direct_ai_pct": 0.0,
                "growth_tech_pct": 20.0,
                "attack_pct": 10.0,
                "gold_pct": 10.0,
                "stable_core_pct": 40.0,
                "growth_core_pct": 15.0,
            },
            None,
            {
                "items": [
                    {
                        "code": "588930",
                        "change_pct": 3.2,
                        "turnover_cny": 8_000_000,
                        "chase_risk": "\u9ad8",
                        "liquidity_level": "\u504f\u5f31",
                    }
                ]
            },
            [],
            [{"theme_key": "ai"}],
            local_market_payload={
                "phase": "\u4e3b\u9898\u8fc7\u70ed",
                "broad_change_pct": 0.2,
                "ai_change_pct": 1.6,
                "risk_avg_pct": 1.7,
                "high_chase_count": 2,
            },
            trade_ledger={"enabled": True, "trades": []},
        )

        confirmation = rows[0]["market_confirmation"]

        self.assertEqual(rows[0]["state"], "\u89c2\u5bdf")
        self.assertEqual(confirmation["relative_strength_status"], "\u5f3a")
        self.assertEqual(confirmation["volume_confirmation"], "\u4e0d\u8db3")
        self.assertEqual(confirmation["pullback_position"], "\u9ad8\u4f4d\u8ffd\u6da8")
        self.assertEqual(confirmation["crowding_level"], "\u9ad8")
        self.assertTrue(confirmation["blocks_action"])
        self.assertIn("\u8ffd\u9ad8", "\n".join(confirmation["blockers"]))

    def test_feishu_card_has_three_receipt_entry_buttons(self) -> None:
        payload = _build_card_payload(
            "daily",
            "Dashboard\uff1ahttps://example.com/dashboard\n\u56de\u6267\u9875\uff1ahttps://example.com/receipt?token=abc",
        )

        buttons = [
            action
            for element in payload["card"]["elements"]
            if element.get("tag") == "action"
            for action in element.get("actions", [])
            if action.get("tag") == "button"
        ]
        labels = [button["text"]["content"] for button in buttons]
        urls = [button.get("url", "") for button in buttons]

        self.assertIn("\u4eca\u5929\u6ca1\u64cd\u4f5c", labels)
        self.assertIn("\u4e70\u5165/\u52a0\u4ed3", labels)
        self.assertIn("\u5356\u51fa/\u51cf\u4ed3", labels)
        self.assertTrue(any("action=noop" in url for url in urls))
        self.assertTrue(any("action=buy" in url for url in urls))
        self.assertTrue(any("action=sell" in url for url in urls))

    def test_feishu_card_relabels_dashboard_as_chinese_web_entry(self) -> None:
        payload = _build_card_payload(
            "daily",
            "Dashboard:https://example.com/dashboard\n回执页：https://example.com/receipt?token=abc",
        )

        text_blocks = [
            element.get("text", {}).get("content", "")
            for element in payload["card"]["elements"]
            if element.get("tag") == "div"
        ]
        combined_text = "\n".join(text_blocks)
        buttons = [
            action
            for element in payload["card"]["elements"]
            if element.get("tag") == "action"
            for action in element.get("actions", [])
            if action.get("tag") == "button"
        ]

        self.assertNotIn("网页：https://example.com/dashboard", combined_text)
        self.assertNotIn("回执页：https://example.com/receipt", combined_text)
        self.assertNotIn("Dashboard", combined_text)
        self.assertTrue(any(button.get("url") == "https://example.com/dashboard" for button in buttons))

    def test_feishu_digest_receipt_line_has_clean_punctuation(self) -> None:
        digest = _build_feishu_digest(
            {
                "clusters": [],
                "market_snapshot": {"items": []},
                "watchlist": {"triggered_count": 0},
                "signal_validation": {"signal_count": 0},
                "feishu_receipts": {"status": "not_run"},
                "dashboard": {"public_url": "https://example.com/dashboard"},
                "portfolio": {"enabled": True},
            }
        )

        self.assertIn("本次未读取；下次日报运行前会读取飞书群；有交易才回一行中文，没操作不用回。", digest)
        self.assertNotIn("。；", digest)

    def test_feishu_digest_prioritizes_industry_review_gates(self) -> None:
        digest = _build_feishu_digest(
            {
                "clusters": [],
                "market_snapshot": {"items": []},
                "watchlist": {"triggered_count": 0},
                "signal_validation": {"signal_count": 0},
                "dashboard": {"public_url": "https://example.com/dashboard"},
                "portfolio": {
                    "enabled": True,
                    "industry_radar": {
                        "rows": [
                            {
                                "name": "普通热点",
                                "layer": "watch",
                                "status": "今日关注",
                                "watch": "新闻热度上升。",
                            },
                            {
                                "name": "AI电力底座",
                                "layer": "secular",
                                "status": "持仓复核",
                                "horizon": "1-3年",
                                "watch": "绿电、算力订单和电价机制。",
                                "base_position_gate": "周报评估",
                                "price_confirmation_status": "价格确认",
                                "price_confirmation_note": "连续命中叠加价格确认，可以进入周报底仓评估，但不自动交易。",
                                "binding_summary": "连续4次；价格闸门：价格确认，周报评估",
                            },
                            {
                                "name": "黄金保险仓",
                                "layer": "core",
                                "status": "今日关注",
                                "watch": "美元和实际利率。",
                                "base_position_gate": "冷却中",
                                "price_confirmation_status": "价格确认",
                                "price_confirmation_note": "冷却期到 2026-05-09；等周报或新回执后再重新评估。",
                                "binding_summary": "价格闸门：价格确认，冷却中",
                            },
                        ]
                    },
                },
            }
        )

        self.assertIn("AI电力底座｜周报评估｜价格确认", digest)
        self.assertIn("黄金保险仓｜冷却中｜价格确认", digest)
        self.assertIn("本周已提醒", digest)
        self.assertIn("本周动作：周报复核", digest)
        self.assertIn("不自动买卖", digest)
        self.assertIn("本周评估：AI电力底座", digest)
        self.assertIn("冷却观察：黄金保险仓", digest)
        self.assertIn("只观察：1 条", digest)
        self.assertLess(digest.index("本周动作：周报复核"), digest.index("本周评估：AI电力底座"))
        self.assertLess(digest.index("本周评估：AI电力底座"), digest.index("**市场快照**"))
        self.assertEqual(digest.count("本周评估："), 1)

    def test_feishu_digest_surfaces_execution_risk_without_amounts(self) -> None:
        digest = _build_feishu_digest(
            {
                "clusters": [],
                "market_snapshot": {"items": []},
                "watchlist": {"triggered_count": 0},
                "signal_validation": {"signal_count": 0},
                "dashboard": {"public_url": "https://example.com/dashboard"},
                "portfolio": {
                    "enabled": True,
                    "execution_checks": {
                        "items": [
                            {
                                "name": "AI主题ETF",
                                "code": "588930",
                                "source": "holding",
                                "change_pct": 3.1,
                                "chase_risk": "高",
                                "liquidity_level": "偏弱",
                                "premium_risk": "高",
                                "turnover_cny": 8_000_000,
                            },
                            {
                                "name": "沪深300ETF",
                                "code": "510300",
                                "source": "holding",
                                "change_pct": 0.2,
                                "chase_risk": "低",
                                "liquidity_level": "好",
                            },
                        ]
                    },
                },
            }
        )

        self.assertIn("执行风险：AI主题ETF", digest)
        self.assertIn("追高风险高", digest)
        self.assertIn("流动性偏弱", digest)
        self.assertIn("折溢价风险高", digest)
        self.assertNotIn("8,000,000", digest)
        self.assertLess(digest.index("执行风险："), digest.index("**年度纪律**") if "**年度纪律**" in digest else digest.index("**新闻**"))

    def test_feishu_action_tendency_prioritizes_reduce_discipline_over_tracking(self) -> None:
        tendency = _build_feishu_action_tendency(
            {
                "portfolio": {
                    "enabled": True,
                    "advice_tracking": {
                        "today_items": [
                            {
                                "action": "继续持有",
                                "subject": "沪深300",
                                "verify_at_utc": "2026-06-06T00:00:00Z",
                            }
                        ]
                    },
                    "action_slot_lines": [
                        "1. **减仓复核**｜AI主题基金(011840)｜参考金额 ¥1,000~¥2,500｜原因：直接AI暴露超线，先处理重叠；不是自动卖出。",
                    ],
                }
            }
        )

        self.assertIn("减仓复核", tendency)
        self.assertIn("直接AI暴露超线", tendency)
        self.assertIn("不是自动卖出", tendency)
        self.assertNotIn("继续持有", tendency)
        self.assertNotIn("¥1,000", tendency)

    def test_feishu_digest_groups_risk_gates_under_annual_discipline_without_objective(self) -> None:
        digest = _build_feishu_digest(
            {
                "clusters": [],
                "market_snapshot": {"items": []},
                "watchlist": {"triggered_count": 0},
                "signal_validation": {"signal_count": 0},
                "dashboard": {"public_url": "https://example.com/dashboard"},
                "portfolio": {
                    "enabled": True,
                    "hard_risk_gate_lines": [
                        "- 纪律优先：进攻仓/AI约束优先级最高，新增资金先不要继续加AI、半导体或港股科技。"
                    ],
                },
            }
        )

        self.assertIn("**年度纪律**", digest)
        self.assertIn("纪律优先：进攻仓", digest)
        self.assertLess(digest.index("**年度纪律**"), digest.index("纪律优先：进攻仓"))
        self.assertLess(digest.index("纪律优先：进攻仓"), digest.index("**新闻**"))

    def test_feishu_digest_uses_cluster_level_chinese_news_when_translation_map_is_empty(self) -> None:
        digest = _build_feishu_digest(
            {
                "clusters": [
                    {
                        "cluster_id": "energy-1",
                        "title_zh": "美国制裁扰动能源价格",
                        "summary_zh": "能源价格可能继续波动，先看油价、美元和运费是否同步确认。",
                        "representative": {"title": "U.S. Sanctions Zigzag in New World of Economic Warfare"},
                        "tags": ["energy", "macro"],
                        "direction": "分化",
                        "credibility_label": "中",
                        "confirmed_source_count": 1,
                    }
                ],
                "translations": {"items": {}},
                "market_snapshot": {"items": []},
                "watchlist": {"triggered_count": 0},
                "signal_validation": {"signal_count": 0},
                "dashboard": {"public_url": "https://example.com/dashboard"},
                "portfolio": {"enabled": True},
            }
        )

        self.assertIn("美国制裁扰动能源价格", digest)
        self.assertIn("能源价格可能继续波动", digest)
        self.assertIn("**1条新闻**", digest)
        self.assertNotIn("**3条新闻**", digest)
        self.assertNotIn("U.S. Sanctions", digest)
        self.assertNotIn("能源、宏观事件", digest)

    def test_feishu_digest_surfaces_signal_validation_summary(self) -> None:
        digest = _build_feishu_digest(
            {
                "clusters": [],
                "market_snapshot": {"items": []},
                "watchlist": {"triggered_count": 0},
                "signal_validation": {
                    "signal_count": 8,
                    "rows": [
                        {
                            "theme": "AI电力底座",
                            "t30": {
                                "samples": 3,
                                "win_rate_pct": 67,
                                "avg_return_pct": 4.2,
                                "avg_relative_return_pct": 1.5,
                            },
                            "verdict": "继续跟踪，但等价格确认。",
                        }
                    ],
                    "mistake_reviews": [
                        {
                            "theme": "黄金",
                            "name": "黄金ETF",
                            "horizon": "T+30",
                            "return_pct": -2.0,
                            "relative_return_pct": -1.1,
                            "reason": "追高风险",
                        }
                    ],
                },
                "dashboard": {"public_url": "https://example.com/dashboard"},
                "portfolio": {"enabled": True},
            }
        )

        self.assertIn("**验算**", digest)
        self.assertIn("AI电力底座：T+30 样本 3", digest)
        self.assertIn("用途：验算只校准系统权重", digest)
        self.assertLess(digest.index("**验算**"), digest.index("**状态**"))

    def test_feishu_validation_summary_marks_small_samples_as_not_conclusive(self) -> None:
        digest = _build_feishu_digest(
            {
                "clusters": [],
                "market_snapshot": {"items": []},
                "watchlist": {"triggered_count": 0},
                "signal_validation": {
                    "signal_count": 2,
                    "rows": [
                        {
                            "theme": "六氟化钨",
                            "t30": {
                                "samples": 2,
                                "win_rate_pct": 100,
                                "avg_return_pct": 8.0,
                                "avg_relative_return_pct": 6.0,
                            },
                            "verdict": "表现较强。",
                        }
                    ],
                },
                "dashboard": {"public_url": "https://example.com/dashboard"},
                "portfolio": {"enabled": True},
            }
        )

        self.assertIn("六氟化钨：T+30 样本 2", digest)
        self.assertIn("样本不足，不下结论", digest)
        self.assertNotIn("胜率 100", digest)
        self.assertIn("用途：验算只校准系统权重", digest)

    def test_feishu_validation_leaderboard_hides_win_rate_for_small_samples(self) -> None:
        digest = _build_feishu_digest(
            {
                "clusters": [],
                "market_snapshot": {"items": []},
                "watchlist": {"triggered_count": 0},
                "signal_validation": {
                    "signal_count": 2,
                    "rows": [],
                    "industry_leaderboard": {
                        "rows": [
                            {
                                "theme": "算电协同",
                                "basis": "T+30",
                                "samples": 2,
                                "win_rate_pct": 100,
                                "avg_return_pct": 9.0,
                                "avg_relative_return_pct": 7.0,
                                "action": "继续观察",
                            }
                        ]
                    },
                },
                "dashboard": {"public_url": "https://example.com/dashboard"},
                "portfolio": {"enabled": True},
            }
        )

        self.assertIn("命中率榜：算电协同", digest)
        self.assertIn("样本 2，样本不足，不展示胜率", digest)
        self.assertNotIn("胜率 100", digest)

    def test_feishu_validation_surfaces_mistake_review_without_relative_return(self) -> None:
        digest = _build_feishu_digest(
            {
                "clusters": [],
                "market_snapshot": {"items": []},
                "watchlist": {"triggered_count": 0},
                "signal_validation": {
                    "signal_count": 4,
                    "rows": [],
                    "mistake_reviews": [
                        {
                            "theme": "黄金保险仓",
                            "name": "黄金ETF",
                            "horizon": "T+30",
                            "return_pct": -3.2,
                            "reason": "追高风险",
                        }
                    ],
                },
                "dashboard": {"public_url": "https://example.com/dashboard"},
                "portfolio": {"enabled": True},
            }
        )

        self.assertIn("复盘提醒：黄金保险仓 / 黄金ETF", digest)
        self.assertIn("追高风险", digest)

    def test_feishu_objective_lines_include_worst_stress_without_private_amounts(self) -> None:
        lines = _build_feishu_objective_lines(
            {
                "portfolio": {
                    "annual_objective": {
                        "base_return_pct_range": [8, 12],
                        "stretch_return_pct_range": [12, 18],
                        "max_annual_drawdown_pct": 12,
                    },
                    "stress_test": {
                        "worst_case": {
                            "name": "A股系统回撤",
                            "estimated_impact_pct": -13.7,
                            "severity": "超过预算",
                            "action": "暂停新增进攻仓，先复核AI重叠。",
                        }
                    },
                }
            }
        )

        text = "\n".join(lines[:2])

        self.assertIn("压力", text)
        self.assertIn("A股系统回撤", text)
        self.assertIn("暂停新增进攻仓", text)
        self.assertNotIn("¥", text)


if __name__ == "__main__":
    unittest.main()
