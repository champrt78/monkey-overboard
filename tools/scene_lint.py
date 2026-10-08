"""Static checker for Godot 4 .tscn and .tres files.

Finds broken references in scenes and resources without running Godot.
Scans a project directory (skipping addons/ and .godot/) and reports:

    MISSING_RESOURCE  an ext_resource path that does not exist on disk
    DUPLICATE_UID     the same uid="uid://..." declared by two files
    MISSING_METHOD    a connection method with no matching func in the target
                      node's script (or the scene root's script)
    BAD_FORMAT        a file that does not look like a Godot text scene/resource

With --data, also runs the tools/validate_data.py checks on .tres files
whose script is a class_name Resource and merges their findings.

Usage:
    python tools/scene_lint.py <project_path> [--json] [--data]
"""
import json
import os
import re
import sys

import validate_data

SKIP_DIRS = ("addons", ".godot")
FILE_SUFFIXES = (".tscn", ".tres")

HEADER_RE = re.compile(r"^\[(gd_scene|gd_resource)\b")
EXT_RESOURCE_RE = re.compile(r'^\[ext_resource\b.*?\bpath\s*=\s*"(res://[^"]*)"')
EXT_RESOURCE_ID_RE = re.compile(r'\bid\s*=\s*["\']?([^"\'()\s]+)["\']?')
UID_RE = re.compile(r'\buid="uid://[^"]*"')
CONNECTION_RE = re.compile(
    r'^\[connection\b.*?\bsignal="([^"]*)".*?\bfrom="([^"]*)".*'
    r'\bto="([^"]*)".*?\bmethod="([^"]*)"'
)
NODE_RE = re.compile(
    r'^\[node\b.*?\bname="([^"]*)"'
    r'(?:\s+path="([^"]*)")?'
    r'(?:\s+parent="([^"]*)")?'
)
SCRIPT_PROP_RE = re.compile(
    r'^\s*script\s*=\s*ExtResource\(\s*["\']?([^"\'()\s]+)["\']?\s*\)'
)


def _res_path_to_project(project_root, res_path):
    """Translate a res:// path to an absolute path under the project root."""
    rel = res_path[len("res://"):]
    return os.path.join(project_root, rel)


def _collect_nodes(lines):
    """Return (node_scripts, root_script_id). node_scripts maps the path of
    each node (format 2 'path' attribute, or 'parent'/'name' in format 3) to
    its script ext_resource id."""
    node_scripts = {}
    root_script_id = None
    current_path = None
    current_is_root = False
    seen_node = False
    for line in lines:
        stripped = line.strip()
        m = NODE_RE.match(stripped)
        if m:
            name, path, parent = m.group(1), m.group(2), m.group(3)
            if path:
                current_path = path
                current_is_root = False
            elif parent and parent != ".":
                current_path = parent + "/" + name
                current_is_root = False
            else:
                current_path = name
                current_is_root = not seen_node
            seen_node = True
            continue
        sm = SCRIPT_PROP_RE.match(stripped)
        if sm and current_path is not None:
            node_scripts[current_path] = sm.group(1)
            if current_is_root:
                root_script_id = sm.group(1)
    return node_scripts, root_script_id


def lint_file_text(text, project_root, rel_path):
    """Lint one .tscn/.tres text. Returns a list of issue dicts
    (keys: file, line, code, detail)."""
    issues = []

    def add(line, code, detail):
        issues.append(
            {"file": rel_path, "line": line, "code": code, "detail": detail}
        )

    lines = text.splitlines()
    header_line = None
    for i, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped and not stripped.startswith(";"):
            header_line = i
            break

    if header_line is None:
        add(1, "BAD_FORMAT", "file is empty")
        return issues
    if not HEADER_RE.match(lines[header_line - 1].strip()):
        add(
            header_line,
            "BAD_FORMAT",
            "first line is not a [gd_scene]/[gd_resource] header: '{}'".format(
                lines[header_line - 1].strip()
            ),
        )
        return issues

    ext_paths = {}
    ext_missing = set()
    for i, line in enumerate(lines, start=1):
        m = EXT_RESOURCE_RE.match(line)
        if not m:
            continue
        res_path = m.group(1)
        idm = EXT_RESOURCE_ID_RE.search(line)
        if idm:
            ext_paths[idm.group(1)] = res_path
        if not os.path.exists(_res_path_to_project(project_root, res_path)):
            ext_missing.add(res_path)
            add(i, "MISSING_RESOURCE", "path '{}' does not exist".format(res_path))

    node_scripts, root_script_id = _collect_nodes(lines)

    for i, line in enumerate(lines, start=1):
        m = CONNECTION_RE.match(line.strip())
        if not m:
            continue
        target, method = m.group(3), m.group(4)
        script_id = node_scripts.get(target)
        if script_id is None:
            script_id = root_script_id
        if script_id is None or script_id not in ext_paths:
            continue
        res_path = ext_paths[script_id]
        if res_path in ext_missing:
            continue
        script_path = _res_path_to_project(project_root, res_path)
        try:
            with open(script_path, "r", encoding="utf-8", errors="replace") as f:
                script_text = f.read()
        except OSError:
            continue
        if not re.search(r"func\s+" + re.escape(method) + r"\s*\(", script_text):
            add(
                i,
                "MISSING_METHOD",
                "method '{}' not found in script '{}' (node '{}')".format(
                    method, res_path, target
                ),
            )

    return issues


