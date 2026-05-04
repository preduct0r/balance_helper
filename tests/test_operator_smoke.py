from __future__ import annotations

import contextlib
import io
import runpy
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class OperatorSmokeTests(unittest.TestCase):
    def test_smoke_workflow_outputs_operator_report(self) -> None:
        namespace = runpy.run_path(str(ROOT / "scripts/smoke_operator_workflow.py"), run_name="__test__")
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            exit_code = namespace["main"]()
        report = output.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Smoke workflow", report)
        self.assertIn("Чек-лист", report)
        self.assertIn("Черновик", report)
        self.assertIn("Digest", report)
        self.assertIn("[НУЖНО УТОЧНИТЬ]", report)


if __name__ == "__main__":
    unittest.main()

