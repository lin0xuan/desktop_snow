"""Click-through desktop host for grain snow."""
from __future__ import annotations

import ctypes
import os
from ctypes import wintypes
from pathlib import Path

from snowdesk.draw import make_cabin
from snowdesk.engine import World

user32 = ctypes.WinDLL("user32", use_last_error=True)
gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
dwmapi = ctypes.WinDLL("dwmapi", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

LRESULT = ctypes.c_ssize_t
WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x80000
WS_EX_TRANSPARENT = 0x20
WS_EX_TOPMOST = 0x8
WS_EX_TOOLWINDOW = 0x80
WS_EX_NOACTIVATE = 0x08000000
WS_EX_APPWINDOW = 0x40000
WS_POPUP = 0x80000000
SW_SHOWNA = 8
WM_TIMER = 0x0113
WM_HOTKEY = 0x0312
WM_DESTROY = 2
MOD_ALT = 1
MOD_CONTROL = 2
DWMWA_EXTENDED_FRAME_BOUNDS = 9
DWMWA_CLOAKED = 14
SPI_SETDESKWALLPAPER = 20
SPI_GETDESKWALLPAPER = 0x73
SPIF = 3
ULW_ALPHA = 2
SKIP = {"Progman", "WorkerW", "Shell_TrayWnd", "Shell_SecondaryTrayWnd", "NotifyIconOverflowWindow", "SnowdeskMsg", "SnowdeskCap"}


class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long), ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class SIZE(ctypes.Structure):
    _fields_ = [("cx", ctypes.c_long), ("cy", ctypes.c_long)]


class BLENDFUNCTION(ctypes.Structure):
    _fields_ = [("BlendOp", ctypes.c_byte), ("BlendFlags", ctypes.c_byte), ("SourceConstantAlpha", ctypes.c_byte), ("AlphaFormat", ctypes.c_byte)]


class WNDCLASSW(ctypes.Structure):
    _fields_ = [
        ("style", wintypes.UINT), ("lpfnWndProc", WNDPROC), ("cbClsExtra", ctypes.c_int), ("cbWndExtra", ctypes.c_int),
        ("hInstance", wintypes.HINSTANCE), ("hIcon", wintypes.HICON), ("hCursor", wintypes.HANDLE),
        ("hbrBackground", wintypes.HBRUSH), ("lpszMenuName", wintypes.LPCWSTR), ("lpszClassName", wintypes.LPCWSTR),
    ]


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD), ("biWidth", ctypes.c_long), ("biHeight", ctypes.c_long),
        ("biPlanes", wintypes.WORD), ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", ctypes.c_long), ("biYPelsPerMeter", ctypes.c_long),
        ("biClrUsed", wintypes.DWORD), ("biClrImportant", wintypes.DWORD),
    ]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", wintypes.DWORD * 3)]


def setup() -> None:
    user32.DefWindowProcW.restype = LRESULT
    user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    user32.CreateWindowExW.restype = wintypes.HWND
    user32.CreateWindowExW.argtypes = [wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.HWND, wintypes.HMENU, wintypes.HINSTANCE, wintypes.LPVOID]
    user32.RegisterClassW.argtypes = [ctypes.POINTER(WNDCLASSW)]
    user32.EnumWindows.argtypes = [WNDENUMPROC, wintypes.LPARAM]
    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.IsIconic.argtypes = [wintypes.HWND]
    user32.IsZoomed.argtypes = [wintypes.HWND]
    user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetWindowLongW.restype = ctypes.c_long
    user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.UpdateLayeredWindow.argtypes = [wintypes.HWND, wintypes.HDC, ctypes.POINTER(POINT), ctypes.POINTER(SIZE), wintypes.HDC, ctypes.POINTER(POINT), wintypes.DWORD, ctypes.POINTER(BLENDFUNCTION), wintypes.DWORD]
    user32.SystemParametersInfoW.argtypes = [wintypes.UINT, wintypes.UINT, wintypes.LPVOID, wintypes.UINT]
    user32.GetMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT]
    user32.GetMessageW.restype = ctypes.c_int
    user32.TranslateMessage.argtypes = [ctypes.POINTER(wintypes.MSG)]
    user32.DispatchMessageW.argtypes = [ctypes.POINTER(wintypes.MSG)]
    user32.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
    user32.SetTimer.argtypes = [wintypes.HWND, ctypes.c_size_t, wintypes.UINT, ctypes.c_void_p]
    dwmapi.DwmGetWindowAttribute.argtypes = [wintypes.HWND, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD]
    gdi32.CreateCompatibleDC.restype = wintypes.HDC
    gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
    gdi32.CreateDIBSection.restype = wintypes.HBITMAP
    gdi32.CreateDIBSection.argtypes = [wintypes.HDC, ctypes.c_void_p, wintypes.UINT, ctypes.POINTER(ctypes.c_void_p), wintypes.HANDLE, wintypes.DWORD]
    gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
    gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
    gdi32.DeleteDC.argtypes = [wintypes.HDC]
    user32.GetDC.restype = wintypes.HDC
    user32.GetCursorPos.argtypes = [ctypes.POINTER(POINT)]
    user32.GetDC.argtypes = [wintypes.HWND]
    user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
    try:
        user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except Exception:
        pass


