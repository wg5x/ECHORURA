from __future__ import annotations

import unittest

from api.rule_audit_scheduler import run_scheduler


class RuleAuditSchedulerTest(unittest.TestCase):
    def test_run_scheduler_runs_audit_repeatedly_until_max_runs(self) -> None:
        calls: list[int] = []
        sleeps: list[float] = []

        run_scheduler(
            run_once=lambda: calls.append(len(calls) + 1),
            interval_seconds=30,
            max_runs=2,
            sleep=sleeps.append,
        )

        self.assertEqual(calls, [1, 2])
        self.assertEqual(sleeps, [30])


if __name__ == "__main__":
    unittest.main()
