from __future__ import annotations

import unittest

from src.daily_news_bot.portfolio import _evaluate_fixed_buy_pool
from src.daily_news_bot.main import _build_feishu_objective_lines
from src.daily_news_bot.senders import _build_card_payload


class MarketConfirmationAndFeishuButtonsTest(unittest.TestCase):
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
