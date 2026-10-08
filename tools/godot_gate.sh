#!/usr/bin/env bash
#
# godot_gate.sh -- the S-03 gate in one command.
#
# Runs every gate step against a Godot 4 project and prints one
# "GATE <name> PASS|FAIL|SKIP <detail>" line per step, in this order:
# import, lint, settings, scenes, tests, play. The last line is
# "GATE: PASS" (exit 0) when no step failed, otherwise "GATE: FAIL"
# (exit 1). Everything printed is also saved to
# <out>/gate-<UTC timestamp>.txt, default <project>/qa/gate/.
#
# Only the UNTYPED_FUNC and CODE_AFTER_TRANSITION lint rules block the
# gate; the full lint report is saved with the rest of the output.
#
# Usage:
#   tools/godot_gate.sh <project_path> [--godot <binary>] [--out <dir>] [--skip-play]
#
# Exit codes: 0 gate passed, 1 gate failed, 2 bad usage,
# 3 NEEDS_SETUP (no Godot binary or no Python interpreter found).
set -u

# The sibling tools are found through this script's own folder, so the gate
# works from the gamemachine-tools checkout and from a game's tools/ copy.
SELF_PATH=${BASH_SOURCE[0]:-$0}
case "$SELF_PATH" in
*/*)
	TOOLS_DIR=$(cd "${SELF_PATH%/*}" && pwd) ;;
*)
	TOOLS_DIR=$(pwd) ;;
esac

IMPORT_TIMEOUT=300
RUN_TIMEOUT=900
PLAY_TIMEOUT=300
BLOCKING_RULES="UNTYPED_FUNC,CODE_AFTER_TRANSITION"
PLAY_PATH="qa/playpaths/core.json"

PYTHON_ARG="${PYTHON:-}"
GODOT_ENV="${GODOT:-}"
TIMEOUT_BIN=$(command -v timeout 2>/dev/null)

PROJECT=""
GODOT_ARG=""
OUT_ARG=""
SKIP_PLAY=0
FAILURES=0
LOG_FILE=""
SCRATCH=""

usage() {
	echo "Usage: tools/godot_gate.sh <project_path> [--godot <binary>] [--out <dir>] [--skip-play]" >&2
}

finish() {
	[ -z "$SCRATCH" ] || rm -rf "$SCRATCH"
}
trap finish EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

# --- Output -------------------------------------------------------------------
# Every line goes to stdout and to the log file, so the log holds the full
# detail behind each verdict as well as the GATE lines themselves.

log() {
	printf '%s\n' "$*"
	printf '%s\n' "$*" >> "$LOG_FILE"
}

log_file() {
	[ -s "$1" ] || return 0
	cat "$1"
	cat "$1" >> "$LOG_FILE"
}

gate_line() {
	local name="$1" status="$2" detail="$3"
	[ -n "$detail" ] || detail="see log"
	log "GATE $name $status $detail"
	case "$status" in
	PASS)
		: ;;
	FAIL)
		FAILURES=$((FAILURES + 1)) ;;
	SKIP)
		# play skipped by --skip-play is the only tolerated skip; any other
		# skipped step means the gate did not actually run.
		if [ "$name" = "play" ] && [ "$SKIP_PLAY" -eq 1 ]; then
			:
		else
			FAILURES=$((FAILURES + 1))
		fi ;;
	*)
		FAILURES=$((FAILURES + 1)) ;;
	esac
}

# --- Helpers ------------------------------------------------------------------

run_capped() {
	# run_capped <seconds> <command> [args...] -- exit 124 when the limit hits.
	local seconds="$1"
	shift
	if [ -n "$TIMEOUT_BIN" ]; then
		"$TIMEOUT_BIN" "$seconds" "$@"
	else
		"$@"
	fi
}

last_line() {
	# Last non-empty line of a file, "" when there is none.
	local file="$1"
	[ -s "$file" ] || return 0
	awk 'NF { line = $0 } END { print line }' "$file"
}

count_lines() {
	# count_lines <file> <ERE> -- how many lines match the pattern.
	local file="$1" pattern="$2" count=""
	[ -s "$file" ] || { echo 0; return; }
	count=$(grep -c -E "$pattern" "$file" 2>/dev/null) || true
	[ -n "$count" ] || count=0
	echo "$count"
}

count_test_files() {
	# Number of test_*.gd files under a directory (0 when it does not exist).
	local dir="$1"
	[ -d "$dir" ] || { echo 0; return; }
	find "$dir" -type f -name 'test_*.gd' 2>/dev/null | wc -l | tr -d '[:space:]'
}

strip_ansi() {
	# Runner output is colourised; the counts are parsed from the clean copy.
	sed 's/\x1b\[[0-9;?]*[a-zA-Z]//g' "$1" > "$2"
}

reported_script_count() {
	# reported_script_count <clean output file> <framework>
	# GUT prints a totals line "Scripts <N>", gdUnit4 prints
	# "Executed test suites: (<N>/<M>)". Prints "" when neither appears.
	local file="$1" framework="$2"
	case "$framework" in
	gut)
		sed -n 's/^[[:space:]]*Scripts[[:space:]]\{1,\}\([0-9]\{1,\}\)[[:space:]]*$/\1/p' "$file" | tail -1 ;;
	gdunit4)
		sed -n 's/.*Executed test suites:[[:space:]]*(\([0-9]\{1,\}\)\/.*/\1/p' "$file" | tail -1 ;;
	*)
		echo "" ;;
	esac
}

