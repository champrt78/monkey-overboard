"""Static linter for Godot 4 GDScript house rules.

Scans every .gd file under a project path and reports findings for the
rules: UNTYPED_VAR, UNTYPED_FUNC, MAGIC_NUMBER, CODE_AFTER_TRANSITION,
LONG_NODE_PATH, PROCESS_ALLOC, GLOBAL_RANDOM.

Usage:
    python tools/gdscript_lint.py <project_path> [--json] [--rules R1,R2] [--exclude <glob>]
"""
import argparse
import fnmatch
import json
import os
import re
import sys

DEFAULT_RULES = [
    "UNTYPED_VAR",
    "UNTYPED_FUNC",
    "MAGIC_NUMBER",
    "CODE_AFTER_TRANSITION",
    "LONG_NODE_PATH",
    "PROCESS_ALLOC",
    "GLOBAL_RANDOM",
]

ALWAYS_EXCLUDED_DIRS = {"addons", ".godot"}

DEFAULT_GAMEPLAY_DIRS = ["src/gameplay", "scripts/gameplay"]

LINT_OK = "# lint-ok"

VAR_RE = re.compile(r"^\s*(?:@\w+\s+)*var\s+([A-Za-z_][\w]*)\s*(.*)$")
TYPE_OR_ASSIGN_RE = re.compile(r"^(\s*:=|\s*:|\.|\s*=\s*$)")
FUNC_RE = re.compile(r"^\s*(?:@\w+\s+)*func\s+([A-Za-z_]\w*)\s*\((.*)\)\s*(->\s*[\w.]+\s*)?:")
TRANSITION_RE = re.compile(r"\b(?:change_state|transition_to|change_scene_to_file)\s*\(")
GET_NODE_RE = re.compile(r"\bget_node\s*\(\s*[\"']([^\"']*)[\"']")
DOLLAR_PATH_RE = re.compile(r"(?<![\w$])\$([A-Za-z_][\w]*(?:/[A-Za-z_][\w]*)*)")
NEW_CALL_RE = re.compile(
    r"(?:(?<=[\w$\]])\.new\s*\(|\bArray\s*\(|\bDictionary\s*\()")
STR_CONCAT_RE = [
    re.compile(r"[\"'].*?[\"']\s*\+"),
    re.compile(r"\+\s*[\"']"),
    re.compile(r"\.\s*(?:name|text|to_string|get_name|get_text)\b[\w\]\)]*\s*\+"),
    re.compile(r"\+\s*(?:\.\s*)?(?:name|text)\b"),
]
RAND_RE = re.compile(r"(?<![\w.])\b(randf|randi|randf_range|randi_range)\s*\(")
NUMBER_RE = re.compile(r"(?<!\w)(-?(?:\d+\.\d*|\.\d+|\d+))(?!\w)")
ALLOWED_NUMS = {0, 1, -1, 2, 0.5}


def is_lint_ok(line: str) -> bool:
    return line.rstrip().endswith(LINT_OK)


def _is_const_or_export(line: str) -> bool:
    stripped = line.lstrip()
    return stripped.startswith("const ") or stripped.startswith("@export")


def _numeric_value(token: str) -> float:
    if "." in token:
        return float(token)
    return float(int(token))


def check_untyped_var(lines: list, suppress: set, findings: list, rule: str) -> None:
    for lineno, line in lines:
        if rule in suppress.get(lineno, set()):
            continue
        m = VAR_RE.match(line)
        if m is None:
            continue
        name, rest = m.group(1), m.group(2)
        if TYPE_OR_ASSIGN_RE.match(rest):
            continue
        findings.append({
            "rule": "UNTYPED_VAR",
            "line": lineno,
            "message": "var '{}' has no type annotation and no ':='".format(name),
        })


