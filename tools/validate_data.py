"""Static data-schema checker for Godot 4 .tres resource files.

Validates every .tres whose script is a class_name Resource against that
script's typed @export fields, without running Godot. Scans a project
directory (skipping addons/ and .godot/) and reports:

    OUT_OF_RANGE    a numeric value outside its @export_range(min, max)
    WRONG_TYPE      a value that does not match int, float, String or bool
    UNKNOWN_FIELD   a [resource] property that is not an @export in the script
    DUPLICATE_ID    two .tres of the same class set the same value in the
                    'id' field
    MISSING_ID      the class declares an 'id' export but the .tres does not
                    set it
    BAD_FORMAT      a .tres that does not look like a Godot text resource

Usage:
    python tools/validate_data.py <project_path> [--json]
"""
import json
import os
import re
import sys

SKIP_DIRS = ("addons", ".godot")

CLASS_NAME_RE = re.compile(r"^\s*class_name\s+(\w+)")
EXTENDS_RE = re.compile(r"^\s*extends\s+(\w+)")
EXPORT_RANGE_RE = re.compile(
    r"^\s*@export_range\(\s*([^,)]+?)\s*,\s*([^,)]+?)"
    r"(?:\s*,\s*[^)]*?)?\)\s*var\s+(\w+)(?:\s*:\s*(\w+))?"
)
EXPORT_RE = re.compile(r"^\s*@export\b\s*var\s+(\w+)(?:\s*:\s*(\w+))?")
RESOURCE_HEADER_RE = re.compile(r"^\[gd_resource\b")
TRES_EXT_RESOURCE_RE = re.compile(r'^\[ext_resource\b.*?\bpath\s*=\s*"(res://[^"]*)"')
TRES_EXT_ID_RE = re.compile(r"\bid\s*=\s*[\"']?([^\"'()\s]+)[\"']?")
TRES_SCRIPT_RE = re.compile(r"^\s*script\s*=\s*ExtResource\(\s*[\"']?([^\"'()\s]+)[\"']?\s*\)")
RESOURCE_SECTION_RE = re.compile(r"^\[resource\]")
PROP_RE = re.compile(r"^\s*(\w+)\s*=\s*(.+?)\s*$")

INT_RE = re.compile(r"^[+-]?\d+$")
FLOAT_RE = re.compile(r"^[+-]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][+-]?\d+)?$")
STRING_RE = re.compile(r'^".*"$')