find_executable() {
	# find_executable <name or path> -- prints a usable path, returns 1 if none.
	local candidate="$1" found=""
	[ -n "$candidate" ] || return 1
	if [ -f "$candidate" ] && [ -x "$candidate" ]; then
		echo "$candidate"
		return 0
	fi
	found=$(command -v "$candidate" 2>/dev/null) || return 1
	[ -n "$found" ] || return 1
	echo "$found"
}

# --- Arguments ----------------------------------------------------------------

while [ $# -gt 0 ]; do
	case "$1" in
	--godot)
		[ $# -ge 2 ] || { echo "godot_gate.sh: error: --godot needs a value" >&2; usage; exit 2; }
		GODOT_ARG="$2"; shift 2 ;;
	--out)
		[ $# -ge 2 ] || { echo "godot_gate.sh: error: --out needs a value" >&2; usage; exit 2; }
		OUT_ARG="$2"; shift 2 ;;
	--skip-play)
		SKIP_PLAY=1; shift ;;
	-h|--help)
		usage; exit 0 ;;
	-*)
		echo "godot_gate.sh: error: unknown option $1" >&2
		usage
		exit 2 ;;
	*)
		if [ -n "$PROJECT" ]; then
			echo "godot_gate.sh: error: more than one project path given" >&2
			usage
			exit 2
		fi
		PROJECT="$1"; shift ;;
	esac
done

if [ -z "$PROJECT" ]; then
	echo "godot_gate.sh: error: missing <project_path>" >&2
	usage
	exit 2
fi

PROJECT_ABS=$(cd "$PROJECT" 2>/dev/null && pwd) || {
	echo "godot_gate.sh: error: project path is not a directory: $PROJECT" >&2
	exit 2
}
PROJECT="$PROJECT_ABS"
if [ ! -f "$PROJECT/project.godot" ]; then
	echo "godot_gate.sh: error: no project.godot in $PROJECT" >&2
	exit 2
fi

GODOT=""
CANDIDATE=""
for CANDIDATE in "$GODOT_ARG" "$GODOT_ENV" "godot"; do
	[ -n "$CANDIDATE" ] || continue
	CANDIDATE=$(find_executable "$CANDIDATE") || continue
	GODOT="$CANDIDATE"
	break
done
if [ -z "$GODOT" ]; then
	echo "NEEDS_SETUP: no Godot binary found (--godot <binary>, \$GODOT, or 'godot' on PATH)" >&2
	exit 3
fi

PYTHON=""
for CANDIDATE in "$PYTHON_ARG" "python" "python3"; do
	[ -n "$CANDIDATE" ] || continue
	CANDIDATE=$(find_executable "$CANDIDATE") || continue
	PYTHON="$CANDIDATE"
	break
done
if [ -z "$PYTHON" ]; then
	echo "NEEDS_SETUP: no Python interpreter found (python or python3 on PATH, or \$PYTHON)" >&2
	exit 3
fi

OUT_ARG=${OUT_ARG:-"$PROJECT/qa/gate"}
if ! mkdir -p "$OUT_ARG" 2>/dev/null; then
	echo "godot_gate.sh: error: cannot create output directory: $OUT_ARG" >&2
	exit 2