def _split_top_level_commas(text: str) -> list:
    parts = []
    depth = 0
    current = ""
    in_string = None
    i = 0
    while i < len(text):
        ch = text[i]
        if in_string is not None:
            if ch == in_string:
                in_string = None
            current += ch
        elif ch in "\"'":
            in_string = ch
            current += ch
        elif ch in "([{<":
            depth += 1
            current += ch
        elif ch in ")]}>":
            depth -= 1
            current += ch
        elif ch == "," and depth == 0:
            parts.append(current)
            current = ""
        else:
            current += ch
        i += 1
    if current.strip():
        parts.append(current)
    return parts


def check_untyped_func(lines: list, suppress: set, findings: list, rule: str) -> None:
    for lineno, line in lines:
        if rule in suppress.get(lineno, set()):
            continue
        m = FUNC_RE.match(line)
        if m is None:
            continue
        name, params_text, arrow = m.group(1), m.group(2), m.group(3)
        problems = []
        if params_text.strip():
            for part in _split_top_level_commas(params_text):
                part = part.strip()
                if not part or part.startswith("&") or part.startswith("var "):
                    continue
                p_name = part.split(":", 1)[0].strip()
                if p_name.startswith("_"):
                    continue
                if ":" not in part:
                    problems.append("'{}' has no type".format(p_name))
        if arrow is None:
            problems.append("no return type (-> Type)")
        if problems:
            findings.append({
                "rule": "UNTYPED_FUNC",
                "line": lineno,
                "message": "func '{}' {}".format(name, ", ".join(problems)),
            })


def check_magic_number(lines: list, suppress: set, findings: list, rule: str) -> None:
    for lineno, line in lines:
        if rule in suppress.get(lineno, set()):
            continue
        if _is_const_or_export(line):
            continue
        for m in NUMBER_RE.finditer(line):
            tok = m.group(1)
            try:
                value = _numeric_value(tok)
            except ValueError:
                continue
            if value in ALLOWED_NUMS:
                continue
            findings.append({
                "rule": "MAGIC_NUMBER",
                "line": lineno,
                "message": "magic number '{}' in gameplay code".format(tok),
            })


def check_code_after_transition(lines: list, suppress: set, findings: list, rule: str) -> None:
    n = len(lines)
    for idx in range(n):
        lineno, line = lines[idx]
        if rule in suppress.get(lineno, set()):
            continue
        if TRANSITION_RE.search(line):
            base_indent = len(line) - len(line.lstrip())
            visited = 0
            for j in range(idx + 1, n):
                nxt_line = lines[j][1]
                if not nxt_line.strip():
                    continue
                indent = len(nxt_line) - len(nxt_line.lstrip())
                if indent < base_indent:
                    break
                if nxt_line.lstrip().startswith("#"):
                    continue
                if visited == 0 and re.match(r"return\b", nxt_line.strip()):
                    break
                visited += 1
                findings.append({
                    "rule": "CODE_AFTER_TRANSITION",
                    "line": lines[j][0],
                    "message": "code after state transition call",
                })


def check_long_node_path(lines: list, suppress: set, findings: list, rule: str) -> None:
    for lineno, line in lines:
        if rule in suppress.get(lineno, set()):
            continue
        for m in GET_NODE_RE.finditer(line):
            path = m.group(1)
            if path.count("/") >= 2:
                findings.append({
                    "rule": "LONG_NODE_PATH",
                    "line": lineno,
                    "message": "node path '{}' has {} segments".format(
                        path, path.count("/") + 1),
                })
        for m in DOLLAR_PATH_RE.finditer(line):
            path = m.group(1)
            if path.count("/") >= 2:
                findings.append({
                    "rule": "LONG_NODE_PATH",
                    "line": lineno,
                    "message": "node path '${}' has {} segments".format(
                        path, path.count("/") + 1),
                })


def _process_scopes(lines: list) -> list:
    scopes = []
    proc_re = re.compile(r"^\s*func\s+(_process|_physics_process)\b.*:")
    n = len(lines)
    for idx, (lineno, line) in enumerate(lines):
        m = proc_re.match(line)
        if m is None:
            continue
        base_indent = len(line) - len(line.lstrip())
        end = n
        for j in range(idx + 1, n):
            nxt = lines[j][1]
            if not nxt.strip():
                continue
            indent = len(nxt) - len(nxt.lstrip())
            if indent <= base_indent:
                end = j
                break
        scopes.append((m.group(1), idx + 1, end, base_indent))
    return scopes


