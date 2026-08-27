#!/usr/bin/env bash
# public-repo-guard.sh: pre-push content guard for a public repo.
#
# Blocks a push when the OUTGOING DIFF (added lines only) contains a private term.
# It scans content, not the command string, so it never false-fires on a commit
# message that happens to mention a term.
#
# Install:   ln -sf ../../scripts/public-repo-guard.sh .git/hooks/pre-push
# Configure: put one extended-regex pattern per line in `.private-terms` at the repo
#            root (gitignored). Company names, ticket-id shapes, customer names,
#            internal script names. Keep terms HIGH-SIGNAL; common first names block
#            legitimate prose.
# Override once, for a deliberately genericized worked example:
#            ALLOW_PUBLIC_LEAK=1 git push ...
set -u

[ "${ALLOW_PUBLIC_LEAK:-}" = "1" ] && exit 0

root=$(git rev-parse --show-toplevel 2>/dev/null || echo .)
terms_file="$root/.private-terms"
if [ ! -s "$terms_file" ]; then
  echo "public-repo-guard: no .private-terms file at $root; nothing to scan for." >&2
  echo "public-repo-guard: create it (one regex per line) so this guard does something." >&2
  exit 0
fi
# Join non-empty, non-comment lines into one case-insensitive alternation.
PATTERN=$(grep -vE '^\s*(#|$)' "$terms_file" | paste -sd '|' -)
[ -z "$PATTERN" ] && exit 0

fail=0
while read -r local_ref local_sha remote_ref remote_sha; do
  [ -z "${local_sha:-}" ] && continue
  [[ "$local_sha" =~ ^0+$ ]] && continue   # deletion push, nothing to scan

  if [[ "$remote_sha" =~ ^0+$ ]] || ! git cat-file -e "${remote_sha}^{commit}" 2>/dev/null; then
    base=$(git merge-base "$local_sha" origin/main 2>/dev/null || true)
    # No origin/main yet (first push of a new repo): scan the whole history from the
    # empty tree. A bare "$local_sha" would diff against the WORKING TREE and find nothing.
    [ -z "$base" ] && base=$(git hash-object -t tree /dev/null)
    range="$base..$local_sha"
  else
    range="$remote_sha..$local_sha"
  fi

  hits=$(git diff --no-color "$range" 2>/dev/null \
           | grep -E '^\+' | grep -vE '^\+\+\+' \
           | grep -inE "$PATTERN" || true)
  if [ -n "$hits" ]; then
    echo "BLOCKED: private term in the outgoing diff for ${local_ref:-?}:" >&2
    echo "$hits" | head -20 >&2
    fail=1
  fi
done

if [ "$fail" = 1 ]; then
  {
    echo ""
    echo ">>> This is a PUBLIC repo. Sanitize the diff before pushing."
    echo ">>> Deliberate, genericized worked example?  ALLOW_PUBLIC_LEAK=1 git push ..."
  } >&2
  exit 1
fi
exit 0
