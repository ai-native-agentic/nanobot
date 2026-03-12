# nanobot justfile
# Standard harness-engineering entry command

default:
    @just check

check:
    ./.harness/run-gates.sh

fmt:
    black --line-length 100 nanobot/ channels/
    ruff check --fix --select E,F,I nanobot/ channels/

test:
    python -m pytest tests/ -v --tb=short

type-check:
    mypy nanobot/ --ignore-missing-imports
