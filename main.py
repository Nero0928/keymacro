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

# ── Windows 專用 ──────────────────────────────────────────
if sys.platform == "win32":
    import win32gui
    import win32console
    import win32api
    import win32con
    import ctypes
    from pynput import keyboard
    from pynput.keyboard import Key, KeyCode, Listener as KbListener
else:
    print("⚠️  此程式僅支援 Windows")
    sys.exit(1)

# ── 嘗試載入 pywin32 ─────────────────────────────────────
try:
    from pynput.keyboard import Key, KeyCode
except ImportError:
    print("❌ 缺少必要套件，請執行：pip install pynput pywin32")
    sys.exit(1)

# ═══════════════════════════════════════════════════════════
#  常數
# ═══════════════════════════════════════════════════════════

WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
SMTO_ABORTIFHUNG = 0x0002

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
#  按鍵發送核心（使用 PostMessage + 視窗有效性檢查）
# ═══════════════════════════════════════════════════════════

def parse_key(key_str: str):
    """解析 'ctrl+c', 'a', 'space' 等字串，回傳 (vk, scan, modifiers)"""
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

def _post_key(hwnd, msg, vk, scan_or_0):
    """包裝 PostMessage，不拋例外"""
    try:
        win32api.PostMessage(hwnd, msg, vk, scan_or_0)
        return True
    except Exception:
        return False

# ── SendInput 相關（用於 DirectInput 遊戲）─────────────────────
# ctypes 結構定義
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
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", ctypes.c_ulong),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", PUL)
    ]

class InputUnion(ctypes.Union):
    _fields_ = [
        ("ki", KeyBdInput),
        ("mi", MouseInput),
        ("hi", HardwareInput)
    ]

class Input(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_ulong),
        ("ii", InputUnion)
    ]

INPUT_KEYBOARD = 1
KEYEVENTF_SCANCODE = 0x0008
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004

user32 = ctypes.windll.user32

def _sendinput_key(vk, scan, down=True):
    """使用 SendInput 發送單一 keybd_event"""
    flags = KEYEVENTF_SCANCODE
    if not down:
        flags |= KEYEVENTF_KEYUP
    
    extra = ctypes.c_ulong(0)
    ii_ary = Input * 1
    ii = ii_ary()
    ii[0].type = INPUT_KEYBOARD
    ii[0].ii.ki = KeyBdInput(vk, scan, flags, 0, ctypes.pointer(extra))
    
    x = user32.SendInput(1, ctypes.byref(ii), ctypes.sizeof(ii[0]))
    return x == 1

def _attach_and_send(target_hwnd, vk, scan, modifiers, hold_ms=50):
    """
    附著到目標視窗執行緒，用 SendInput 發送按鍵（適用於 DirectInput 遊戲）
    """
    try:
        # 取得目標視窗的執行緒 ID
        target_tid = user32.GetWindowThreadProcessId(target_hwnd, 0)
        # 取得目前執行緒 ID
        current_tid = user32.GetCurrentThreadId()
        
        # 附著到目標執行緒（这样 SendInput 会发送到目标窗口）
        user32.AttachThreadInput(current_tid, target_tid, True)
        
        # 發送修飾鍵
        for mod in modifiers:
            if mod in MODIFIER_VK:
                m_vk, m_scan = MODIFIER_VK[mod]
                _sendinput_key(m_vk, m_scan, down=True)
        
        time.sleep(0.005)
        
        # 主按鍵 DOWN
        _sendinput_key(vk, scan, down=True)
        time.sleep(hold_ms / 1000.0)
        
        # 主按鍵 UP
        _sendinput_key(vk, scan, down=False)
        time.sleep(0.005)
        
        # 釋放修飾鍵
        for mod in reversed(modifiers):
            if mod in MODIFIER_VK:
                m_vk, m_scan = MODIFIER_VK[mod]
                _sendinput_key(m_vk, m_scan, down=False)
        
        # 解除附著
        user32.AttachThreadInput(current_tid, target_tid, False)
        return True
    except Exception as e:
        try:
            user32.AttachThreadInput(current_tid, target_tid, False)
        except:
            pass
        return False