def lint_file(path, project_root, rel_path):
    """Lint one file on disk. Returns a list of issue dicts."""
    try:
        with open(path, "r", encoding="utf-8") as handle:
            text = handle.read()
    except UnicodeDecodeError:
        return [
            {
                "file": rel_path,
                "line": 1,
                "code": "BAD_FORMAT",
                "detail": "file is not decodable as UTF-8 text",
            }
        ]
    except OSError as exc:
        return [
            {
                "file": rel_path,
                "line": 1,
                "code": "BAD_FORMAT",
                "detail": "cannot read file ({})".format(exc),
            }
        ]
    return lint_file_text(text, project_root, rel_path)


def iter_scene_files(project_root):
    """Yield absolute paths of .tscn/.tres files, skipping addons/ and .godot/."""
    for dirpath, dirnames, filenames in os.walk(project_root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            if name.endswith(FILE_SUFFIXES):
                yield os.path.join(dirpath, name)


def lint_project(project_root):
    """Lint a project directory. Returns a list of issue dicts, sorted by
    (file, line), including the cross-file DUPLICATE_UID check."""
    project_root = os.path.abspath(project_root)
    files = sorted(iter_scene_files(project_root), key=lambda p: p)

    issues = []
    uid_locations = {}
    for path in files:
        rel_path = os.path.relpath(path, project_root).replace(os.sep, "/")
        try:
            with open(path, "r", encoding="utf-8") as handle:
                text = handle.read()
        except UnicodeDecodeError:
            issues.append(
                {
                    "file": rel_path,
                    "line": 1,
                    "code": "BAD_FORMAT",
                    "detail": "file is not decodable as UTF-8 text",
                }
            )
            continue
        except OSError as exc:
            issues.append(
                {
                    "file": rel_path,
                    "line": 1,
                    "code": "BAD_FORMAT",
                    "detail": "cannot read file ({})".format(exc),
                }
            )
            continue

        issues.extend(lint_file_text(text, project_root, rel_path))

        for i, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            if not HEADER_RE.match(stripped):
                continue
            m = UID_RE.search(stripped)
            if not m:
                continue
            uid = m.group(0)[len("uid="):].strip('"')
            if uid in uid_locations:
                first_file, first_line = uid_locations[uid]
                issues.append(
                    {
                        "file": rel_path,
                        "line": i,
                        "code": "DUPLICATE_UID",
                        "detail": "uid '{}' also declared in {} (line {})".format(
                            uid, first_file, first_line
                        ),
                    }
                )
            else:
                uid_locations[uid] = (rel_path, i)

    issues.sort(key=lambda item: (item["file"], item["line"]))
    return issues


def format_issue(issue):
    return "{}:{}: {} {}".format(
        issue["file"], issue["line"], issue["code"], issue["detail"]
    )


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    as_json = False
    as_data = False
    paths = []
    for arg in argv:
        if arg == "--json":
            as_json = True
        elif arg == "--data":
            as_data = True
        else:
            paths.append(arg)

    if len(paths) != 1 or not os.path.isdir(paths[0]):
        sys.stderr.write(
            "usage: python tools/scene_lint.py <project_path> [--json] [--data]\n"
        )
        return 2

    issues = lint_project(paths[0])
    if as_data:
        issues = issues + validate_data.validate_project(paths[0])
        issues.sort(key=lambda item: (item["file"], item["line"]))
    if as_json:
        print(json.dumps(issues, indent=2))
    elif issues:
        for issue in issues:
            print(format_issue(issue))
    else:
        print("OK")
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
