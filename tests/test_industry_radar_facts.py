from __future__ import annotations

from types import SimpleNamespace
import unittest

from src.daily_news_bot.industry_radar import build_industry_radar


class IndustryRadarFactsTest(unittest.TestCase):
    def test_default_fact_library_is_kept_when_custom_config_overrides_one_field(self) -> None:
        radar = build_industry_radar(
            {
                "industry_radar": {
                    "items": [
                        {
                            "id": "semiconductor_materials",
                            "watch": "自定义：只看价格、订单和出口限制。",
                        }
                    ]
                }
            },
            [],
            [{"theme_keys": ["semiconductor"]}],
            [{"theme_key": "semiconductor", "priority": "高", "score": 9}],
        )

        row = next(item for item in radar["rows"] if item["id"] == "semiconductor_materials")
        self.assertEqual(row["watch"], "自定义：只看价格、订单和出口限制。")
        self.assertIn("不可替代", row["fact_summary"])
        self.assertIn("确认", row["facts"])
        self.assertGreaterEqual(row["score_card"]["policy"], 1)
        self.assertGreaterEqual(row["score_card"]["supply"], 1)

    def test_fact_library_uses_news_hits_for_daily_attention(self) -> None:
        cluster = SimpleNamespace(
            theme="半导体材料",
            tags=["semiconductor"],
            representative=SimpleNamespace(
                title="出口管制与库存紧张推高六氟化钨价格",
                summary="半导体前驱体出现供应约束和订单排队。",
                content="",
            ),
            articles=[],
        )

        radar = build_industry_radar({}, [cluster], [], [])
        row = next(item for item in radar["rows"] if item["id"] == "semiconductor_materials")

        self.assertEqual(row["status"], "今日关注")
        self.assertIn("六氟化钨", row["hits"])
        self.assertGreaterEqual(row["score_card"]["news"], 1)

    def test_sub_industry_radar_binds_to_portfolio_and_candidate_pool(self) -> None:
        cluster = SimpleNamespace(
            theme="电子特气",
            tags=["semiconductor"],
            representative=SimpleNamespace(
                title="电子级氦气供应紧张，半导体客户长协推进",
                summary="气源和提纯产线成为新约束。",
                content="",
            ),
            articles=[],
        )

        radar = build_industry_radar(
            {
                "holdings": [{"name": "半导体ETF", "code": "512480"}],
            },
            [cluster],
            [],
            [
                {
                    "theme_key": "semiconductor",
                    "priority": "高",
                    "score": 10,
                    "instruments": [{"name": "科创芯片ETF", "code": "588200"}],
                }
            ],
        )
        row = next(item for item in radar["rows"] if item["id"] == "helium_supply_chain")

        self.assertEqual(row["status"], "今日关注")
        self.assertIn("氦气", row["hits"])
        self.assertIn("半导体ETF(512480)", row["binding_summary"])
        self.assertIn("科创芯片ETF(588200)", row["binding_summary"])
        self.assertGreaterEqual(len(radar["rows"]), 18)

    def test_optical_interconnect_is_tracked_as_ai_infra_sub_industry(self) -> None:
        cluster = SimpleNamespace(
            theme="AI数据中心互联",
            tags=["ai", "semiconductor"],
            representative=SimpleNamespace(
                title="空心光纤、CPO与OCS推动AI数据中心光通信互联升级",
                summary="光模块和高速互联降低延迟、功耗和存储压力，成为算力集群新瓶颈。",
                content="",
            ),
            articles=[],
        )

        radar = build_industry_radar({}, [cluster], [], [])
        row = next(item for item in radar["rows"] if item["id"] == "optical_interconnect")

        self.assertEqual(row["status"], "今日关注")
        self.assertIn("空心光纤", row["hits"])
        self.assertIn("CPO", row["hits"])
        self.assertIn("AI数据中心", row["why"])
        self.assertIn("客户导入", row["verify"])
        self.assertGreaterEqual(row["score_card"]["news"], 1)

    def test_additional_industry_lines_cover_robotics_defense_chemicals_and_coal(self) -> None:
        cases = [
            (
                "embodied_robotics",
                "具身智能机器人、伺服系统和减速器订单放量",
                "机器人本体、传感器和执行器进入客户验证。",
                ["具身智能", "伺服"],
                "客户验证",
            ),
            (
                "defense_low_altitude",
                "低空经济、无人机和军工电子订单加速",
                "卫星通信、航空发动机和无人系统成为政策重点。",
                ["低空经济", "无人机"],
                "订单",
            ),
            (
                "chemicals_fertilizer",
                "化肥、农药和硫酸价格受出口管制影响",
                "尿素和磷化工库存下降，海外价格走强。",
                ["化肥", "硫酸"],
                "价格",
            ),
            (
                "coal_power_security",
                "煤炭和火电容量电价支撑电力安全",
                "迎峰度夏用电负荷抬升，煤电调峰价值提升。",
                ["煤炭", "容量电价"],
                "用电负荷",
            ),
        ]

        for row_id, title, summary, expected_hits, expected_verify in cases:
            with self.subTest(row_id=row_id):
                cluster = SimpleNamespace(
                    theme=title,
                    tags=[],
                    representative=SimpleNamespace(title=title, summary=summary, content=""),
                    articles=[],
                )

                radar = build_industry_radar({}, [cluster], [], [])
                row = next(item for item in radar["rows"] if item["id"] == row_id)

                self.assertEqual(row["status"], "今日关注")
                for hit in expected_hits:
                    self.assertIn(hit, row["hits"])
                self.assertIn(expected_verify, row["verify"])

    def test_industry_radar_marks_portfolio_gap_before_new_buy_pool_expansion(self) -> None:
        cluster = SimpleNamespace(
            theme="具身智能机器人订单",
            tags=[],
            representative=SimpleNamespace(
                title="具身智能机器人和伺服系统进入客户验证",
                summary="减速器、执行器和传感器订单开始放量。",
                content="",
            ),
            articles=[],
        )

        radar_without_position = build_industry_radar({}, [cluster], [], [])
        gap_row = next(item for item in radar_without_position["rows"] if item["id"] == "embodied_robotics")

        self.assertEqual(gap_row["coverage_status"], "组合缺口")
        self.assertIn("先记录观察", gap_row["coverage_note"])
        self.assertIn("组合缺口", gap_row["binding_summary"])

        radar_with_position = build_industry_radar(
            {
                "holdings": [{"name": "人工智能ETF", "code": "011840"}],
                "industry_radar": {
                    "items": [
                        {
                            "id": "embodied_robotics",
                            "instruments": ["011840"],
                        }
                    ]
                },
            },
            [cluster],
            [],
            [],
        )
        held_row = next(item for item in radar_with_position["rows"] if item["id"] == "embodied_robotics")

        self.assertEqual(held_row["coverage_status"], "持仓复核")
        self.assertIn("不自动加仓", held_row["coverage_note"])
        self.assertIn("持仓复核", held_row["binding_summary"])


if __name__ == "__main__":
    unittest.main()