def _iter_files(project_root, suffix):
    """Yield absolute paths of files with suffix, skipping addons/ and .godot/."""
    for dirpath, dirnames, filenames in os.walk(project_root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            if name.endswith(suffix):
                yield os.path.join(dirpath, name)


def _read_text(path):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return handle.read()
    except (OSError, UnicodeDecodeError):
        return None


def parse_script_exports(text):
    """Parse @export and @export_range variables out of GDScript text.

    Returns a dict mapping field name to {"type": str or None,
    "range": (min, max) or None}."""
    fields = {}
    for line in text.splitlines():
        m = EXPORT_RANGE_RE.match(line)
        if m:
            min_s, max_s, name, decl = m.groups()
            rng = None
            try:
                min_v = float(min_s)
                max_v = float(max_s)
                rng = (min_v, max_v)
            except ValueError:
                rng = None
            fields[name] = {
                "type": decl,
                "range": rng,
                "range_text": "@export_range({}, {})".format(min_s, max_s),
            }
            continue
        m = EXPORT_RE.match(line)
        if m:
            name, decl = m.groups()
            fields[name] = {"type": decl, "range": None}
    return fields


def _scan_scripts(project_root):
    """Map each class_name to (absolute path, extends target, exports)."""
    entries = {}
    for path in _iter_files(project_root, ".gd"):
        text = _read_text(path)
        if text is None:
            continue
        class_name = None
        extends = None
        for line in text.splitlines():
            m = CLASS_NAME_RE.match(line)
            if m:
                class_name = m.group(1)
            else:
                m = EXTENDS_RE.match(line)
                if m:
                    extends = m.group(1)
            if class_name and extends:
                break
        if class_name:
            entries[class_name] = (path, extends, parse_script_exports(text))
    return entries


def _resource_classes(entries):
    """Set of class names that derive from Resource, transitively."""
    result = set()
    for name in entries:
        seen = set()
        current = name
        while True:
            if current in seen:
                break
            seen.add(current)
            if current == "Resource":
                result.add(name)
                break
            entry = entries.get(current)
            if not entry:
                break
            current = entry[1]
            if current is None:
                break
    return result


def _classify_value(token):
    """Classify a raw .tres property value token as 'int', 'float',
    'string', 'bool' or 'other'."""
    if INT_RE.match(token):
        return "int"
    if FLOAT_RE.match(token) and ("." in token or "e" in token or "E" in token):
        return "float"
    if STRING_RE.match(token):
        return "string"
    if token in ("true", "false"):
        return "bool"
    return "other"


def _check_value(issue_file, line, name, value, field, issues):
    category = _classify_value(value)
    decl = field["type"]
    if decl == "int" and category != "int":
        issues.append(
            {
                "file": issue_file,
                "line": line,
                "code": "WRONG_TYPE",
                "detail": "field '{}' expects int, got {}".format(name, category),
            }
        )
    elif decl == "float" and category not in ("int", "float"):
        issues.append(
            {
                "file": issue_file,
                "line": line,
                "code": "WRONG_TYPE",
                "detail": "field '{}' expects float, got {}".format(name, category),
            }
        )
    elif decl == "String" and category != "string":
        issues.append(
            {
                "file": issue_file,
                "line": line,
                "code": "WRONG_TYPE",
                "detail": "field '{}' expects String, got {}".format(name, category),
            }
        )
    elif decl == "bool" and category != "bool":
        issues.append(
            {
                "file": issue_file,
                "line": line,
                "code": "WRONG_TYPE",
                "detail": "field '{}' expects bool, got {}".format(name, category),
            }
        )
    rng = field["range"]
    if rng and category in ("int", "float"):
        number = int(value) if category == "int" else float(value)
        if number < rng[0] or number > rng[1]:
            issues.append(
                {
                    "file": issue_file,
                    "line": line,
                    "code": "OUT_OF_RANGE",
                    "detail": "field '{}' value {} is outside {}".format(
                        name, value, field.get("range_text", "@export_range")
                    ),
                }
            )


def _fields_for(class_name, entries, cache):
    """@export fields of a class including inherited ones; the
    most-derived class's fields win on name clashes."""
    if class_name in cache:
        return cache[class_name]
    fields = {}
    entry = entries.get(class_name)
    if entry and entry[1] and entry[1] in entries:
        for key, value in _fields_for(entry[1], entries, cache).items():
            fields[key] = value
    if entry:
        for key, value in entry[2].items():
            fields[key] = value
    cache[class_name] = fields
    return fields


def _parse_resource(text):
    """Split a .tres text into (header_line, ext_paths, script_id,
    resource_line, props). props is a list of (line, name, value)."""
    lines = text.splitlines()
    header_line = None
    for i, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped and not stripped.startswith(";"):
            header_line = i
            break
    ext_paths = {}
    script_id = None
    resource_line = None
    props = []
    in_resource = False
    for i, line in enumerate(lines, start=1):
        stripped = line.strip()
        m = TRES_EXT_RESOURCE_RE.match(line)
        if m:
            idm = TRES_EXT_ID_RE.search(line)
            if idm:
                ext_paths[idm.group(1)] = m.group(1)
            continue
        if RESOURCE_SECTION_RE.match(stripped):
            resource_line = i
            in_resource = True
            continue
        if in_resource and stripped.startswith("["):
            in_resource = False
            continue
        if not in_resource:
            continue
        m = TRES_SCRIPT_RE.match(stripped)
        if m:
            script_id = m.group(1)
            continue
        m = PROP_RE.match(stripped)
        if m:
            props.append((i, m.group(1), m.group(2)))
    return header_line, ext_paths, script_id, resource_line, props


def check_resource_text(text, rel_path, fields, issues):
    """Check one .tres text against its script's @export fields.

    Returns (id_value, resource_line) for the caller's id bookkeeping,
    or None if the file was unusable (a BAD_FORMAT issue was already
    appended)."""
    header_line, ext_paths, script_id, resource_line, props = _parse_resource(text)
    if header_line is None or not RESOURCE_HEADER_RE.match(
        text.splitlines()[header_line - 1].strip()
    ):
        issues.append(
            {
                "file": rel_path,
                "line": header_line or 1,
                "code": "BAD_FORMAT",
                "detail": "first line is not a [gd_resource] header",
            }
        )
        return None
    if resource_line is None:
        issues.append(
            {
                "file": rel_path,
                "line": header_line,
                "code": "BAD_FORMAT",
                "detail": "file has no [resource] section",
            }
        )
        return None

    script_rel = ext_paths.get(script_id, "")
    id_value = None
    for i, name, value in props:
        if name == "id":
            id_value = value
        if name not in fields:
            issues.append(
                {
                    "file": rel_path,
                    "line": i,
                    "code": "UNKNOWN_FIELD",
                    "detail": "field '{}' is not an @export of script '{}'".format(
                        name, script_rel
                    ),
                }
            )
            continue
        _check_value(rel_path, i, name, value, fields[name], issues)
    return id_value, resource_line


def validate_project(project_root):
    """Validate a project directory. Returns a list of issue dicts
    (keys: file, line, code, detail), sorted by (file, line)."""
    project_root = os.path.abspath(project_root)
    issues = []

    entries = _scan_scripts(project_root)
    resource_classes = _resource_classes(entries)
    script_to_class = {}
    for name in resource_classes:
        script_to_class[os.path.abspath(entries[name][0])] = name

    cache = {}
    id_locations = {}
    missing_id = []

    for path in sorted(_iter_files(project_root, ".tres"), key=os.path.normcase):
        rel_path = os.path.relpath(path, project_root).replace(os.sep, "/")
        text = _read_text(path)
        if text is None:
            issues.append(
                {
                    "file": rel_path,
                    "line": 1,
                    "code": "BAD_FORMAT",
                    "detail": "file is not decodable as UTF-8 text",
                }
            )
            continue

        parsed = _parse_resource(text)
        header_line, ext_paths, script_id, resource_line, props = parsed
        lines = text.splitlines()
        if header_line is None:
            issues.append(
                {
                    "file": rel_path,
                    "line": 1,
                    "code": "BAD_FORMAT",
                    "detail": "file is empty",
                }
            )
            continue
        if not RESOURCE_HEADER_RE.match(lines[header_line - 1].strip()):
            issues.append(
                {
                    "file": rel_path,
                    "line": header_line,
                    "code": "BAD_FORMAT",
                    "detail": "first line is not a [gd_resource] header",
                }
            )
            continue
        if resource_line is None:
            issues.append(
                {
                    "file": rel_path,
                    "line": header_line,
                    "code": "BAD_FORMAT",
                    "detail": "file has no [resource] section",
                }
            )
            continue
        if script_id is None or script_id not in ext_paths:
            continue
        res_rel = ext_paths[script_id]
        if not res_rel.endswith(".gd"):
            continue
        script_abs = os.path.abspath(
            os.path.join(project_root, res_rel[len("res://"):])
        )
        class_name = script_to_class.get(script_abs)
        if class_name is None:
            continue
        fields = _fields_for(class_name, entries, cache)

        result = check_resource_text(text, rel_path, fields, issues)
        if result is None:
            continue
        id_value, resource_line = result

        if "id" not in fields:
            continue
        if id_value is None:
            missing_id.append((rel_path, resource_line, class_name))
        else:
            id_display = id_value.strip('"')
            key = (class_name, id_display)
            if key in id_locations:
                first_rel, first_line = id_locations[key]
                prop_line = resource_line
                for i, name, value in parsed[4]:
                    if name == "id":
                        prop_line = i
                        break
                issues.append(
                    {
                        "file": rel_path,
                        "line": prop_line,
                        "code": "DUPLICATE_ID",
                        "detail": "id '{}' also set in {} (line {})".format(
                            id_display, first_rel, first_line
                        ),
                    }
                )
            else:
                id_locations[key] = (rel_path, resource_line)

    for rel_path, line, class_name in missing_id:
        issues.append(
            {
                "file": rel_path,
                "line": line,
                "code": "MISSING_ID",
                "detail": "class '{}' declares an 'id' export but this resource does not set it".format(
                    class_name
                ),
            }
        )

    issues.sort(key=lambda item: (item["file"], item["line"]))
    return issues


def format_issue(issue):
    return "{}:{}: {} {}".format(
        issue["file"], issue["line"], issue["code"], issue["detail"]
    )


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    as_json = False
    paths = []
    for arg in argv:
        if arg == "--json":
            as_json = True
        else:
            paths.append(arg)

    if len(paths) != 1 or not os.path.isdir(paths[0]):
        sys.stderr.write("usage: python tools/validate_data.py <project_path> [--json]\n")
        return 2

    issues = validate_project(paths[0])
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
