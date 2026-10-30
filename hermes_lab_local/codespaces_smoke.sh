#!/usr/bin/env bash
# One authorized real Hermes-written file in isolated TEST uid. NO GitHub writes.
set -euo pipefail
umask 077
BASE="/workspaces/.honey-hermes-test"
USER_NAME="honey-hermes-test"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$SCRIPT_DIR/.." && pwd)"
[[ "${CODESPACES:-}" == "true" ]] || { echo CODESPACE_ONLY; exit 51; }
[[ "$(git -C "$REPO" branch --show-current)" == "hermes-lab/actions-publisher-20261029-01" ]] || { echo WRONG_LAB_BRANCH; exit 52; }
sudo -n test -d "$BASE/home/.hermes" || { echo ISOLATION_NOT_PREPARED; exit 53; }
if ! sudo -n -u "$USER_NAME" test -f "$BASE/home/.hermes/auth.json"; then
  echo "OWNER_OAUTH_NOT_COMPLETED"; exit 54
fi
sudo -n -u "$USER_NAME" env -i HOME="$BASE/home" HERMES_HOME="$BASE/home/.hermes" \
  PATH="/usr/local/bin:/usr/bin:/bin" TERM="${TERM:-dumb}" \
  HERMES_TEST_BASE="$BASE" HERMES_LAB_SCRIPT_DIR="$SCRIPT_DIR" bash -c '
    set -euo pipefail
    umask 077
    src="$HERMES_TEST_BASE/source/hermes-agent"
    test -d "$src/.git"
    test "$(git -C "$src" rev-parse HEAD)" = "bf0203a794a07aac3ff764972ab9087baa4e4f4e"
    out="$HERMES_TEST_BASE/inbox/task-01"
    mkdir "$out" # refuse duplicate work; no auto-retry
    printf "%s\n" "Return strictly ONE Python function, no Markdown or explanation:" \
      "def normalize_label(text):" \
      "    return str(text).strip().casefold()" > "$out/request.txt"
    cd "$HERMES_TEST_BASE/sandbox"
    source "$src/activate"
    set +e
    timeout --kill-after=5s 90s hermes chat --query-file "$out/request.txt" --oneshot \
      --format stream-json --max-turns 1 > "$out/stream.jsonl" 2> "$out/diagnostics-private.log"
    status=$?
    set -e
    if [[ "$status" -ne 0 ]]; then
      echo "HERMES_AUTHENTICATED_TURN_FAILED status=$status (private diagnostics retained, not uploaded)"
      exit 55
    fi
    python3 "$HERMES_LAB_SCRIPT_DIR/codespaces_stream_gate.py" "$out/stream.jsonl" "$out/original_response.txt"
    python3 "$HERMES_LAB_SCRIPT_DIR/verify_artifact.py" "$out/original_response.txt" "$out/verified" "codespace-task-01" bf0203a794a07aac3ff764972ab9087baa4e4f4e
    python3 -m py_compile "$out/verified/normalize_label.py"
    echo "HERMES_ORIGINAL_BYTES_PRIVATE_QA_PASS_NO_GITHUB_WRITE"
  '
