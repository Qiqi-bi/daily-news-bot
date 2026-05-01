from __future__ import annotations

import unittest

from src.daily_news_bot.trade_ledger import aggregate_trade_ledger, build_trade_sync_status


class TradeSyncStatusTest(unittest.TestCase):
    def test_reports_latest_known_trade_and_receipt_poll_state(self) -> None:
        ledger = {
            "enabled": True,
            "path": "config/trade_ledger.yaml",
            "trades": [
                {
                    "date": "2026-04-29",
                    "code": "510300",
                    "side": "buy",
                    "amount_cny": 1000,
                    "price": 5,
                    "source": "manual",
                },
                {
                    "date": "2026-04-30",
                    "code": "518880",
                    "side": "sell",
                    "shares": 100,
                    "price": 6,
                    "source": "feishu_poll",
                    "message_id": "mid_1",
                },
            ],
        }

        summary = aggregate_trade_ledger(ledger)
        status = build_trade_sync_status(
            summary,
            {
                "ok": True,
                "skipped": False,
                "status": "ok",
                "message_count": 8,
                "appended_count": 0,
                "checked_at_utc": "2026-05-01T00:00:00Z",
            },
        )

        self.assertEqual(status["value"], "已同步")
        self.assertEqual(status["last_trade_date"], "2026-04-30")
        self.assertEqual(status["last_trade_side"], "sell")
        self.assertIn("最近操作 2026-04-30", status["note"])
        self.assertIn("本次扫描 8 条", status["note"])

    def test_not_run_receipt_state_is_not_reported_as_error(self) -> None:
        summary = aggregate_trade_ledger(
            {
                "enabled": True,
                "path": "config/trade_ledger.yaml",
                "trades": [{"date": "2026-05-01", "code": "510300", "side": "buy", "amount_cny": 1000, "price": 5}],
            }
        )

        status = build_trade_sync_status(summary, {"status": "not_run", "appended_count": 0})

        self.assertEqual(status["value"], "按账本")
        self.assertEqual(status["tone"], "neutral")
        self.assertIn("本次未读取飞书回执", status["note"])


if __name__ == "__main__":
    unittest.main()
