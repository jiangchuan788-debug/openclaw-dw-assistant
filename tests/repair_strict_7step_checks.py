import importlib.util
import sys
import types
import unittest
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


if __name__ == "__main__":
    unittest.main()
