from __future__ import annotations

import unittest

from src.daily_news_bot.portfolio import _annual_objective_payload, _evaluate_fixed_buy_pool


class ReturnBudgetAndOddsTest(unittest.TestCase):
    def test_annual_objective_splits_return_budget_by_sleeve(self) -> None:
        payload = _annual_objective_payload(
            {
                "allocation_framework": {
                    "stable_core_target_pct": [35, 45],
                    "growth_core_target_pct": [15, 20],
                    "attack_target_pct": [20, 30],
                    "insurance_target_pct": [10, 15],
                    "reserve_target_pct": [0, 10],
                },
                "annual_objective": {
                    "return_assumptions_pct": {
                        "stable_core": [4, 6],
                        "growth_core": [8, 12],
                        "attack": [12, 18],
                        "insurance": [0, 6],
                        "reserve": [0, 2],
                    }
                },
            }
        )

        budget = payload["return_budget"]
        stable = next(row for row in budget["rows"] if row["key"] == "stable_core")
        attack = next(row for row in budget["rows"] if row["key"] == "attack")

        self.assertEqual(stable["target_mid_pct"], 40.0)
        self.assertEqual(stable["expected_return_mid_pct"], 5.0)
        self.assertEqual(stable["contribution_mid_pct"], 2.0)
        self.assertEqual(attack["target_mid_pct"], 25.0)
        self.assertEqual(attack["contribution_mid_pct"], 3.75)
        self.assertGreater(budget["estimated_return_contribution_pct_range"][1], 10)

    def test_fixed_buy_pool_rows_include_odds_and_confirmation_gate(self) -> None:
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
            {"items": [{"code": "588930", "change_pct": 0.8, "chase_risk": "\u4f4e", "liquidity_level": "\u6b63\u5e38"}]},
            [],
            [{"theme_key": "ai"}],
            trade_ledger={"enabled": True, "trades": []},
        )

        row = rows[0]
        odds = row["opportunity_score"]

        self.assertEqual(row["state"], "\u53ef\u4e70")
        self.assertEqual(odds["label"], "\u53ef\u590d\u6838")
        self.assertGreaterEqual(odds["confirmation_count"], odds["confirmation_required"])
        self.assertIn("expected_upside_pct_range", odds)
        self.assertIn("max_drawdown_pct", odds)


if __name__ == "__main__":
    unittest.main()