def send_key_to_window(hwnd, vk, scan, modifiers, hold_ms=50, stop_event=None):
    """
    發送單一按鍵（含輔助鍵）。
    策略：
    1. 先用 PostMessage（標準 Win32 視窗）
    2. PostMessage 失敗時，用 AttachThreadInput + SendInput（DirectInput 遊戲）
    """
    scan_down = (scan << 16) | 1
    scan_up = (scan << 16) | 1 | 0xC0000000

    # 先嘗試 PostMessage
    post_success = False
    try:
        # 發送修飾鍵 DOWN
        for mod in modifiers:
            if stop_event and stop_event.is_set():
                return
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

        # 主按鍵 DOWN
        _post_key(hwnd, WM_KEYDOWN, vk, scan_down)
        time.sleep(hold_ms / 1000.0)

        if stop_event and stop_event.is_set():
            _post_key(hwnd, WM_KEYUP, vk, scan_up)
            for mod in reversed(modifiers):
                if mod in MODIFIER_VK:
                    m_vk, _ = MODIFIER_VK[mod]
                    _post_key(hwnd, WM_KEYUP, m_vk, 0)
            return

        # 主按鍵 UP
        _post_key(hwnd, WM_KEYUP, vk, scan_up)
        time.sleep(0.008)

        # 釋放修飾鍵 UP
        for mod in reversed(modifiers):
            if mod in MODIFIER_VK:
                m_vk, _ = MODIFIER_VK[mod]
                _post_key(hwnd, WM_KEYUP, m_vk, 0)
        
        post_success = True
    except Exception:
        pass

    # 如果 PostMessage 失敗（通常是 DirectInput 遊戲），使用 AttachThreadInput + SendInput
    if not post_success:
        _attach_and_send(hwnd, vk, scan, modifiers, hold_ms)

    # 如果兩者都失敗，最後手段：直接 SendInput（系統範圍）
    if not post_success:
        try:
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
        except Exception:
            pass

