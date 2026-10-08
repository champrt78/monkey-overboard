#!/usr/bin/env bash
#
# mutation_proof.sh -- prove that a test can fail.
#
# Reverts the listed source files to --base, runs the --test command,
# records its exit code, always restores the original files, and prints
# "MUTATION_PROOF: PASS" when the test failed on the reverted code
# (exit 0), "MUTATION_PROOF: FAIL (test passed without the change)"
# when it passed (exit 1).
#
# Usage:
#   tools/mutation_proof.sh --base <sha> --test "<command>" <file> [<file> ...]
set -u

BASE=""
TEST_CMD=""
FILES=()

while [ $# -gt 0 ]; do
	case "$1" in
	--base)
		[ $# -ge 2 ] || { echo "MUTATION_PROOF: error: --base needs a value" >&2; exit 2; }
		BASE="$2"; shift 2 ;;
	--test)
		[ $# -ge 2 ] || { echo "MUTATION_PROOF: error: --test needs a value" >&2; exit 2; }
		TEST_CMD="$2"; shift 2 ;;
	*)
		FILES+=("$1"); shift ;;
	esac
done

if [ -z "$BASE" ] || [ -z "$TEST_CMD" ] || [ ${#FILES[@]} -eq 0 ]; then
	echo "MUTATION_PROOF: error: missing --base, --test or file argument(s)" >&2
	echo "Usage: tools/mutation_proof.sh --base <sha> --test \"<command>\" <file> [<file> ...]" >&2
	exit 2
fi

TOPLEVEL=$(git rev-parse --show-toplevel 2>/dev/null) || {
	echo "MUTATION_PROOF: error: not a git repository" >&2
	exit 2
}
cd "$TOPLEVEL" || exit 2

BASE=$(git rev-parse --verify --quiet "$BASE^{commit}") || {
	echo "MUTATION_PROOF: error: '$BASE' is not a commit in this repository" >&2
	exit 2
}

if [ -n "$(git status --porcelain)" ]; then
	echo "MUTATION_PROOF: error: working tree has uncommitted changes; commit or stash first" >&2
	exit 2
fi

SAVEDIR=$(mktemp -d) || exit 2
REL_FILES=()
for f in "${FILES[@]}"; do
	# Accept cwd-relative or absolute paths; normalize to repo-root-relative
	rel="$f"
	case "$f" in
	"$TOPLEVEL"/*) rel="${f#"$TOPLEVEL"/}" ;;
	esac
	if [ ! -e "$rel" ]; then
		echo "MUTATION_PROOF: error: file not found in worktree: $rel" >&2
		rm -rf "$SAVEDIR"
		exit 2
	fi
	REL_FILES+=("$rel")
done

RESTORED=0
cleanup() {
	[ "$RESTORED" -eq 1 ] && return
	RESTORED=1
	local f
	for f in "${REL_FILES[@]}"; do
		cp -f "$SAVEDIR/$f" "$f"
	done
	rm -rf "$SAVEDIR"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

for f in "${REL_FILES[@]}"; do
	saved="$SAVEDIR/$f"
	mkdir -p "$(dirname "$saved")"
	cp -f "$f" "$saved"
done

for f in "${REL_FILES[@]}"; do
	if git cat-file -e "$BASE:$f" 2>/dev/null; then
		git show "$BASE:$f" > "$f"
	else
		rm -f "$f"
	fi
done

bash -c "$TEST_CMD"
TEST_RC=$?

cleanup
trap - EXIT INT TERM

if [ "$TEST_RC" -ne 0 ]; then
	echo "MUTATION_PROOF: PASS"
	exit 0
fi
echo "MUTATION_PROOF: FAIL (test passed without the change)"
exit 1
