#!/usr/bin/env python3
"""
KeyMacro — 背景遊戲按鍵發送器
類似 X-Mouse Button Control，支援觸發鍵、組合鍵、頻率設定、無限循環

相依套件：pynput, pywin32
pip install pynput pywin32
"""

import sys
import time
import threading
import json
import os
import ctypes
import tkinter as tk
from tkinter import ttk, messagebox

# ── Windows 平台檢查 ──────────────────────────────────────
if sys.platform != "win32":
    print("⚠️  此程式僅支援 Windows")
    sys.exit(1)

# ── Windows 專用模組 ──────────────────────────────────────
import win32gui
import win32api
import win32con
from pynput.keyboard import Key, KeyCode, Listener as KbListener

# ── ctypes API ─────────────────────────────────────────────
user32 = ctypes.windll.user32

# ── SendInput 結構（必須在函式定義之前）─────────────────────
PUL = ctypes.POINTER(ctypes.c_ulong)

class KeyBdInput(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.c_ushort),
        ("wScan", ctypes.c_ushort),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", PUL)
    ]

class HardwareInput(ctypes.Structure):
    _fields_ = [
        ("uMsg", ctypes.c_ulong),
        ("wParamL", ctypes.c_short),
        ("wParamH", ctypes.c_ushort)
    ]

class MouseInput(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long), ("dy", ctypes.c_long),
        ("mouseData", ctypes.c_ulong), ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong), ("dwExtraInfo", PUL)
    ]

class InputUnion(ctypes.Union):
    _fields_ = [("ki", KeyBdInput), ("mi", MouseInput), ("hi", HardwareInput)]

class Input(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ulong), ("ii", InputUnion)]

INPUT_KEYBOARD = 1
KEYEVENTF_SCANCODE = 0x0008
KEYEVENTF_KEYUP = 0x0002
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101

# ═══════════════════════════════════════════════════════════
#  按鍵對應表（虛擬鍵碼 + Scan Code）
# ═══════════════════════════════════════════════════════════

VK_CODE = {
    'a': (0x41, 0x1E), 'b': (0x42, 0x30), 'c': (0x43, 0x2E),
    'd': (0x44, 0x20), 'e': (0x45, 0x12), 'f': (0x46, 0x21),
    'g': (0x47, 0x22), 'h': (0x48, 0x23), 'i': (0x49, 0x17),
    'j': (0x4A, 0x24), 'k': (0x4B, 0x25), 'l': (0x4C, 0x26),
    'm': (0x4D, 0x32), 'n': (0x4E, 0x31), 'o': (0x4F, 0x18),
    'p': (0x50, 0x19), 'q': (0x51, 0x10), 'r': (0x52, 0x13),
    's': (0x53, 0x1F), 't': (0x54, 0x14), 'u': (0x55, 0x16),
    'v': (0x56, 0x2F), 'w': (0x57, 0x11), 'x': (0x58, 0x2D),
    'y': (0x59, 0x15), 'z': (0x5A, 0x2C),
    '0': (0x30, 0x0B), '1': (0x31, 0x02), '2': (0x32, 0x03),
    '3': (0x33, 0x04), '4': (0x34, 0x05), '5': (0x35, 0x06),
    '6': (0x36, 0x07), '7': (0x37, 0x08), '8': (0x38, 0x09),
    '9': (0x39, 0x0A),
    'num0': (0x60, 0x52), 'num1': (0x61, 0x4F), 'num2': (0x62, 0x50),
    'num3': (0x63, 0x51), 'num4': (0x64, 0x4B), 'num5': (0x65, 0x4C),
    'num6': (0x66, 0x4D), 'num7': (0x67, 0x47), 'num8': (0x68, 0x48),
    'num9': (0x69, 0x49), 'num*': (0x6A, 0x37), 'num+': (0x6B, 0x4E),
    'num-': (0x6D, 0x4A), 'num.': (0x6E, 0x53),
    'f1': (0x70, 0x3B), 'f2': (0x71, 0x3C), 'f3': (0x72, 0x3D),
    'f4': (0x73, 0x3E), 'f5': (0x74, 0x3F), 'f6': (0x75, 0x40),
    'f7': (0x76, 0x41), 'f8': (0x77, 0x42), 'f9': (0x78, 0x43),
    'f10': (0x79, 0x44), 'f11': (0x7A, 0x57), 'f12': (0x7B, 0x58),
    'space': (0x20, 0x39), 'enter': (0x0D, 0x1C), 'tab': (0x09, 0x0F),
    'escape': (0x1B, 0x01), 'backspace': (0x08, 0x0E),
    'delete': (0x2E, 0x53), 'insert': (0x2D, 0x52),
    'home': (0x24, 0x47), 'end': (0x23, 0x4F),
    'pageup': (0x21, 0x49), 'pagedown': (0x22, 0x51),
    'up': (0x26, 0x48), 'down': (0x28, 0x50),
    'left': (0x25, 0x4B), 'right': (0x27, 0x4D),
    '!': ('shift', '1'), '@': ('shift', '2'), '#': ('shift', '3'),
    '$': ('shift', '4'), '%': ('shift', '5'), '^': ('shift', '6'),
    '&': ('shift', '7'), '*': ('shift', '8'), '(': ('shift', '9'),
    ')': ('shift', '0'),
    'ctrl': 'ctrl', 'shift': 'shift', 'alt': 'alt', 'win': 'win',
    'control': 'ctrl', 'lctrl': 'lctrl', 'rctrl': 'rctrl',
    'lshift': 'lshift', 'rshift': 'rshift',
    'lalt': 'lalt', 'ralt': 'ralt',
    'lwin': 'lwin', 'rwin': 'rwin',
}

