"""Pixel-art asset import checker for Godot 4 projects.

Scans a project's assets folder for image files (.png, .webp, .svg), looks at
each file's sibling ".import" settings, and flags import options that will blur
or otherwise break pixel art.

Usage:
    python tools/asset_import_check.py <project_path> [--json] [--assets-dir assets]

Exit status:
    0  no findings other than warnings
    1  one or more non-warning findings
"""
import argparse
import json
import os
import sys

IMAGE_EXTENSIONS = (".png", ".webp", ".svg")

# Keys in a paths.json that may name the default assets directory.
ASSETS_DIR_KEYS = ("assets_dir", "assets")


def find_assets_dir(project_path, assets_dir_arg):
    """Resolve the assets directory to scan.

    An explicit --assets-dir wins. Otherwise read <project>/tools/paths.json and
    use its assets directory key if present. Otherwise fall back to "assets".
    The result is always resolved relative to project_path.
    """
    if assets_dir_arg:
        return os.path.normpath(os.path.join(project_path, assets_dir_arg))

    paths_json = os.path.join(project_path, "tools", "paths.json")
    try:
        with open(paths_json, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        data = None
    if isinstance(data, dict):
        for key in ASSETS_DIR_KEYS:
            value = data.get(key)
            if isinstance(value, str) and value:
                return os.path.normpath(os.path.join(project_path, value))
    return os.path.normpath(os.path.join(project_path, "assets"))


def iter_image_files(assets_dir):
    """Yield every image file (png/webp/svg) under assets_dir, sorted by path."""
    if not os.path.isdir(assets_dir):
        return
    found = []
    for root, _dirs, files in os.walk(assets_dir):
        for name in files:
            if name.lower().endswith(IMAGE_EXTENSIONS):
                found.append(os.path.join(root, name))
    for path in sorted(found):
        yield path


def read_png_size(path):
    """Return (width, height) from a PNG IHDR block, or None if not readable."""
    try:
        with open(path, "rb") as handle:
            data = handle.read(33)
    except OSError:
        return None
    if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    width = int.from_bytes(data[16:20], "big")
    height = int.from_bytes(data[20:24], "big")
    return width, height


def parse_import_file(path):
    """Parse a Godot .import file (INI-like) into {key: value}.

    Keys are the raw key names (e.g. "mipmaps/generate", "filter"), section
    headings aside. Later duplicate keys overwrite earlier ones.
    """
    settings = {}
    try:
        with open(path, "r", encoding="utf-8") as handle:
            lines = handle.read().splitlines()
    except OSError:
        return settings
    for line in lines:
        line = line.strip()
        if not line or line.startswith("[") or line.startswith(("#", ";")):
            continue
        if "=" not in line:
            continue
        key, _sep, value = line.partition("=")
        settings[key.strip()] = value.strip()
    return settings


def _is_true(value):
    return value.strip().strip('"').lower() in ("true", "1", "yes")


def _under_art_or_sprites(rel_path):
    parts = [p.lower() for p in rel_path.replace(os.sep, "/").split("/")]
    return "art" in parts or "sprites" in parts


def check_file(image_path, project_path):
    """Return a list of finding dicts for a single image file."""
    findings = []
    rel_path = os.path.relpath(image_path, project_path)
    display = rel_path.replace(os.sep, "/")
    name = os.path.basename(image_path).lower()

    import_path = image_path + ".import"
    if not os.path.isfile(import_path):
        findings.append(
            {
                "file": display,
                "code": "MISSING_IMPORT",
                "detail": "no sibling '{}.import' found".format(
                    os.path.basename(image_path)
                ),
                "warning": False,
            }
        )
        return findings

    settings = parse_import_file(import_path)

    mipmap_value = settings.get("mipmaps/generate")
    if mipmap_value is not None and _is_true(mipmap_value):
        findings.append(
            {
                "file": display,
                "code": "MIPMAPS_ON",
                "detail": "mipmaps/generate=true".format(),
                "warning": False,
            }
        )

    compress_mode = settings.get("compress/mode")
    if compress_mode in ("1", "2") and _under_art_or_sprites(rel_path):
        kind = "lossy" if compress_mode == "1" else "VRAM compressed"
        findings.append(
            {
                "file": display,
                "code": "LOSSY",
                "detail": "compress/mode={} ({}) for a file under an art/sprites folder".format(
                    compress_mode, kind
                ),
                "warning": False,
            }
        )

    for key, value in settings.items():
        if "filter" in key.lower() and _is_true(value):
            findings.append(
                {
                    "file": display,
                    "code": "FILTER_ON",
                    "detail": "{} is enabled".format(key),
                    "warning": False,
                }
            )

    if name.endswith(".png") and ("atlas" in name or "sheet" in name):
        size = read_png_size(image_path)
        if size is not None:
            width, height = size
            if width % 8 != 0 or height % 8 != 0:
                findings.append(
                    {
                        "file": display,
                        "code": "NPOT_ATLAS",
                        "detail": "PNG {}x{} is not a multiple of 8".format(width, height),
                        "warning": True,
                    }
                )

    return findings


def scan(project_path, assets_dir_arg=None):
    """Run the check over the assets dir; return a list of finding dicts."""
    assets_dir = find_assets_dir(project_path, assets_dir_arg)
    findings = []
    for image_path in iter_image_files(assets_dir):
        findings.extend(check_file(image_path, project_path))
    return findings


def render_text(findings):
    lines = []
    for finding in findings:
        lines.append(
            "{}: {} {}".format(finding["file"], finding["code"], finding["detail"])
        )
    issues = sum(1 for f in findings if not f["warning"])
    warnings = sum(1 for f in findings if f["warning"])
    lines.append("Summary: {} issue(s), {} warning(s)".format(issues, warnings))
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Flag image imports that will blur or break pixel art."
    )
    parser.add_argument("project_path", help="path to the Godot project root")
    parser.add_argument("--json", action="store_true", help="emit a JSON list of findings")
    parser.add_argument(
        "--assets-dir",
        default=None,
        help="assets directory (relative to project_path); defaults from tools/paths.json or 'assets'",
    )
    args = parser.parse_args(argv)

    findings = scan(args.project_path, args.assets_dir)

    if args.json:
        print(json.dumps(findings, indent=2))
    elif findings:
        print(render_text(findings))
    else:
        print("OK")

    has_issues = any(not f["warning"] for f in findings)
    return 1 if has_issues else 0


if __name__ == "__main__":
    sys.exit(main())
