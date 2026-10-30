"""Independent Python package import paths and exact dependency versions from isolated venv."""
import importlib,importlib.metadata,json,pathlib,sys
from pathlib import Path
out=Path(sys.argv[1]).resolve()
pins={
 "onnxruntime":"1.23.1","numpy":"2.2.6","coloredlogs":"15.0.1",
 "flatbuffers":"25.12.19","humanfriendly":"10.0","mpmath":"1.3.0",
 "protobuf":"7.36.2","pyreadline3":"3.5.6","sympy":"1.14.0",
 "packaging":"26.3"}
assert sys.platform=="win32" and sys.version_info[:2]==(3,12),"WINDOWS_PY312_MISMATCH"
assert sys.prefix!=sys.base_prefix,"NOT_IN_VIRTUALENV"
assert pathlib.Path(sys.prefix).resolve()==(out/"venv").resolve(),"DIFFERENT_VENV"
for name,version in pins.items():
    actual=importlib.metadata.version(name)
    assert actual==version,f"VERSION_MISMATCH_{name}_{actual}"
import numpy,onnxruntime
for module in (numpy,onnxruntime):
    modpath=Path(module.__file__).resolve()
    assert modpath.is_relative_to(Path(sys.prefix).resolve()),"GLOBAL_PACKAGE_LEAK_"+module.__name__
assert onnxruntime.get_available_providers().__contains__("CPUExecutionProvider")
(out/"isolated-runtime-imports.json").write_text(json.dumps({
 "python":sys.version.split()[0],"venv_isolated":True,"packages":pins,
 "numpy_resolved_in_venv":True,"onnxruntime_resolved_in_venv":True,
 "cpu_provider_available":True,"inference_executed":False},indent=2),encoding="utf8")
print("ST3_VENV_ISOLATED_EXACT_10_VERSIONS_PASS",flush=True)