MODIFIER_VK = {
    'ctrl': (0x11, 0x1D), 'shift': (0x10, 0x2A), 'alt': (0x12, 0x38),
    'win': (0x5B, 0x5B), 'lctrl': (0xA2, 0x1D), 'rctrl': (0xA3, 0x1D),
    'lshift': (0xA0, 0x2A), 'rshift': (0xA1, 0x36),
    'lalt': (0xA4, 0x38), 'ralt': (0xA5, 0x38),
    'lwin': (0x5B, 0x5B), 'rwin': (0x5C, 0x5C),
}

# ═══════════════════════════════════════════════════════════
#  按鍵發送核心
# ═══════════════════════════════════════════════════════════

def parse_key(key_str):
    key_str = key_str.strip().lower()
    parts = key_str.split('+')
    modifiers = []
    main_key = parts[-1]
    for m in parts[:-1]:
        m = m.strip()
        if m in MODIFIER_VK:
            modifiers.append(m)
    if main_key in VK_CODE:
        vk, scan = VK_CODE[main_key]
        return vk, scan, modifiers
    return None, None, modifiers

def _sendinput_key(vk, scan, down=True):
    """使用 SendInput 發送單一按鍵"""
    flags = KEYEVENTF_SCANCODE
    if not down:
        flags |= KEYEVENTF_KEYUP
    extra = ctypes.c_ulong(0)
    ii_ary = Input * 1
    ii = ii_ary()
    ii[0].type = INPUT_KEYBOARD
    ii[0].ii.ki = KeyBdInput(vk, scan, flags, 0, ctypes.pointer(extra))
    return user32.SendInput(1, ctypes.byref(ii), ctypes.sizeof(ii[0])) == 1

