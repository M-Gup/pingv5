"""A submission's NETID: who the harness belongs to.

Declare it on your Harness subclass, as a plain string:

    class MyHarness(Harness):
        NETID = "ab1234"

The game uses it to let your harness in (the organisers keep a list of NETIDs). It is read
from the file without running it, so it must be a plain string literal in the class body.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

NETID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")


def normalise(netid: str) -> str:
    """NETIDs compare without case and surrounding spaces."""
    return netid.strip().lower()


def is_valid(netid: str) -> bool:
    return bool(NETID_PATTERN.match(normalise(netid)))


def _base_name(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ""


def read_netid(submission: Path | str) -> str | None:
    """The NETID declared on the submission's Harness subclass, or None. Static: the file is
    parsed, never executed."""
    try:
        tree = ast.parse(Path(submission).read_text(encoding="utf-8"))
    except (OSError, SyntaxError, ValueError):
        return None
    for node in tree.body:
        if not isinstance(node, ast.ClassDef) or not any(_base_name(b) == "Harness" for b in node.bases):
            continue
        for stmt in node.body:
            if isinstance(stmt, ast.Assign):
                targets, value = stmt.targets, stmt.value
            elif isinstance(stmt, ast.AnnAssign) and stmt.value is not None:
                targets, value = [stmt.target], stmt.value
            else:
                continue
            if any(isinstance(t, ast.Name) and t.id == "NETID" for t in targets) \
                    and isinstance(value, ast.Constant) and isinstance(value.value, str):
                return normalise(value.value)
    return None
