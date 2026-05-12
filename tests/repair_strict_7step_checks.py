import importlib.util
import json
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
    def test_resolve_repair_table_prefers_dest_table_over_src_table(self):
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

    def test_resolve_repair_table_prefers_dest_table_for_nonstandard_target_layer_name(self):
        module = load_module()
        row = {
            "src_db": "dwd",
            "src_tbl": "dwd_mkt_sms_cost_monthly",
            "dest_db": "dwd_sec",
            "dest_tbl": "dwd_cst_sms_cost_total",
        }

        table_name = module.resolve_repair_table(row)

        self.assertEqual(table_name, "dwd_cst_sms_cost_total")

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

    def test_step1_scan_alerts_marks_out_of_window_alert_as_manual_review(self):
        module = load_module()
        rows = [
            {
                "id": 1,
                "name": "old alert",
                "src_db": "dwd",
                "src_tbl": "dwd_old_table",
                "dest_db": "dwd",
                "dest_tbl": "dwd_old_table",
                "begin": datetime(2026, 4, 20, 0, 0, 0),
                "end": datetime(2026, 4, 21, 0, 0, 0),
                "diff": 1,
            }
        ]

        fake_cursor = mock.MagicMock()
        fake_cursor.fetchall.return_value = rows
        fake_conn = mock.MagicMock()
        fake_conn.cursor.return_value.__enter__.return_value = fake_cursor
        fake_db_module = types.ModuleType("alert.db_config")
        fake_db_module.get_db_connection = mock.MagicMock(return_value=fake_conn)

        with mock.patch.dict(sys.modules, {"alert.db_config": fake_db_module}), \
            mock.patch.object(module, "log"):
            alerts = module.step1_scan_alerts(now=datetime(2026, 5, 10, 10, 0, 0))

        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["table"], "dwd_old_table")
        self.assertEqual(alerts[0]["status"], "skipped_out_of_window")

    def test_step2_search_in_workflow_prefers_non_datax_candidate_when_names_conflict(self):
        module = load_module()

        def fake_ds_api_get(endpoint):
            if endpoint == "/projects/158514956085248/workflow-definition/wf-1":
                return True, {
                    "processDefinition": {"name": "simontang_test"},
                    "taskDefinitionList": [
                        {
                            "code": "task-datax",
                            "name": "ads_3324_tdtools_match_batch_result",
                            "taskType": "DATAX",
                        },
                        {
                            "code": "task-shell",
                            "name": "ads_3324_tdtools_match_batch_result",
                            "taskType": "SHELL",
                        },
                    ],
                }, ""
            raise AssertionError(endpoint)

        with mock.patch.object(module, "ds_api_get", side_effect=fake_ds_api_get):
            result = module.step2_search_in_workflow("wf-1", "ads_3324_tdtools_match_batch_result")

        self.assertEqual(result["task_code"], "task-shell")
        self.assertEqual(result["task_type"], "SHELL")

    def test_step2_search_in_workflow_does_not_match_sql_only_reference_from_other_task(self):
        module = load_module()

        def fake_ds_api_get(endpoint):
            if endpoint == "/projects/158514956085248/workflow-definition/wf-1":
                return True, {
                    "processDefinition": {"name": "DWD"},
                    "taskDefinitionList": [
                        {
                            "code": "task-main",
                            "name": "dwd_asset_main",
                            "taskType": "SHELL",
                            "taskParams": json.dumps(
                                {"sql": "insert overwrite table dwd_asset_main select * from dwb_asset_info"}
                            ),
                        }
                    ],
                }, ""
            raise AssertionError(endpoint)

        with mock.patch.object(module, "ds_api_get", side_effect=fake_ds_api_get):
            result = module.step2_search_in_workflow("wf-1", "dwb_asset_info")

        self.assertIsNone(result)

    def test_step2_find_locations_preserves_alert_status_and_diff_metadata(self):
        module = load_module()
        alerts = [
            {
                "id": 1,
                "table": "dwd_old_table",
                "dt": "2026-05-02",
                "diff": -49,
                "status": "skipped_out_of_window",
                "error": "超出自动修复窗口",
            }
        ]

        with mock.patch.object(
            module,
            "step2_search_in_workflow",
            return_value={
                "workflow_code": "wf-1",
                "workflow_name": "DWD",
                "task_code": "task-1",
                "task_name": "dwd_old_table",
            },
        ), mock.patch.object(module, "log"):
            tasks = module.step2_find_locations(alerts)

        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]["status"], "skipped_out_of_window")
        self.assertEqual(tasks[0]["error"], "超出自动修复窗口")
        self.assertEqual(tasks[0]["diff"], -49)

    def test_step2_find_locations_allows_scheduled_workflow_when_matching_real_task(self):
        module = load_module()
        alerts = [{"id": 1, "table": "dwd_fox_chatbot_dialog", "dt": "2026-05-11", "diff": 1}]

        def fake_ds_api_get(endpoint):
            if endpoint == "/projects/158514956085248/workflow-definition/158514956979200":
                return True, {
                    "processDefinition": {"name": "DWD"},
                    "taskDefinitionList": [
                        {
                            "code": "task-real",
                            "name": "dwd_fox_chatbot_dialog",
                            "taskType": "SHELL",
                        }
                    ],
                }, ""
            if endpoint == "/projects/158514956085248/schedules?pageNo=1&pageSize=200":
                return True, {
                    "totalList": [
                        {
                            "processDefinitionCode": "158514956979200",
                            "releaseState": "ONLINE",
                        }
                    ]
                }, ""
            raise AssertionError(endpoint)

        with mock.patch.object(module, "ds_api_get", side_effect=fake_ds_api_get), \
            mock.patch.object(module, "log"):
            tasks = module.step2_find_locations(alerts)

        self.assertEqual(tasks[0]["workflow_code"], "158514956979200")
        self.assertEqual(tasks[0]["workflow_name"], "DWD")
        self.assertEqual(tasks[0]["task_code"], "task-real")

    def test_step2_find_locations_skips_scheduled_parent_subprocess_match(self):
        module = load_module()
        alerts = [{"id": 1, "table": "ods_cash_model_model", "dt": "2026-05-10", "diff": 1}]

        def fake_ds_api_get(endpoint):
            if endpoint == "/projects/158514956085248/workflow-definition/158514956979200":
                return True, {
                    "processDefinition": {"name": "DWD"},
                    "taskDefinitionList": [
                        {
                            "code": "task-parent",
                            "name": "ods_cash_model_model",
                            "taskType": "SUB_PROCESS",
                        }
                    ],
                }, ""
            if endpoint == "/projects/158514956085248/workflow-definition/158514957656064":
                return True, {
                    "processDefinition": {"name": "DWD(D-1)"},
                    "taskDefinitionList": [],
                }, ""
            if endpoint == "/projects/158514956085248/workflow-definition/158514958374912":
                return True, {
                    "processDefinition": {"name": "国内-数仓工作流(H-1)"},
                    "taskDefinitionList": [],
                }, ""
            if endpoint == "/projects/158514956085248/workflow-definition/158514957337600":
                return True, {
                    "processDefinition": {"name": "国内-数仓工作流(D-1)"},
                    "taskDefinitionList": [],
                }, ""
            if endpoint == "/projects/158514956085248/workflow-definition/158514957297664":
                return True, {
                    "processDefinition": {"name": "DWB"},
                    "taskDefinitionList": [],
                }, ""
            if endpoint == "/projects/158514956085248/workflow-definition/158514957701120":
                return True, {
                    "processDefinition": {"name": "DWB(D-1)"},
                    "taskDefinitionList": [],
                }, ""
            if endpoint == "/projects/158514956085248/workflow-definition/158514957779968":
                return True, {
                    "processDefinition": {"name": "DWS"},
                    "taskDefinitionList": [],
                }, ""
            if endpoint == "/projects/158514956085248/workflow-definition/158514958004224":
                return True, {
                    "processDefinition": {"name": "DWS(D-1)"},
                    "taskDefinitionList": [],
                }, ""
            if endpoint == "/projects/158514956085248/workflow-definition?pageNo=1&pageSize=100":
                return True, {"totalList": [], "totalPage": 1}, ""
            if endpoint == "/projects/158514956085248/schedules?pageNo=1&pageSize=200":
                return True, {
                    "totalList": [
                        {
                            "processDefinitionCode": "158514956979200",
                            "releaseState": "ONLINE",
                        }
                    ]
                }, ""
            raise AssertionError(endpoint)

        with mock.patch.object(module, "ds_api_get", side_effect=fake_ds_api_get), \
            mock.patch.object(module, "log"):
            tasks = module.step2_find_locations(alerts)

        self.assertEqual(tasks[0]["workflow_code"], "")
        self.assertEqual(tasks[0]["workflow_name"], "未找到")

    def test_get_remaining_alert_tables_excludes_out_of_window_rows_by_begin_end(self):
        module = load_module()
        rows = [
            {
                "src_db": "ods",
                "src_tbl": "ods_long_window_table",
                "dest_db": "dwd",
                "dest_tbl": "dwd_long_window_table",
                "begin": datetime(2026, 2, 8, 0, 0, 0),
                "end": datetime(2026, 5, 9, 0, 0, 0),
            },
            {
                "src_db": "ods",
                "src_tbl": "ods_recent_table",
                "dest_db": "dwd",
                "dest_tbl": "dwd_recent_table",
                "begin": datetime(2026, 5, 9, 0, 0, 0),
                "end": datetime(2026, 5, 10, 0, 0, 0),
            },
        ]

        fake_cursor = mock.MagicMock()
        fake_cursor.fetchall.return_value = rows
        fake_conn = mock.MagicMock()
        fake_conn.cursor.return_value.__enter__.return_value = fake_cursor
        fake_db_module = types.ModuleType("alert.db_config")
        fake_db_module.get_db_connection = mock.MagicMock(return_value=fake_conn)

        with mock.patch.dict(sys.modules, {"alert.db_config": fake_db_module}):
            tables = module.get_remaining_alert_tables(now=datetime(2026, 5, 10, 10, 0, 0))

        self.assertEqual(tables, {"dwd_recent_table"})

    def test_summarize_repair_outcome_keeps_out_of_window_alert_in_manual_review(self):
        module = load_module()
        alerts = [
            {
                "id": 1,
                "table": "dwd_old_table",
                "dt": "2026-05-02",
                "status": "skipped_out_of_window",
                "error": "告警窗口 begin=2026-05-02, end=2026-05-09，begin 早于自动修复窗口起点 2026-05-04，转人工处理",
            }
        ]
        manual_review_tasks = [
            {
                "table": "dwd_old_table",
                "dt": "2026-05-02",
                "status": "skipped_out_of_window",
                "error": "告警窗口 begin=2026-05-02, end=2026-05-09，begin 早于自动修复窗口起点 2026-05-04，转人工处理",
            }
        ]

        summary = module.summarize_repair_outcome(
            alerts=alerts,
            completed_tasks=[],
            failed_tasks=[],
            manual_review_tasks=manual_review_tasks,
            remaining_tables=set(),
        )

        self.assertEqual(summary["resolved_count"], 0)
        self.assertEqual(summary["remaining_count"], 1)
        self.assertEqual(summary["manual_review_count"], 1)
        self.assertEqual(summary["resolved_tasks"], [])
        self.assertEqual(summary["remaining_tasks"][0]["table"], "dwd_old_table")
        self.assertEqual(summary["remaining_tasks"][0]["result"], "manual_review")

    def test_execute_repairs_in_batches_limits_parallel_work_to_four(self):
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
            results, completed_tasks, failed_tasks = module.execute_repairs_in_batches(tasks, max_parallel=4)

        self.assertEqual(
            step3_calls,
            [
                ["table_0", "table_1", "table_2", "table_3"],
                ["table_4", "table_5", "table_6", "table_7"],
                ["table_8", "table_9", "table_10", "table_11"],
            ],
        )
        self.assertEqual(step4_calls, step3_calls)
        self.assertEqual(len(results), 12)
        self.assertEqual(len(completed_tasks), 12)
        self.assertEqual(failed_tasks, [])

    def test_step3_start_repair_skips_when_scheduler_instance_is_running(self):
        module = load_module()
        tasks = [
            {
                "table": "国内-数仓工作流(H-1)_target",
                "dt": "2026-05-12",
                "workflow_code": "wf-hourly",
                "workflow_name": "国内-数仓工作流(H-1)",
                "task_code": "task-1",
                "task_name": "dwd_hourly_target",
            }
        ]

        with mock.patch.object(module, "find_conflicting_running_instance", return_value={"id": 321, "commandType": "SCHEDULER", "state": "RUNNING_EXECUTION"}), \
            mock.patch.object(module, "ds_api_post") as mocked_post, \
            mock.patch.object(module, "log"), \
            mock.patch("time.sleep"):
            results, running_instances = module.step3_start_repair(tasks)

        mocked_post.assert_not_called()
        self.assertEqual(results[0]["status"], "failed")
        self.assertIn("运行中实例", results[0]["error"])
        self.assertEqual(running_instances, [])

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
        self.assertIn("底层是否需要删数", manual_review[0]["error"])

    def test_generate_tv_report_lists_manual_review_items(self):
        module = load_module()
        summary = {
            "initial_alert_count": 1,
            "resolved_count": 0,
            "remaining_count": 1,
            "manual_review_count": 1,
            "rerun_tasks": [],
            "resolved_tasks": [],
            "remaining_tasks": [
                {
                    "table": "ods_qsq_erp_cpop_settlement_order_procedure",
                    "error": "疑似当前层数据多于底层，重跑一次后仍未恢复，建议检查底层是否需要删数，并人工判断修复",
                }
            ],
            "post_fuyan_remaining_tables": {"ods_qsq_erp_cpop_settlement_order_procedure"},
        }

        with mock.patch.object(module, "log"):
            report = module.generate_tv_report(summary, [])

        self.assertIn("需人工处理", report)
        self.assertIn("ods_qsq_erp_cpop_settlement_order_procedure", report)
        self.assertIn("底层是否需要删数", report)

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

    def test_summarize_repair_outcome_uses_post_fuyan_remaining_tables(self):
        module = load_module()
        alerts = [
            {"table": "dwd_fox_call_history", "dt": "2026-04-21"},
            {"table": "dwd_asset_biz_report", "dt": "2026-04-21"},
        ]
        completed_tasks = [
            {"table": "dwd_fox_call_history", "dt": "2026-04-21"},
            {"table": "dwd_asset_biz_report", "dt": "2026-04-21"},
        ]
        failed_tasks = []
        manual_review_tasks = []
        remaining_tables = {"dwd_asset_biz_report"}

        summary = module.summarize_repair_outcome(
            alerts=alerts,
            completed_tasks=completed_tasks,
            failed_tasks=failed_tasks,
            manual_review_tasks=manual_review_tasks,
            remaining_tables=remaining_tables,
        )

        self.assertEqual(summary["initial_alert_count"], 2)
        self.assertEqual(summary["resolved_count"], 1)
        self.assertEqual(summary["remaining_count"], 1)
        self.assertEqual(
            [item["table"] for item in summary["resolved_tasks"]],
            ["dwd_fox_call_history"],
        )
        self.assertEqual(
            [item["table"] for item in summary["remaining_tasks"]],
            ["dwd_asset_biz_report"],
        )
        self.assertEqual(summary["manual_review_count"], 1)
        self.assertEqual(
            [item["table"] for item in summary["rerun_tasks"]],
            ["dwd_fox_call_history", "dwd_asset_biz_report"],
        )

    def test_summarize_repair_outcome_marks_redundant_remaining_task_with_delete_hint(self):
        module = load_module()
        alerts = [{"table": "dwd_mkt_sms_cost_monthly", "dt": "2026-04-29", "diff": -49}]
        completed_tasks = [{"table": "dwd_mkt_sms_cost_monthly", "dt": "2026-04-29", "diff": -49}]
        failed_tasks = []
        manual_review_tasks = []
        remaining_tables = {"dwd_mkt_sms_cost_monthly"}

        summary = module.summarize_repair_outcome(
            alerts=alerts,
            completed_tasks=completed_tasks,
            failed_tasks=failed_tasks,
            manual_review_tasks=manual_review_tasks,
            remaining_tables=remaining_tables,
        )

        self.assertEqual(summary["remaining_count"], 1)
        self.assertIn("底层是否需要删数", summary["remaining_tasks"][0]["error"])

    def test_summarize_repair_outcome_keeps_manual_review_task_as_remaining_when_no_remaining_tables(self):
        module = load_module()
        alerts = [{"table": "dwd_user_coupon", "dt": "2026-04-29"}]
        completed_tasks = []
        failed_tasks = []
        manual_review_tasks = [
            {
                "table": "dwd_user_coupon",
                "dt": "2026-04-29",
                "status": "skipped_manual_review",
                "error": "需人工处理",
            }
        ]

        summary = module.summarize_repair_outcome(
            alerts=alerts,
            completed_tasks=completed_tasks,
            failed_tasks=failed_tasks,
            manual_review_tasks=manual_review_tasks,
            remaining_tables=set(),
        )

        self.assertEqual(summary["resolved_count"], 0)
        self.assertEqual(summary["remaining_count"], 1)
        self.assertEqual(summary["remaining_tasks"][0]["table"], "dwd_user_coupon")

    def test_summarize_repair_outcome_fills_default_error_for_failed_remaining_task(self):
        module = load_module()
        alerts = [{"table": "dwd_user_individual", "dt": "2026-05-12"}]
        completed_tasks = [{"table": "dwd_user_individual", "dt": "2026-05-12", "end_time": "2026-05-12 14:12:07"}]
        failed_tasks = [{"table": "dwd_user_individual", "dt": "2026-05-12", "final_status": "failed", "error": ""}]

        summary = module.summarize_repair_outcome(
            alerts=alerts,
            completed_tasks=completed_tasks,
            failed_tasks=failed_tasks,
            manual_review_tasks=[],
            remaining_tables={"dwd_user_individual"},
        )

        self.assertEqual(summary["remaining_count"], 1)
        self.assertEqual(summary["remaining_tasks"][0]["table"], "dwd_user_individual")
        self.assertEqual(summary["remaining_tasks"][0]["result"], "manual_review")
        self.assertEqual(summary["remaining_tasks"][0]["error"], "复验完成后告警仍存在，需人工处理")

    def test_main_skips_fuyan_when_no_repairs_were_started(self):
        module = load_module()
        alerts = [{"table": "dwd_fox_call_history", "dt": "2026-04-21"}]
        unresolved_tables = {"dwd_fox_call_history"}

        with mock.patch.object(module, "step1_scan_alerts", return_value=alerts), mock.patch.object(
            module, "step2_find_locations", return_value=[{"table": "dwd_fox_call_history", "dt": "2026-04-21"}]
        ), mock.patch.object(
            module, "load_manual_review_state", return_value={}
        ), mock.patch.object(
            module, "apply_repair_strategy", return_value=([{"table": "dwd_fox_call_history", "dt": "2026-04-21"}], [])
        ), mock.patch.object(
            module, "execute_repairs_in_batches", return_value=([{"table": "dwd_fox_call_history"}], [], [])
        ), mock.patch.object(
            module, "record_redundant_retry_attempt"
        ), mock.patch.object(
            module, "record_manual_review_tasks"
        ), mock.patch.object(
            module, "save_manual_review_state"
        ), mock.patch.object(
            module, "step5_execute_fuyan"
        ) as mock_step5, mock.patch.object(
            module, "evaluate_repair_outcome"
        ) as mock_evaluate, mock.patch.object(
            module, "get_remaining_alert_tables", return_value=unresolved_tables
        ), mock.patch.object(
            module, "step6_save_report"
        ) as mock_step6, mock.patch.object(module, "log"):
            module.main()

        mock_step5.assert_not_called()
        mock_evaluate.assert_not_called()
        summary = mock_step6.call_args[0][4]
        final_fuyan_results = mock_step6.call_args[0][3]
        self.assertEqual(final_fuyan_results, [])
        self.assertEqual(summary["remaining_count"], 1)
        self.assertEqual(summary["resolved_count"], 0)

    def test_generate_tv_report_describes_resolved_and_manual_review_after_fuyan(self):
        module = load_module()
        summary = {
            "initial_alert_count": 2,
            "resolved_count": 1,
            "remaining_count": 1,
            "manual_review_count": 1,
            "rerun_tasks": [
                {
                    "table": "dwd_fox_call_history",
                    "dt": "2026-04-21",
                    "instance_id": 806135,
                    "end_time": "2026-04-29 14:05:14",
                },
                {
                    "table": "dwd_asset_biz_report",
                    "dt": "2026-04-21",
                    "instance_id": 806136,
                    "end_time": "2026-04-29 14:05:03",
                },
            ],
            "resolved_tasks": [
                {"table": "dwd_fox_call_history", "dt": "2026-04-21"}
            ],
            "remaining_tasks": [
                {
                    "table": "dwd_asset_biz_report",
                    "dt": "2026-04-21",
                    "error": "疑似当前层数据多于底层，重跑一次后仍未恢复，建议检查底层是否需要删数，并人工判断修复",
                }
            ],
            "post_fuyan_remaining_tables": {"dwd_asset_biz_report"},
        }
        fuyan_results = [
            {"name": "每日复验全级别数据(W-1)", "status": "success", "id": 806145}
        ]

        with mock.patch.object(module, "log"):
            report = module.generate_tv_report(summary, fuyan_results)

        self.assertIn("初始去重告警: 2 个", report)
        self.assertIn("复验后已消失: 1 个", report)
        self.assertIn("复验后仍存在: 1 个", report)
        self.assertIn("当前未处理告警表: 1 个", report)
        self.assertIn("本次已重跑任务", report)
        self.assertIn("实例ID: 806135", report)
        self.assertIn("实例ID: 806136", report)
        self.assertIn("dwd_fox_call_history", report)
        self.assertIn("dwd_asset_biz_report", report)
        self.assertIn("底层是否需要删数", report)

    def test_evaluate_repair_outcome_queries_remaining_tables_after_fuyan_wait(self):
        module = load_module()
        completed_tasks = [{"table": "dwd_fox_call_history", "dt": "2026-04-21"}]
        failed_tasks = []
        alerts = [{"table": "dwd_fox_call_history", "dt": "2026-04-21"}]
        fuyan_results = [{"name": "每日复验全级别数据(W-1)", "status": "success", "id": 806145}]

        with mock.patch.object(
            module,
            "wait_for_fuyan_results",
            return_value=fuyan_results,
        ) as wait_mock, mock.patch.object(
            module,
            "get_remaining_alert_tables",
            return_value=set(),
        ) as remaining_mock:
            summary, final_fuyan_results = module.evaluate_repair_outcome(
                alerts=alerts,
                completed_tasks=completed_tasks,
                failed_tasks=failed_tasks,
                manual_review_tasks=[],
                fuyan_results=fuyan_results,
            )

        wait_mock.assert_called_once_with(fuyan_results)
        remaining_mock.assert_called_once()
        self.assertEqual(final_fuyan_results, fuyan_results)
        self.assertEqual(summary["resolved_count"], 1)
        self.assertEqual(summary["remaining_count"], 0)

    def test_step5_execute_fuyan_falls_back_to_process_style_when_workflow_style_fails(self):
        module = load_module()
        module.FUYAN_WORKFLOWS = [
            {"name": "每日复验全级别数据(W-1)", "code": "wf-daily", "level": "all"}
        ]
        attempts = []

        def fake_ds_api_post(endpoint, data):
            attempts.append((endpoint, dict(data)))
            if endpoint.endswith("start-workflow-instance"):
                return False, {}, "workflow style unsupported"
            return True, {"data": [24680]}, ""

        with mock.patch.object(module, "ds_api_post", side_effect=fake_ds_api_post), \
            mock.patch.object(module, "log"), \
            mock.patch.object(module.os, "makedirs"), \
            mock.patch("builtins.open", mock.mock_open()):
            results = module.step5_execute_fuyan(
                completed_tasks=[{"table": "dwb_asset_info"}],
                failed_tasks=[],
                alerts=[{"table": "dwb_asset_info"}],
            )

        self.assertEqual(len(attempts), 2)
        self.assertTrue(attempts[0][0].endswith("start-workflow-instance"))
        self.assertTrue(attempts[1][0].endswith("start-process-instance"))
        self.assertEqual(results[0]["status"], "success")
        self.assertEqual(results[0]["id"], 24680)

    def test_step5_execute_fuyan_skips_blocked_level1_recheck_workflow(self):
        module = load_module()
        module.FUYAN_WORKFLOWS = [
            {"name": "每小时复验1级表数据(D-1)", "code": "wf-l1", "level": "1"},
        ]
        module.BLOCKED_FUYAN_WORKFLOW_NAMES = {"每小时复验1级表数据(D-1)"}

        with mock.patch.object(module, "ds_api_post") as post_mock, \
            mock.patch.object(module, "log"), \
            mock.patch.object(module.os, "makedirs"), \
            mock.patch("builtins.open", mock.mock_open()):
            results = module.step5_execute_fuyan(
                completed_tasks=[{"table": "dwb_asset_info"}],
                failed_tasks=[],
                alerts=[{"table": "dwb_asset_info"}],
            )

        post_mock.assert_not_called()
        self.assertEqual(results, [])


if __name__ == "__main__":
    unittest.main()
