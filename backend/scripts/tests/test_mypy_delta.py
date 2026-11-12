"""The type ratchet must distinguish type debt from checker failures."""
import subprocess
import unittest
from unittest.mock import patch

from scripts import mypy_delta


class CheckerFailureTests(unittest.TestCase):
    @patch.object(mypy_delta.subprocess, 'run')
    def test_configuration_failure_is_not_an_empty_success(self, run):
        run.return_value = subprocess.CompletedProcess([], 2, '', 'invalid configuration')
        with self.assertRaisesRegex(RuntimeError, 'invalid configuration'):
            mypy_delta.run_mypy()

    @patch.object(mypy_delta.subprocess, 'run')
    def test_unrecognized_failure_is_not_an_empty_success(self, run):
        run.return_value = subprocess.CompletedProcess([], 1, 'unexpected failure', '')
        with self.assertRaises(RuntimeError):
            mypy_delta.run_mypy()

    @patch.object(mypy_delta.subprocess, 'run')
    def test_missing_checker_reports_an_actionable_failure(self, run):
        run.side_effect = FileNotFoundError('mypy is missing')
        with self.assertRaisesRegex(RuntimeError, 'mypy'):
            mypy_delta.run_mypy()

    @patch.object(mypy_delta.subprocess, 'run')
    def test_type_errors_are_valid_checker_output(self, run):
        output = 'app/example.py:3: error: Bad argument  [arg-type]\n'
        run.return_value = subprocess.CompletedProcess([], 1, output, '')
        self.assertEqual(mypy_delta.run_mypy(), output)
        self.assertEqual(mypy_delta.parse_signatures(output), {'app/example.py::arg-type'})

    @patch.object(mypy_delta, 'run_mypy', side_effect=RuntimeError('checker failed'))
    def test_warn_and_rebaseline_cannot_hide_checker_failure(self, run):
        for args in ([], ['--warn'], ['--rebaseline']):
            with self.subTest(args=args):
                self.assertEqual(mypy_delta.main(args), 2)


class RatchetTests(unittest.TestCase):
    def setUp(self):
        import tempfile
        from pathlib import Path
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'baseline.json'
        self.path.write_text('["app/example.py::arg-type"]\n')
        self.original = self.path.read_bytes()
        patcher = patch.object(mypy_delta, 'BASELINE_PATH', self.path)
        patcher.start()
        self.addCleanup(patcher.stop)

    @patch.object(mypy_delta, 'run_mypy', return_value='')
    def test_clean_result_passes(self, run):
        self.assertEqual(mypy_delta.main([]), 0)

    @patch.object(mypy_delta, 'run_mypy', return_value='app/example.py:99: error: Existing debt  [arg-type]\n')
    def test_existing_signature_passes_despite_line_shift(self, run):
        self.assertEqual(mypy_delta.main([]), 0)

    @patch.object(mypy_delta, 'run_mypy', return_value='app/new.py:4: error: New debt  [assignment]\n')
    def test_new_signature_fails_without_mutating_baseline(self, run):
        self.assertEqual(mypy_delta.main([]), 1)
        self.assertEqual(self.path.read_bytes(), self.original)

    @patch.object(mypy_delta, 'run_mypy', side_effect=RuntimeError('checker failed'))
    def test_failed_rebaseline_preserves_existing_file(self, run):
        self.assertEqual(mypy_delta.main(['--rebaseline']), 2)
        self.assertEqual(self.path.read_bytes(), self.original)

    @patch.object(mypy_delta.subprocess, 'run')
    def test_partial_unrecognized_diagnostics_fail_closed(self, run):
        output = 'app/example.py:3: error: Existing  [arg-type]\napp/new.py:4: error: Unparseable\n'
        run.return_value = subprocess.CompletedProcess([], 1, output, '')
        with self.assertRaises(RuntimeError):
            mypy_delta.run_mypy()


if __name__ == '__main__':
    unittest.main()
