#!/usr/bin/env python3
"""
KeyMacro — 背景遊戲按鍵發送器
類似 X-Mouse Button Control，支援觸發鍵、組合鍵、頻率設定

相依套件：pynput, pywin32
pip install pynput pywin32
"""

import sys
import time
import threading
import json
import os
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

# ── 嘗試載入 pywin32，若失敗則提示安裝 ──────────────────────
try:
    from pynput.keyboard import Key, KeyCode
except ImportError:
    print("❌ 缺少必要套件，請執行：pip install pynput pywin32")
    sys.exit(1)

# ═══════════════════════════════════════════════════════════
#  按鍵對應表（虛擬鍵碼 + Scan Code）
# ═══════════════════════════════════════════════════════════

VK_CODE = {
    # 字母
    'a': (0x41, 0x1E), 'b': (0x42, 0x30), 'c': (0x43, 0x2E),
    'd': (0x44, 0x20), 'e': (0x45, 0x12), 'f': (0x46, 0x21),
    'g': (0x47, 0x22), 'h': (0x48, 0x23), 'i': (0x49, 0x17),
    'j': (0x4A, 0x24), 'k': (0x4B, 0x25), 'l': (0x4C, 0x26),
    'm': (0x4D, 0x32), 'n': (0x4E, 0x31), 'o': (0x4F, 0x18),
    'p': (0x50, 0x19), 'q': (0x51, 0x10), 'r': (0x52, 0x13),
    's': (0x53, 0x1F), 't': (0x54, 0x14), 'u': (0x55, 0x16),
    'v': (0x56, 0x2F), 'w': (0x57, 0x11), 'x': (0x58, 0x2D),
    'y': (0x59, 0x15), 'z': (0x5A, 0x2C),
    # 數字
    '0': (0x30, 0x0B), '1': (0x31, 0x02), '2': (0x32, 0x03),
    '3': (0x33, 0x04), '4': (0x34, 0x05), '5': (0x35, 0x06),
    '6': (0x36, 0x07), '7': (0x37, 0x08), '8': (0x38, 0x09),
    '9': (0x39, 0x0A),
    # 數字鍵盤
    'num0': (0x60, 0x52), 'num1': (0x61, 0x4F), 'num2': (0x62, 0x50),
    'num3': (0x63, 0x51), 'num4': (0x64, 0x4B), 'num5': (0x65, 0x4C),
    'num6': (0x66, 0x4D), 'num7': (0x67, 0x47), 'num8': (0x68, 0x48),
    'num9': (0x69, 0x49), 'num*': (0x6A, 0x37), 'num+': (0x6B, 0x4E),
    'num-': (0x6D, 0x4A), 'num.': (0x6E, 0x53),
    # 功能鍵
    'f1': (0x70, 0x3B), 'f2': (0x71, 0x3C), 'f3': (0x72, 0x3D),
    'f4': (0x73, 0x3E), 'f5': (0x74, 0x3F), 'f6': (0x75, 0x40),
    'f7': (0x76, 0x41), 'f8': (0x77, 0x42), 'f9': (0x78, 0x43),
    'f10': (0x79, 0x44), 'f11': (0x7A, 0x57), 'f12': (0x7B, 0x58),
    # 特殊鍵
    'space': (0x20, 0x39), 'enter': (0x0D, 0x1C), 'tab': (0x09, 0x0F),
    'escape': (0x1B, 0x01), 'backspace': (0x08, 0x0E),
    'delete': (0x2E, 0x53), 'insert': (0x2D, 0x52),
    'home': (0x24, 0x47), 'end': (0x23, 0x4F),
    'pageup': (0x21, 0x49), 'pagedown': (0x22, 0x51),
    'up': (0x26, 0x48), 'down': (0x28, 0x50),
    'left': (0x25, 0x4B), 'right': (0x27, 0x4D),
    # 符號（需 Shift）
    '!': ('shift', '1'), '@': ('shift', '2'), '#': ('shift', '3'),
    '$': ('shift', '4'), '%': ('shift', '5'), '^': ('shift', '6'),
    '&': ('shift', '7'), '*': ('shift', '8'), '(': ('shift', '9'),
    ')': ('shift', '0'),
    # 輔助鍵名稱對應
    'ctrl': 'ctrl', 'shift': 'shift', 'alt': 'alt', 'win': 'win',
    'control': 'ctrl', 'lctrl': 'lctrl', 'rctrl': 'rctrl',
    'lshift': 'lshift', 'rshift': 'rshift', 'lalt': 'lalt', 'ralt': 'ralt',
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
#  按鍵發送核心（使用 PostMessage 發至背景視窗）
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

def send_key_to_window(hwnd: int, vk: int, scan: int, modifiers: list, hold_ms: float = 50):
    """發送單一按鍵至指定視窗（含輔助鍵）"""
    WM_KEYDOWN = 0x0100
    WM_KEYUP = 0x0101
    WM_SYSKEYDOWN = 0x0104
    WM_SYSKEYUP = 0x0105
    
    # 發送修飾鍵
    for mod in modifiers:
        if mod in MODIFIER_VK:
            mod_vk, _ = MODIFIER_VK[mod]
            win32api.PostMessage(hwnd, WM_KEYDOWN, mod_vk, 0)
    
    time.sleep(0.01)
    
    # 發送主按鍵
    win32api.PostMessage(hwnd, WM_KEYDOWN, vk, (scan << 16) | 1)
    time.sleep(hold_ms / 1000.0)
    win32api.PostMessage(hwnd, WM_KEYUP, vk, (scan << 16) | 1 | 0xC0000000)
    
    time.sleep(0.01)
    
    # 釋放修飾鍵（倒序）
    for mod in reversed(modifiers):
        if mod in MODIFIER_VK:
            mod_vk, _ = MODIFIER_VK[mod]
            win32api.PostMessage(hwnd, WM_KEYUP, mod_vk, 0xC0000000)

def find_window_by_title(title: str) -> int:
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

def get_all_windows() -> list:
    """取得所有可見視窗的標題列表（排除空的、重複的）"""
    windows = []
    seen_titles = set()
    
    def callback(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd).strip()
            if title and title not in seen_titles:
                # 排除系統視窗
                try:
                    cls_name = win32gui.GetClassName(hwnd)
                    if cls_name in ('WorkerW', 'Shell_TrayWnd', 'DV2ControlHost', 
                                    'MsgrIMEWindowClass', 'Windows.UI.Core.CoreWindow'):
                        return True
                except:
                    pass
                windows.append((title, hwnd))
                seen_titles.add(title)
        return True
    
    win32gui.EnumWindows(callback, None)
    # 按視窗標題排序
    windows.sort(key=lambda x: x[0].lower())
    return windows

def send_macro_sequence(sequence: list, hwnd: int, hold_ms: float, interval_ms: float, repeat: int):
    """發送一連串按鍵（巨集）"""
    for _ in range(repeat):
        for key_str in sequence:
            if hwnd == 0 or not win32gui.IsWindow(hwnd):
                return
            vk, scan, modifiers = parse_key(key_str)
            if vk:
                send_key_to_window(hwnd, vk, scan, modifiers, hold_ms)
            time.sleep(interval_ms / 1000.0)

# ═══════════════════════════════════════════════════════════
#  熱鍵監聽（pynput）
# ═══════════════════════════════════════════════════════════

class HotkeyListener:
    def __init__(self, on_activate, on_stop):
        self.on_activate = on_activate
        self.on_stop = on_stop
        self.current_key = None
        self.listener = None
        self._running = False
        self._key_held = False
    
    def _convert_key(self, key):
        """將 pynput Key/KeyCode 轉為字串"""
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
    
    def _normalize_key(self, s: str) -> str:
        """標準化按鍵名稱"""
        mapping = {
            'control': 'ctrl', 'control_l': 'ctrl', 'control_r': 'ctrl',
            'alt_l': 'alt', 'alt_r': 'alt',
            'shift_l': 'shift', 'shift_r': 'shift',
            'cmd': 'win', 'cmd_l': 'win', 'cmd_r': 'win',
            'windows': 'win',
        }
        return mapping.get(s, s)
    
    def on_press(self, key):
        key_name = self._convert_key(key)
        key_name = self._normalize_key(key_name)
        
        if key_name == self.current_key and not self._key_held:
            self._key_held = True
            threading.Thread(target=self._delayed_activate, daemon=True).start()
    
    def _delayed_activate(self):
        time.sleep(0.05)
        if self._key_held and self._running:
            self.on_activate()
    
    def on_release(self, key):
        key_name = self._convert_key(key)
        key_name = self._normalize_key(key_name)
        if key_name == self.current_key:
            self._key_held = False
    
    def start(self, hotkey: str):
        self.current_key = self._normalize_key(hotkey)
        self._running = True
        self._key_held = False
        self.listener = KbListener(on_press=self.on_press, on_release=self.on_release)
        self.listener.start()
    
    def stop(self):
        self._running = False
        if self.listener:
            self.listener.stop()

# ═══════════════════════════════════════════════════════════
#  GUI 主體
# ═══════════════════════════════════════════════════════════

class KeyMacroGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("KeyMacro — 背景遊戲按鍵發送器")
        self.root.geometry("700x600")
        self.root.resizable(False, False)
        
        self.hotkey_str = tk.StringVar(value="f1")
        self.target_window = tk.StringVar(value="")
        self.sequence_str = tk.StringVar(value="a, b, c")
        self.hold_ms = tk.IntVar(value=50)
        self.interval_ms = tk.IntVar(value=100)
        self.repeat_count = tk.IntVar(value=1)
        self.delay_before = tk.IntVar(value=500)
        self.is_running = False
        self.listener_thread = None
        self.stop_hotkey = "f2"
        self.window_var = tk.StringVar(value="")
        self.window_list = []  # (title, hwnd)
        
        self.listener = HotkeyListener(
            on_activate=self._execute_macro,
            on_stop=self._stop_macro
        )
        
        self._build_ui()
        self._refresh_windows()
        self._load_config()
    
    def _build_ui(self):
        style = ttk.Style()
        style.configure("Title.TLabel", font=("Microsoft JhengHei", 14, "bold"))
        style.configure("Sub.TLabel", font=("Microsoft JhengHei", 10))
        
        # ── 主框架 ──────────────────────────────────────
        main_frame = ttk.Frame(self.root, padding=15)
        main_frame.pack(fill="both", expand=True)
        
        # ── 標題 ───────────────────────────────────────
        ttk.Label(main_frame, text="🎮 KeyMacro", style="Title.TLabel").grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 10))
        
        # ── 觸發鍵設定 ─────────────────────────────────
        row = 1
        ttk.Label(main_frame, text="觸發熱鍵：", style="Sub.TLabel").grid(row=row, column=0, sticky="w", pady=5)
        ttk.Entry(main_frame, textvariable=self.hotkey_str, width=15, font=("Microsoft JhengHei", 11)).grid(row=row, column=1, sticky="w", pady=5)
        ttk.Label(main_frame, text="（按住此鍵觸發巨集）", font=("Microsoft JhengHei", 9)).grid(row=row, column=2, sticky="w", pady=5)
        
        # ── 停止鍵 ─────────────────────────────────────
        row += 1
        ttk.Label(main_frame, text="停止熱鍵：", style="Sub.TLabel").grid(row=row, column=0, sticky="w", pady=5)
        ttk.Entry(main_frame, text=self.stop_hotkey, width=15, font=("Microsoft JhengHei", 11), state="readonly").grid(row=row, column=1, sticky="w", pady=5)
        ttk.Label(main_frame, text="（隨時中斷發送）", font=("Microsoft JhengHei", 9)).grid(row=row, column=2, sticky="w", pady=5)
        
        # ── 目標視窗 ───────────────────────────────────
        row += 1
        ttk.Label(main_frame, text="目標視窗：", style="Sub.TLabel").grid(row=row, column=0, sticky="w", pady=5)
        
        # 上方：下拉選單 + 重新整理按鈕
        sel_frame = ttk.Frame(main_frame)
        sel_frame.grid(row=row, column=1, columnspan=2, sticky="w", pady=5)
        
        self.window_combo = ttk.Combobox(sel_frame, textvariable=self.window_var, 
                                          width=38, state="readonly", font=("Microsoft JhengHei", 10))
        self.window_combo.pack(side="left", padx=(0, 5))
        self.window_combo.bind("<<ComboboxSelected>>", self._on_window_selected)
        
        ttk.Button(sel_frame, text="🔄 重新整理", command=self._refresh_windows, width=10).pack(side="left", padx=2)
        
        # 下方：說明 + 目前選取
        ttk.Label(main_frame, text="（選擇目標視窗，或留空表示前景視窗）", 
                  font=("Microsoft JhengHei", 9), foreground="gray").grid(
                      row=row+1, column=1, columnspan=2, sticky="w")
        self.selected_hwnd = [0]  # 選中的視窗 handle
        
        # ── 巨集序列 ───────────────────────────────────
        row += 2
        ttk.Separator(main_frame, orient="horizontal").grid(row=row, column=0, columnspan=3, sticky="ew", pady=8)
        row += 1
        ttk.Label(main_frame, text="巨集序列（逗號分隔）：", style="Sub.TLabel").grid(row=row, column=0, sticky="nw", pady=5)
        text_seq = tk.Text(main_frame, width=45, height=6, font=("Consolas", 10))
        text_seq.grid(row=row, column=1, columnspan=2, sticky="w", pady=5)
        self.text_seq = text_seq
        
        hint_text = (
            "範例：\n"
            "  ctrl+c       →  發送 Ctrl+C\n"
            "  a, b, c      →  依序發送 A、B、C\n"
            "  space        →  空白鍵\n"
            "  shift+a      →  Shift+A（大寫 A）\n"
            "  f1, f2, f3   →  依序按 F1、F2、F3\n"
            "支援：ctrl/shift/alt/win + 按鍵組合"
        )
        ttk.Label(main_frame, text=hint_text, font=("Microsoft JhengHei", 8), foreground="gray", justify="left").grid(
            row=row+1, column=1, columnspan=2, sticky="w", padx=5
        )
        
        # ── 頻率設定 ───────────────────────────────────
        row += 2
        ttk.Separator(main_frame, orient="horizontal").grid(row=row, column=0, columnspan=3, sticky="ew", pady=8)
        row += 1
        
        freq_frame = ttk.Frame(main_frame)
        freq_frame.grid(row=row, column=0, columnspan=3, sticky="w", pady=5)
        
        ttk.Label(freq_frame, text="按鍵按住時間（ms）：").grid(row=0, column=0, sticky="w", padx=5)
        ttk.Entry(freq_frame, textvariable=self.hold_ms, width=8).grid(row=0, column=1, sticky="w", padx=5)
        
        ttk.Label(freq_frame, text="按鍵間隔（ms）：").grid(row=0, column=2, sticky="w", padx=5)
        ttk.Entry(freq_frame, textvariable=self.interval_ms, width=8).grid(row=0, column=3, sticky="w", padx=5)
        
        ttk.Label(freq_frame, text="重複次數：").grid(row=1, column=0, sticky="w", padx=5, pady=(5,0))
        ttk.Entry(freq_frame, textvariable=self.repeat_count, width=8).grid(row=1, column=1, sticky="w", padx=5, pady=(5,0))
        
        ttk.Label(freq_frame, text="啟動前延遲（ms）：").grid(row=1, column=2, sticky="w", padx=5, pady=(5,0))
        ttk.Entry(freq_frame, textvariable=self.delay_before, width=8).grid(row=1, column=3, sticky="w", padx=5, pady=(5,0))
        
        # ── 按鈕列 ────────────────────────────────────
        row += 1
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=row, column=0, columnspan=3, pady=15)
        
        self.btn_toggle = ttk.Button(btn_frame, text="▶ 啟動監聽", command=self._toggle_listening, width=18)
        self.btn_toggle.pack(side="left", padx=5)
        
        ttk.Button(btn_frame, text="🧪 測試發送（單次）", command=self._test_send, width=18).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="💾 儲存設定", command=self._save_config, width=14).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="📋 說明", command=self._show_help, width=10).pack(side="left", padx=5)
        
        # ── 狀態列 ────────────────────────────────────
        row += 1
        self.status_label = tk.Label(main_frame, text="📴 未啟動", font=("Microsoft JhengHei", 10), fg="gray")
        self.status_label.grid(row=row, column=0, columnspan=3, sticky="w", pady=(5, 0))
    
    def _refresh_windows(self):
        """重新整理視窗列表"""
        try:
            self.window_list = get_all_windows()
            display_list = [f"{title}" for title, _ in self.window_list]
            if not display_list:
                display_list = ["（目前沒有可見視窗）"]
            self.window_combo["values"] = display_list
            if display_list and display_list[0] != "（目前沒有可見視窗）":
                self.window_combo.current(0)
                self._on_window_selected(None)
        except Exception as e:
            self.window_combo["values"] = [f"（錯誤：{e}）"]
    
    def _on_window_selected(self, event):
        """當使用者選擇視窗時更新 target_window"""
        idx = self.window_combo.current()
        if idx >= 0 and idx < len(self.window_list):
            title, hwnd = self.window_list[idx]
            self.target_window.set(title)
            self.selected_hwnd[0] = hwnd
        else:
            self.target_window.set("")
            self.selected_hwnd[0] = 0
    
    def _execute_macro(self):
        """執行巨集"""
        sequence = [k.strip() for k in self.text_seq.get("1.0", "end").strip().split(',') if k.strip()]
        if not sequence:
            return
        
        hold = self.hold_ms.get()
        interval = self.interval_ms.get()
        repeat = self.repeat_count.get()
        delay = self.delay_before.get()
        
        # 優先使用已選中的 hwnd，否則用名稱查詢
        if self.selected_hwnd[0] != 0 and win32gui.IsWindow(self.selected_hwnd[0]):
            hwnd = self.selected_hwnd[0]
        elif self.target_window.get().strip():
            hwnd = find_window_by_title(self.target_window.get().strip())
            if hwnd == 0:
                self._update_status(f"❌ 找不到視窗：{self.target_window.get()}", "red")
                return
        else:
            hwnd = win32gui.GetForegroundWindow()
        
        def run():
            time.sleep(delay / 1000.0)
            self._update_status(f"🔄 發送中...（{repeat}x）", "orange")
            send_macro_sequence(sequence, hwnd, hold, interval, repeat)
            self._update_status(f"✅ 發送完成", "green")
            time.sleep(1)
            self._update_status(f"📡 監聽中：{self.hotkey_str.get()}", "blue")
        
        threading.Thread(target=run, daemon=True).start()
    
    def _stop_macro(self):
        self._update_status("⏹ 已中斷", "red")
    
    def _test_send(self):
        self._execute_macro()
    
    def _toggle_listening(self):
        if not self.is_running:
            hotkey = self.hotkey_str.get().strip()
            if not hotkey:
                messagebox.showwarning("警告", "請輸入觸發熱鍵")
                return
            self.listener.start(hotkey)
            self.is_running = True
            self.btn_toggle.config(text="⏹ 停止監聽")
            self._update_status(f"📡 監聽中：{hotkey}", "blue")
        else:
            self.listener.stop()
            self.is_running = False
            self.btn_toggle.config(text="▶ 啟動監聽")
            self._update_status("📴 已停止", "gray")
    
    def _update_status(self, text: str, color: str):
        def _inner():
            self.status_label.config(text=text, fg=color)
        self.root.after(0, _inner)
    
    def _get_config_path(self):
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
    
    def _save_config(self):
        cfg = {
            "hotkey": self.hotkey_str.get(),
            "target_window": self.target_window.get(),
            "selected_hwnd": self.selected_hwnd[0],
            "sequence": self.text_seq.get("1.0", "end").strip(),
            "hold_ms": self.hold_ms.get(),
            "interval_ms": self.interval_ms.get(),
            "repeat_count": self.repeat_count.get(),
            "delay_before": self.delay_before.get(),
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
                saved_title = cfg.get("target_window", "")
                saved_hwnd = cfg.get("selected_hwnd", 0)
                self.text_seq.insert("1.0", cfg.get("sequence", "a, b, c"))
                self.hold_ms.set(cfg.get("hold_ms", 50))
                self.interval_ms.set(cfg.get("interval_ms", 100))
                self.repeat_count.set(cfg.get("repeat_count", 1))
                self.delay_before.set(cfg.get("delay_before", 500))
                
                # 嘗試恢復選中的視窗
                if saved_hwnd and win32gui.IsWindow(saved_hwnd):
                    self.selected_hwnd[0] = saved_hwnd
                    self.target_window.set(saved_title)
                    self.window_var.set(saved_title)
                    
                    # 如果清單中有這個視窗，選中它
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
            "1. 從下拉選單選擇目標遊戲視窗\n"
            "2. 設定觸發熱鍵（按住時觸發，如 F1）\n"
            "3. 輸入巨集序列，用逗號分隔（如 ctrl+c, a, b）\n"
            "4. 設定按鍵頻率、重複次數\n"
            "5. 點擊「啟動監聽」\n"
            "6. 切換到遊戲，按住熱鍵即可觸發\n\n"
            "【巨集格式】\n"
            "  a, b, c         → 依序發送 A → B → C\n"
            "  ctrl+c          → Ctrl+C\n"
            "  shift+a         → Shift+A\n"
            "  alt+f4          → Alt+F4\n"
            "  space, enter    → 空白鍵 → Enter\n"
            "  f1, f2, f3      → F1 → F2 → F3\n\n"
            "【視窗選擇】\n"
            "  從下拉選單選擇目標遊戲\n"
            "  留空（選擇第一項）表示發送至前景視窗\n"
            "  點擊「重新整理」更新視窗列表\n\n"
            "【停止鍵】\n"
            "  F2 可隨時中斷發送"
        )
        messagebox.showinfo("說明", help_text)
    
    def run(self):
        self.root.mainloop()

# ═══════════════════════════════════════════════════════════
#  進入點
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("KeyMacro.App")
    
    root = tk.Tk()
    app = KeyMacroGUI(root)
    app.run()
