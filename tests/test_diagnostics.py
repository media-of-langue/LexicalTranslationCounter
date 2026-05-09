import os
import io
import sys
import unittest
from contextlib import redirect_stdout
from unittest import mock


TEST_ROOT = os.path.dirname(os.path.abspath(__file__))
SRC_ROOT = os.path.normpath(os.path.join(TEST_ROOT, "..", "src"))
if SRC_ROOT not in sys.path:
    sys.path.insert(0, SRC_ROOT)

from ltc import diagnostics
from ltc.cli import doctor


class DiagnosticsTest(unittest.TestCase):
    def test_probe_module_ok(self):
        with mock.patch("ltc.diagnostics.importlib.import_module", return_value=object()):
            result = diagnostics.probe_module("example.module")
        self.assertTrue(result.ok)
        self.assertEqual(result.name, "example.module")

    def test_probe_module_runs_runtime_check_when_available(self):
        runtime_check = mock.Mock()
        module = mock.Mock(runtime_check=runtime_check)
        with mock.patch("ltc.diagnostics.importlib.import_module", return_value=module):
            result = diagnostics.probe_module("example.module")
        self.assertTrue(result.ok)
        runtime_check.assert_called_once_with()

    def test_probe_module_includes_runtime_metadata_note(self):
        module = mock.Mock(
            runtime_check=mock.Mock(),
            runtime_metadata=mock.Mock(return_value={"note": "smoke/dev model"}),
        )
        with mock.patch("ltc.diagnostics.importlib.import_module", return_value=module):
            result = diagnostics.probe_module("example.module")
        self.assertTrue(result.ok)
        self.assertEqual(result.note, "smoke/dev model")

    def test_probe_module_failure(self):
        with mock.patch(
            "ltc.diagnostics.importlib.import_module",
            side_effect=ModuleNotFoundError("missing"),
        ):
            result = diagnostics.probe_module("example.module")
        self.assertFalse(result.ok)
        self.assertEqual(result.error_type, "ModuleNotFoundError")
        self.assertIn("missing", result.error_message)

    def test_probe_module_runtime_check_failure_is_reported(self):
        module = mock.Mock(runtime_check=mock.Mock(side_effect=RuntimeError("boom")))
        with mock.patch("ltc.diagnostics.importlib.import_module", return_value=module):
            result = diagnostics.probe_module("example.module")
        self.assertFalse(result.ok)
        self.assertEqual(result.error_type, "RuntimeError")
        self.assertIn("boom", result.error_message)

    def test_run_module_diagnostics_honors_selected_groups(self):
        fake_groups = {"demo": ["a", "b"]}
        with mock.patch.object(diagnostics, "MODULE_GROUPS", fake_groups):
            with mock.patch.object(
                diagnostics, "probe_module", side_effect=lambda name: name
            ) as probe:
                results = diagnostics.run_module_diagnostics(groups=("demo",))
        self.assertEqual(results, {"demo": ["a", "b"]})
        self.assertEqual(probe.call_count, 2)


class DoctorCliTest(unittest.TestCase):
    def test_format_text_contains_summary(self):
        results = {
            "demo": [
                diagnostics.DiagnosticResult(name="a", ok=True, note="smoke/dev model"),
                diagnostics.DiagnosticResult(
                    name="b",
                    ok=False,
                    error_type="ModuleNotFoundError",
                    error_message="missing",
                ),
            ]
        }
        text = doctor.format_text(results)
        self.assertIn("[demo]", text)
        self.assertIn("smoke/dev model", text)
        self.assertIn("summary: 1 ok, 1 failed", text)

    def test_fail_on_error_exits_nonzero(self):
        with mock.patch.object(
            doctor,
            "run_module_diagnostics",
            return_value={
                "demo": [
                    diagnostics.DiagnosticResult(
                        name="a",
                        ok=False,
                        error_type="RuntimeError",
                        error_message="boom",
                    )
                ]
            },
        ):
            with redirect_stdout(io.StringIO()):
                with self.assertRaises(SystemExit) as ctx:
                    doctor.main(["ltc-doctor", "--fail-on-error"])
        self.assertEqual(ctx.exception.code, 1)
