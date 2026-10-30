#!/usr/bin/env bash
# Hosted TEST admission only: no Hermes execution, secrets, network, or GitHub writes.
set -euo pipefail
umask 077
EXPECTED="baonguyenlgn-ship-it/honey-hermes-smoke-lab"
BRANCH="hermes-lab/actions-publisher-20261029-01"
USER_NAME="honey-hermes-test"
BASE="/workspaces/.honey-hermes-test"
if [[ "${CODESPACES:-}" != "true" ]]; then echo "CODESPACES_ONLY"; exit 21; fi
if [[ "$(git rev-parse --is-inside-work-tree)" != "true" ]]; then echo "NOT_GIT_REPO"; exit 22; fi
url="$(git remote get-url origin)"
case "$url" in
  "https://github.com/$EXPECTED"|"https://github.com/$EXPECTED.git"|"git@github.com:$EXPECTED.git") ;;
  *) echo "WRONG_LAB_REPOSITORY"; exit 23 ;;
esac
if [[ "$(git branch --show-current)" != "$BRANCH" ]]; then echo "WRONG_LAB_BRANCH"; exit 24; fi
if ! sudo -n true; then echo "NO_NONINTERACTIVE_ADMIN_FOR_ISOLATION"; exit 25; fi
if ! id "$USER_NAME" >/dev/null 2>&1; then
  sudo -n useradd --system --create-home --shell /bin/bash "$USER_NAME"
fi
sudo -n mkdir -p "$BASE/home/.hermes" "$BASE/source" "$BASE/sandbox" "$BASE/inbox"
sudo -n chown -R "$USER_NAME:$USER_NAME" "$BASE"
sudo -n chmod 700 "$BASE" "$BASE/home" "$BASE/home/.hermes" "$BASE/source" "$BASE/sandbox" "$BASE/inbox"
if [[ -e "$BASE/home/.hermes/auth.json" ]]; then
  sudo -n chmod 600 "$BASE/home/.hermes/auth.json"
fi
# No mirror of GitHub OAuth/session credentials into the low-privilege user.
if sudo -n -u "$USER_NAME" test -r "/home/vscode/.config/gh/hosts.yml"; then
  echo "GITHUB_CREDENTIALS_READABLE_BY_HERMES_REFUSE"; exit 26
fi
echo "HERMES_CODESPACE_ISOLATED_USER_PREPARED"
echo "HERMES_TEST_ROOT=$BASE"
echo "NEXT=Explicit official Nous OAuth on this isolated host only; no status claim yet"
