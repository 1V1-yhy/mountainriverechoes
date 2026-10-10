import ctypes, os
from ctypes import POINTER, c_void_p, c_wchar_p, c_long, c_int, byref

class GUID(ctypes.Structure):
    _fields_ = [("Data1", ctypes.c_ulong), ("Data2", ctypes.c_ushort),
                ("Data3", ctypes.c_ushort), ("Data4", ctypes.c_ubyte * 8)]
    def __init__(self, d1=0, d2=0, d3=0, d4=(0,) * 8):
        super().__init__(d1, d2, d3, (d4[0], d4[1], d4[2], d4[3], d4[4], d4[5], d4[6], d4[7]))

CLSID_ShellLink = GUID(0x00021401, 0, 0, (0xC0, 0, 0, 0, 0, 0, 0, 0x46))
IID_IShellLinkW = GUID(0x000214F9, 0, 0, (0xC0, 0, 0, 0, 0, 0, 0, 0x46))
IID_IPersistFile = GUID(0x0000010B, 0, 0, (0xC0, 0, 0, 0, 0, 0, 0, 0x46))

ole32 = ctypes.windll.ole32
ole32.CoInitialize.restype = c_long
ole32.CoCreateInstance.argtypes = [POINTER(GUID), c_void_p, c_int, POINTER(GUID), POINTER(c_void_p)]
ole32.CoCreateInstance.restype = c_long

ole32.CoInitialize(None)

pUnk = c_void_p()
hr = ole32.CoCreateInstance(byref(CLSID_ShellLink), None, 1, byref(IID_IShellLinkW), byref(pUnk))
if hr < 0:
    raise SystemExit("CoCreateInstance failed: 0x%x" % hr)

def call_vtbl(iface, idx, restype, argtypes, *args):
    vt = ctypes.cast(iface, POINTER(POINTER(c_void_p)))[0]
    fn = ctypes.cast(vt[idx], ctypes.CFUNCTYPE(restype, c_void_p, *argtypes))
    return fn(iface, *args)

desktop = os.path.join(os.path.expanduser('~'), 'Desktop')
target = r'D:\我看不到你\mountainriverechoes\dist\miao_player.exe'
working = r'D:\我看不到你\mountainriverechoes\dist'
lnk = os.path.join(desktop, '苗族音乐.lnk')

call_vtbl(pUnk, 20, c_long, [c_wchar_p], target)        # SetPath
call_vtbl(pUnk, 9,  c_long, [c_wchar_p], working)      # SetWorkingDirectory
call_vtbl(pUnk, 7,  c_long, [c_wchar_p], '苗族音乐播放器')  # SetDescription

ppf = c_void_p()
call_vtbl(pUnk, 0, c_long, [POINTER(GUID), POINTER(c_void_p)], byref(IID_IPersistFile), byref(ppf))
hr = call_vtbl(ppf, 6, c_long, [c_wchar_p, c_int], lnk, 1)  # Save
if hr < 0:
    raise SystemExit("Save failed: 0x%x" % hr)

call_vtbl(ppf, 2, c_long, [])
call_vtbl(pUnk, 2, c_long, [])
print("OK created:", lnk)
