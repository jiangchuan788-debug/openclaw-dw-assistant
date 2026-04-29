import importlib.util
import sys
import types
import unittest
from datetime import datetime
from unittest import mock


MODULE_PATH = "/Users/jiangchuanchen/Desktop/openclaw-dw-assistant/core/repair_strict_7step.py"


def load_module():
    fake_config = types.ModuleType("config")
    fake_config.auto_load_env = object()
    previous_config = sys.modules.get("config")
    sys.modules["config"] = fake_config
    try:
        spec = importlib.util.spec_from_file_location("repair_strict_7step", MODULE_PATH)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        if previous_config is not None:
            sys.modules["config"] = previous_config
        else:
            sys.modules.pop("config", None)


class RepairStrict7StepTests(unittest.TestCase):
    def test_resolve_repair_table_prefers_downstream_warehouse_layer_over_ods(self):
        module = load_module()
        row = {
            "src_db": "ods",
            "src_tbl": "ods_qsq_erp_biz_report",
            "dest_db": "dwd",
            "dest_tbl": "dwd_qsq_erp_biz_report",
        }

        table_name = module.resolve_repair_table(row)

        self.assertEqual(table_name, "dwd_qsq_erp_biz_report")

    def test_resolve_repair_table_prefers_dest_table_when_both_sides_same_layer(self):
        module = load_module()
        row = {
            "src_db": "dwd",
            "src_tbl": "dwd_source_example",
            "dest_db": "dwd",
            "dest_tbl": "dwd_target_example",
        }

        table_name = module.resolve_repair_table(row)

        self.assertEqual(table_name, "dwd_target_example")

    def test_resolve_alert_dt_prefers_begin_date(self):
        module = load_module()
        row = {
            "begin": datetime(2026, 4, 28, 0, 0, 0),
            "end": datetime(2026, 4, 29, 0, 0, 0),
        }

        dt = module.resolve_alert_dt(row, now=datetime(2026, 4, 29, 10, 0, 0))

        self.assertEqual(dt, "2026-04-28")

    def test_resolve_alert_dt_uses_end_minus_one_day_when_begin_missing(self):
        module = load_module()
        row = {
            "begin": None,
            "end": datetime(2026, 4, 29, 0, 0, 0),
        }

        dt = module.resolve_alert_dt(row, now=datetime(2026, 4, 29, 10, 0, 0))

        self.assertEqual(dt, "2026-04-28")

    def test_resolve_alert_dt_falls_back_to_today_when_no_window_available(self):
        module = load_module()
        row = {"begin": None, "end": None}

        dt = module.resolve_alert_dt(row, now=datetime(2026, 4, 29, 10, 0, 0))

        self.assertEqual(dt, "2026-04-29")

    def test_execute_repairs_in_batches_limits_parallel_work_to_five(self):
        module = load_module()
        tasks = [{"table": f"table_{idx}", "dt": "2026-04-26"} for idx in range(12)]
        step3_calls = []
        step4_calls = []

        def fake_step3(batch):
            step3_calls.append([item["table"] for item in batch])
            results = []
            running_instances = []
            for item in batch:
                task = dict(item)
                task["status"] = "success"
                task["instance_id"] = f"instance_{item['table']}"
                results.append(task)
                running_instances.append(
                    {
                        "table": item["table"],
                        "instance_id": task["instance_id"],
                        "task": task,
                    }
                )
            return results, running_instances

        def fake_step4(running_instances):
            step4_calls.append([item["table"] for item in running_instances])
            completed = [dict(item["task"], final_status="success") for item in running_instances]
            return completed, []

        with mock.patch.object(module, "step3_start_repair", side_effect=fake_step3), mock.patch.object(
            module, "step4_wait_and_check", side_effect=fake_step4
        ):
            results, completed_tasks, failed_tasks = module.execute_repairs_in_batches(tasks, max_parallel=5)

        self.assertEqual(
            step3_calls,
            [
                ["table_0", "table_1", "table_2", "table_3", "table_4"],
                ["table_5", "table_6", "table_7", "table_8", "table_9"],
                ["table_10", "table_11"],
            ],
        )
        self.assertEqual(step4_calls, step3_calls)
        self.assertEqual(len(results), 12)
        self.assertEqual(len(completed_tasks), 12)
        self.assertEqual(failed_tasks, [])

    def test_apply_repair_strategy_allows_first_retry_for_suspected_redundant_data(self):
        module = load_module()
        tasks = [
            {
                "table": "ods_qsq_erp_cpop_settlement_order_procedure",
                "dt": "2026-04-27",
                "diff": -4,
            }
        ]

        runnable, manual_review = module.apply_repair_strategy(tasks, {})

        self.assertEqual([item["table"] for item in runnable], ["ods_qsq_erp_cpop_settlement_order_procedure"])
        self.assertEqual(manual_review, [])

    def test_apply_repair_strategy_escalates_repeated_redundant_data_alert_to_manual_review(self):
        module = load_module()
        tasks = [
            {
                "table": "ods_qsq_erp_cpop_settlement_order_procedure",
                "dt": "2026-04-27",
                "diff": -4,
            }
        ]
        strategy_state = {
            "ods_qsq_erp_cpop_settlement_order_procedure": {
                "2026-04-27": {
                    "redundant_retry_done": True,
                    "manual_review_required": False,
                }
            }
        }

        runnable, manual_review = module.apply_repair_strategy(tasks, strategy_state)

        self.assertEqual(runnable, [])
        self.assertEqual(len(manual_review), 1)
        self.assertEqual(manual_review[0]["status"], "skipped_manual_review")
        self.assertIn("人工处理", manual_review[0]["error"])

    def test_generate_tv_report_lists_manual_review_items(self):
        module = load_module()
        manual_review_tasks = [
            {
                "table": "ods_qsq_erp_cpop_settlement_order_procedure",
                "error": "疑似冗余数据，已重跑一次仍未恢复，转人工处理",
            }
        ]

        with mock.patch.object(module, "log"), mock.patch.dict(sys.modules, {"alert.db_config": None}, clear=False):
            report = module.generate_tv_report(
                completed_tasks=[],
                failed_tasks=[],
                fuyan_results=[],
                alerts=[],
                manual_review_tasks=manual_review_tasks,
            )

        self.assertIn("需人工处理", report)
        self.assertIn("ods_qsq_erp_cpop_settlement_order_procedure", report)

    def test_count_remaining_alert_tables_dedupes_by_resolved_table(self):
        module = load_module()

        rows = [
            {
                "src_db": "ods",
                "src_tbl": "ods_qsq_erp_biz_report",
                "dest_db": "dwd",
                "dest_tbl": "dwd_qsq_erp_biz_report",
            },
            {
                "src_db": "ods",
                "src_tbl": "ods_qsq_erp_biz_report",
                "dest_db": "dwd",
                "dest_tbl": "dwd_qsq_erp_biz_report",
            },
            {
                "src_db": "ods",
                "src_tbl": "ods_other",
                "dest_db": "dwd",
                "dest_tbl": "dwd_other",
            },
        ]

        fake_cursor = mock.MagicMock()
        fake_cursor.fetchall.return_value = rows
        fake_conn = mock.MagicMock()
        fake_conn.cursor.return_value.__enter__.return_value = fake_cursor
        fake_db_module = types.ModuleType("alert.db_config")
        fake_db_module.get_db_connection = mock.MagicMock(return_value=fake_conn)

        with mock.patch.dict(sys.modules, {"alert.db_config": fake_db_module}):
            count = module.count_remaining_alert_tables()

        self.assertEqual(count, 2)


if __name__ == "__main__":
    unittest.main()
