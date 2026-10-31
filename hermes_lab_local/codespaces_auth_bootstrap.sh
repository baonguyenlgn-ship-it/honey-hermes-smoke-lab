#!/usr/bin/env bash
# Explicit OWNER identity boundary. Run only inside the TEST Codespace after postCreate preflight.
set -euo pipefail
umask 077
BASE="/workspaces/.honey-hermes-test"
USER_NAME="honey-hermes-test"
CHECKOUT="bf0203a794a07aac3ff764972ab9087baa4e4f4e"
[[ "${CODESPACES:-}" == "true" ]] || { echo CODESPACE_ONLY; exit 31; }
[[ "$(git branch --show-current)" == "hermes-lab/actions-publisher-20261029-01" ]] || { echo WRONG_BRANCH; exit 32; }
sudo -n test -d "$BASE/home/.hermes" || { echo HOST_NOT_PREPARED; exit 33; }
sudo -n runuser -u "$USER_NAME" -- env -i HOME="$BASE/home" HERMES_HOME="$BASE/home/.hermes" \
  PATH="/usr/local/bin:/usr/bin:/bin" \
  HERMES_EXPECTED_SHA="$CHECKOUT" HERMES_TEST_BASE="$BASE" bash -c '
  set -euo pipefail
  umask 077
  src="$HERMES_TEST_BASE/source/hermes-agent"
  if [[ ! -d "$src/.git" ]]; then
    mkdir -p "$src"
    git init -q "$src"
    git -C "$src" remote add origin https://github.com/NousResearch/hermes-agent.git
    git -C "$src" fetch -q --depth 1 origin v0.22.5
    test "$(git -C "$src" rev-parse FETCH_HEAD^{commit})" = "$HERMES_EXPECTED_SHA"
    git -C "$src" checkout -q --detach FETCH_HEAD
  fi
  test "$(git -C "$src" rev-parse HEAD)" = "$HERMES_EXPECTED_SHA"
  cd "$src"
  source ./activate
  echo "HERMES_PINNED_INSTALL_READY"
  echo "Owner authentication ONLY: use official Nous Portal browser/device OAuth. Never paste a token."
  hermes auth add nous --type oauth
  hermes setup --portal
  hermes portal info
  '
