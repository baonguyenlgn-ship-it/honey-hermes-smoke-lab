"""New V3.1 integration controls using genuine GitHub readback and real TEST enrollment, no fixture signer."""
import json,tempfile,base64,os
from pathlib import Path
from cryptography.hazmat.primitives.serialization import load_pem_public_key,Encoding,PublicFormat
from .one_use_lease_gate import TrustedHostContext,verify_signed_lease,AdmissionDenied
from .gate_bridge import fetch_snapshot,verify_original_inbox_ticket,verify_pr_snapshot
from .execution_adapter import prepare
from .task_binding import runtime_task,RUNTIME_TASK
root=Path(__file__).resolve().parents[1]/"authority_test"
pr,comment=fetch_snapshot()
assert pr["head"]["sha"]==os.environ["GITHUB_SHA"]
original_head=json.loads(comment["body"].partition(chr(10))[2])["expected_head"]
ticket=verify_original_inbox_ticket(comment,original_head)
assert ticket["authorized_for_execution"] is False
assert runtime_task(ticket["task_id"])==RUNTIME_TASK
bundle=json.loads((root/"lease.json").read_text());enrollment=json.loads((root/"enrollment.json").read_text());audit=json.loads((root/"audit.json").read_text())
raw=load_pem_public_key((root/"public.pem").read_bytes()).public_bytes(Encoding.Raw,PublicFormat.Raw)
with tempfile.TemporaryDirectory() as d:
 host=TrustedHostContext(enrollment["custodian"],raw,Path(d)/"not-created.db","uid:999:honey-hermes-test","uid:1000:vscode")
 verify_signed_lease(bundle,ticket,host,now=audit["captured_at"])
 for action in [lambda:prepare(pr,comment,bundle,host,None),lambda:verify_pr_snapshot(pr,expected_head=original_head),lambda:runtime_task("UNAPPROVED_TASK")]:
  try:action()
  except AdmissionDenied:pass
  else:raise AssertionError("FALSE_PASS")
 assert not host.state_db.exists()
print("V31_REAL_UPSTREAM_CONTRACT_AND_TASK_MAPPING_PASS_NO_EXECUTION")
print("LIVE_CONSENT_MISSING_DENIED; STALE_LEASE_HEAD_DENIED; UNKNOWN_TASK_DENIED; LEDGER_WRITES=0")
