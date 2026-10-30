"""Only the reviewed intake task maps to the existing bounded runtime."""
from .one_use_lease_gate import AdmissionDenied, TASK
RUNTIME_TASK="hermes-lab-rename-label-v1"
def runtime_task(task):
    if type(task) is not str or task != TASK:
        raise AdmissionDenied("TASK_MAPPING_DENIED")
    return RUNTIME_TASK
