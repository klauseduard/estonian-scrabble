#!/usr/bin/env bash
# Claude Code PostToolUse hook: keep Python files ruff-clean as they are written.
#
# Reads the hook payload on stdin, autofixes the touched .py file, and reports
# anything ruff could not fix back to the model as additionalContext — so the
# violation gets addressed in the same turn rather than surfacing later at
# commit time.
#
# Exits 0 unconditionally. A style hook must never block a write.
set -uo pipefail

payload=$(cat)
file=$(printf '%s' "$payload" | jq -r '.tool_response.filePath // .tool_input.file_path // empty')

[ -n "$file" ] || exit 0
case "$file" in
    *.py) ;;
    *) exit 0 ;;
esac
[ -f "$file" ] || exit 0

root=$(git -C "$(dirname "$file")" rev-parse --show-toplevel 2>/dev/null) || exit 0

if [ -x "$root/.venv/bin/ruff" ]; then
    RUFF="$root/.venv/bin/ruff"
elif command -v ruff >/dev/null 2>&1; then
    RUFF="$(command -v ruff)"
else
    exit 0
fi

cd "$root" || exit 0

# --force-exclude so ruff still honours exclusions when handed an explicit path.
"$RUFF" check --fix --force-exclude "$file" >/dev/null 2>&1

# --quiet so the "All checks passed!" summary does not read as a violation.
remaining=$("$RUFF" check --quiet --force-exclude --output-format=concise "$file" 2>/dev/null) || true
if [ -n "$remaining" ]; then
    jq -n --arg ctx "ruff violations remaining in $file (not auto-fixable, please fix):
$remaining" '{hookSpecificOutput: {hookEventName: "PostToolUse", additionalContext: $ctx}}'
fi

exit 0