def check_process_alloc(lines: list, suppress: set, findings: list, rule: str) -> None:
    for func_name, start, end, base_indent in _process_scopes(lines):
        for j in range(start, end):
            lineno, line = lines[j]
            if rule in suppress.get(lineno, set()):
                continue
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            indent = len(line) - len(line.lstrip())
            if indent <= base_indent:
                continue
            if NEW_CALL_RE.search(line):
                findings.append({
                    "rule": "PROCESS_ALLOC",
                    "line": lineno,
                    "message": "allocation inside {}()".format(func_name),
                })
            elif any(p.search(line) for p in STR_CONCAT_RE):
                findings.append({
                    "rule": "PROCESS_ALLOC",
                    "line": lineno,
                    "message": "string concatenation inside {}()".format(func_name),
                })


def check_global_random(text: str, lines: list, suppress: set, findings: list,
                         rule: str, base_name: str) -> None:
    if "gen" not in base_name.lower():
        return
    has_rng = re.search(r"\bRandomNumberGenerator\b", text) is not None
    for lineno, line in lines:
        if rule in suppress.get(lineno, set()):
            continue
        m = RAND_RE.search(line)
        if m is not None and not has_rng:
            findings.append({
                "rule": "GLOBAL_RANDOM",
                "line": lineno,
                "message": "global random call '{}'()".format(m.group(1)),
            })


def build_suppress(lines: list) -> dict:
    suppress = {}
    for lineno, line in lines:
        if is_lint_ok(line):
            suppress[lineno] = set(DEFAULT_RULES)
    return suppress


CHECKS = {
    "UNTYPED_VAR": lambda ctx: check_untyped_var(
        ctx["lines"], ctx["suppress"], ctx["findings"], ctx["rule"]),
    "UNTYPED_FUNC": lambda ctx: check_untyped_func(
        ctx["lines"], ctx["suppress"], ctx["findings"], ctx["rule"]),
    "MAGIC_NUMBER": lambda ctx: check_magic_number(
        ctx["lines"], ctx["suppress"], ctx["findings"], ctx["rule"]),
    "CODE_AFTER_TRANSITION": lambda ctx: check_code_after_transition(
        ctx["lines"], ctx["suppress"], ctx["findings"], ctx["rule"]),
    "LONG_NODE_PATH": lambda ctx: check_long_node_path(
        ctx["lines"], ctx["suppress"], ctx["findings"], ctx["rule"]),
    "PROCESS_ALLOC": lambda ctx: check_process_alloc(
        ctx["lines"], ctx["suppress"], ctx["findings"], ctx["rule"]),
    "GLOBAL_RANDOM": lambda ctx: check_global_random(
        ctx["text"], ctx["lines"], ctx["suppress"], ctx["findings"],
        ctx["rule"], ctx["base_name"]),
}


def lint_text(text: str, file_path: str, project_path: str = None,
              rules: list = None) -> list:
    """Lint GDScript text. file_path is used for the GLOBAL_RANDOM filename
    check; project_path (default: cwd) locates tools/paths.json for the
    MAGIC_NUMBER gameplay check. Findings are dicts with keys file, line,
    rule, message, sorted by line."""
    if rules is None:
        rules = DEFAULT_RULES
    if project_path is None:
        project_path = os.getcwd()
    rel = os.path.relpath(file_path, project_path).replace(os.sep, "/")
    if rel.startswith(".."):
        rel = os.path.abspath(file_path).replace(os.sep, "/")
    base_name = os.path.basename(file_path)
    lines = list(enumerate(text.splitlines(), 1))
    suppress = build_suppress(lines)
    gameplay_dirs = find_gameplay_dirs(project_path)
    ctx = {
        "text": text,
        "lines": lines,
        "suppress": suppress,
        "findings": [],
        "rule": None,
        "base_name": base_name,
    }
    for rule in rules:
        if rule not in CHECKS:
            continue
        ctx["rule"] = rule
        if rule == "MAGIC_NUMBER":
            padded = "/" + rel + "/"
            if not any(("/" + d + "/") in padded for d in gameplay_dirs):
                continue
        CHECKS[rule](ctx)
    ctx["findings"].sort(key=lambda f: f["line"])
    return [
        {
            "file": rel,
            "line": f["line"],
            "rule": f["rule"],
            "message": f["message"],
        }
        for f in ctx["findings"]
    ]