fi
OUT_DIR=$(cd "$OUT_ARG" && pwd) || {
	echo "godot_gate.sh: error: cannot enter output directory: $OUT_ARG" >&2
	exit 2
}

SCRATCH=$(mktemp -d) || {
	echo "godot_gate.sh: error: mktemp failed" >&2
	exit 2
}
CAP="$SCRATCH/cap.txt"
CAP_CLEAN="$SCRATCH/cap-clean.txt"

LOG_FILE="$OUT_DIR/gate-$(date -u +%Y%m%d-%H%M%S).txt"
if ! : > "$LOG_FILE"; then
	echo "godot_gate.sh: error: cannot write log file: $LOG_FILE" >&2
	exit 2
fi

log "godot_gate: project=$PROJECT godot=$GODOT python=$PYTHON"
log "godot_gate: log=$LOG_FILE"

# --- Steps --------------------------------------------------------------------

step_import() {
	log "--- import: $GODOT --headless --path <project> --import ---"
	local rc=0
	run_capped "$IMPORT_TIMEOUT" "$GODOT" --headless --path "$PROJECT" --import > "$CAP" 2>&1 || rc=$?
	log_file "$CAP"
	if [ "$rc" -eq 0 ]; then
		gate_line import PASS "godot --import exited 0"
	elif [ "$rc" -eq 124 ]; then
		gate_line import FAIL "godot --import timed out after ${IMPORT_TIMEOUT}s"
	else
		gate_line import FAIL "godot --import exited $rc"
	fi
}

step_lint() {
	# The full report is only saved; the blocking run decides the verdict.
	local rc=0 total=0 blocking=0
	log "--- lint: gdscript_lint.py full report (saved, never blocks) ---"
	"$PYTHON" "$TOOLS_DIR/gdscript_lint.py" "$PROJECT" > "$CAP" 2>&1 || rc=$?
	log_file "$CAP"
	if [ "$rc" -gt 1 ]; then
		gate_line lint FAIL "gdscript_lint.py full report exited $rc"
		return
	fi
	total=$(count_lines "$CAP" '\.gd:[0-9]+: [A-Z_]+ ')

	rc=0
	log "--- lint: gdscript_lint.py --rules $BLOCKING_RULES ---"
	"$PYTHON" "$TOOLS_DIR/gdscript_lint.py" "$PROJECT" --rules "$BLOCKING_RULES" > "$CAP" 2>&1 || rc=$?
	log_file "$CAP"
	case "$rc" in
	0)
		gate_line lint PASS "0 findings in $BLOCKING_RULES, $total finding(s) in the full report" ;;
	1)
		blocking=$(count_lines "$CAP" '\.gd:[0-9]+: [A-Z_]+ ')
		gate_line lint FAIL "$blocking finding(s) in $BLOCKING_RULES" ;;
	*)
		gate_line lint FAIL "gdscript_lint.py exited $rc" ;;
	esac
}

step_settings() {
	log "--- settings: project_settings_check.py ---"
	local rc=0 summary=""
	"$PYTHON" "$TOOLS_DIR/project_settings_check.py" "$PROJECT" > "$CAP" 2>&1 || rc=$?
	log_file "$CAP"
	summary=$(last_line "$CAP")
	if [ "$rc" -eq 0 ]; then
		gate_line settings PASS "$summary"
	else
		gate_line settings FAIL "$summary"
	fi
}

step_scenes() {
	log "--- scenes: scene_lint.py ---"
	local rc=0 issues=0
	"$PYTHON" "$TOOLS_DIR/scene_lint.py" "$PROJECT" > "$CAP" 2>&1 || rc=$?
	log_file "$CAP"
	if [ "$rc" -eq 0 ]; then
		gate_line scenes PASS "no scene or resource issues"
	elif [ "$rc" -eq 1 ]; then
		issues=$(count_lines "$CAP" ':[0-9]+: [A-Z_]+ ')
		gate_line scenes FAIL "$issues issue(s) reported"
	else
		gate_line scenes FAIL "scene_lint.py exited $rc"
	fi
}

