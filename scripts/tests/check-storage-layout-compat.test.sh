#!/usr/bin/env bash
# Exercise the checked-in safe/breaking fixtures without compiling contracts.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CHECKER="${REPO_ROOT}/scripts/check-storage-layout-compat.sh"
SAFE="${REPO_ROOT}/scripts/fixtures/storage_compat_safe"
BREAKING="${REPO_ROOT}/scripts/fixtures/storage_compat_breaking"

# Missing fixtures must fail the suite, rather than compare two empty layouts.
for fixture in "$SAFE/old_types.rs" "$SAFE/new_types.rs" \
               "$BREAKING/old_types.rs" "$BREAKING/new_types.rs"; do
  if [[ ! -f "$fixture" ]]; then
    echo "FAIL: required storage-layout fixture is missing: $fixture" >&2
    exit 1
  fi
done

assert_exit() {
  local label="$1" expected="$2" actual output
  shift 2
  if output=$(bash "$CHECKER" "$@" 2>&1); then
    actual=0
  else
    actual=$?
  fi
  if [[ "$actual" -ne "$expected" ]]; then
    printf 'FAIL: %s: expected exit %s, got %s\n%s\n' \
      "$label" "$expected" "$actual" "$output" >&2
    exit 1
  fi
  printf 'PASS: %s (exit %s)\n' "$label" "$actual"
}

assert_exit 'safe fixture pair' 0 "$SAFE" "$SAFE"
assert_exit 'breaking fixture pair' 1 "$SAFE" "$BREAKING"
assert_exit 'acknowledged breaking fixture pair' 0 "$SAFE" "$BREAKING" \
  --acknowledge-breaking-change