def find_gameplay_dirs(project_path: str) -> list:
    """Gameplay dirs are <src_dir>/gameplay for each src_dir in the project's
    tools/paths.json (if present and readable), else the default two."""
    paths_json = os.path.join(project_path, "tools", "paths.json")
    dirs = []
    if os.path.isfile(paths_json):
        try:
            with open(paths_json, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            for entry in data.get("src_dirs", []):
                if isinstance(entry, str) and entry.strip():
                    dirs.append(
                        os.path.join(entry.strip(), "gameplay").replace(os.sep, "/"))
        except (OSError, ValueError):
            dirs = []
    return dirs if dirs else list(DEFAULT_GAMEPLAY_DIRS)


def collect_gd_files(project_path: str, exclude_globs: list) -> list:
    found = []
    for dirpath, dirnames, filenames in os.walk(project_path):
        dirnames[:] = [
            d for d in dirnames
            if d not in ALWAYS_EXCLUDED_DIRS
            and not any(fnmatch.fnmatch(d, g) for g in exclude_globs)
        ]
        for name in filenames:
            if not name.endswith(".gd"):
                continue
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, project_path).replace(os.sep, "/")
            if any(fnmatch.fnmatch(rel, g) for g in exclude_globs):
                continue
            found.append(full)
    found.sort()
    return found


def lint_path(project_path: str, rules: list = None,
              exclude_globs: list = None) -> list:
    """Lint every .gd file under project_path. Findings carry the file path
    relative to project_path, POSIX style."""
    if exclude_globs is None:
        exclude_globs = []
    all_findings = []
    for full in collect_gd_files(project_path, exclude_globs):
        try:
            with open(full, "r", encoding="utf-8", errors="replace") as handle:
                text = handle.read()
        except OSError:
            continue
        all_findings.extend(lint_text(text, full, project_path, rules))
    all_findings.sort(key=lambda f: (f["file"], f["line"]))
    return all_findings


def _parse_rules(value: str) -> list:
    return [part.strip() for part in value.split(",") if part.strip()]


def main(argv: list = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    parser = argparse.ArgumentParser(
        prog="gdscript_lint.py",
        description="Static linter for Godot 4 GDScript house rules.",
    )
    parser.add_argument("project_path", help="path to the Godot project to scan")
    parser.add_argument("--json", action="store_true",
                        help="print findings as a JSON list")
    parser.add_argument("--rules", default=None,
                        help="comma-separated rule ids to run (default: all)")
    parser.add_argument("--exclude", action="append", default=[],
                        help="glob to exclude, matched against the relative path")
    args = parser.parse_args(argv)

    project_path = os.path.abspath(args.project_path)
    if not os.path.isdir(project_path):
        parser.error("project path is not a directory: {}".format(args.project_path))

    if args.rules is not None:
        rules = _parse_rules(args.rules)
        unknown = [r for r in rules if r not in DEFAULT_RULES]
        if unknown:
            parser.error("unknown rule(s): {}".format(", ".join(unknown)))
    else:
        rules = list(DEFAULT_RULES)

    findings = lint_path(project_path, rules, args.exclude)

    if args.json:
        print(json.dumps(findings, indent=2))
    else:
        for finding in findings:
            print("{}:{}: {} {}".format(
                finding["file"], finding["line"],
                finding["rule"], finding["message"]))
        files_with = len({f["file"] for f in findings})
        print("{} findings in {} files".format(len(findings), files_with))

    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
