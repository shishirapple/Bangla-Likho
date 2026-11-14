# -*- coding: utf-8 -*-
"""Windows backend.

Keys are captured with a low-level keyboard hook (through pynput's win32_event_filter),
swallowed while composing, and Bangla text is injected with SendInput(KEYEVENTF_UNICODE)
synchronously inside the hook, so ordering is always exact and latency is ~0.
"""
import ctypes
import traceback
from ctypes import wintypes

from core import parse_hotkey

KEYEVENTF_EXTENDEDKEY = 0x1
KEYEVENTF_KEYUP = 0x2
KEYEVENTF_UNICODE = 0x4
LLKHF_INJECTED = 0x10

VK_TO_NAME = {0x20: "space", 0x0D: "enter", 0x09: "tab", 0x08: "backspace", 0x1B: "esc",
              0x26: "up", 0x28: "down", 0x25: "left", 0x27: "right", 0x24: "home",
              0x23: "end", 0x2E: "delete", 0x21: "pageup", 0x22: "pagedown"}
NAME_TO_VK = {v: k for k, v in VK_TO_NAME.items()}
EXTENDED = {"up", "down", "left", "right", "home", "end", "delete", "pageup", "pagedown"}
OEM = {0xBA: (";", ":"), 0xBB: ("=", "+"), 0xBC: (",", "<"), 0xBD: ("-", "_"), 0xBE: (".", ">"),
       0xBF: ("/", "?"), 0xC0: ("`", "~"), 0xDB: ("[", "{"), 0xDC: ("\\", "|"),
       0xDD: ("]", "}"), 0xDE: ("'", '"')}
SHIFT_DIGITS = ")!@#$%^&*("
MOD_VKS = {0x10: "shift", 0xA0: "shift", 0xA1: "shift", 0x11: "ctrl", 0xA2: "ctrl",
           0xA3: "ctrl", 0x12: "alt", 0xA4: "alt", 0xA5: "alt", 0x5B: "cmd", 0x5C: "cmd"}

ULONG_PTR = ctypes.c_size_t


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD), ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD), ("dwExtraInfo", ULONG_PTR)]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG), ("mouseData", wintypes.DWORD),
                ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD), ("dwExtraInfo", ULONG_PTR)]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [("uMsg", wintypes.DWORD), ("wParamL", wintypes.WORD), ("wParamH", wintypes.WORD)]


class _U(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT), ("hi", HARDWAREINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("u", _U)]


class GUITHREADINFO(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.DWORD), ("flags", wintypes.DWORD), ("hwndActive", wintypes.HWND),
                ("hwndFocus", wintypes.HWND), ("hwndCapture", wintypes.HWND),
                ("hwndMenuOwner", wintypes.HWND), ("hwndMoveSize", wintypes.HWND),
                ("hwndCaret", wintypes.HWND), ("rcCaret", wintypes.RECT)]


def caret_pos():
    """Screen position (x, y_bottom) of the text caret in the focused control, or None."""
    try:
        u = ctypes.windll.user32
        gti = GUITHREADINFO()
        gti.cbSize = ctypes.sizeof(GUITHREADINFO)
        if not u.GetGUIThreadInfo(0, ctypes.byref(gti)) or not gti.hwndCaret:
            return None
        pt = wintypes.POINT(gti.rcCaret.left, gti.rcCaret.bottom)
        u.ClientToScreen(gti.hwndCaret, ctypes.byref(pt))
        if pt.x == 0 and pt.y == 0:
            return None
        return pt.x, pt.y
    except Exception:
        return None


