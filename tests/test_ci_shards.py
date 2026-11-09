"""Parallel CI must execute the entire suite once and preserve failures."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from test_module_api import load_tool

runner = load_tool('run_ci_tests')


class CIShardTests(unittest.TestCase):
    def test_all_files_including_nested_tests_run_exactly_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / 'tests' / 'nested'
            folder.mkdir(parents=True)
            expected = set()
            for i in range(23):
                path = (folder if i % 2 else folder.parent) / ('test_' + str(i) + '.py')
                path.touch(); expected.add(path)
            other = folder / 'addon_test.py'; other.touch(); expected.add(other)
            assigned = [p for shard in range(4) for p in runner.shard_files(root, shard, 4)]
            self.assertEqual(set(assigned), expected)
            self.assertEqual(len(assigned), len(expected))

    def test_invalid_shard_fails(self):
        for shard, total in ((-1, 4), (4, 4), (0, 0)):
            with self.assertRaises(ValueError): runner.shard_files(runner.ROOT, shard, total)

    def test_pytest_failure_propagates_to_ci(self):
        with patch('sys.argv', ['run_ci_tests.py', '--shard', '0', '--total', '4']):
            with patch.object(runner.subprocess, 'run') as process:
                process.return_value.returncode = 1
                with self.assertRaises(SystemExit) as failure: runner.main()
                self.assertEqual(failure.exception.code, 1)
