#!/usr/bin/env bash
# Symlink the versioned hooks in this directory into .git/hooks.
#
# A symlink (rather than a copy) means edits to the tracked hook take effect
# immediately, with no reinstall step.
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
HOOK_SRC="$REPO_ROOT/tools/hooks"
HOOK_DST="$REPO_ROOT/.git/hooks"

for hook in pre-commit; do
    ln -sf "../../tools/hooks/$hook" "$HOOK_DST/$hook"
    echo "installed $hook -> tools/hooks/$hook"
done
