"""Check that Mermaid diagrams in Markdown fit a readable column.

A `graph LR` chain grows to the right without limit, so a pipeline of eight
labelled stages renders about 2,000 px wide. That forces horizontal scrolling
on a laptop and breaks the reading rhythm of the surrounding text.

The width here is an estimate, not a render. It assumes roughly 8 px per
character at the default Mermaid font, plus node padding and the gap between
nodes. That is close enough to separate "fits a column" from "needs scrolling",
which is the only judgement this script makes.

Run with `python -m tools.check_diagrams [files...]`; defaults to every tracked
Markdown file. Exits non-zero if any diagram is too wide.
"""

import glob
import re
import sys
from typing import List, Tuple

# A comfortable reading column. GitHub renders Markdown at roughly 900 px of
# usable width; 800 leaves room for a narrower window or a side panel.
MAX_WIDTH_PX = 800

_PX_PER_CHAR = 8
_NODE_PADDING = 40
_NODE_GAP = 50

_LABEL_RE = re.compile(
    r'\["([^"]+)"\]'  # ["text"]
    r'|\(\("?([^")]+)"?\)\)'  # ((text))
    r'|\(\["([^"]+)"\]\)'  # (["text"])
    r'|\{"?([^"}]+)"?\}'  # {"text"}
)


def _labels(source: str) -> List[str]:
    return ["".join(part for part in match if part) for match in _LABEL_RE.findall(source)]


def _widest_line(labels: List[str]) -> int:
    return max((max(len(line) for line in label.split("<br/>")) for label in labels), default=0)


def estimate_width(source: str) -> Tuple[str, int, int]:
    """Return (direction, node count, estimated pixel width) for one diagram."""
    match = re.search(r"graph\s+(LR|RL|TD|TB|BT)", source)
    direction = match.group(1) if match else "TD"
    labels = _labels(source)
    widest = _widest_line(labels)
    count = len(labels)
    if direction in ("LR", "RL"):
        width = count * (widest * _PX_PER_CHAR + _NODE_PADDING)
        width += max(count - 1, 0) * _NODE_GAP
    else:
        # Top-down grows downward; width is one node plus room for edge labels.
        width = widest * _PX_PER_CHAR + _NODE_PADDING * 2
    return direction, count, width


def check(paths: List[str]) -> int:
    failures = 0
    for path in paths:
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        for index, source in enumerate(re.findall(r"```mermaid\n(.*?)```", text, re.S), 1):
            direction, count, width = estimate_width(source)
            if width <= MAX_WIDTH_PX:
                continue
            failures += 1
            print(
                f"{path}: diagram {index} is about {width} px wide "
                f"(graph {direction}, {count} nodes, limit {MAX_WIDTH_PX})"
            )
            if direction in ("LR", "RL"):
                print(
                    "    Use `graph TD` unless left-to-right order carries meaning, "
                    "or shorten the labels."
                )
            else:
                print("    Shorten the longest label.")
    return failures


def main() -> None:
    paths = sys.argv[1:] or sorted(glob.glob("**/*.md", recursive=True))
    failures = check([p for p in paths if "/node_modules/" not in p])
    if failures:
        print(f"\n{failures} diagram(s) too wide. See docs/STYLE.md.")
        sys.exit(1)


if __name__ == "__main__":
    main()
