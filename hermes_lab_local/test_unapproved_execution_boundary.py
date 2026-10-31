"""Reproduce the actual unreviewed execution-permission seam.

All host, GitHub, signer/ledger and subprocess functions are mocked.  A test
failing here is a *real source contract bug*, not proof of provider behavior.
"""
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from hermes_lab_local.live_execution_gate import (
    AdmissionDenied, run_supervised_once, HOST, LEASE_FILE, FREE_EVIDENCE
)


class UnapprovedExecutionBoundary(unittest.TestCase):
    def invoke(self, *, prepared, claimed):
        bundle={"claims":{"jti":"test-jti-not-a-real-lease"}}
        host=object()
        fake_pr={"head":{"sha":"does-not-leave-test"}}
        live={"body":"not-an-actual-owner-comment"}
        patches=[
            patch("hermes_lab_local.live_execution_gate.os.geteuid",return_value=1000,create=True),
            patch.dict(os.environ,{"CODESPACES":"true","CODESPACE_NAME":HOST}),
            patch("hermes_lab_local.live_execution_gate.protected_json",side_effect=lambda x:bundle if x==LEASE_FILE else {}),
            patch("hermes_lab_local.live_execution_gate.trusted_context",return_value=host),
            patch("hermes_lab_local.live_execution_gate.fence_check",return_value="mocked"),
            patch("hermes_lab_local.live_execution_gate.verify_free_account_evidence"),
            patch("hermes_lab_local.live_execution_gate.fetch_snapshot",return_value=(fake_pr,{"id":123})),
            patch("hermes_lab_local.live_execution_gate.fetch_live_consent",return_value=live),
            patch("hermes_lab_local.live_execution_gate.prepare",return_value=prepared),
            patch("hermes_lab_local.live_execution_gate.claim",return_value=claimed),
        ]
        entered=[p.__enter__() for p in patches]
        try:
            runner=__import__("unittest.mock",fromlist=["Mock"]).Mock(
                return_value=SimpleNamespace(returncode=0))
            with self.assertRaisesRegex(AdmissionDenied,"EXECUTION_PERMISSION_NOT_GRANTED"):
                run_supervised_once(919191,run_command=runner)
            # Refuse before ledger is claimed OR any model/broker can execute.
            entered[-1].assert_not_called()
            runner.assert_not_called()
        finally:
            for p in reversed(patches):p.__exit__(None,None,None)

    def test_preflight_explicitly_denies_execution_even_when_signed_claim_exists(self):
        self.invoke(
            prepared={"permitted_to_execute":False},
            claimed={"status":"CLAIMED_NOT_EXECUTED",
                     "owner_live_comment_id":919191,"permitted_to_execute":False})

    def test_missing_runtime_permission_fails_closed_before_claim(self):
        self.invoke(prepared={},
            claimed={"status":"CLAIMED_NOT_EXECUTED",
                     "owner_live_comment_id":919191,"permitted_to_execute":False})


if __name__=="__main__":
    unittest.main()
