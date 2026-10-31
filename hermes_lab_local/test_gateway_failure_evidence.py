"""New isolated Hermes gateway-failure triage checks; zero real model calls."""
import tempfile
import unittest
from pathlib import Path

from hermes_lab_local.gateway_failure_evidence import (
    MAX_LOG_BYTES, diagnose, diagnose_bounded_file,
)

HISTORICAL_CI_FAILURE = (
    "HERMES_LOCAL_CLI_DIAGNOSTIC_FAILURE=⚠️ Something went wrong and "
    "I couldn't finish this reply.\nTechnical details are in the "
    "gateway log (hermes logs)."
)
SENSITIVE = "ghp_xxx_secret_should_never_be_displayed"


class NoSecretTriage(unittest.TestCase):
    def check(self, expected, log):
        result=diagnose(log+f"\nAuthorization: Bearer {SENSITIVE}")
        self.assertEqual(result["classification"],expected)
        self.assertFalse(result["root_cause_proven"])
        self.assertFalse(result["auto_retry_authorized"])
        self.assertFalse(result["live_model_call_performed"])
        self.assertFalse(result["details_disclosed"])
        self.assertFalse(result["production_authorized"])
        self.assertNotIn(SENSITIVE,str(result))

    def test_historical_actual_ci_message_is_not_a_root_cause(self):
        self.check("GATEWAY_GENERIC_FAILURE_ONLY", HISTORICAL_CI_FAILURE)

    def test_custom_provider_without_credentials(self):
        self.check("CUSTOM_PROVIDER_UNBOUND",
                   "AuthError: provider 'custom' resolved without credentials")

    def test_local_401(self):
        self.check("CUSTOM_ENDPOINT_HTTP_401","HTTP 401: Invalid API Key")

    def test_missing_local_endpoint(self):
        self.check("LOCAL_ENDPOINT_UNREACHABLE","Connection refused 127.0.0.1")

    def test_session_busy(self):
        self.check("GATEWAY_SESSION_BUSY","RuntimeStoreError: session_busy")

    def test_context_failure(self):
        self.check("CONTEXT_COMPRESSION_FAILURE","compression exhaustion")

    def test_rate_limit(self):
        self.check("MODEL_RATE_LIMIT","HTTP 429")

    def test_provider_400(self):
        self.check("PROVIDER_REQUEST_REJECTED","Error code: 400")

    def test_unclassified_is_not_auto_fix(self):
        self.check("UNCLASSIFIED_NO_ROOT_CAUSE_PROOF","hello world")

    def test_none_is_untrusted(self):
        self.assertEqual(diagnose(None)["classification"],"INVALID_OR_OVERSIZE_LOG")

    def test_big_log_denied(self):
        self.assertEqual(
            diagnose("A"*(MAX_LOG_BYTES+1))["classification"],
            "INVALID_OR_OVERSIZE_LOG")

    def test_path_is_data_and_not_executed(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/"gateway.log"
            p.write_text(HISTORICAL_CI_FAILURE+"\n"+SENSITIVE,encoding="utf8")
            result=diagnose_bounded_file(p)
            self.assertEqual(result["classification"],"GATEWAY_GENERIC_FAILURE_ONLY")
            self.assertNotIn(SENSITIVE,str(result))

    def test_missing_file_is_denied(self):
        with tempfile.TemporaryDirectory() as folder:
            result=diagnose_bounded_file(Path(folder)/"missing.log")
            self.assertEqual(result["classification"],"INVALID_OR_OVERSIZE_LOG")

    def test_overlarge_file_is_denied(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/"overlarge.log"
            p.write_bytes(b"X"*(MAX_LOG_BYTES+1))
            self.assertEqual(
                diagnose_bounded_file(p)["classification"],
                "INVALID_OR_OVERSIZE_LOG")

    def test_nothing_is_assigned_a_retry_permission(self):
        for t in (HISTORICAL_CI_FAILURE, "HTTP 401", "HTTP 429",
                  "Connection refused", "not an error", None):
            self.assertIs(diagnose(t)["auto_retry_authorized"], False)


if __name__ == "__main__":
    unittest.main()