step_tests() {
	local framework=""
	if [ -d "$PROJECT/addons/gut" ]; then
		framework="gut"
	elif [ -d "$PROJECT/addons/gdUnit4" ]; then
		framework="gdunit4"
	else
		gate_line tests FAIL "no test framework (neither addons/gut nor addons/gdUnit4)"
		return
	fi

	local rc=0 runner=""
	case "$framework" in
	gut)
		if [ -f "$PROJECT/tools/run_gut.sh" ]; then
			runner="tools/run_gut.sh"
			log "--- tests: GUT via $runner ---"
			( cd "$PROJECT" && bash tools/run_gut.sh ) > "$CAP" 2>&1 || rc=$?
		elif [ -f "$PROJECT/addons/gut/gut_cmdln.gd" ]; then
			runner="addons/gut/gut_cmdln.gd"
			log "--- tests: GUT via $runner ---"
			( cd "$PROJECT" && run_capped "$RUN_TIMEOUT" "$GODOT" --headless --path . \
				-s addons/gut/gut_cmdln.gd -gdir=res://tests -gexit ) > "$CAP" 2>&1 || rc=$?
		else
			gate_line tests FAIL "$framework detected but no runner (tools/run_gut.sh or addons/gut/gut_cmdln.gd)"
			return
		fi ;;
	gdunit4)
		if [ -f "$PROJECT/addons/gdUnit4/bin/GdUnitCmdTool.gd" ]; then
			runner="addons/gdUnit4/bin/GdUnitCmdTool.gd"
			log "--- tests: gdUnit4 via $runner ---"
			( cd "$PROJECT" && run_capped "$RUN_TIMEOUT" "$GODOT" --headless --path . \
				-s -d res://addons/gdUnit4/bin/GdUnitCmdTool.gd -a ./tests -rd ./tests/reports \
				--ignoreHeadlessMode ) > "$CAP" 2>&1 || rc=$?
		else
			gate_line tests FAIL "$framework detected but no runner (addons/gdUnit4/bin/GdUnitCmdTool.gd)"
			return
		fi ;;
	esac

	log_file "$CAP"
	strip_ansi "$CAP" "$CAP_CLEAN"

	local ran="" on_disk="0" problems=""
	ran=$(reported_script_count "$CAP_CLEAN" "$framework")
	on_disk=$(count_test_files "$PROJECT/tests")
	if [ "$rc" -ne 0 ]; then
		if [ "$rc" -eq 124 ]; then
			problems="${problems}${runner} timed out after ${RUN_TIMEOUT}s; "
		else
			problems="${problems}${runner} exited $rc; "
		fi
	fi
	if [ -z "$ran" ]; then
		problems="${problems}could not parse a script count from the output; "
	elif [ "$ran" -ne "$on_disk" ]; then
		problems="${problems}ran $ran script(s), $on_disk test_*.gd files on disk; "
	fi
	if [ -n "$problems" ]; then
		gate_line tests FAIL "${problems%; }"
	else
		gate_line tests PASS "ran $ran script(s), $on_disk test_*.gd files on disk"
	fi
}

step_play() {
	if [ "$SKIP_PLAY" -eq 1 ]; then
		gate_line play SKIP "--skip-play"
		return
	fi
	if [ ! -f "$PROJECT/tools/play_check.gd" ]; then
		gate_line play FAIL "missing play path: tools/play_check.gd not found"
		return
	fi
	if [ ! -f "$PROJECT/$PLAY_PATH" ]; then
		gate_line play FAIL "missing play path: $PLAY_PATH not found"
		return
	fi
	log "--- play: $GODOT --headless -s res://tools/play_check.gd -- --path $PLAY_PATH ---"
	local rc=0 verdict=""
	( cd "$PROJECT" && run_capped "$PLAY_TIMEOUT" "$GODOT" --headless --path . \
		-s res://tools/play_check.gd -- --path "$PLAY_PATH" ) > "$CAP" 2>&1 || rc=$?
	log_file "$CAP"
	verdict=$(grep -E '^PLAY_CHECK: ' "$CAP" | tail -1)
	if [ "$rc" -eq 0 ]; then
		gate_line play PASS "${verdict:-play_check exited 0}"
	elif [ "$rc" -eq 124 ]; then
		gate_line play FAIL "play_check timed out after ${PLAY_TIMEOUT}s"
	else
		gate_line play FAIL "${verdict:-play_check exited $rc}"
	fi
}

step_import
step_lint
step_settings
step_scenes
step_tests
step_play

if [ "$FAILURES" -eq 0 ]; then
	log "GATE: PASS"
	exit 0
fi
log "GATE: FAIL ($FAILURES step(s) failed)"
exit 1
