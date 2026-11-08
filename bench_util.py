"""
Helper that makes wall-clock benchmarks more repeatable on Windows laptops.

On hybrid (performance + efficiency core) CPUs, Windows may apply "power
throttling" (EcoQoS) to a process it considers to be in the background and
run it on the slower efficiency cores.  In my first runs this made the same
sort take anywhere from 150 ms to 320 ms.  stabilize_timing() opts the
current process out of execution-speed throttling and raises its priority
class, which brought the run-to-run spread down to a few percent.

On other operating systems it does nothing.
"""

import ctypes
import sys

_PROCESS_POWER_THROTTLING = 4               # PROCESS_INFORMATION_CLASS value
_THROTTLE_EXECUTION_SPEED = 0x1
_HIGH_PRIORITY_CLASS = 0x80


def stabilize_timing():
    """Disable Windows power throttling for this process; return True on success."""
    if sys.platform != "win32":
        return False
    from ctypes import wintypes

    class _State(ctypes.Structure):          # PROCESS_POWER_THROTTLING_STATE
        _fields_ = [("Version", wintypes.ULONG),
                    ("ControlMask", wintypes.ULONG),
                    ("StateMask", wintypes.ULONG)]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    kernel32.SetProcessInformation.argtypes = [wintypes.HANDLE, ctypes.c_int,
                                               ctypes.c_void_p, wintypes.DWORD]
    kernel32.SetPriorityClass.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    handle = kernel32.GetCurrentProcess()
    # ControlMask = speed throttling is being configured; StateMask = 0 -> turn it off.
    state = _State(1, _THROTTLE_EXECUTION_SPEED, 0)
    ok = kernel32.SetProcessInformation(handle, _PROCESS_POWER_THROTTLING,
                                        ctypes.byref(state), ctypes.sizeof(state))
    kernel32.SetPriorityClass(handle, _HIGH_PRIORITY_CLASS)
    return bool(ok)
