#!/usr/bin/env python3
"""CI helper: fail if a dbt/Trino EXPLAIN plan shows a full table scan marker."""

from __future__ import annotations

import re
import sys

FULL_SCAN_MARKERS = (
    re.compile(r"SEQ SCAN", re.I),
    re.compile(r"Table Scan", re.I),
    re.compile(r"FULL TABLE SCAN", re.I),
)


def plan_has_full_table_scan(explain_text: str) -> bool:
    return any(p.search(explain_text) for p in FULL_SCAN_MARKERS)


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: check_explain_full_scan.py <explain.txt>", file=sys.stderr)
        return 2
    text = open(argv[1], encoding="utf-8").read()
    if plan_has_full_table_scan(text):
        print("FAIL: full table scan detected in EXPLAIN output")
        return 1
    print("PASS: no full table scan markers")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
