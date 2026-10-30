"""Explicit legacy-head to live-head binding, requiring BOTH authentic signatures and separate Owner intent.
No model, broker or dispatch here. An old dry-run ticket is preserved unchanged.
"""
import json
from .one_use_lease_gate import AdmissionDenied, verify_signed_lease, claim_once
from .gate_bridge import verify_pr_snapshot, verify_original_inbox_ticket
from .dual_consent import parse_live_owner_comment
from .task_binding import runtime_task

def prepare(pr, legacy_comment, bundle, host, live_comment, *, now=None):
    if live_comment is None:
        raise AdmissionDenied("LIVE_OWNER_EXECUTION_CONSENT_MISSING")
    if not isinstance(bundle,dict) or not isinstance(bundle.get("claims"),dict):
        raise AdmissionDenied("NO_EXTERNAL_SIGNED_LEASE")
    head=bundle["claims"].get("head")
    verify_pr_snapshot(pr,expected_head=head)
    try: original_head=json.loads(legacy_comment["body"].partition(chr(10))[2])["expected_head"]
    except (KeyError,TypeError,ValueError,IndexError):
        raise AdmissionDenied("LEGACY_PACKET_INVALID") from None
    original=verify_original_inbox_ticket(legacy_comment,original_head)
    # Only this intermediate verification copy binds the execution HEAD; legacy data is never changed.
    current=dict(original,expected_head=head)
    claims=verify_signed_lease(bundle,current,host,now=now)
    consent=parse_live_owner_comment(live_comment,original,claims)
    return {"original_ticket":original,"bound_ticket":current,"consent":consent,
            "runtime_task":runtime_task(original["task_id"]),"permitted_to_execute":False}

def claim(pr, legacy_comment, pr_again, bundle, host, live_comment, *, now=None):
    if live_comment is None:
        raise AdmissionDenied("LIVE_OWNER_EXECUTION_CONSENT_MISSING")
    from .host_authority import trusted_context, fence_check
    if trusted_context(bundle)!=host:
        raise AdmissionDenied("CALLER_HOST_CONTEXT_DENIED")
    fence=fence_check(bundle)
    ready=prepare(pr,legacy_comment,bundle,host,live_comment,now=now)
    verify_pr_snapshot(pr_again,expected_head=bundle["claims"]["head"])
    receipt=claim_once(bundle,ready["bound_ticket"],host,now=now)
    if fence_check(bundle)!=fence:
        raise AdmissionDenied("HOST_FENCE_CHANGED")
    return dict(receipt,owner_live_comment_id=ready["consent"]["owner_live_comment_id"],
                runtime_task=ready["runtime_task"],permitted_to_execute=False)
