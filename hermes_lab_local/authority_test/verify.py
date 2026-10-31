"""Independent verifier for the real host TEST enrollment; no issuance/model rights."""
import base64, hashlib, json
from pathlib import Path
REPO='baonguyenlgn-ship-it/honey-hermes-smoke-lab'
BRANCH='hermes-lab/actions-publisher-20261029-01'
HOST='dreadful-wraith-6v5gr7w9x9r7c6rj'
HEAD='e6a364d7964377d670ad7d78efe7a7e104f6e504'
PATHS=['hermes_lab_local/repair_generated/normalize_label.py','hermes_lab_local/repair_generated/receipt.json']
def canonical(x): return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
def scope(c, *, head=HEAD,host=HOST,worker='uid:999:honey-hermes-test',broker='uid:1000:vscode'):
 expected={'repo':REPO,'pr':4,'branch':BRANCH,'head':head,'host_id':host,'worker_actor':worker,'broker_actor':broker,'task_id':'LAB-NORMALIZE-REPAIR-V1','model':'upstage/solar-mini4:free','max_repairs':2,'allowed_paths':PATHS,'mode':'test-lab-once','cost_policy':'no-new-billable-service'}
 if any(c.get(k)!=v for k,v in expected.items()): raise ValueError('SCOPE_MISMATCH')
 if not 0<c['expires_at']-c['issued_at']<=900: raise ValueError('TTL')
 return True

def verify(root):
 from cryptography.hazmat.primitives.serialization import load_pem_public_key
 from cryptography.exceptions import InvalidSignature
 root=Path(root); e=json.loads((root/'enrollment.json').read_text()); b=json.loads((root/'lease.json').read_text())
 pub=(root/'public.pem').read_bytes(); assert hashlib.sha256(pub).hexdigest()=='9b31279911d8231e325eeb2decf17708626b8902c081d1861f35581f559d8bab'; key=load_pem_public_key(pub)
 assert hashlib.sha256(pub).hexdigest()==e['public_pem_sha256']
 key.verify(base64.b64decode(e['possession_signature_b64']),e['challenge'].encode())
 key.verify(base64.b64decode(b['sig_b64']),canonical(b['claims'])); scope(b['claims'])
 checks=[]
 for overrides in [{'head':'f'*40},{'host':'wrong-host'},{'worker':'wrong-worker'},{'broker':'wrong-broker'}]:
  try: scope(b['claims'],**overrides)
  except ValueError: checks.append('DENIED_'+next(iter(overrides)))
  else: raise AssertionError('NEGATIVE_FALSE_PASS')
 bad=dict(b['claims'],allowed_paths=['Production/forbidden'])
 try:key.verify(base64.b64decode(b['sig_b64']),canonical(bad))
 except InvalidSignature:checks.append('DENIED_TAMPERED_SIGNATURE')
 else:raise AssertionError('TAMPER_ACCEPTED')
 key.verify((root/'audit.sig').read_bytes(),(root/'audit.json').read_bytes())
 a=json.loads((root/'audit.json').read_text())
 assert a['separate_process_replay_probe']=='REAL_PROCESS_RESTART_REPLAY_DENIED' and a['separate_process_fence_probe']=='REAL_REVOKED_FENCE_DENIED'
 assert a['issuer_is_fixture'] is False and a['claim_count']==1 and a['replay_denied'] and a['restart_replay_denied'] and a['revoked_fence_denied'] and a['worker_key_read_denied']
 assert b['claims']['issued_at']<=a['captured_at']<b['claims']['expires_at']
 assert a['lease_sha256']==hashlib.sha256(canonical(b)).hexdigest()
 assert a['model_calls']==0 and a['live_consent_present'] is False
 print(json.dumps({'status':'REAL_TEST_AUTHORITY_WINDOWS_SIGNATURE_SCOPE_PASS','lease_jti':b['claims']['jti'],'public_pem_sha256':e['public_pem_sha256'],'checks':checks,'live_e2e':False},sort_keys=True))
if __name__=='__main__': verify(Path(__file__).parent)
