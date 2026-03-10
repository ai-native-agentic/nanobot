#!/usr/bin/env bash
set -euo pipefail

CONFIG_FILE="${1:-}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ -z "$CONFIG_FILE" ]]; then
  echo "Usage: $0 <config.yaml>"
  exit 2
fi

eval "$(python3 - "$CONFIG_FILE" <<'PY'
import shlex
import sys
from pathlib import Path

cfg_path = Path(sys.argv[1])

defaults = {
    "line_length": 100,
    "ruff_select": ["E", "F", "I"],
    "ruff_ignore": [],
    "mypy_strict": False,
    "include_paths": ["."],
}

try:
    import yaml
except Exception:
    data = {}
else:
    data = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}

gate = data.get("gates", {}).get("gate_a", {})
line_length = gate.get("black_line_length", defaults["line_length"])
ruff_select = gate.get("ruff_select", defaults["ruff_select"])
ruff_ignore = gate.get("ruff_ignore", defaults["ruff_ignore"])
mypy_enabled = bool(gate.get("mypy_enabled", True))
mypy_strict = bool(gate.get("mypy_strict", defaults["mypy_strict"]))
paths = data.get("include_paths", defaults["include_paths"])

# Also read project-level ruff ignore from pyproject.toml if present
root = cfg_path.parent.parent
pyproject = root / "pyproject.toml"
if pyproject.exists() and not ruff_ignore:
    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib
        except ImportError:
            tomllib = None
    if tomllib:
        try:
            with open(pyproject, "rb") as f:
                pydata = tomllib.load(f)
            ruff_ignore = pydata.get("tool", {}).get("ruff", {}).get("lint", {}).get("ignore", [])
        except Exception:
            pass

print(f"BLACK_LINE_LENGTH={int(line_length)}")
print(f"RUFF_SELECT={shlex.quote(','.join(ruff_select))}")
print(f"RUFF_IGNORE={shlex.quote(','.join(ruff_ignore)) if ruff_ignore else ''}")
print(f"MYPY_ENABLED={1 if mypy_enabled else 0}")
print(f"MYPY_STRICT={1 if mypy_strict else 0}")
print(f"TARGET_PATHS={shlex.quote(' '.join(paths))}")
PY
)"

IFS=' ' read -r -a TARGET_ARRAY <<< "$TARGET_PATHS"

if command -v black >/dev/null 2>&1; then
  black --check --line-length "$BLACK_LINE_LENGTH" "${TARGET_ARRAY[@]}"
else
  echo "black is not installed"
  exit 1
fi

if command -v ruff >/dev/null 2>&1; then
  RUFF_ARGS=(check --select "$RUFF_SELECT")
  if [[ -n "${RUFF_IGNORE:-}" ]]; then
    RUFF_ARGS+=(--ignore "$RUFF_IGNORE")
  fi
  ruff "${RUFF_ARGS[@]}" "${TARGET_ARRAY[@]}"
else
  echo "ruff is not installed"
  exit 1
fi

if [[ "${MYPY_ENABLED:-1}" -eq 0 ]]; then
  echo "mypy: skipped (disabled in config)"
elif command -v mypy >/dev/null 2>&1; then
  if [[ "$MYPY_STRICT" -eq 1 ]]; then
    mypy --strict "${TARGET_ARRAY[@]}"
  else
    mypy "${TARGET_ARRAY[@]}"
  fi
else
  echo "mypy is not installed"
  exit 1
fi