def _attach_and_send(target_hwnd, vk, scan, modifiers, hold_ms=50):
    """附著目標執行緒後用 SendInput 發送（DirectInput 遊戲）"""
    try:
        target_tid = user32.GetWindowThreadProcessId(target_hwnd, 0)
        current_tid = user32.GetCurrentThreadId()
        user32.AttachThreadInput(current_tid, target_tid, True)
        for mod in modifiers:
            if mod in MODIFIER_VK:
                m_vk, m_scan = MODIFIER_VK[mod]
                _sendinput_key(m_vk, m_scan, down=True)
        time.sleep(0.005)
        _sendinput_key(vk, scan, down=True)
        time.sleep(hold_ms / 1000.0)
        _sendinput_key(vk, scan, down=False)
        time.sleep(0.005)
        for mod in reversed(modifiers):
            if mod in MODIFIER_VK:
                m_vk, m_scan = MODIFIER_VK[mod]
                _sendinput_key(m_vk, m_scan, down=False)
        user32.AttachThreadInput(current_tid, target_tid, False)
        return True
    except Exception:
        try:
            user32.AttachThreadInput(current_tid, target_tid, False)
        except:
            pass
        return False

def _post_key(hwnd, msg, vk, scan_or_0):
    """包裝 PostMessage"""
    try:
        win32api.PostMessage(hwnd, msg, vk, scan_or_0)
        return True
    except Exception:
        return False

def _fake_foreground(hwnd_target, func):
    """
    將目標視窗短暫拉到前景，執行 func，然後還原。
    透過 AttachThreadInput 技巧突破 foreground lock。
    """
    target_tid = user32.GetWindowThreadProcessId(hwnd_target, 0)
    current_tid = user32.GetCurrentThreadId()
    user32.AttachThreadInput(current_tid, target_tid, True)
    prev_foreground = user32.GetForegroundWindow()
    user32.SetForegroundWindow(hwnd_target)
    time.sleep(0.05)
    try:
        func()
    finally:
        time.sleep(0.02)
        user32.SetForegroundWindow(prev_foreground)
        user32.AttachThreadInput(current_tid, target_tid, False)

def _sendinput_with_fake_foreground(hwnd, vk, scan, modifiers, hold_ms):
    """前景模擬模式下發送單一按鍵"""
    def _do():
        for mod in modifiers:
            if mod in MODIFIER_VK:
                m_vk, m_scan = MODIFIER_VK[mod]
                _sendinput_key(m_vk, m_scan, down=True)
        time.sleep(0.005)
        _sendinput_key(vk, scan, down=True)
        time.sleep(hold_ms / 1000.0)
        _sendinput_key(vk, scan, down=False)
        time.sleep(0.005)
        for mod in reversed(modifiers):
            if mod in MODIFIER_VK:
                m_vk, m_scan = MODIFIER_VK[mod]
                _sendinput_key(m_vk, m_scan, down=False)
    _fake_foreground(hwnd, _do)

def send_key_to_window(hwnd, vk, scan, modifiers, hold_ms=50, stop_event=None):
    """發送單一按鍵：PostMessage → AttachThreadInput → 前景模擬"""
    scan_down = (scan << 16) | 1
    scan_up   = (scan << 16) | 1 | 0xC0000000
    post_ok = False

    try:
        for mod in modifiers:
            if stop_event and stop_event.is_set(): return
            if mod in MODIFIER_VK:
                m_vk, _ = MODIFIER_VK[mod]
                _post_key(hwnd, WM_KEYDOWN, m_vk, 0)
        if stop_event and stop_event.is_set():
            for mod in reversed(modifiers):
                if mod in MODIFIER_VK:
                    m_vk, _ = MODIFIER_VK[mod]
                    _post_key(hwnd, WM_KEYUP, m_vk, 0)
            return
        time.sleep(0.008)
        _post_key(hwnd, WM_KEYDOWN, vk, scan_down)
        time.sleep(hold_ms / 1000.0)
        if stop_event and stop_event.is_set():
            _post_key(hwnd, WM_KEYUP, vk, scan_up)
            for mod in reversed(modifiers):
                if mod in MODIFIER_VK:
                    m_vk, _ = MODIFIER_VK[mod]
                    _post_key(hwnd, WM_KEYUP, m_vk, 0)
            return
        _post_key(hwnd, WM_KEYUP, vk, scan_up)
        time.sleep(0.008)
        for mod in reversed(modifiers):
            if mod in MODIFIER_VK:
                m_vk, _ = MODIFIER_VK[mod]
                _post_key(hwnd, WM_KEYUP, m_vk, 0)
        post_ok = True
    except Exception:
        pass

    if not post_ok:
        _attach_and_send(hwnd, vk, scan, modifiers, hold_ms)