def windows() -> list[dict]:
    found = []

    @WNDENUMPROC
    def enum(hwnd, _):
        if not user32.IsWindowVisible(hwnd) or user32.IsIconic(hwnd):
            return True
        buf = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, buf, 256)
        if buf.value in SKIP:
            return True
        ex = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        if ex & WS_EX_TOOLWINDOW and not (ex & WS_EX_APPWINDOW):
            return True
        cloaked = wintypes.DWORD()
        dwmapi.DwmGetWindowAttribute(hwnd, DWMWA_CLOAKED, ctypes.byref(cloaked), 4)
        if cloaked.value:
            return True
        rect = RECT()
        if dwmapi.DwmGetWindowAttribute(hwnd, DWMWA_EXTENDED_FRAME_BOUNDS, ctypes.byref(rect), ctypes.sizeof(rect)) != 0:
            return True
        if rect.right - rect.left < 80 or rect.bottom - rect.top < 60:
            return True
        found.append({
            "key": str(int(hwnd)),
            "left": rect.left, "top": rect.top, "right": rect.right, "bottom": rect.bottom,
            "zoomed": bool(user32.IsZoomed(hwnd)),
        })
        return True

    user32.EnumWindows(enum, 0)
    return found


def paint(hwnd, image, x, y) -> None:
    from PIL import ImageChops
    im = image.convert("RGBA")
    r, g, b, a = im.split()
    data = ImageChops.merge if False else None
    r, g, b = ImageChops.multiply(r, a), ImageChops.multiply(g, a), ImageChops.multiply(b, a)
    raw = __import__("PIL").Image.merge("RGBA", (b, g, r, a)).tobytes()
    w, h = im.size
    screen = user32.GetDC(None)
    mem = gdi32.CreateCompatibleDC(screen)
    bmi = BITMAPINFO()
    bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bmi.bmiHeader.biWidth = w
    bmi.bmiHeader.biHeight = -h
    bmi.bmiHeader.biPlanes = 1
    bmi.bmiHeader.biBitCount = 32
    bits = ctypes.c_void_p()
    hbmp = gdi32.CreateDIBSection(screen, ctypes.byref(bmi), 0, ctypes.byref(bits), None, 0)
    ctypes.memmove(bits, raw, len(raw))
    gdi32.SelectObject(mem, hbmp)
    user32.UpdateLayeredWindow(hwnd, screen, ctypes.byref(POINT(x, y)), ctypes.byref(SIZE(w, h)), mem, ctypes.byref(POINT(0, 0)), 0, ctypes.byref(BLENDFUNCTION(0, 0, 255, 1)), ULW_ALPHA)
    gdi32.DeleteObject(hbmp)
    gdi32.DeleteDC(mem)
    user32.ReleaseDC(None, screen)


def previous_wallpaper() -> str:
    import winreg
    buf = ctypes.create_unicode_buffer(520)
    user32.SystemParametersInfoW(SPI_GETDESKWALLPAPER, 520, buf, 0)
    current = buf.value
    if current and "cabin.bmp" not in current.lower():
        return current
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Wallpapers") as key:
            val, _ = winreg.QueryValueEx(key, "BackgroundHistoryPath1")
            if val and os.path.exists(val) and "cabin.bmp" not in val.lower():
                return val
    except OSError:
        pass
    return r"C:\\Windows\\Web\\Wallpaper\\Windows\\img0.jpg"


def main() -> None:
    setup()
    w, h = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
    root = Path(__file__).resolve().parent.parent
    cabin = root / "cabin.bmp"
    if not cabin.exists():
        make_cabin().crop((80, 0, 80 + w, h)).convert("RGB").save(cabin, "BMP")
    previous = previous_wallpaper()
    user32.SystemParametersInfoW(20, 0, ctypes.c_wchar_p(str(cabin)), SPIF)
    world = World(w, h)
    hinst = kernel32.GetModuleHandleW(None)
    proc = WNDPROC(lambda hwnd, msg, wp, lp: user32.DefWindowProcW(hwnd, msg, wp, lp))
    cls = WNDCLASSW()
    cls.lpfnWndProc = proc
    cls.hInstance = hinst
    cls.lpszClassName = "SnowdeskCap"
    user32.RegisterClassW(ctypes.byref(cls))
    overlay = user32.CreateWindowExW(
        WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOPMOST | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE,
        "SnowdeskCap", "snow", WS_POPUP, 0, 0, w, h, None, None, hinst, None,
    )
    user32.ShowWindow(overlay, SW_SHOWNA)

    def on_msg(hwnd, msg, wp, lp):
        if msg == WM_TIMER:
            try:
                world.sync(windows())
                cursor = POINT()
                if user32.GetCursorPos(ctypes.byref(cursor)):
                    world.disturb(cursor.x, cursor.y, cursor.x - getattr(world, "_mx", cursor.x))
                    world._mx = cursor.x
                world.step(0.05)
                if world.tick if False else True:
                    paint(overlay, world.render(), 0, 0)
            except Exception as exc:
                print("tick", type(exc).__name__, exc, flush=True)
            return 0
        if msg == WM_HOTKEY:
            user32.PostQuitMessage(0)
            return 0
        return user32.DefWindowProcW(hwnd, msg, wp, lp)

    msg_proc = WNDPROC(on_msg)
    mcls = WNDCLASSW()
    mcls.lpfnWndProc = msg_proc
    mcls.hInstance = hinst
    mcls.lpszClassName = "SnowdeskMsg"
    user32.RegisterClassW(ctypes.byref(mcls))
    msg_hwnd = user32.CreateWindowExW(0, "SnowdeskMsg", "snowdesk", 0, 0, 0, 0, 0, None, None, hinst, None)
    user32.RegisterHotKey(msg_hwnd, 1, MOD_CONTROL | MOD_ALT, ord("Q"))
    user32.SetTimer(msg_hwnd, 1, 50, None)
    print("grain snow running. Ctrl+Alt+Q quits.", flush=True)
    msg = wintypes.MSG()
    try:
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))
    finally:
        user32.SystemParametersInfoW(20, 0, ctypes.c_wchar_p(previous), SPIF)
        print("wallpaper restored", flush=True)


if __name__ == "__main__":
    main()
