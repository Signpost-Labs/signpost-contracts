"""Regression coverage for the real, side-effect-free normalization helpers."""
import pytest

from scripts.migrate_region import migrate_position, migrate_region


@pytest.mark.parametrize("normalize", [migrate_region, migrate_position])
@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("", ""),
        ("  \t\n", ""),
        ("  north  ", "NORTH"),
        ("miXeD", "MIXED"),
        ("\t ÉuRope straße \n", "ÉUROPE STRASSE"),
        ("NORTH WEST", "NORTH WEST"),
    ],
)
def test_normalization(normalize, value, expected):
    assert normalize(value) == expected
    assert normalize(expected) == expected