def find_window_by_title(title: str):
    """透過視窗標題尋找 hwnd"""
    result = [0]
    def callback(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            window_title = win32gui.GetWindowText(hwnd)
            if title.lower() in window_title.lower():
                result[0] = hwnd
                return False
        return True
    win32gui.EnumWindows(callback, None)
    return result[0]

def get_all_windows():
    """取得所有可見視窗"""
    windows = []
    seen_titles = set()
    def callback(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd).strip()
            if title and title not in seen_titles:
                try:
                    cls = win32gui.GetClassName(hwnd)
                    if cls in ('WorkerW', 'Shell_TrayWnd', 'DV2ControlHost',
                               'MsgrIMEWindowClass', 'Windows.UI.Core.CoreWindow'):
                        return True
                except:
                    pass
                windows.append((title, hwnd))
                seen_titles.add(title)
        return True
    win32gui.EnumWindows(callback, None)
    windows.sort(key=lambda x: x[0].lower())
    return windows

def send_macro_sequence(sequence, target_title, hold_ms, interval_ms, repeat, stop_event=None):
    """
    發送巨集序列。
    repeat=-1 表示無限循環，直到 stop_event 設定。
    每次迴圈都重新查詢視窗，解決背景視窗句柄失效問題。
    """
    iteration = 0
    while True:
        # 檢查停止旗標
        if stop_event and stop_event.is_set():
            return

        # 無限模式：迴圈一次後遞增迭代計數
        # 有限模式：檢查是否已達重複次數
        if repeat >= 0:
            if iteration >= repeat:
                break
            iteration += 1

        # 每次迴圈都重新查詢視窗（應對背景/最小化後句柄失效）
        hwnd = 0
        if target_title.strip():
            hwnd = find_window_by_title(target_title.strip())

        if hwnd == 0 or not win32gui.IsWindow(hwnd):
            # 視窗已關閉或找不到，跳過這次
            time.sleep(0.1)
            continue

        # 發送序列中的每個按鍵
        for key_str in sequence:
            if stop_event and stop_event.is_set():
                return
            vk, scan, modifiers = parse_key(key_str)
            if vk:
                send_key_to_window(hwnd, vk, scan, modifiers, hold_ms, stop_event)
            if stop_event and stop_event.is_set():
                return
            time.sleep(interval_ms / 1000.0)

        # 無限模式：每次間隔（除了最後一次 sleep）
        if repeat < 0:
            # 連續快速執行時，短暫讓出控制權，避免吃滿 CPU
            time.sleep(0.001)

# ═══════════════════════════════════════════════════════════
#  熱鍵管理（支援 Toggle 模式）
# ═══════════════════════════════════════════════════════════

class HotkeyManager:
    def __init__(self, on_trigger, on_stop):
        self.on_trigger = on_trigger
        self.on_stop = on_stop
        self.trigger_key = None
        self.stop_key = None
        self.trigger_listener = None
        self.stop_listener = None
        self._running = False
        self._trigger_key_held = False
        self._is_toggle_mode = False
        self._macro_active = False

    def _convert_key(self, key):
        if isinstance(key, Key):
            name = key.name.lower()
            if name in ('alt_l', 'alt_r'): return 'alt'
            if name in ('ctrl_l', 'ctrl_r'): return 'ctrl'
            if name in ('shift_l', 'shift_r'): return 'shift'
            if name in ('cmd', 'cmd_r', 'cmd_l'): return 'win'
            return name
        if isinstance(key, KeyCode):
            if key.char:
                return key.char.lower()
        return str(key).replace("'", "").lower()

    def _normalize_key(self, s: str):
        return {
            'control': 'ctrl', 'control_l': 'ctrl', 'control_r': 'ctrl',
            'alt_l': 'alt', 'alt_r': 'alt',
            'shift_l': 'shift', 'shift_r': 'shift',
            'cmd': 'win', 'cmd_l': 'win', 'cmd_r': 'win',
            'windows': 'win',
        }.get(s, s)

    def _trigger_on_press(self, key):
        key_name = self._normalize_key(self._convert_key(key))

        # Toggle 模式：按一下啟動，再按一下停止
        if self._is_toggle_mode and key_name == self.trigger_key:
            if not self._trigger_key_held:
                self._trigger_key_held = True
                if self._macro_active:
                    self.on_stop()
                    self._macro_active = False
                else:
                    self._macro_active = True
                    threading.Thread(target=self._delayed_trigger, daemon=True).start()
        # 一般模式：按住時執行（鬆開不停）
        elif not self._is_toggle_mode and key_name == self.trigger_key and not self._trigger_key_held:
            self._trigger_key_held = True
            self._macro_active = True
            threading.Thread(target=self._delayed_trigger, daemon=True).start()

    def _delayed_trigger(self):
        time.sleep(0.05)
        if self._running and self._trigger_key_held:
            self.on_trigger()

    def _trigger_on_release(self, key):
        key_name = self._normalize_key(self._convert_key(key))
        if key_name == self.trigger_key:
            self._trigger_key_held = False
            # 一般模式：鬆開鍵時停止巨集
            if not self._is_toggle_mode:
                if self._macro_active:
                    self.on_stop()
                    self._macro_active = False

    def _stop_on_press(self, key):
        key_name = self._normalize_key(self._convert_key(key))
        if key_name == self.stop_key:
            self.on_stop()
            self._macro_active = False

    def start(self, trigger, stop, toggle_mode):
        self.trigger_key = self._normalize_key(trigger)
        self.stop_key = self._normalize_key(stop)
        self._is_toggle_mode = toggle_mode
        self._running = True
        self._trigger_key_held = False
        self._macro_active = False

        self.trigger_listener = KbListener(
            on_press=self._trigger_on_press,
            on_release=self._trigger_on_release
        )
        self.trigger_listener.start()

        if not toggle_mode and self.stop_key != self.trigger_key:
            self.stop_listener = KbListener(
                on_press=self._stop_on_press,
                on_release=lambda _: None
            )
            self.stop_listener.start()

    def stop(self):
        self._running = False
        self._macro_active = False
        if self.trigger_listener:
            self.trigger_listener.stop()
            self.trigger_listener = None
        if self.stop_listener:
            self.stop_listener.stop()
            self.stop_listener = None

# ═══════════════════════════════════════════════════════════
#  GUI
# ═══════════════════════════════════════════════════════════

class KeyMacroGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("KeyMacro — 背景遊戲按鍵發送器")
        self.root.geometry("720x680")
        self.root.resizable(False, False)

        self.hotkey_str = tk.StringVar(value="f1")
        self.stop_hotkey_str = tk.StringVar(value="f2")
        self.target_window = tk.StringVar(value="")
        self.hold_ms = tk.IntVar(value=50)
        self.interval_ms = tk.IntVar(value=100)
        self.repeat_count = tk.IntVar(value=-1)  # -1 = 無限
        self.delay_before = tk.IntVar(value=500)
        self.toggle_mode = tk.BooleanVar(value=False)
        self.infinite_mode = tk.BooleanVar(value=True)  # 預設開啟
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
        style = ttk.Style()
        style.configure("Title.TLabel", font=("Microsoft JhengHei", 14, "bold"))
        style.configure("Sub.TLabel", font=("Microsoft JhengHei", 10))

        main_frame = ttk.Frame(self.root, padding=15)
        main_frame.pack(fill="both", expand=True)

        # ── 標題 ───────────────────────────────────────
        ttk.Label(main_frame, text="🎮 KeyMacro", style="Title.TLabel").grid(
            row=0, column=0, columnspan=4, sticky="w", pady=(0, 8))

        # ── 熱鍵設定 ─────────────────────────────────
        row = 1
        ttk.Label(main_frame, text="觸發熱鍵：", style="Sub.TLabel").grid(
            row=row, column=0, sticky="w", pady=5)
        ttk.Entry(main_frame, textvariable=self.hotkey_str, width=12,
                  font=("Microsoft JhengHei", 11)).grid(row=row, column=1, sticky="w", pady=5)
        ttk.Label(main_frame, text="（按住觸發 / Toggle 模式時按一下）",
                  font=("Microsoft JhengHei", 9)).grid(row=row, column=2, columnspan=2, sticky="w", pady=5)

        row += 1
        ttk.Label(main_frame, text="停止熱鍵：", style="Sub.TLabel").grid(
            row=row, column=0, sticky="w", pady=5)
        ttk.Entry(main_frame, textvariable=self.stop_hotkey_str, width=12,
                  font=("Microsoft JhengHei", 11)).grid(row=row, column=1, sticky="w", pady=5)
        ttk.Label(main_frame, text="（立即中斷發送 / Toggle 模式時再按一下觸發鍵）",
                  font=("Microsoft JhengHei", 9)).grid(row=row, column=2, columnspan=2, sticky="w", pady=5)

        # ── 模式選項 ─────────────────────────────────
        row += 1
        mode_frame = ttk.Frame(main_frame)
        mode_frame.grid(row=row, column=0, columnspan=4, sticky="w", pady=5)
        ttk.Checkbutton(mode_frame, text="🔄 同一鍵開關（Toggle）",
                        variable=self.toggle_mode).pack(side="left", padx=(0, 15))
        ttk.Checkbutton(mode_frame, text="♾️ 無限循環（持續發送直到停止）",
                        variable=self.infinite_mode).pack(side="left")

        ttk.Label(main_frame, text="（ Toggle：按一下啟動、再按一下停止｜關閉：按住觸發，鬆開停止 ）",
                  font=("Microsoft JhengHei", 8), foreground="gray").grid(
                      row=row+1, column=0, columnspan=4, sticky="w", padx=5)

        # ── 目標視窗 ─────────────────────────────────
        row += 2
        ttk.Separator(main_frame, orient="horizontal").grid(
            row=row, column=0, columnspan=4, sticky="ew", pady=4)

        row += 1
        ttk.Label(main_frame, text="目標視窗：", style="Sub.TLabel").grid(
            row=row, column=0, sticky="w", pady=5)

        sel_frame = ttk.Frame(main_frame)
        sel_frame.grid(row=row, column=1, columnspan=3, sticky="w", pady=5)

        self.window_combo = ttk.Combobox(sel_frame, textvariable=self.window_var,
                                          width=40, state="readonly", font=("Microsoft JhengHei", 10))
        self.window_combo.pack(side="left", padx=(0, 5))
        self.window_combo.bind("<<ComboboxSelected>>", self._on_window_selected)
        ttk.Button(sel_frame, text="🔄 更新", command=self._refresh_windows, width=8).pack(side="left", padx=2)

        row += 1
        ttk.Label(main_frame, text="（選擇目標視窗，程式會自動偵測句柄變化）",
                  font=("Microsoft JhengHei", 9), foreground="gray").grid(
                      row=row, column=1, columnspan=3, sticky="w")
        self.selected_hwnd = [0]

        # ── 巨集序列 ─────────────────────────────────
        row += 1
        ttk.Separator(main_frame, orient="horizontal").grid(
            row=row, column=0, columnspan=4, sticky="ew", pady=4)

        row += 1
        ttk.Label(main_frame, text="巨集序列：", style="Sub.TLabel").grid(
            row=row, column=0, sticky="nw", pady=5)

        seq_frame = ttk.Frame(main_frame)
        seq_frame.grid(row=row, column=1, columnspan=3, sticky="w", pady=5)

        self.text_seq = tk.Text(seq_frame, width=48, height=6,
                                  font=("Consolas", 10))
        self.text_seq.pack(side="left", fill="both", expand=True)
        scroll_y = ttk.Scrollbar(seq_frame, orient="vertical", command=self.text_seq.yview)
        scroll_y.pack(side="right", fill="y")
        self.text_seq.configure(yscrollcommand=scroll_y.set)

        row += 1
        ttk.Label(main_frame, text="範例：  ctrl+c  |  a, b, c  |  space  |  shift+a  |  f1, f2, f3",
                  font=("Microsoft JhengHei", 8), foreground="gray").grid(
                      row=row, column=1, columnspan=3, sticky="w")

        # ── 頻率設定 ─────────────────────────────────
        row += 1
        ttk.Separator(main_frame, orient="horizontal").grid(
            row=row, column=0, columnspan=4, sticky="ew", pady=4)

        row += 1
        freq_frame = ttk.Frame(main_frame)
        freq_frame.grid(row=row, column=0, columnspan=4, sticky="w", pady=5)

        fields = [
            ("按鍵按住（ms）：", self.hold_ms, 0, 0),
            ("按鍵間隔（ms）：", self.interval_ms, 0, 2),
            ("♾️ 重複次數（-1=無限）：", self.repeat_count, 1, 0),
            ("啟動前延遲（ms）：", self.delay_before, 1, 2),
        ]
        for label_text, var, r, c in fields:
            ttk.Label(freq_frame, text=label_text).grid(row=r, column=c, sticky="w", padx=5, pady=(5,0))
            ttk.Entry(freq_frame, textvariable=var, width=9).grid(row=r, column=c+1, sticky="w", padx=5, pady=(5,0))

        # ── 按鈕列 ─────────────────────────────────
        row += 1
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=row, column=0, columnspan=4, pady=10)

        self.btn_toggle = ttk.Button(btn_frame, text="▶ 啟動監聽",
                                      command=self._toggle_listening, width=18)
        self.btn_toggle.pack(side="left", padx=5)
        ttk.Button(btn_frame, text="🛑 立即停止", command=self._stop_all,
                   width=14).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="💾 儲存設定", command=self._save_config,
                   width=12).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="📋 說明", command=self._show_help,
                   width=8).pack(side="left", padx=5)

        # ── 狀態列 ─────────────────────────────────
        row += 1
        self.status_label = tk.Label(main_frame, text="📴 未啟動",
                                       font=("Microsoft JhengHei", 10), fg="gray")
        self.status_label.grid(row=row, column=0, columnspan=4, sticky="w", pady=(5, 0))

        self.active_label = tk.Label(main_frame, text="",
                                       font=("Microsoft JhengHei", 9), fg="orange")
        self.active_label.grid(row=row, column=1, columnspan=3, sticky="w", pady=(5, 0))

    def _refresh_windows(self):
        try:
            self.window_list = get_all_windows()
            display_list = [title for title, _ in self.window_list]
            if not display_list:
                display_list = ["（目前沒有可見視窗）"]
            self.window_combo["values"] = display_list
            if display_list and display_list[0] != "（目前沒有可見視窗）":
                self.window_combo.current(0)
                self._on_window_selected(None)
        except Exception as e:
            self.window_combo["values"] = [f"（錯誤：{e}）"]

    def _on_window_selected(self, event):
        idx = self.window_combo.current()
        if idx >= 0 and idx < len(self.window_list):
            title, hwnd = self.window_list[idx]
            self.target_window.set(title)
            self.selected_hwnd[0] = hwnd
        else:
            self.target_window.set("")
            self.selected_hwnd[0] = 0

    def _execute_macro(self):
        sequence = [k.strip() for k in self.text_seq.get("1.0", "end").strip().split(',') if k.strip()]
        if not sequence:
            return

        self.stop_event.clear()
        hold = self.hold_ms.get()
        interval = self.interval_ms.get()
        repeat = self.repeat_count.get()
        delay = self.delay_before.get()
        target = self.target_window.get()

        is_infinite = self.infinite_mode.get() or repeat < 0
        status_prefix = "♾️ 無限循環中" if is_infinite else f"🔄 執行中"
        self._update_active(f"{status_prefix}...")

        def run():
            time.sleep(delay / 1000.0)
            self._update_status("⚙️ 發送中（可隨時按停止鍵中斷）...", "orange")
            send_macro_sequence(sequence, target, hold, interval, repeat, self.stop_event)

            if self.stop_event.is_set():
                self._update_status("⏹ 已中斷", "red")
            else:
                self._update_status("✅ 發送完成", "green")
            time.sleep(0.5)
            if not self.stop_event.is_set():
                self._update_status(f"📡 監聽中：{self.hotkey_str.get()}", "blue")
            self._update_active("")

        t = threading.Thread(target=run, daemon=True)
        with self.lock:
            self.active_threads.append(t)
        t.start()

    def _stop_all(self):
        self.stop_event.set()
        self._update_status("⏹ 已中斷", "red")
        self._update_active("")

    def _cleanup_threads(self):
        with self.lock:
            self.active_threads = [t for t in self.active_threads if t.is_alive()]

    def _toggle_listening(self):
        if not self.is_running:
            trigger = self.hotkey_str.get().strip()
            stop = self.stop_hotkey_str.get().strip()
            if not trigger:
                messagebox.showwarning("警告", "請輸入觸發熱鍵")
                return
            self.manager.start(trigger, stop, self.toggle_mode.get())
            self.is_running = True
            self.btn_toggle.config(text="⏹ 停止監聽")
            mode = []
            if self.toggle_mode.get(): mode.append("Toggle")
            if self.infinite_mode.get() or self.repeat_count.get() < 0: mode.append("無限")
            desc = " / ".join(mode) if mode else "按住觸發"
            self._update_status(f"📡 監聽中：{trigger}（{desc}）", "blue")
        else:
            self._stop_all()
            self.manager.stop()
            self.is_running = False
            self.btn_toggle.config(text="▶ 啟動監聽")
            self._update_status("📴 已停止", "gray")

    def _update_status(self, text, color):
        def _inner():
            self.status_label.config(text=text, fg=color)
        self.root.after(0, _inner)

    def _update_active(self, text):
        def _inner():
            self.active_label.config(text=text)
        self.root.after(0, _inner)

    def _get_config_path(self):
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

    def _save_config(self):
        cfg = {
            "hotkey": self.hotkey_str.get(),
            "stop_hotkey": self.stop_hotkey_str.get(),
            "target_window": self.target_window.get(),
            "selected_hwnd": self.selected_hwnd[0],
            "sequence": self.text_seq.get("1.0", "end").strip(),
            "hold_ms": self.hold_ms.get(),
            "interval_ms": self.interval_ms.get(),
            "repeat_count": self.repeat_count.get(),
            "delay_before": self.delay_before.get(),
            "toggle_mode": self.toggle_mode.get(),
            "infinite_mode": self.infinite_mode.get(),
        }
        with open(self._get_config_path(), "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        self._update_status("💾 已儲存", "green")

    def _load_config(self):
        path = self._get_config_path()
        if os.path.exists(path):
            try:
                with open(path, encoding="utf-8") as f:
                    cfg = json.load(f)
                self.hotkey_str.set(cfg.get("hotkey", "f1"))
                self.stop_hotkey_str.set(cfg.get("stop_hotkey", "f2"))
                saved_title = cfg.get("target_window", "")
                saved_hwnd = cfg.get("selected_hwnd", 0)
                self.text_seq.insert("1.0", cfg.get("sequence", "a, b, c"))
                self.hold_ms.set(cfg.get("hold_ms", 50))
                self.interval_ms.set(cfg.get("interval_ms", 100))
                self.repeat_count.set(cfg.get("repeat_count", -1))
                self.delay_before.set(cfg.get("delay_before", 500))
                self.toggle_mode.set(cfg.get("toggle_mode", False))
                self.infinite_mode.set(cfg.get("infinite_mode", True))

                if saved_hwnd and win32gui.IsWindow(saved_hwnd):
                    self.selected_hwnd[0] = saved_hwnd
                    self.target_window.set(saved_title)
                    self.window_var.set(saved_title)
                    for i, (title, hwnd) in enumerate(self.window_list):
                        if hwnd == saved_hwnd:
                            self.window_combo.current(i)
                            break
                elif saved_title:
                    self.target_window.set(saved_title)
                    self.window_var.set(saved_title)
            except Exception:
                pass

    def _show_help(self):
        help_text = (
            "【KeyMacro 使用說明】\n\n"
            "【基本操作】\n"
            "1. 選擇目標遊戲視窗\n"
            "2. 設定觸發熱鍵（按住/Toggle）\n"
            "3. 設定巨集序列（逗號分隔）\n"
            "4. 調整頻率與重複次數\n"
            "5. 啟動監聽，切換到遊戲使用\n\n"
            "【模式說明】\n"
            "• Toggle 模式：按一下啟動，再按一下停止\n"
            "• 無限循環：巨集持續重複直到手動停止\n"
            "• 關閉兩者：按住熱鍵期間執行，鬆開停止\n\n"
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
        messagebox.showinfo("說明", help_text)

    def run(self):
        self.root.mainloop()

# ═══════════════════════════════════════════════════════════
#  進入點
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("KeyMacro.App")
    root = tk.Tk()
    app = KeyMacroGUI(root)
    app.run()
