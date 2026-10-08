"""Prove that CI ran and was green for a commit.

One command answers one question: "is CI proven green for this commit, and if
not, why?". It reads the GitHub remote from git config, asks gh for the
workflow runs that target a commit, derives a verdict, runs a few static
checks against the workflow files, and reports the repo's default branch.

Usage:
    python tools/ci_proof.py --repo <path> [--sha <commit>] [--json]

Verdicts:
    GREEN     at least one run, all completed runs succeeded
    RED       any completed run did not succeed
    RUNNING   at least one run in progress / queued, none failed
    NO_RUNS   zero runs recorded for the sha
    NO_REMOTE no GitHub remote configured for the repo
    NO_GH     the gh CLI is not installed

Exit codes:
    0 GREEN
    1 RED
    2 RUNNING
    3 NO_RUNS or NO_REMOTE
    4 gh missing
"""
import argparse
import glob
import json
import os
import re
import shutil
import subprocess
import sys

_IN_PROGRESS_STATUSES = {"in_progress", "queued", "waiting"}
_GITHUB_URL_RE = re.compile(r"^(https?://github\.com/|git@github\.com:).*")
_EVENT_RE = re.compile(r"^(push|pull_request):$")
_BRANCHES_RE = re.compile(r"^branches:\s*$")
_BRANCHES_INLINE_RE = re.compile(r"^branches:\s*\[([^\]]*)\]")
_LIST_ITEM_RE = re.compile(r"^-\s+(.*\S)")
_SH_SCRIPT_RE = re.compile(r"([~\w./-]*?/[\w./-]+\.sh|^\./[\w./-]+\.sh|[\w.-]+\.sh)")
# A step's run: line (optionally under a "- " list marker).
_RUN_RE = re.compile(r"\brun:\s*(.*)$")


