"""Linter for worker briefs.

Rejects a brief file that is missing required sections, has broken
requirement numbering, an empty FILES list, or no unchecked DONE items.

Usage:
    python tools/brief_check.py <brief.md> [--json]
"""
import json
import re
import sys

REQUIRED_HEADINGS = [
    "TASK",
    "OBJECTIVE",
    "REQUIREMENTS",
    "MUST NOT CHANGE",
    "FILES",
    "DONE",
    "REPORT",
]

# A line that looks like a section heading: all-caps words, optionally
# followed by a colon and more text, or nothing after (the newline case).
HEADING_RE = re.compile(r"^[A-Z][A-Z0-9][A-Z0-9 /&'&-]*(:\s*.*)?$")


def _heading_line_matches(line, name):
    s = line.strip().lower()
    lname = name.lower()
    return s == lname or s.startswith(lname + ":") or s.startswith(lname + " (")


def _is_heading(line):
    return bool(HEADING_RE.match(line.strip()))


def _find_heading_index(lines, name):
    for i, line in enumerate(lines):
        if _heading_line_matches(line, name):
            return i
    return None


def heading_present(lines, name):
    return _find_heading_index(lines, name) is not None


def get_section(lines, name):
    """Return the content lines of a section (heading remainder plus body),
    stopping at the next heading line or end of file."""
    idx = _find_heading_index(lines, name)
    if idx is None:
        return []
    content = []
    first = lines[idx].strip()
    lname = name.lower()
    low = first.lower()
    if low.startswith(lname + ":"):
        remainder = first[len(name) + 1:].strip()
        if remainder:
            content.append(remainder)
    for line in lines[idx + 1:]:
        if _is_heading(line):
            break
        content.append(line)
    return content


def _check_headings(lines):
    problems = []
    for h in REQUIRED_HEADINGS:
        if not heading_present(lines, h):
            problems.append("headings: missing required heading '{}'".format(h))
    return problems


def _check_requirements(lines):
    problems = []
    nums = []
    for line in get_section(lines, "REQUIREMENTS"):
        m = re.match(r"^\s*(\d+)\.", line)
        if m:
            nums.append(int(m.group(1)))
    if not nums:
        return ["requirements: no numbered requirement lines found"]
    if 1 not in nums:
        problems.append("requirements: no line starting with '1.'")
    else:
        ordered = sorted(set(nums))
        expected = list(range(1, max(ordered) + 1))
        if ordered != expected:
            problems.append(
                "requirements: numbers must be consecutive with no gaps, found {}".format(
                    ", ".join(str(n) for n in ordered)
                )
            )
    return problems


def _check_files(lines):
    section = get_section(lines, "FILES")
    if not any(line.strip() for line in section):
        return ["files: no path listed under FILES"]
    return []


def _check_done(lines):
    section = get_section(lines, "DONE")
    if not any(line.lstrip().startswith("[ ]") for line in section):
        return ["done: no unchecked '[ ]' item under DONE"]
    return []


def lint(text):
    """Return a list of '<check>: <detail>' problem strings (empty if valid)."""
    lines = text.splitlines()
    problems = []
    problems.extend(_check_headings(lines))
    problems.extend(_check_requirements(lines))
    problems.extend(_check_files(lines))
    problems.extend(_check_done(lines))
    return problems


def _read_text(path):
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    as_json = False
    paths = []
    for arg in argv:
        if arg == "--json":
            as_json = True
        else:
            paths.append(arg)

    if len(paths) != 1:
        sys.stderr.write("usage: python tools/brief_check.py <brief.md> [--json]\n")
        if as_json:
            print(json.dumps({"ok": False, "problems": ["usage: expected exactly one brief path"]}))
        return 2
    brief_path = paths[0]

    try:
        text = _read_text(brief_path)
    except OSError as exc:
        problems = ["file: cannot read '{}' ({})".format(brief_path, exc)]
    else:
        problems = lint(text)

    if as_json:
        print(json.dumps({"ok": not problems, "problems": problems}))
    elif problems:
        for problem in problems:
            print(problem)
    else:
        print("OK")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
