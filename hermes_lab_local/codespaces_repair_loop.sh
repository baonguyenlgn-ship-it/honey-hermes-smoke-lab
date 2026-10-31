#!/usr/bin/env bash
# Single supervised DEV/TEST run; no service, polling, paid fallback, or GitHub write.
set -euo pipefail
umask 077
ROOT="/workspaces/.honey-hermes-test"
REPO="$(cd "$(dirname "$0")/.." && pwd)"
[[ "$CODESPACES" == "true" ]] || { echo CODESPACE_ONLY; exit 71; }
[[ "$(git -C "$REPO" branch --show-current)" == "hermes-lab/actions-publisher-20261029-01" ]] || { echo WRONG_LAB_BRANCH; exit 72; }
sudo -n test -d "$ROOT/home/.hermes" || { echo NO_PRIVATE_HOME; exit 73; }
sudo -n runuser -u honey-hermes-test -- env -i HOME="$ROOT/home" HERMES_HOME="$ROOT/home/.hermes" USER="honey-hermes-test" CODESPACES=true PATH="/usr/local/bin:/usr/bin:/bin" PYTHONPATH="$REPO" python3 -m hermes_lab_local.repair_loop