def _run(args, cwd=None):
    return subprocess.run(
        args,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def github_remote(repo):
    """Return the URL of the first GitHub remote in the repo, else None."""
    result = _run(["git", "remote", "-v"], cwd=repo)
    if result.returncode != 0:
        return None
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        if _GITHUB_URL_RE.match(parts[1]):
            return parts[1]
    return None


def resolve_sha(repo, sha):
    """Return the sha to test, resolving the default to HEAD of the repo."""
    if sha:
        full = _run(["git", "rev-parse", "--verify", sha + "^{commit}"], cwd=repo)
        if full.returncode == 0 and full.stdout.strip():
            return full.stdout.strip()
        return sha
    result = _run(["git", "rev-parse", "HEAD"], cwd=repo)
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def gh_available():
    return shutil.which("gh") is not None


def fetch_runs(repo, sha):
    """Call gh run list for the sha. Returns (ok, runs, error)."""
    fields = "status,conclusion,name,workflowName,headBranch,url"
    result = _run(
        ["gh", "run", "list", "--commit", sha, "--json", fields],
        cwd=repo,
    )
    if result.returncode != 0:
        return False, None, result.stdout.strip()
    try:
        runs = json.loads(result.stdout)
    except (json.JSONDecodeError, ValueError):
        return False, None, result.stdout.strip()
    if not isinstance(runs, list):
        return False, None, result.stdout.strip()
    return True, runs, None


def compute_verdict(runs):
    """Derive the CI verdict from a list of run dicts (status, conclusion)."""
    if not runs:
        return "NO_RUNS"
    completed = [r for r in runs if r.get("status") == "completed"]
    if any((r.get("conclusion") or "").lower() != "success" for r in completed):
        return "RED"
    if any(r.get("status") in _IN_PROGRESS_STATUSES for r in runs):
        return "RUNNING"
    return "GREEN"


def default_branch(repo):
    """Return the repo's default branch name via gh, else None."""
    result = _run(
        ["gh", "repo", "view", "--json", "defaultBranchRef"], cwd=repo
    )
    if result.returncode != 0:
        return None
    try:
        payload = json.loads(result.stdout)
    except (json.JSONDecodeError, ValueError):
        return None
    ref = payload.get("defaultBranchRef") or {}
    name = ref.get("name")
    return name or None


def workflow_files(repo):
    """Return sorted .github/workflows/*.yml paths under repo."""
    pattern = os.path.join(repo, ".github", "workflows", "*.yml")
    return sorted(glob.glob(pattern))


def find_branch_filters(text):
    """Find push / pull_request branch filters. Returns (event, [branches])."""
    results = []
    lines = text.splitlines()
    for idx, raw in enumerate(lines):
        match = _EVENT_RE.match(raw.strip())
        if not match:
            continue
        event = match.group(1)
        branches, found = [], False
        for j in range(idx + 1, len(lines)):
            nxt = lines[j].strip()
            if not nxt or nxt.startswith("#"):
                continue
            if _EVENT_RE.match(nxt):
                break
            if _BRANCHES_RE.match(nxt):
                found = True
                for k in range(j + 1, len(lines)):
                    item = lines[k].strip()
                    if not item:
                        continue
                    m = _LIST_ITEM_RE.match(item)
                    if m:
                        branches.append(m.group(1))
                        continue
                    break
                break
            inline = _BRANCHES_INLINE_RE.match(nxt)
            if inline:
                found = True
                branches = [
                    b.strip() for b in inline.group(1).split(",") if b.strip()
                ]
                break
        if found and branches:
            results.append((event, branches))
    return results


def _sh_scripts_in(text):
    """Return the .sh script paths invoked directly from a run: line."""
    scripts = set()
    for raw in text.splitlines():
        match = _RUN_RE.search(raw)
        if not match:
            continue
        value = match.group(1).strip()
        if value and value[0] in ("'", '"'):
            value = value[1:]
        scripts.update(_SH_SCRIPT_RE.findall(value))
    return sorted(scripts)


def git_file_mode(repo, path):
    """Return the git index mode for a repo-relative path, else None."""
    result = _run(["git", "ls-files", "-s", "--", path], cwd=repo)
    if result.returncode != 0 or not result.stdout.strip():
        return None
    first = result.stdout.splitlines()[0]
    parts = first.split()
    return parts[0] if parts else None


def find_execbit_issues(repo, files):
    """Warnings for .sh called from run: whose git mode is not 100755."""
    warnings = []
    seen = set()
    for path in files:
        try:
            with open(path, "r", encoding="utf-8") as handle:
                text = handle.read()
        except OSError:
            continue
        for script in _sh_scripts_in(text):
            if script in seen:
                continue
            seen.add(script)
            rel = script.lstrip("./")
            mode = git_file_mode(repo, rel)
            if mode is None:
                continue
            if mode != "100755":
                warnings.append(
                    "exec-bit: '{}' is called directly but its git mode is {} "
                    "(expected 100755)".format(script, mode)
                )
    return warnings


def static_warnings(repo):
    """Run all the static workflow checks. Returns a list of warnings."""
    warnings = []
    files = workflow_files(repo)
    if not files:
        warnings.append("workflows: no workflow files found in .github/workflows/")
        return warnings
    for path in files:
        try:
            with open(path, "r", encoding="utf-8") as handle:
                text = handle.read()
        except OSError:
            continue
        name = os.path.relpath(path, repo)
        for event, branches in find_branch_filters(text):
            warnings.append(
                "branch-filter: '{}' limits {} to branches: {}".format(
                    name, event, ", ".join(branches)
                )
            )
    warnings.extend(find_execbit_issues(repo, files))
    return warnings


def _verdict_exit(verdict):
    return {
        "GREEN": 0,
        "RED": 1,
        "RUNNING": 2,
        "NO_RUNS": 3,
        "NO_REMOTE": 3,
        "NO_GH": 4,
    }.get(verdict, 3)


def build_report(repo, sha=None):
    """Assemble the report. Returns (report_dict, exit_code)."""
    report = {
        "verdict": None,
        "sha": None,
        "runs": [],
        "warnings": [],
        "default_branch": None,
    }

    if not gh_available():
        report["verdict"] = "NO_GH"
        report["warnings"].append("gh: gh CLI not found on PATH")
        return report, 4

    report["sha"] = resolve_sha(repo, sha) or (sha or "")

    if github_remote(repo) is None:
        report["verdict"] = "NO_REMOTE"
        report["warnings"].append("remote: no GitHub remote configured")
        report["warnings"].extend(static_warnings(repo))
        return report, 3

    report["default_branch"] = default_branch(repo)

    ok, runs, error = fetch_runs(repo, report["sha"])
    if not ok:
        report["verdict"] = "NO_RUNS"
        report["warnings"].append("gh: failed to list runs: {}".format(error))
        report["warnings"].extend(static_warnings(repo))
        return report, 3

    report["runs"] = runs
    report["verdict"] = compute_verdict(runs)
    report["warnings"].extend(static_warnings(repo))
    return report, _verdict_exit(report["verdict"])


def format_human(report):
    """Render a human-readable summary of the report."""
    lines = []
    lines.append(
        "CI proof for {} -> {}".format(report.get("sha") or "?", report["verdict"])
    )
    if report.get("default_branch"):
        lines.append("Default branch: {}".format(report["default_branch"]))
    runs = report.get("runs") or []
    if runs:
        lines.append("Runs for this commit: {}".format(len(runs)))
        for run in runs:
            lines.append(
                "  - [{}] {} ({}) -> {}".format(
                    run.get("status") or "?",
                    run.get("name") or run.get("workflowName") or "?",
                    run.get("headBranch") or "?",
                    run.get("conclusion") or "pending",
                )
            )
    else:
        lines.append("Runs for this commit: 0")
    warnings = report.get("warnings") or []
    if warnings:
        lines.append("Warnings:")
        for warning in warnings:
            lines.append("  ! {}".format(warning))
    else:
        lines.append("Warnings: none")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Prove that CI ran and was green for a commit."
    )
    parser.add_argument("--repo", required=True, help="path to the git repository")
    parser.add_argument("--sha", default=None, help="commit sha (default: HEAD)")
    parser.add_argument("--json", action="store_true", help="print JSON output")
    args = parser.parse_args(argv)

    repo = os.path.abspath(args.repo)
    if not os.path.isdir(repo):
        payload = {
            "verdict": "NO_REMOTE",
            "sha": None,
            "runs": [],
            "warnings": ["repo: '{}' is not a directory".format(args.repo)],
            "default_branch": None,
        }
        if args.json:
            print(json.dumps(payload))
        else:
            print("error: '{}' is not a directory".format(args.repo))
        return 3

    report, code = build_report(repo, args.sha)
    if args.json:
        print(json.dumps(report))
    else:
        print(format_human(report))
    return code


if __name__ == "__main__":
    sys.exit(main())
