"""Checker for Godot 4 project.godot files.

Reports deviations from the pixel-art render contract and basic
project hygiene. Read-only: never modifies project.godot.

Usage:
    python tools/project_settings_check.py <project_path> [--json] [--profile pixel2d]
"""
import json
import os
import re
import sys

# Full dotted setting name -> (expected raw value, description).
# None expected value means "must be present (any value)".
PIXEL2D_SETTINGS = [
    ("display/window/size/viewport_width", None, "viewport_width present"),
    ("display/window/size/viewport_height", None, "viewport_height present"),
    ("display/window/stretch/mode", "viewport", 'stretch/mode == "viewport"'),
    ("display/window/stretch/aspect", "keep", 'stretch/aspect == "keep"'),
    ("display/window/stretch/scale_mode", "integer", 'stretch/scale_mode == "integer"'),
    ("rendering/textures/canvas_textures/default_texture_filter", "0",
     "default_texture_filter == 0 (nearest)"),
    ("rendering/2d/snap/snap_2d_transforms_to_pixel", "true",
     "snap_2d_transforms_to_pixel == true"),
    ("rendering/2d/snap/snap_2d_vertices_to_pixel", "true",
     "snap_2d_vertices_to_pixel == true"),
]


def parse_project_godot(text):
    """Parse project.godot as INI-like text.

    Returns (settings, autoloads): settings is a dict of
    "section/key" -> value, autoloads is a list of (name, raw_value)
    in file order. Quoted strings have their quotes stripped; Godot
    literals such as Vector2i(480, 270) pass through unchanged.
    Multi-line braced values (input actions) are joined.
    """
    settings = {}
    autoloads = []
    section = None
    pending_key = None
    pending_value_lines = []
    depth = 0

    def flush():
        nonlocal pending_key, pending_value_lines
        if pending_key is not None:
            settings[pending_key] = normalize_value(
                "\n".join(pending_value_lines).strip()
            )
            pending_key = None
            pending_value_lines = []

    for raw_line in text.splitlines():
        if pending_key is not None:
            pending_value_lines.append(raw_line)
            depth += raw_line.count("{") - raw_line.count("}")
            if depth <= 0:
                flush()
            continue
        line = raw_line.strip()
        if not line or line.startswith(";") or line.startswith("#"):
            continue
        m = re.match(r"^\[([^\]]*)\]$", line)
        if m:
            section = m.group(1)
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if section is None:
            continue
        if section == "autoload":
            autoloads.append((key, value))
        else:
            prefix = "" if key.startswith(section + "/") else section + "/"
            settings[prefix + key] = normalize_value(value)
            depth = value.count("{") - value.count("}")
            if depth > 0:
                pending_key = prefix + key
                pending_value_lines = [value]
    flush()
    return settings, autoloads


def normalize_value(value):
    """Strip matching surrounding double quotes; pass literals through."""
    if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
        return value[1:-1]
    return value


def resolve_res(path, project_root):
    """Resolve a res:// path (or relative path) against the project root."""
    target = path
    if target.startswith("res://"):
        target = target[len("res://"):]
    return os.path.normpath(os.path.join(project_root, target))


def check_main_scene(settings, project_root):
    value = settings.get("application/run/main_scene")
    if value is None or value == "":
        return "MISSING", "application/run/main_scene is not set"
    path = resolve_res(value, project_root)
    if not os.path.isfile(path):
        return "FAIL", "main_scene '{}' does not exist".format(value)
    return "PASS", "main_scene '{}' exists".format(value)


def check_autoloads(autoloads, project_root):
    if not autoloads:
        return "PASS", "no autoloads defined"
    for name, raw in autoloads:
        target = normalize_value(raw)
        if target.startswith("*"):
            target = target[1:]
        path = resolve_res(target, project_root)
        if not os.path.isfile(path):
            return "FAIL", "autoload '{}' -> '{}' does not exist".format(name, target)
    return "PASS", "all {} autoload(s) point to existing files".format(len(autoloads))


def check_settings(settings):
    results = []
    for full_name, expected, description in PIXEL2D_SETTINGS:
        if full_name not in settings:
            results.append((full_name, "MISSING", "setting is absent ({})".format(description)))
            continue
        value = settings[full_name]
        if expected is not None and not _values_equal(value, expected):
            results.append(
                (full_name, "FAIL", "expected {}, found {}".format(expected, value))
            )
        else:
            results.append((full_name, "PASS", "{}: {}".format(description, value)))
    return results


def _values_equal(actual, expected):
    if actual == expected:
        return True
    low = actual.lower()
    if low in ("true", "false"):
        return expected == low
    try:
        return int(actual) == int(expected)
    except (TypeError, ValueError):
        return False


def run_checks(project_root, profile):
    """Return (checks, autoload_order) for the given profile."""
    godot_path = os.path.join(project_root, "project.godot")
    try:
        with open(godot_path, "r", encoding="utf-8") as handle:
            text = handle.read()
    except OSError:
        return [("project.godot", "FAIL", "cannot read {}".format(godot_path))], []

    settings, autoloads = parse_project_godot(text)
    checks = check_settings(settings)
    checks.append(
        ("application/run/main_scene",) + check_main_scene(settings, project_root)
    )
    checks.append(("autoloads",) + check_autoloads(autoloads, project_root))
    return checks, [name for name, _ in autoloads]


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    as_json = False
    profile = "pixel2d"
    paths = []
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--json":
            as_json = True
        elif arg == "--profile":
            i += 1
            if i >= len(argv):
                sys.stderr.write("usage: --profile requires a value\n")
                return 2
            profile = argv[i]
        else:
            paths.append(arg)
        i += 1

    if len(paths) != 1:
        sys.stderr.write(
            "usage: python tools/project_settings_check.py "
            "<project_path> [--json] [--profile pixel2d]\n"
        )
        return 2
    project_root = paths[0]

    if profile != "pixel2d":
        sys.stderr.write("unknown profile: {}\n".format(profile))
        return 2

    checks, autoload_order = run_checks(project_root, profile)
    counts = {"PASS": 0, "FAIL": 0, "MISSING": 0}
    for _, status, _ in checks:
        counts[status] += 1
    ok = counts["FAIL"] == 0 and counts["MISSING"] == 0

    if as_json:
        payload = {
            "project": os.path.abspath(project_root),
            "profile": profile,
            "checks": [
                {"check": name, "status": status, "detail": detail}
                for name, status, detail in checks
            ],
            "autoload_order": autoload_order,
            "summary": counts,
            "ok": ok,
        }
        print(json.dumps(payload, indent=2))
    else:
        for name, status, detail in checks:
            line = "{} {}".format(status, name)
            if status != "PASS":
                line += "  ({})".format(detail)
            print(line)
        print("autoload order: {}".format(
            ", ".join(autoload_order) if autoload_order else "(none)"))
        print("{}: {} passed, {} failed, {} missing".format(
            "OK" if ok else "FAIL", counts["PASS"], counts["FAIL"], counts["MISSING"]))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
