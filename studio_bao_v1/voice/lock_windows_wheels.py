"""Record platform-scoped SHA256 wheel lock and prove offline --require-hashes install.
No model download, inference, customer data, or production artifacts.
"""
import hashlib, json, os, pathlib, shutil, subprocess, sys, tempfile

PINS={
    "onnxruntime":"1.23.1", "numpy":"2.2.6", "coloredlogs":"15.0.1",
    "flatbuffers":"25.12.19", "humanfriendly":"10.0", "mpmath":"1.3.0",
    "protobuf":"7.36.2", "pyreadline3":"3.5.6", "sympy":"1.14.0",
    "packaging":"26.3"
}
MAX_BYTES=65000000
out=pathlib.Path(sys.argv[1]).resolve()
out.mkdir(parents=True,exist_ok=True)
data={
  "schema":"honey.m1-windows-wheel-hash-lock.v1",
  "status":"UNTESTED",
  "python_runtime":sys.version.split()[0],
  "platform":sys.platform,
  "package_count_expected":len(PINS),
  "wheel_count":0,
  "total_wheel_bytes":0,
  "wheel_hashes":[],
  "fully_offline_install_pass":False,
  "source_index_used_for_download":"default-pip-index-before-offline-install-only",
  "production_supply_chain_approved":False,
  "model_or_audio_executed":False,
  "transitive_lock_scope":"Windows CPython 3.12 x64; not universal or future-proof",
  "error_type":None
}
wheelhouse=out/"wheelhouse"
target=out/"installed-target"
lockpath=out/"requirements-win-py312-hashes.txt"
error=None
try:
  if sys.platform!="win32" or sys.version_info[:2]!=(3,12):
    raise RuntimeError("PINNED_WINDOWS_PY312_ONLY")
  wheelhouse.mkdir(exist_ok=True)
  reqs=[f"{name}=={version}" for name,version in PINS.items()]
  cmd=[sys.executable,"-m","pip","download","--disable-pip-version-check",
       "--no-input","--no-cache-dir","--only-binary=:all:","--no-deps",
       "--dest",str(wheelhouse),*reqs]
  subprocess.run(cmd,check=True,timeout=200)
  wheels=list(wheelhouse.glob("*.whl"))
  if len(wheels)!=len(PINS):
    raise RuntimeError(f"WHEEL_COUNT_MISMATCH_{len(wheels)}")
  found={}
  for f in wheels:
    parts=f.name.split("-")
    if len(parts)<5:raise RuntimeError("INVALID_WHEEL_FILENAME")
    name=parts[0].replace("_","-").lower()
    version=parts[1]
    if name not in PINS or name in found or version!=PINS[name]:
      raise RuntimeError("PACKAGE_OR_VERSION_MISMATCH_"+f.name[:65])
    size=f.stat().st_size
    if size<=0 or size>25000000:raise RuntimeError("UNEXPECTED_WHEEL_SIZE_"+name)
    digest=hashlib.sha256(f.read_bytes()).hexdigest()
    found[name]={"name":name,"version":version,"filename":f.name,"bytes":size,"sha256":digest}
  total=sum(v["bytes"] for v in found.values())
  if total>MAX_BYTES:raise RuntimeError("WHEEL_DOWNLOAD_BUDGET_EXCEEDED")
  data["total_wheel_bytes"]=total
  data["wheel_count"]=len(found)
  data["wheel_hashes"]=[found[k] for k in sorted(found)]
  for entry in data["wheel_hashes"]:
    print("HONEY_PINNED_WHEEL_SHA256",entry["name"],entry["version"],entry["sha256"],flush=True)
  locktext="\n".join(
    f'{v["name"]}=={v["version"]} --hash=sha256:{v["sha256"]}'
    for v in data["wheel_hashes"])+"\n"
  lockpath.write_text(locktext,encoding="utf-8")
  # Require explicit hashes and offline resolution, including all known transitive dependencies.
  env=dict(os.environ)
  env["PIP_NO_INDEX"]="1"
  env["PIP_DISABLE_PIP_VERSION_CHECK"]="1"
  install=[sys.executable,"-m","pip","install","--no-index",
           "--find-links",str(wheelhouse),"--only-binary=:all:","--require-hashes",
           "--no-input","--ignore-installed","--target",str(target),
           "-r",str(lockpath)]
  subprocess.run(install,check=True,timeout=180,env=env)
  data["fully_offline_install_pass"]=True
  data["status"]="WINDOWS_WHEEL_HASH_LOCK_OFFLINE_INSTALL_VERIFIED"
except Exception as exc:
  error=type(exc).__name__+":"+str(exc)
  data["status"]="WHEEL_HASH_LOCK_BLOCKED"
  data["error_type"]=error[:250]
finally:
  data["wheels_discarded"]=True
  (out/"wheel-lock-report.json").write_text(
    json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
  shutil.rmtree(wheelhouse,ignore_errors=True)
  shutil.rmtree(target,ignore_errors=True)
  print("HONEY_WHEEL_LOCK_STATUS="+data["status"],flush=True)
  print("NO_MODEL_NO_WAV_NO_COMMERCIAL_ACCEPTANCE",flush=True)
if error:
  raise RuntimeError("OFFLINE_WHEEL_HASH_LOCK_FAILED:"+error)
