"""Offline CLI regressions; the optimizer is a local executable fixture."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "record_wasm_sizes.py"
FAKE = '''#!/usr/bin/env python3
import json, os, pathlib, sys
args = sys.argv[1:]
pathlib.Path("arguments.json").write_text(json.dumps(args))
out = pathlib.Path(args[args.index("--wasm-out") + 1])
if out.exists():
    sys.exit(91)
mode = os.environ.get("OPTIMIZER_MODE", "success")
if mode == "partial":
    out.write_bytes(b"partial")
if mode in ("fail", "partial"):
    sys.exit(23)
if mode != "missing":
    out.write_bytes(b"fresh")
'''


class RecordWasmSizesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "abi").mkdir()
        self.record = self.root / "abi/wasm-sizes.json"
        self.original = b'{"other": 123, "sample": 999}\n'
        self.record.write_bytes(self.original)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        executable = self.bin / "stellar"
        executable.write_text(FAKE)
        executable.chmod(0o755)
        self.wasm = self.root / "wasm"
        self.wasm.mkdir()
        self.output = self.wasm / "promiscope_sample.optimized.wasm"
        self.output.write_bytes(b"old and stale")
        self.env = dict(os.environ, PATH=str(self.bin) + os.pathsep + os.environ["PATH"], WASM=str(self.wasm))

    def run_cli(self, mode="success", args=("sample",)):
        return subprocess.run([sys.executable, str(SCRIPT), *args], cwd=self.root,
                              env=dict(self.env, OPTIMIZER_MODE=mode),
                              capture_output=True, text=True, timeout=10)

    def test_success_replaces_stale_artifact_and_preserves_other_entries(self):
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(self.record.read_text()), {"other": 123, "sample": 5})
        self.assertEqual(self.output.read_bytes(), b"fresh")

    def test_arguments_with_spaces_and_shell_metacharacters_are_literal(self):
        self.wasm = self.root / "wasm files; echo UNEXPECTED"
        self.wasm.mkdir()
        self.output = self.wasm / "promiscope_sample.optimized.wasm"
        self.env["WASM"] = str(self.wasm)
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads((self.root / "arguments.json").read_text()),
                         ["contract", "optimize", "--wasm", str(self.wasm / "promiscope_sample.wasm"),
                          "--wasm-out", str(self.output)])
        self.assertNotIn("UNEXPECTED\n", result.stdout)

    def test_optimizer_failure_preserves_json_and_removes_stale_output(self):
        result = self.run_cli("fail")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.record.read_bytes(), self.original)
        self.assertFalse(self.output.exists())

    def test_partial_output_from_failed_optimizer_is_not_recorded(self):
        result = self.run_cli("partial")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.record.read_bytes(), self.original)

    def test_success_without_output_does_not_reuse_stale_size(self):
        result = self.run_cli("missing")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.record.read_bytes(), self.original)

    def test_failure_does_not_create_json(self):
        self.record.unlink()
        self.assertNotEqual(self.run_cli("fail").returncode, 0)
        self.assertFalse(self.record.exists())

    def test_first_success_creates_json_without_previous_output(self):
        self.record.unlink()
        self.output.unlink()
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(self.record.read_text()), {"sample": 5})

    def test_missing_optimizer_does_not_write_json(self):
        self.env["PATH"] = str(self.root / "no-executables")
        result = self.run_cli()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.record.read_bytes(), self.original)

    def test_missing_contract_shows_usage_without_writing(self):
        result = self.run_cli(args=())
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Usage:", result.stderr)
        self.assertEqual(self.record.read_bytes(), self.original)


if __name__ == "__main__":
    unittest.main()
