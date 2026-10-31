# Hermes LAB bounded repair — safe operation and acceptance

Scope: existing Draft PR #4 on hermes-lab/actions-publisher-20261029-01 and existing Codespace dreadful-wraith only. This does not grant Honey Core, B07, Production or unattended authority.

## Tested milestone

- Hermes real OAuth + FREE Nous model once generated original Python TEST source; previous GitHub Windows readback #41054617502 PASS 12/12.
- New Windows state-machine and broker adversarial QA #41057462177 PASS 17/17. These 17 cases use FIXTURE responses and do NOT prove actual Hermes autonomous repair.
- Source now includes repair_loop.py, codespaces_repair_loop.sh, repair_broker.py and test_bounded_repair.py. A separate Windows workflow is armed ONLY for publication to hermes_lab_local/repair_generated/.

## Live execution gate, not yet accomplished

Only a trusted, write-capable operator of the EXISTING Codespace may run the one-shot command: bash hermes_lab_local/codespaces_repair_loop.sh. It uses the unprivileged honey-hermes-test account and current private Nous OAuth, disables nonessential tools, pins upstage/solar-mini4:free and Hermes SHA, and keeps source and logs outside Git. Task ID is fixed and mkdir fails on replay. One initial model response plus max TWO QA-triggered repair turns. Provider errors get ZERO retries, and unsuccessful QA gets no publication. No recurring watcher/daemon, paid model fallback, new Codespace, or user credentials in Git.

If private acceptance prints HERMES_REAL_LAB_PRIVATE_QA_PASS_SHA=..., only the separate trusted operator may run: python3 -m hermes_lab_local.repair_broker. This broker refuses a dirty worktree, a changed remote branch HEAD, another repository, duplicate artifact paths or bad SHA/QA/provenance; only two new LAB files get a single non-force push. Production remains untouched. The independent Windows workflow hermes-lab-real-repair-readback.yml then verifies immutable Git blob bytes and explicit false authority claims.

Acceptance levels are strictly different: fixture QA PASS != real Hermes repaired FAIL != GitHub SHA PASS != fully unattended E2E. Each requires distinct real run IDs, SHA, and genuine evidence. If Codespace terminal control is unavailable, do not pretend a model call ran. Work quota does not authorize a third-party paid browser runner, Desktop Commander fallback or copying OAuth out of the host.

Resume: first read current PR #4 HEAD, reconcile existing Codespace local diff without force/reset, confirm OAuth remains logged in (no re-login), free tier and resource budget, then run one supervised real bounded repair test. If it already passed on initial attempt, the full two-repair path is only state-machine-tested, not live demonstrated. On provider error stop, no infinite loop or spending.