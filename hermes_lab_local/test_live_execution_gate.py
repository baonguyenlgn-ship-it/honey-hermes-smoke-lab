"""NEW bounded-host launch security checks; does NOT call provider, GitHub or ledger."""
import unittest
from unittest.mock import patch

from hermes_lab_local.live_execution_gate import (
    verify_free_account_evidence, run_supervised_once, AdmissionDenied, MODEL
)

NOW = 1793440000


def evidence(**changes):
    base = {
        "schema": "honey.hermes.host-free-account-readback.v1",
        "source": "AUTHENTICATED_NOUS_ACCOUNT",
        "plan": "FREE",
        "model_id": MODEL,
        "account_free_verified": True,
        "input_usd_per_million": 0,
        "output_usd_per_million": 0,
        "observed_at": NOW - 10,
        "no_paid_fallback": True,
    }
    base.update(changes)
    return base


class NewHostLaunchGuards(unittest.TestCase):
    def accepts_only_fresh_zero_price(self, value):
        with self.assertRaises(AdmissionDenied):
            verify_free_account_evidence(value, now=NOW)

    def test_new_fresh_verified_exact_free_snapshot_is_eligible_only(self):
        self.assertIsNone(verify_free_account_evidence(evidence(), now=NOW))

    def test_new_missing_cost_source_denied(self):
        self.accepts_only_fresh_zero_price({})

    def test_new_extra_unreviewed_fields_denied(self):
        self.accepts_only_fresh_zero_price(evidence(override=True))

    def test_new_paid_lookalike_model_denied(self):
        self.accepts_only_fresh_zero_price(evidence(model_id="upstage/solar-mini4"))

    def test_new_wrong_plan_denied(self):
        self.accepts_only_fresh_zero_price(evidence(plan="METERED"))

    def test_new_no_account_proof_denied(self):
        self.accepts_only_fresh_zero_price(evidence(account_free_verified=False))

    def test_new_nonzero_input_price_denied(self):
        self.accepts_only_fresh_zero_price(evidence(input_usd_per_million=0.01))

    def test_new_nonzero_output_price_denied(self):
        self.accepts_only_fresh_zero_price(evidence(output_usd_per_million=0.01))

    def test_new_boolean_zero_price_type_denied(self):
        self.accepts_only_fresh_zero_price(evidence(input_usd_per_million=False))

    def test_new_stale_account_quote_denied(self):
        self.accepts_only_fresh_zero_price(evidence(observed_at=NOW - 121))

    def test_new_future_account_quote_denied(self):
        self.accepts_only_fresh_zero_price(evidence(observed_at=NOW + 1))

    def test_new_paid_fallback_denied(self):
        self.accepts_only_fresh_zero_price(evidence(no_paid_fallback=False))

    def test_new_unprivileged_cannot_touch_lease_or_launch(self):
        with patch("hermes_lab_local.live_execution_gate.os.geteuid",
                   return_value=999, create=True), patch(
                   "hermes_lab_local.live_execution_gate.protected_json"
                   ) as protected, patch(
                   "hermes_lab_local.live_execution_gate.subprocess.run"
                   ) as runner:
            with self.assertRaisesRegex(AdmissionDenied, "AUTHORIZED_CODESPACE"):
                run_supervised_once(6528462845)
            protected.assert_not_called()
            runner.assert_not_called()

    def test_new_bad_live_comment_id_blocks_before_touching_host(self):
        with patch("hermes_lab_local.live_execution_gate.os.geteuid",
                   return_value=1000, create=True), patch.dict(
                   "hermes_lab_local.live_execution_gate.os.environ",
                   {"CODESPACES": "true",
                    "CODESPACE_NAME": "dreadful-wraith-6v5gr7w9x9r7c6rj"}), patch(
                   "hermes_lab_local.live_execution_gate.protected_json"
                   ) as protected:
            with self.assertRaisesRegex(AdmissionDenied, "AUTHORIZED_CODESPACE"):
                run_supervised_once(-1)
            protected.assert_not_called()


if __name__ == "__main__":
    unittest.main()
