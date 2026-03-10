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
mypy_strict = bool(gate.get("mypy_strict", defaults["mypy_strict"]))
paths = data.get("include_paths", defaults["include_paths"])

print(f"BLACK_LINE_LENGTH={int(line_length)}")
print(f"RUFF_SELECT={shlex.quote(','.join(ruff_select))}")
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
  ruff check --select "$RUFF_SELECT" "${TARGET_ARRAY[@]}"
else
  echo "ruff is not installed"
  exit 1
fi

if command -v mypy >/dev/null 2>&1; then
  if [[ "$MYPY_STRICT" -eq 1 ]]; then
    mypy --strict "${TARGET_ARRAY[@]}"
  else
    mypy "${TARGET_ARRAY[@]}"
  fi
else
  echo "mypy is not installed"
  exit 1
fi