# ═══════════════════════════════════════════════════════════
#  視窗工具
# ═══════════════════════════════════════════════════════════

def find_window_by_title(title):
    result = [0]
    def callback(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            if title.lower() in win32gui.GetWindowText(hwnd).lower():
                result[0] = hwnd
                return False
        return True
    win32gui.EnumWindows(callback, None)
    return result[0]

def get_all_windows():
    windows = []
    seen = set()
    def callback(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd).strip()
            if title and title not in seen:
                try:
                    cls = win32gui.GetClassName(hwnd)
                    if cls in ('WorkerW', 'Shell_TrayWnd', 'DV2ControlHost',
                               'MsgrIMEWindowClass', 'Windows.UI.Core.CoreWindow'):
                        return True
                except:
                    pass
                windows.append((title, hwnd))
                seen.add(title)
        return True
    win32gui.EnumWindows(callback, None)
    windows.sort(key=lambda x: x[0].lower())
    return windows

# ═══════════════════════════════════════════════════════════
#  巨集發送
# ═══════════════════════════════════════════════════════════

def send_macro_sequence(sequence, target_title, hold_ms, interval_ms, repeat, stop_event=None):
    """
    發送巨集序列。每次按鍵使用前景模擬法，確保 DirectInput 遊戲能收到。
    repeat=-1 為無限循環，直到 stop_event 設定。
    """
    iteration = 0
    while True:
        if stop_event and stop_event.is_set():
            return
        if repeat >= 0:
            if iteration >= repeat:
                break
            iteration += 1

        # 每次重新查詢視窗
        hwnd = 0
        if target_title.strip():
            hwnd = find_window_by_title(target_title.strip())
        if hwnd == 0 or not win32gui.IsWindow(hwnd):
            time.sleep(0.1)
            continue

        for key_str in sequence:
            if stop_event and stop_event.is_set():
                return
            vk, scan, modifiers = parse_key(key_str)
            if vk:
                _sendinput_with_fake_foreground(hwnd, vk, scan, modifiers, hold_ms)
            if stop_event and stop_event.is_set():
                return
            time.sleep(interval_ms / 1000.0)

        if repeat < 0:
            time.sleep(0.001)

# ═══════════════════════════════════════════════════════════
#  熱鍵管理
# ═══════════════════════════════════════════════════════════

class HotkeyManager:
    def __init__(self, on_trigger, on_stop):
        self.on_trigger = on_trigger
        self.on_stop = on_stop
        self.trigger_key = None
        self.stop_key = None
        self.t_listener = None
        self.s_listener = None
        self._running = False
        self._held = False
        self._is_toggle = False
        self._active = False

    def _norm(self, key):
        if isinstance(key, Key):
            n = key.name.lower()
            if n in ('alt_l','alt_r'): return 'alt'
            if n in ('ctrl_l','ctrl_r'): return 'ctrl'
            if n in ('shift_l','shift_r'): return 'shift'
            if n in ('cmd','cmd_l','cmd_r'): return 'win'
            return n
        if isinstance(key, KeyCode) and key.char:
            return key.char.lower()
        return str(key).replace("'","").lower()

    def _trigger_press(self, key):
        kn = self._norm(key)
        if self._is_toggle and kn == self.trigger_key:
            if not self._held:
                self._held = True
                if self._active:
                    self.on_stop()
                    self._active = False
                else:
                    self._active = True
                    threading.Thread(target=self._delayed, daemon=True).start()
        elif not self._is_toggle and kn == self.trigger_key and not self._held:
            self._held = True
            self._active = True
            threading.Thread(target=self._delayed, daemon=True).start()

    def _delayed(self):
        time.sleep(0.05)
        if self._running and self._held:
            self.on_trigger()

    def _trigger_release(self, key):
        kn = self._norm(key)
        if kn == self.trigger_key:
            self._held = False
            if not self._is_toggle and self._active:
                self.on_stop()
                self._active = False

    def _stop_press(self, key):
        kn = self._norm(key)
        if kn == self.stop_key:
            self.on_stop()
            self._active = False

    def start(self, trigger, stop, toggle):
        self.trigger_key = trigger.lower()
        self.stop_key = stop.lower()
        self._is_toggle = toggle
        self._running = True
        self._held = False
        self._active = False
        self.t_listener = KbListener(on_press=self._trigger_press,
                                      on_release=self._trigger_release)
        self.t_listener.start()
        if not toggle and self.stop_key != self.trigger_key:
            self.s_listener = KbListener(on_press=self._stop_press,
                                          on_release=lambda _: None)
            self.s_listener.start()

    def stop(self):
        self._running = False
        self._active = False
        if self.t_listener:
            self.t_listener.stop()
            self.t_listener = None
        if self.s_listener:
            self.s_listener.stop()
            self.s_listener = None

# ═══════════════════════════════════════════════════════════
#  GUI
# ═══════════════════════════════════════════════════════════

class KeyMacroGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("KeyMacro — 背景遊戲按鍵發送器")
        self.root.geometry("720x680")
        self.root.resizable(False, False)

        self.hotkey_str = tk.StringVar(value="f1")
        self.stop_hotkey_str = tk.StringVar(value="f2")
        self.target_window = tk.StringVar(value="")
        self.hold_ms = tk.IntVar(value=50)
        self.interval_ms = tk.IntVar(value=100)
        self.repeat_count = tk.IntVar(value=-1)
        self.delay_before = tk.IntVar(value=500)
        self.toggle_mode = tk.BooleanVar(value=False)
        self.infinite_mode = tk.BooleanVar(value=True)
        self.is_running = False
        self.window_var = tk.StringVar(value="")
        self.window_list = []
        self.stop_event = threading.Event()
        self.active_threads = []
        self.lock = threading.Lock()

        self.manager = HotkeyManager(
            on_trigger=self._execute_macro,
            on_stop=self._stop_all
        )

        self._build_ui()
        self._refresh_windows()
        self._load_config()

    def _build_ui(self):
        s = ttk.Style()
        s.configure("T.TLabel", font=("Microsoft JhengHei", 10))
        s.configure("B.TLabel", font=("Microsoft JhengHei", 14, "bold"))

        mf = ttk.Frame(self.root, padding=15)
        mf.pack(fill="both", expand=True)
        r = 0

        ttk.Label(mf, text="🎮 KeyMacro", style="B.TLabel").grid(
            row=r, column=0, columnspan=4, sticky="w", pady=(0,8)); r+=1

        ttk.Label(mf, text="觸發熱鍵：", style="T.TLabel").grid(row=r, column=0, sticky="w", pady=4)
        ttk.Entry(mf, textvariable=self.hotkey_str, width=12,
                  font=("Microsoft JhengHei",11)).grid(row=r, column=1, sticky="w", pady=4)
        ttk.Label(mf, text="（按住觸發 / Toggle 時按一下）",
                  font=("Microsoft JhengHei",9)).grid(row=r, column=2, columnspan=2, sticky="w", pady=4)
        r+=1

        ttk.Label(mf, text="停止熱鍵：", style="T.TLabel").grid(row=r, column=0, sticky="w", pady=4)
        ttk.Entry(mf, textvariable=self.stop_hotkey_str, width=12,
                  font=("Microsoft JhengHei",11)).grid(row=r, column=1, sticky="w", pady=4)
        ttk.Label(mf, text="（立即中斷 / Toggle 時再按觸發鍵）",
                  font=("Microsoft JhengHei",9)).grid(row=r, column=2, columnspan=2, sticky="w", pady=4)
        r+=1

        frm = ttk.Frame(mf)
        frm.grid(row=r, column=0, columnspan=4, sticky="w", pady=4)
        ttk.Checkbutton(frm, text="🔄 同一鍵開關（Toggle）",
                        variable=self.toggle_mode).pack(side="left", padx=(0,12))
        ttk.Checkbutton(frm, text="♾️ 無限循環",
                        variable=self.infinite_mode).pack(side="left")
        ttk.Label(mf, text="（ Toggle：按一下啟/停｜♾️：持續發送直到停止｜兩者關閉：按住執行、鬆開停止 ）",
                  font=("Microsoft JhengHei",8), foreground="gray").grid(
                      row=r+1, column=0, columnspan=4, sticky="w", padx=5)
        r+=2

        ttk.Separator(mf, orient="horizontal").grid(
            row=r, column=0, columnspan=4, sticky="ew", pady=4); r+=1

        ttk.Label(mf, text="目標視窗：", style="T.TLabel").grid(row=r, column=0, sticky="w", pady=4)
        sf = ttk.Frame(mf)
        sf.grid(row=r, column=1, columnspan=3, sticky="w", pady=4)
        self.wcombo = ttk.Combobox(sf, textvariable=self.window_var,
                                    width=40, state="readonly", font=("Microsoft JhengHei",10))
        self.wcombo.pack(side="left", padx=(0,5))
        self.wcombo.bind("<<ComboboxSelected>>", self._on_win_sel)
        ttk.Button(sf, text="🔄 更新", command=self._refresh_windows, width=8).pack(side="left", padx=2)
        ttk.Label(mf, text="（選擇目標視窗，會自動偵測句柄變化）",
                  font=("Microsoft JhengHei",9), foreground="gray").grid(
                      row=r+1, column=1, columnspan=3, sticky="w")
        self._sel_hwnd = [0]; r+=2

        ttk.Separator(mf, orient="horizontal").grid(
            row=r, column=0, columnspan=4, sticky="ew", pady=4); r+=1

        ttk.Label(mf, text="巨集序列：", style="T.TLabel").grid(row=r, column=0, sticky="nw", pady=4)
        ef = ttk.Frame(mf)
        ef.grid(row=r, column=1, columnspan=3, sticky="w", pady=4)
        self.tseq = tk.Text(ef, width=48, height=6, font=("Consolas",10))
        self.tseq.pack(side="left", fill="both", expand=True)
        sy = ttk.Scrollbar(ef, orient="vertical", command=self.tseq.yview)
        sy.pack(side="right", fill="y")
        self.tseq.configure(yscrollcommand=sy.set)
        ttk.Label(mf, text="範例：ctrl+c | a, b, c | space | shift+a | f1, f2, f3",
                  font=("Microsoft JhengHei",8), foreground="gray").grid(
                      row=r+1, column=1, columnspan=3, sticky="w"); r+=2

        ttk.Separator(mf, orient="horizontal").grid(
            row=r, column=0, columnspan=4, sticky="ew", pady=4); r+=1

        ff = ttk.Frame(mf)
        ff.grid(row=r, column=0, columnspan=4, sticky="w", pady=4)
        fields = [
            ("按鍵按住（ms）：", self.hold_ms, 0, 0),
            ("按鍵間隔（ms）：", self.interval_ms, 0, 2),
            ("♾️ 重複次數（-1=無限）：", self.repeat_count, 1, 0),
            ("啟動前延遲（ms）：", self.delay_before, 1, 2),
        ]
        for lbl, var, row, col in fields:
            ttk.Label(ff, text=lbl).grid(row=row, column=col, sticky="w", padx=5, pady=(4,0))
            ttk.Entry(ff, textvariable=var, width=9).grid(row=row, column=col+1, sticky="w", padx=5, pady=(4,0))
        r+=1

        bf = ttk.Frame(mf)
        bf.grid(row=r, column=0, columnspan=4, pady=10)
        self.btoggle = ttk.Button(bf, text="▶ 啟動監聽", command=self._toggle, width=18)
        self.btoggle.pack(side="left", padx=5)
        ttk.Button(bf, text="🛑 立即停止", command=self._stop_all, width=14).pack(side="left", padx=5)
        ttk.Button(bf, text="💾 儲存設定", command=self._save_cfg, width=12).pack(side="left", padx=5)
        ttk.Button(bf, text="📋 說明", command=self._show_help, width=8).pack(side="left", padx=5)
        r+=1

        self.slbl = tk.Label(mf, text="📴 未啟動", font=("Microsoft JhengHei",10), fg="gray")
        self.slbl.grid(row=r, column=0, columnspan=4, sticky="w", pady=(5,0))
        self.albl = tk.Label(mf, text="", font=("Microsoft JhengHei",9), fg="orange")
        self.albl.grid(row=r, column=1, columnspan=3, sticky="w", pady=(5,0))

    def _refresh_windows(self):
        try:
            self.window_list = get_all_windows()
            lst = [t for t,_ in self.window_list] or ["（目前沒有可見視窗）"]
            self.wcombo["values"] = lst
            if lst and lst[0] != "（目前沒有可見視窗）":
                self.wcombo.current(0)
                self._on_win_sel(None)
        except Exception as e:
            self.wcombo["values"] = [f"（錯誤：{e}）"]

    def _on_win_sel(self, _):
        idx = self.wcombo.current()
        if 0 <= idx < len(self.window_list):
            t, h = self.window_list[idx]
            self.target_window.set(t)
            self._sel_hwnd[0] = h
        else:
            self.target_window.set("")
            self._sel_hwnd[0] = 0

    def _execute_macro(self):
        seq = [k.strip() for k in self.tseq.get("1.0","end").strip().split(',') if k.strip()]
        if not seq:
            return
        self.stop_event.clear()
        target = self.target_window.get()
        is_inf = self.infinite_mode.get() or self.repeat_count.get() < 0
        self._upd_active(f"{'♾️ 無限循環中' if is_inf else '🔄 執行中'}...")

        def run():
            time.sleep(self.delay_before.get() / 1000.0)
            self._upd_status("⚙️ 發送中...", "orange")
            send_macro_sequence(seq, target,
                                self.hold_ms.get(),
                                self.interval_ms.get(),
                                self.repeat_count.get(),
                                self.stop_event)
            if self.stop_event.is_set():
                self._upd_status("⏹ 已中斷", "red")
            else:
                self._upd_status("✅ 發送完成", "green")
            time.sleep(0.5)
            if not self.stop_event.is_set():
                self._upd_status(f"📡 監聽中：{self.hotkey_str.get()}", "blue")
            self._upd_active("")

        t = threading.Thread(target=run, daemon=True)
        with self.lock:
            self.active_threads.append(t)
        t.start()

    def _stop_all(self):
        self.stop_event.set()
        self._upd_status("⏹ 已中斷", "red")
        self._upd_active("")

    def _toggle(self):
        if not self.is_running:
            t = self.hotkey_str.get().strip()
            s = self.stop_hotkey_str.get().strip()
            if not t:
                messagebox.showwarning("警告", "請輸入觸發熱鍵")
                return
            self.manager.start(t, s, self.toggle_mode.get())
            self.is_running = True
            self.btoggle.config(text="⏹ 停止監聽")
            parts = []
            if self.toggle_mode.get(): parts.append("Toggle")
            if self.infinite_mode.get() or self.repeat_count.get() < 0: parts.append("無限")
            desc = " / ".join(parts) if parts else "按住觸發"
            self._upd_status(f"📡 監聽中：{t}（{desc}）", "blue")
        else:
            self._stop_all()
            self.manager.stop()
            self.is_running = False
            self.btoggle.config(text="▶ 啟動監聽")
            self._upd_status("📴 已停止", "gray")

    def _upd_status(self, txt, color):
        def f():
            self.slbl.config(text=txt, fg=color)
        self.root.after(0, f)

    def _upd_active(self, txt):
        def f():
            self.albl.config(text=txt)
        self.root.after(0, f)

    def _cfg_path(self):
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

    def _save_cfg(self):
        cfg = {
            "hotkey": self.hotkey_str.get(),
            "stop_hotkey": self.stop_hotkey_str.get(),
            "target_window": self.target_window.get(),
            "selected_hwnd": self._sel_hwnd[0],
            "sequence": self.tseq.get("1.0","end").strip(),
            "hold_ms": self.hold_ms.get(),
            "interval_ms": self.interval_ms.get(),
            "repeat_count": self.repeat_count.get(),
            "delay_before": self.delay_before.get(),
            "toggle_mode": self.toggle_mode.get(),
            "infinite_mode": self.infinite_mode.get(),
        }
        with open(self._cfg_path(), "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        self._upd_status("💾 已儲存", "green")

    def _load_config(self):
        p = self._cfg_path()
        if not os.path.exists(p):
            return
        try:
            with open(p, encoding="utf-8") as f:
                cfg = json.load(f)
            self.hotkey_str.set(cfg.get("hotkey","f1"))
            self.stop_hotkey_str.set(cfg.get("stop_hotkey","f2"))
            saved_title = cfg.get("target_window","")
            saved_hwnd = cfg.get("selected_hwnd", 0)
            self.tseq.insert("1.0", cfg.get("sequence","a, b, c"))
            self.hold_ms.set(cfg.get("hold_ms",50))
            self.interval_ms.set(cfg.get("interval_ms",100))
            self.repeat_count.set(cfg.get("repeat_count",-1))
            self.delay_before.set(cfg.get("delay_before",500))
            self.toggle_mode.set(cfg.get("toggle_mode",False))
            self.infinite_mode.set(cfg.get("infinite_mode",True))
            if saved_hwnd and win32gui.IsWindow(saved_hwnd):
                self._sel_hwnd[0] = saved_hwnd
                self.target_window.set(saved_title)
                self.window_var.set(saved_title)
                for i,(t,h) in enumerate(self.window_list):
                    if h == saved_hwnd:
                        self.wcombo.current(i); break
            elif saved_title:
                self.target_window.set(saved_title)
                self.window_var.set(saved_title)
        except Exception:
            pass

    def _show_help(self):
        messagebox.showinfo("說明",
            "【KeyMacro 使用說明】\n\n"
            "【基本操作】\n"
            "1. 選擇目標遊戲視窗\n"
            "2. 設定觸發熱鍵\n"
            "3. 輸入巨集序列（逗號分隔）\n"
            "4. 調整頻率與重複次數\n"
            "5. 啟動監聽，切換到遊戲使用\n\n"
            "【模式說明】\n"
            "• Toggle：按一下啟動，再按一下停止\n"
            "• 無限循環：持續重複直到手動停止\n"
            "• 兩者關閉：按住熱鍵期間執行，鬆開停止\n\n"
            "【巨集格式】\n"
            "  a, b, c       → A→B→C\n"
            "  ctrl+c        → Ctrl+C\n"
            "  shift+a       → Shift+A\n"
            "  space, enter  → 空白鍵→Enter\n\n"
            "【停止方式】\n"
            "  • 停止熱鍵（預設 F2）\n"
            "  • Toggle：再按一次觸發鍵\n"
            "  • 一般模式：鬆開觸發鍵\n"
            "  • 「立即停止」按鈕"
        )

    def run(self):
        self.root.mainloop()

# ═══════════════════════════════════════════════════════════
#  進入點
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("KeyMacro.App")
    tk.Tk().withdraw()  # 避免短暫閃白
    root = tk.Tk()
    app = KeyMacroGUI(root)
    app.run()