class WinOutput:
    def __init__(self):
        self.user32 = ctypes.windll.user32

    def _send(self, items):
        arr = (INPUT * len(items))(*items)
        self.user32.SendInput(len(arr), arr, ctypes.sizeof(INPUT))

    @staticmethod
    def _ki(vk, scan, flags):
        i = INPUT()
        i.type = 1
        i.u.ki = KEYBDINPUT(vk, scan, flags, 0, 0)
        return i

    def text(self, s):
        if not s:
            return
        data = s.encode("utf-16-le")
        units = [int.from_bytes(data[i:i + 2], "little") for i in range(0, len(data), 2)]
        items = []
        for u in units:
            items.append(self._ki(0, u, KEYEVENTF_UNICODE))
            items.append(self._ki(0, u, KEYEVENTF_UNICODE | KEYEVENTF_KEYUP))
        self._send(items)

    def key(self, name):
        vk = NAME_TO_VK.get(name)
        if not vk:
            return
        ext = KEYEVENTF_EXTENDEDKEY if name in EXTENDED else 0
        self._send([self._ki(vk, 0, ext), self._ki(vk, 0, ext | KEYEVENTF_KEYUP)])

    def set_composing(self, b):
        pass

    def set_enabled(self, b):
        pass


class WinBackend:
    def __init__(self, composer, cfg):
        self.c = composer
        self.cfg = cfg
        self.mods = set()
        self.eaten = set()
        self.hk = {
            "toggle": parse_hotkey(cfg["hotkey_toggle"]),
            "voice": parse_hotkey(cfg["hotkey_voice"]),
        }
        self.listener = None
        self.mouse = None
        self.hotkeys_suspended = False

    @staticmethod
    def make_output():
        return WinOutput()

    def _translate(self, vk, mods):
        if vk in VK_TO_NAME:
            return VK_TO_NAME[vk], ""
        shift = "shift" in mods
        if 0x41 <= vk <= 0x5A:
            caps = bool(ctypes.windll.user32.GetKeyState(0x14) & 1)
            ch = chr(vk)
            return "char", ch if (shift != caps) else ch.lower()
        if 0x30 <= vk <= 0x39:
            return "char", (SHIFT_DIGITS[vk - 0x30] if shift else chr(vk))
        if 0x60 <= vk <= 0x69:
            return "char", chr(vk - 0x60 + 0x30)
        if vk == 0x6E:  # numeric keypad decimal
            return "char", "."
        if vk in OEM:
            return "char", OEM[vk][1 if shift else 0]
        return None, ""

    def set_hotkeys_suspended(self, suspended):
        self.hotkeys_suspended = bool(suspended)

    def _hotkey(self, vk, mods):
        if self.hotkeys_suspended:
            return None
        if not (0x41 <= vk <= 0x5A or 0x30 <= vk <= 0x39 or 0x70 <= vk <= 0x7B):
            return None
        key = chr(vk).lower() if vk < 0x70 else "f%d" % (vk - 0x6F)
        for name, (m, k) in self.hk.items():
            if k == key and m == mods:
                return name
        return None

    def set_hotkeys(self, cfg):
        self.cfg = cfg
        self.hk = {
            "toggle": parse_hotkey(cfg["hotkey_toggle"]),
            "voice": parse_hotkey(cfg["hotkey_voice"]),
        }

    def _filter(self, msg, data):
        suppress = False
        try:
            if data.flags & LLKHF_INJECTED:
                return True
            vk = data.vkCode
            down = msg in (0x100, 0x104)
            up = msg in (0x101, 0x105)
            m = MOD_VKS.get(vk)
            if m:
                if down:
                    self.mods.add(m)
                else:
                    self.mods.discard(m)
                return True
            if up:
                if vk in self.eaten:
                    self.eaten.discard(vk)
                    suppress = True
            elif down:
                mods = frozenset(self.mods)
                hot = self._hotkey(vk, mods)
                if hot == "toggle":
                    self.c.toggle()
                    suppress = True
                elif hot == "voice":
                    self.c.voice_cb()
                    suppress = True
                else:
                    name, ch = self._translate(vk, mods)
                    if name and self.c.key(name, ch, mods):
                        suppress = True
                if suppress:
                    self.eaten.add(vk)
        except Exception:
            traceback.print_exc()
        if suppress:
            self.listener.suppress_event()
        return True

    def start(self):
        from pynput import keyboard as K, mouse as M
        self.listener = K.Listener(on_press=lambda k: None, win32_event_filter=self._filter)
        self.listener.start()
        self.mouse = M.Listener(on_click=lambda x, y, b, p: self.c.mouse_click() if p else None)
        self.mouse.start()

    def stop(self):
        for n in ("listener", "mouse"):
            try:
                getattr(self, n).stop()
            except Exception:
                pass
