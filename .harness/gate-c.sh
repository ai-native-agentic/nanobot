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
from collections import defaultdict
from pathlib import Path
import sys

root = Path(sys.argv[1])
config_path = Path(sys.argv[2])

try:
    import yaml
except Exception:
    print("Gate C requires pyyaml")
    raise SystemExit(1)

cfg = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
gate = cfg.get("gates", {}).get("gate_c", {})
max_len = int(gate.get("max_function_length", 80))
max_complexity = int(gate.get("max_complexity", 12))
include_paths = cfg.get("include_paths", ["."])
exclude_paths = set(cfg.get("exclude_paths", []))

function_issues = []
complexity_issues = []
import_graph = defaultdict(set)

def is_excluded(path: Path) -> bool:
    text = str(path).replace("\\", "/")
    return any(text.startswith(ex.rstrip("/")) for ex in exclude_paths)

MATCH_NODE = getattr(ast, "Match", ())

def complexity(node: ast.AST) -> int:
    score = 1
    for item in ast.walk(node):
        if isinstance(item, (ast.If, ast.For, ast.While, ast.Try, MATCH_NODE, ast.BoolOp, ast.With, ast.AsyncFor)):
            score += 1
    return score

def module_name(py_file: Path) -> str:
    rel = py_file.relative_to(root)
    parts = list(rel.parts)
    if parts[-1] == "__init__.py":
        parts = parts[:-1]
    else:
        parts[-1] = parts[-1].removesuffix(".py")
    return ".".join(parts)

for rel in include_paths:
    base = root / rel
    if not base.exists():
        continue
    for py_file in base.rglob("*.py"):
        rel_file = py_file.relative_to(root)
        if is_excluded(rel_file):
            continue
        content = py_file.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(py_file))

        current_module = module_name(py_file)

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.end_lineno:
                fn_len = node.end_lineno - node.lineno + 1
                if fn_len > max_len:
                    function_issues.append(
                        f"{rel_file}:{node.lineno} {node.name} length={fn_len} > {max_len}"
                    )
                fn_complexity = complexity(node)
                if fn_complexity > max_complexity:
                    complexity_issues.append(
                        f"{rel_file}:{node.lineno} {node.name} complexity={fn_complexity} > {max_complexity}"
                    )

            if isinstance(node, ast.ImportFrom) and node.module:
                import_graph[current_module].add(node.module)
            if isinstance(node, ast.Import):
                for alias in node.names:
                    import_graph[current_module].add(alias.name)

modules = set(import_graph.keys())

cycles = []
visiting = set()
visited = set()

def dfs(module: str, stack: list[str]) -> None:
    visiting.add(module)
    stack.append(module)
    for dep in import_graph.get(module, set()):
        if dep not in modules:
            continue
        if dep in visiting:
            start = stack.index(dep)
            cycles.append(" -> ".join(stack[start:] + [dep]))
            continue
        if dep not in visited:
            dfs(dep, stack)
    visiting.remove(module)
    visited.add(module)
    stack.pop()

for mod in modules:
    if mod not in visited:
        dfs(mod, [])

failed = False
if function_issues:
    failed = True
    print("Gate C failed: function length violations")
    for item in function_issues[:50]:
        print(f" - {item}")

if complexity_issues:
    failed = True
    print("Gate C failed: complexity violations")
    for item in complexity_issues[:50]:
        print(f" - {item}")

if cycles:
    failed = True
    print("Gate C failed: import cycles detected")
    for item in cycles[:20]:
        print(f" - {item}")

if failed:
    raise SystemExit(1)

print("Gate C passed")
PY
