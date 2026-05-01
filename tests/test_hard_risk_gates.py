from __future__ import annotations

from datetime import datetime, timezone
import unittest

from src.daily_news_bot.portfolio import _hard_risk_gate_lines, _hard_risk_gate_status


class HardRiskGateTest(unittest.TestCase):
    def test_hard_risk_gates_turn_config_into_plain_limits(self) -> None:
        lines = _hard_risk_gate_lines(
            {
                "profile": {"monthly_contribution_cny": 10000},
                "risk_controls": {
                    "hard_gates": {
                        "max_single_action_pct_of_monthly": 30,
                        "max_monthly_attack_add_pct_of_monthly": 20,
                        "confirmation_required_count": 3,
                        "confirmation_window_days": 14,
                        "max_monthly_action_count": 1,
                    }
                },
            },
            {},
        )

        text = "\n".join(lines)
        self.assertIn("¥3,000.00", text)
        self.assertIn("¥2,000.00", text)
        self.assertIn("14 天内 3 次确认", text)
        self.assertIn("每月最多 1 次主动调仓", text)

    def test_hard_risk_gates_count_current_month_trades_and_attack_budget(self) -> None:
        portfolio = {
            "profile": {"monthly_contribution_cny": 10000},
            "risk_controls": {
                "hard_gates": {
                    "max_monthly_attack_add_pct_of_monthly": 20,
                    "max_monthly_action_count": 2,
                }
            },
            "holdings": [{"code": "588930", "sleeve": "attack"}],
        }
        ledger = {
            "enabled": True,
            "trades": [
                {"date": "2026-05-03", "side": "buy", "code": "588930", "amount_cny": 1200},
                {"date": "2026-05-08", "side": "sell", "code": "510300", "amount_cny": 500},
                {"date": "2026-04-28", "side": "buy", "code": "588930", "amount_cny": 900},
            ],
        }

        status = _hard_risk_gate_status(portfolio, ledger, now=datetime(2026, 5, 20, tzinfo=timezone.utc))
        lines = _hard_risk_gate_lines(portfolio, {}, ledger, now=datetime(2026, 5, 20, tzinfo=timezone.utc))
        text = "\n".join(lines)

        self.assertEqual(status["action_count"], 2)
        self.assertEqual(status["action_remaining"], 0)
        self.assertEqual(status["attack_add_used_cny"], 1200)
        self.assertEqual(status["attack_add_remaining_cny"], 800)
        self.assertTrue(status["blocks_new_action"])
        self.assertIn("2026-05 已记录主动调仓 2/2 次", text)
        self.assertIn("剩余额度 ¥800.00", text)


if __name__ == "__main__":
    unittest.main()
