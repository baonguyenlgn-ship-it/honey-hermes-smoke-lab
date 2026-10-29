# Windows memory probe repair — 2026-10-30 KST

Run #40959862067 failed **before concurrent inference**. All four ONNX SHA values matched and runtime wheels installed, but ctypes called psapi.GetProcessMemoryInfo with implicit default 32-bit HANDLE signature on 64-bit Windows, producing `OSError: GetProcessMemoryInfo failed`. This does not invalidate prior single-utterance WAV proof and does not prove a five-request failure.

Repair: separate stdlib-only `win_process_memory.py` with explicit `HANDLE`, `DWORD`, pointer and BOOL ABI declarations, observable Windows memory preflight as the first step **before any heavy model download**. The benchmark imports the same tested function. Preserve the same 5-request test, same model, same cost and privacy boundaries. Do not state concurrency PASS until actual Windows CI and independent benchmark checks pass. 
