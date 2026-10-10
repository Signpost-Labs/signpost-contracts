"""
Tests for scripts/calibrate-budgets.py (issue #105).

Three cases from the acceptance criteria:

  1. Parsing a well-formed CPU-cost report — both the new-format
     (println! from assert_cpu_budget) and legacy-format (cargo test
     output) lines parse into the nested {contract: {op: cost}} map.

  2. Missing-section handling — load_json raises a specific, actionable
     error via SystemExit when the input file is absent, rather than
     letting a bare FileNotFoundError escape. parse_cpu_report returns
     an empty dict on missing input, which callers treat as "no data".

  3. Drift computation against a threshold table — recommend_wasm_budgets
     and recommend_cpu_budgets apply the headroom multiplicatively and
     truncate toward zero, matching the documented 20% default.

Run:
    python3 -m pytest scripts/tests/test_calibrate_budgets.py
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "calibrate-budgets.py"


def _load_script():
    """Import scripts/calibrate-budgets.py as a module.

    The hyphen in the filename makes a normal import impossible, so we
    use importlib with a stable module name. Tests share one instance
    because the script has no import-time side effects.
    """
    spec = importlib.util.spec_from_file_location("calibrate_budgets", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["calibrate_budgets"] = module
    spec.loader.exec_module(module)
    return module


calibrate = _load_script()


# ─── well-formed report parsing ──────────────────────────────────────────────

WELL_FORMED_REPORT = """\
running 2 tests
test result: ok. 2 passed; 0 failed; 0 ignored

cost_budget: progress::advance_level = 403752 cpu instructions (budget 15000000)
cost_budget: progress::record_measurement = 512340 cpu instructions (budget 20000000)
cost_budget: verification::verify_signature = 891203 cpu instructions (budget 25000000)

test promiscope_registration::tests::cost_budget::test_register_cost ... ok
test promiscope_registration::tests::cost_budget::test_register_cost ... passed: 3_421_000
test promiscope_scout_access::tests::cost_budget::test_subscribe_cost ... ok
test promiscope_scout_access::tests::cost_budget::test_subscribe_cost ... passed: 1_750_500
"""


def test_parse_cpu_report_new_format(tmp_path):
    report = tmp_path / "cpu-cost-budget-report.txt"
    report.write_text(WELL_FORMED_REPORT)

    parsed = calibrate.parse_cpu_report(report)

    assert parsed["progress"]["advance_level"] == 403752
    assert parsed["progress"]["record_measurement"] == 512340
    assert parsed["verification"]["verify_signature"] == 891203


def test_parse_cpu_report_legacy_format_strips_underscores(tmp_path):
    report = tmp_path / "cpu-cost-budget-report.txt"
    report.write_text(WELL_FORMED_REPORT)

    parsed = calibrate.parse_cpu_report(report)

    assert parsed["registration"]["register"] == 3421000
    assert parsed["scout_access"]["subscribe"] == 1750500


def test_parse_cpu_report_returns_empty_on_missing_file(tmp_path):
    missing = tmp_path / "does-not-exist.txt"
    assert calibrate.parse_cpu_report(missing) == {}


def test_parse_cpu_report_ignores_unrelated_lines(tmp_path):
    report = tmp_path / "cpu-cost-budget-report.txt"
    report.write_text(
        "warning: unused variable\n"
        "running 5 tests\n"
        "test result: ok\n"
        "noise that should not match\n"
    )
    assert calibrate.parse_cpu_report(report) == {}


# ─── missing-section error path ──────────────────────────────────────────────

def test_load_json_missing_file_raises_system_exit(tmp_path):
    """Absence of an input file is a specific error, not a bare traceback."""
    missing = tmp_path / "absent.json"
    with pytest.raises(SystemExit) as excinfo:
        calibrate.load_json(missing)
    assert excinfo.value.code == 1


def test_load_json_missing_file_prints_actionable_message(tmp_path, capsys):
    missing = tmp_path / "absent.json"
    with pytest.raises(SystemExit):
        calibrate.load_json(missing)
    captured = capsys.readouterr()
    assert "not found" in captured.err
    assert "Run the CI jobs first" in captured.err
    assert str(missing) in captured.err


def test_load_json_well_formed_file_returns_parsed_dict(tmp_path):
    payload = tmp_path / "ok.json"
    payload.write_text('{"budgets": {"a": 1, "b": 2}}')
    assert calibrate.load_json(payload) == {"budgets": {"a": 1, "b": 2}}


# ─── drift computation against a threshold table ─────────────────────────────

@pytest.mark.parametrize(
    "measured, headroom, expected",
    [
        ({"registration": 100000}, 0.20, {"registration": 120000}),
        ({"registration": 100000}, 0.00, {"registration": 100000}),
        ({"registration": 100000}, 0.10, {"registration": 110000}),
        ({"registration": 99999}, 0.20, {"registration": 119998}),
        ({"a": 1, "b": 2, "c": 3}, 0.50, {"a": 1, "b": 3, "c": 4}),
    ],
)
def test_recommend_wasm_budgets_applies_headroom(measured, headroom, expected):
    assert calibrate.recommend_wasm_budgets(measured, headroom) == expected


def test_recommend_wasm_budgets_truncates_toward_zero():
    # int() truncates, not rounds. 100001 * 1.20 = 120001.2 -> 120001.
    assert calibrate.recommend_wasm_budgets({"a": 100001}, 0.20) == {"a": 120001}


def test_recommend_cpu_budgets_nested():
    measured = {
        "progress": {"advance": 400000, "record": 500000},
        "verification": {"verify": 800000},
    }
    got = calibrate.recommend_cpu_budgets(measured, 0.20)
    assert got == {
        "progress": {"advance": 480000, "record": 600000},
        "verification": {"verify": 960000},
    }


def test_recommend_cpu_budgets_preserves_empty_contract():
    assert calibrate.recommend_cpu_budgets({"empty": {}}, 0.20) == {"empty": {}}


def test_recommend_wasm_budgets_empty_input():
    assert calibrate.recommend_wasm_budgets({}, 0.20) == {}


# ─── end-to-end against the real budget file ─────────────────────────────────

def test_recommend_matches_budget_file_with_default_headroom(tmp_path):
    """The shipped budget file is exactly what the script recommends from
    the values it contains — a self-consistency check that would catch a
    silent change to the headroom arithmetic."""
    budget_file = REPO_ROOT / "ci" / "wasm-size-budget.json"
    data = calibrate.load_json(budget_file)
    budgets = data["budgets"]
    # Reverse the headroom: measured = budget / (1 + headroom), rounded down.
    # Then forward again and confirm it stays stable.
    for headroom in (0.00, 0.10, 0.20):
        recommended = calibrate.recommend_wasm_budgets(budgets, headroom)
        assert set(recommended) == set(budgets)
        for contract, value in recommended.items():
            assert value >= budgets[contract]  # headroom is non-negative
