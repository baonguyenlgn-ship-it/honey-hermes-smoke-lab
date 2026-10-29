"""Windows 64-bit GetProcessMemoryInfo with declared HANDLE / pointer ABI."""
import ctypes
import sys
from ctypes import wintypes

if sys.platform != "win32":
    raise RuntimeError("WINDOWS_ONLY")

class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
    _fields_=[
        ("cb",wintypes.DWORD),("PageFaultCount",wintypes.DWORD),
        ("PeakWorkingSetSize",ctypes.c_size_t),("WorkingSetSize",ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage",ctypes.c_size_t),("QuotaPagedPoolUsage",ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage",ctypes.c_size_t),("QuotaNonPagedPoolUsage",ctypes.c_size_t),
        ("PagefileUsage",ctypes.c_size_t),("PeakPagefileUsage",ctypes.c_size_t)
    ]
_kernel32=ctypes.WinDLL("kernel32",use_last_error=True)
_psapi=ctypes.WinDLL("psapi",use_last_error=True)
_kernel32.GetCurrentProcess.argtypes=[]
_kernel32.GetCurrentProcess.restype=wintypes.HANDLE
_psapi.GetProcessMemoryInfo.argtypes=[wintypes.HANDLE,ctypes.POINTER(PROCESS_MEMORY_COUNTERS),wintypes.DWORD]
_psapi.GetProcessMemoryInfo.restype=wintypes.BOOL

def working_memory():
    pm=PROCESS_MEMORY_COUNTERS()
    pm.cb=ctypes.sizeof(pm)
    handle=_kernel32.GetCurrentProcess()
    if not handle: raise OSError("INVALID_PROCESS_HANDLE")
    ctypes.set_last_error(0)
    ok=_psapi.GetProcessMemoryInfo(handle,ctypes.byref(pm),pm.cb)
    if not ok:
        raise OSError(ctypes.get_last_error(),"GetProcessMemoryInfo failed with declared ABI")
    out={"working_set_bytes":int(pm.WorkingSetSize),
         "peak_working_set_bytes":int(pm.PeakWorkingSetSize),
         "pagefile_bytes":int(pm.PagefileUsage)}
    if out["working_set_bytes"]<=0 or out["peak_working_set_bytes"]<out["working_set_bytes"]:
        raise AssertionError("INVALID_WINDOWS_PROCESS_MEMORY_DATA")
    return out

if __name__=="__main__":
    sample=working_memory()
    print("WINDOWS_MEMORY_ABI_PROBE_PASS="+str({k:round(v/1048576,2) for k,v in sample.items()}),flush=True)
