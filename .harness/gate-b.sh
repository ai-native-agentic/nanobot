#!/usr/bin/env bash
set -euo pipefail

CONFIG_FILE="${1:-}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ -z "$CONFIG_FILE" ]]; then
  echo "Usage: $0 <config.yaml>"
  exit 2
fi

python3 - "$ROOT_DIR" "$CONFIG_FILE" <<'PY'
import ast
import sys
from pathlib import Path

root = Path(sys.argv[1])
config_path = Path(sys.argv[2])

try:
    import yaml
except Exception:
    print("Gate B requires pyyaml")
    raise SystemExit(1)

cfg = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
gate = cfg.get("gates", {}).get("gate_b", {})
root_package = gate.get("root_package")
boundaries = gate.get("boundaries", [])
include_paths = cfg.get("include_paths", [root_package] if root_package else ["."])
exclude_paths = set(cfg.get("exclude_paths", []))

if not root_package or not boundaries:
    print("Gate B: no root_package/boundaries configured; skipping")
    raise SystemExit(0)

violations = []

def is_excluded(path: Path) -> bool:
    text = str(path).replace("\\", "/")
    return any(text.startswith(ex.rstrip("/")) for ex in exclude_paths)

for rel in include_paths:
    base = root / rel
    if not base.exists():
        continue
    for py_file in base.rglob("*.py"):
        rel_file = py_file.relative_to(root)
        if is_excluded(rel_file):
            continue
        source_layer = None
        rel_parts = rel_file.parts
        try:
            pkg_idx = rel_parts.index(root_package)
            if len(rel_parts) > pkg_idx + 1:
                source_layer = rel_parts[pkg_idx + 1]
        except ValueError:
            continue

        if source_layer is None:
            continue

        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        imported = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imported.add(node.module)

        for boundary in boundaries:
            if boundary.get("source") != source_layer:
                continue
            forbidden = boundary.get("forbidden", [])
            for item in imported:
                for target in forbidden:
                    prefix = f"{root_package}.{target}"
                    if item == prefix or item.startswith(prefix + "."):
                        violations.append(f"{rel_file}: {source_layer} -> {target} via {item}")

if violations:
    print("Gate B failed: forbidden cross-layer imports found")
    for line in violations:
        print(f" - {line}")
    raise SystemExit(1)

print("Gate B passed")
PY
