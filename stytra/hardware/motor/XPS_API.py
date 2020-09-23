import sys
from ctypes import *
from typing import Any, List
from newportxps import NewportXPS

sys.path.append(r'C:\Users\kkoetter\python_code')

c_word = c_ushort
c_dword = c_ulong


def bind(
    lib: CDLL, func: str, argtypes: List[Any] = None, restype: Any = None
) -> CFUNCTYPE:
    _func = getattr(lib, func, null_function)
    _func.argtypes = argtypes
    _func.restype = restype

    return _func


def null_function():
    pass

lib = cdll.LoadLibrary(r"J:\_Shared\Katharina\Motor\Newport_motto\stage\Newport.XPS.CommandInterface.dll")

print("lib", lib)


from newportxps import NewportXPS
xps = NewportXPS('192.168.0.254', username='Administrator', password='Administrator')
print(xps.status_report())


for gname, info in xps.groups.items():
    print(gname, info)


for sname, info in xps.stages.items():
    print(sname, xps.get_stage_position(sname), info)


# xps.move_stage('SampleZ.Pos', 1.0)
# xps.home_group('DetectorX')
