#!/usr/bin/env python3
"""
KeyMacro Browser — 瀏覽器遊戲按鍵發送器
適用於 MapleStory World 等瀏覽器遊戲

原理：
- 使用 Playwright 啟動/控制瀏覽器
- 透過 CDP（Chrome DevTools Protocol）注入 JavaScript
- 直接呼叫遊戲的 keydown/keyup 事件處理器

相依套件：
pip install playwright
playwright install chromium

使用方法：
1. 首次：python browser_macro.py --install
2. 之後：python browser_macro.py
"""

import sys
import time
import threading
import json
import os
import tkinter as tk
from tkinter import ttk, messagebox

if sys.platform != "win32":
    print("⚠️  此程式僅支援 Windows")
    sys.exit(1)

# ═══════════════════════════════════════════════════════════
#  Playwright + CDP 核心
# ═══════════════════════════════════════════════════════════

try:
    from playwright.sync_api import sync_playwright, Playwright
    import asyncio
except ImportError:
    print("❌ 缺少 playwright，請執行：")
    print("   pip install playwright")
    print("   playwright install chromium")
    sys.exit(1)

# Virtual Key Code → Key Name 映射（用於 JS KeyboardEvent）
VK_TO_KEYNAME = {
    0x41: 'a', 0x42: 'b', 0x43: 'c', 0x44: 'd', 0x45: 'e',
    0x46: 'f', 0x47: 'g', 0x48: 'h', 0x49: 'i', 0x4A: 'j',
    0x4B: 'k', 0x4C: 'l', 0x4D: 'm', 0x4E: 'n', 0x4F: 'o',
    0x50: 'p', 0x51: 'q', 0x52: 'r', 0x53: 's', 0x54: 't',
    0x55: 'u', 0x56: 'v', 0x57: 'w', 0x58: 'x', 0x59: 'y',
    0x5A: 'z',
    0x30: '0', 0x31: '1', 0x32: '2', 0x33: '3', 0x34: '4',
    0x35: '5', 0x36: '6', 0x37: '7', 0x38: '8', 0x39: '9',
    0x0D: 'Enter', 0x20: ' ', 0x09: 'Tab', 0x1B: 'Escape',
    0x08: 'Backspace',
    0x70: 'F1', 0x71: 'F2', 0x72: 'F3', 0x73: 'F4',
    0x74: 'F5', 0x75: 'F6', 0x76: 'F7', 0x77: 'F8',
    0x78: 'F9', 0x79: 'F10', 0x7A: 'F11', 0x7B: 'F12',
    0x25: 'ArrowLeft', 0x27: 'ArrowRight', 0x26: 'ArrowUp', 0x28: 'ArrowDown',
}

# 掃描碼對應表
VK_TO_SCANCODE = {
    0x41: 0x1E, 0x42: 0x30, 0x43: 0x2E, 0x44: 0x20, 0x45: 0x12,
    0x46: 0x21, 0x47: 0x22, 0x48: 0x23, 0x49: 0x17, 0x4A: 0x24,
    0x4B: 0x25, 0x4C: 0x26, 0x4D: 0x32, 0x4E: 0x31, 0x4F: 0x18,
    0x50: 0x19, 0x51: 0x10, 0x52: 0x13, 0x53: 0x1F, 0x54: 0x14,
    0x55: 0x16, 0x56: 0x2F, 0x57: 0x11, 0x58: 0x2D, 0x59: 0x15,
    0x5A: 0x2C,
    0x30: 0x0B, 0x31: 0x02, 0x32: 0x03, 0x33: 0x04, 0x34: 0x05,
    0x35: 0x06, 0x36: 0x07, 0x37: 0x08, 0x38: 0x09, 0x39: 0x0A,
    0x0D: 0x1C, 0x20: 0x39, 0x09: 0x0F, 0x1B: 0x01, 0x08: 0x0E,
    0x70: 0x3B, 0x71: 0x3C, 0x72: 0x3D, 0x73: 0x3E, 0x74: 0x3F,
    0x75: 0x40, 0x76: 0x41, 0x77: 0x42, 0x78: 0x43, 0x79: 0x44,
    0x7A: 0x57, 0x7B: 0x58,
    0x25: 0x4B, 0x27: 0x4D, 0x26: 0x48, 0x28: 0x50,
}

class BrowserMacro:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.ready = False
        self._lock = threading.Lock()
    
    def _make_js_key_event(self, vk, scan, keydown):
        """產生 JS KeyboardEvent 初始化物件"""
        key_name = VK_TO_KEYNAME.get(vk, chr(vk) if 0x41 <= vk <= 0x5A else "")
        code = f"Key{key_name.upper()}" if key_name.isalpha() else (
            f"Arrow{key_name.replace('Arrow','')}" if key_name.startswith("Arrow") else key_name
        )
        key = key_name if key_name else chr(vk) if 0x41 <= vk <= 0x5A else ""

        return {
            "key": key,
            "code": code,
            "keyCode": vk,
            "which": vk,
            "charCode": 0,
            "scanCode": scan,
            "location": 0,
            "bubbles": True,
            "cancelable": True,
            "repeat": False,
            "isComposing": False,
            "detail": 0,
            "view": "window",
        }

    def _inject_js_key(self, page, vk, scan, modifiers, keydown, stop_event=None):
        """
        注入 JS 來發送鍵盤事件。
        策略：嘗試多層次注入，確保事件能傳到遊戲。
        """
        key_name = VK_TO_KEYNAME.get(vk, "")
        code = f"Key{key_name.upper()}" if key_name.isalpha() else (
            f"Arrow{key_name.replace('Arrow','')}" if key_name.startswith("Arrow") else key_name
        )
        key = key_name if key_name else chr(vk) if 0x41 <= vk <= 0x5A else ""

        # 方法1：嘗試在 document 上 dispatchEvent
        js_code = f"""
        (function() {{
            const vk = {vk};
            const scan = {scan};
            const keydown = {str(keydown).lower()};
            const key = "{key}";
            const code = "{code}";
            
            const eventOpts = {{
                bubbles: true,
                cancelable: true,
                view: window,
                key: key,
                code: code,
                keyCode: vk,
                which: vk,
                charCode: 0,
                location: 0,
                repeat: false,
                isComposing: false
            }};
            
            // 先試 document
            let el = document;
            // 找可能的遊戲容器
            const iframes = document.querySelectorAll('iframe');
            if (iframes.length > 0) {{
                el = iframes[0].contentDocument || iframes[0].contentWindow?.document;
            }}
            
            if (el) {{
                try {{
                    const evt = new KeyboardEvent(keydown ? 'keydown' : 'keyup', eventOpts);
                    el.dispatchEvent(evt);
                    return 'ok';
                }} catch(e) {{
                    return 'doc_failed: ' + e.message;
                }}
            }}
            
            // 方法2：嘗試 activeElement
            try {{
                const active = document.activeElement;
                if (active && active !== document.body) {{
                    const evt = new KeyboardEvent(keydown ? 'keydown' : 'keyup', eventOpts);
                    active.dispatchEvent(evt);
                    return 'active_ok';
                }}
            }} catch(e) {{}}
            
            // 方法3：向所有 iframe 廣播
            try {{
                iframes.forEach(iframe => {{
                    try {{
                        const doc = iframe.contentDocument || iframe.contentWindow?.document;
                        if (doc) {{
                            const evt = new KeyboardEvent(keydown ? 'keydown' : 'keyup', eventOpts);
                            doc.dispatchEvent(evt);
                        }}
                    }} catch(ee) {{}}
                }});
                return 'broadcast_ok';
            }} catch(e) {{
                return 'broadcast_failed: ' + e.message;
            }}
        }})()
        """
        
        try:
            if stop_event and stop_event.is_set():
                return None
            result = page.evaluate(js_code)
            return result
        except Exception as e:
            return f"error: {e}"
    
    def send_key(self, vk, scan, modifiers, hold_ms, stop_event=None):
        """發送單一按鍵到瀏覽器遊戲"""
        if not self.page or not self.ready:
            return
        
        # 先發送修飾鍵
        MOD_VK = {'ctrl': 0x11, 'shift': 0x10, 'alt': 0x12}
        for mod in modifiers:
            if stop_event and stop_event.is_set():
                return
            m_vk = MOD_VK.get(mod)
            if m_vk:
                m_scan = VK_TO_SCANCODE.get(m_vk, 0)
                self._inject_js_key(self.page, m_vk, m_scan, [], True, stop_event)
        
        time.sleep(0.005)
        
        # 主按鍵
        result = self._inject_js_key(self.page, vk, scan, modifiers, True, stop_event)
        time.sleep(hold_ms / 1000.0)
        
        if stop_event and stop_event.is_set():
            self._inject_js_key(self.page, vk, scan, modifiers, False, stop_event)
            for mod in reversed(modifiers):
                m_vk = MOD_VK.get(mod)
                if m_vk:
                    m_scan = VK_TO_SCANCODE.get(m_vk, 0)
                    self._inject_js_key(self.page, m_vk, m_scan, [], False, stop_event)
            return
        
        self._inject_js_key(self.page, vk, scan, modifiers, False, stop_event)
        
        time.sleep(0.005)
        
        # 釋放修飾鍵
        for mod in reversed(modifiers):
            if stop_event and stop_event.is_set():
                return
            m_vk = MOD_VK.get(mod)
            if m_vk:
                m_scan = VK_TO_SCANCODE.get(m_vk, 0)
                self._inject_js_key(self.page, m_vk, m_scan, [], False, stop_event)
    
    def launch(self, game_url, headless=False, update_status=None):
        """啟動瀏覽器並開啟遊戲"""
        def _launch():
            try:
                if update_status:
                    update_status("🌐 啟動瀏覽器...")
                
                with sync_playwright() as p:
                    self.playwright = p
                    
                    # 嘗試啟動 Chromium
                    try:
                        self.browser = p.chromium.launch(
                            headless=headless,
                            args=[
                                '--disable-blink-features=AutomationControlled',
                                '--disable-infobars',
                                '--no-first-run',
                                '--disable-web-security',
                                '--disable-features=IsolateOrigins,site-per-process',
                            ]
                        )
                    except Exception as e:
                        if update_status:
                            update_status(f"❌ 瀏覽器啟動失敗：{e}\n請確認已執行：playwright install chromium")
                        return
                    
                    self.context = self.browser.new_context(
                        viewport={'width': 1280, 'height': 720},
                        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36'
                    )
                    
                    self.page = self.context.new_page()
                    
                    if update_status:
                        update_status(f"🔗 前往：{game_url}")
                    
                    self.page.goto(game_url, wait_until='domcontentloaded', timeout=30000)
                    time.sleep(3)  # 等遊戲載入
                    
                    self.ready = True
                    if update_status:
                        update_status("✅ 瀏覽器已就緒，請確認遊戲已載入後開始使用")
                    
                    # 保持瀏覽器開著
                    while self.ready:
                        time.sleep(0.5)
            
            except Exception as e:
                if update_status:
                    update_status(f"❌ 錯誤：{e}")
                self.ready = False
        
        threading.Thread(target=_launch, daemon=True).start()
    
    def close(self):
        self.ready = False
        if self.browser:
            try:
                self.browser.close()
            except:
                pass

# ═══════════════════════════════════════════════════════════
#  按鍵對應（與 main.py 共用邏輯）
# ═══════════════════════════════════════════════════════════

VK_CODE = {
    'a': 0x41, 'b': 0x42, 'c': 0x43, 'd': 0x44, 'e': 0x45,
    'f': 0x46, 'g': 0x47, 'h': 0x48, 'i': 0x49, 'j': 0x4A,
    'k': 0x4B, 'l': 0x4C, 'm': 0x4D, 'n': 0x4E, 'o': 0x4F,
    'p': 0x50, 'q': 0x51, 'r': 0x52, 's': 0x53, 't': 0x54,
    'u': 0x55, 'v': 0x56, 'w': 0x57, 'x': 0x58, 'y': 0x59,
    'z': 0x5A,
    '0': 0x30, '1': 0x31, '2': 0x32, '3': 0x33, '4': 0x34,
    '5': 0x35, '6': 0x36, '7': 0x37, '8': 0x38, '9': 0x39,
    'f1': 0x70, 'f2': 0x71, 'f3': 0x72, 'f4': 0x73, 'f5': 0x74,
    'f6': 0x75, 'f7': 0x76, 'f8': 0x77, 'f9': 0x78, 'f10': 0x79,
    'f11': 0x7A, 'f12': 0x7B,
    'space': 0x20, 'enter': 0x0D, 'tab': 0x09, 'escape': 0x1B, 'backspace': 0x08,
    'up': 0x26, 'down': 0x28, 'left': 0x25, 'right': 0x27,
}

MODIFIER_VK = {'ctrl': 0x11, 'shift': 0x10, 'alt': 0x12, 'win': 0x5B}

def parse_key(key_str):
    key_str = key_str.strip().lower()
    parts = key_str.split('+')
    modifiers = []
    main_key = parts[-1]
    for m in parts[:-1]:
        if m.strip() in MODIFIER_VK:
            modifiers.append(m.strip())
    vk = VK_CODE.get(main_key)
    scan = VK_TO_SCANCODE.get(vk, 0)
    return vk, scan, modifiers

# ═══════════════════════════════════════════════════════════
#  巨集執行緒
# ═══════════════════════════════════════════════════════════

def run_macro(macro: BrowserMacro, sequence, hold_ms, interval_ms, repeat, stop_event, update_status):
    iteration = 0
    while True:
        if stop_event.is_set():
            return
        if repeat >= 0:
            if iteration >= repeat:
                break
            iteration += 1
        
        for key_str in sequence:
            if stop_event.is_set():
                return
            vk, scan, modifiers = parse_key(key_str)
            if vk:
                macro.send_key(vk, scan, modifiers, hold_ms, stop_event)
            if stop_event.is_set():
                return
            time.sleep(interval_ms / 1000.0)
        
        if repeat < 0:
            time.sleep(0.001)

# ═══════════════════════════════════════════════════════════
#  GUI
# ═══════════════════════════════════════════════════════════

class BrowserMacroGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("KeyMacro Browser — 瀏覽器遊戲專用")
        self.root.geometry("720x680")
        self.root.resizable(False, False)
        
        self.macro = BrowserMacro()
        self.stop_event = threading.Event()
        self.is_running = False
        
        self.game_url = tk.StringVar(value="https://maplestory.nexon.com/game/world")
        self.hotkey_str = tk.StringVar(value="f1")
        self.stop_hotkey_str = tk.StringVar(value="f2")
        self.hold_ms = tk.IntVar(value=50)
        self.interval_ms = tk.IntVar(value=200)
        self.repeat_count = tk.IntVar(value=-1)
        self.delay_before = tk.IntVar(value=2000)
        self.toggle_mode = tk.BooleanVar(value=False)
        self.infinite_mode = tk.BooleanVar(value=True)
        self.headless = tk.BooleanVar(value=False)
        
        self._build_ui()
        self._load_config()
    
    def _build_ui(self):
        s = ttk.Style()
        s.configure("T.TLabel", font=("Microsoft JhengHei", 10))
        s.configure("B.TLabel", font=("Microsoft JhengHei", 14, "bold"))
        
        mf = ttk.Frame(self.root, padding=15)
        mf.pack(fill="both", expand=True)
        r = 0
        
        ttk.Label(mf, text="🌐 KeyMacro Browser", style="B.TLabel").grid(
            row=r, column=0, columnspan=3, sticky="w", pady=(0,6)); r+=1
        
        ttk.Label(mf, text="⚠️ 適用於 MapleStory World 等瀏覽器遊戲",
                  font=("Microsoft JhengHei", 9), foreground="red").grid(
                      row=r, column=0, columnspan=3, sticky="w"); r+=1
        
        ttk.Separator(mf, orient="horizontal").grid(
            row=r, column=0, columnspan=3, sticky="ew", pady=6); r+=1
        
        ttk.Label(mf, text="遊戲網址：", style="T.TLabel").grid(row=r, column=0, sticky="w", pady=4)
        ttk.Entry(mf, textvariable=self.game_url, width=50,
                  font=("Microsoft JhengHei", 10)).grid(
                      row=r, column=1, columnspan=2, sticky="w", pady=4); r+=1
        
        btn_frame = ttk.Frame(mf)
        btn_frame.grid(row=r, column=0, columnspan=3, sticky="w", pady=4)
        self.btn_launch = ttk.Button(btn_frame, text="🌐 啟動遊戲瀏覽器",
                                      command=self._launch_browser, width=22)
        self.btn_launch.pack(side="left", padx=(0,5))
        ttk.Button(btn_frame, text="❌ 關閉瀏覽器",
                    command=self._close_browser, width=14).pack(side="left")
        
        self.status_browser = tk.Label(mf, text="📴 瀏覽器未啟動",
                                        font=("Microsoft JhengHei", 9), fg="gray")
        self.status_browser.grid(row=r+1, column=0, columnspan=3, sticky="w"); r+=2
        
        ttk.Separator(mf, orient="horizontal").grid(
            row=r, column=0, columnspan=3, sticky="ew", pady=6); r+=1
        
        ttk.Label(mf, text="觸發熱鍵：", style="T.TLabel").grid(row=r, column=0, sticky="w", pady=4)
        ttk.Entry(mf, textvariable=self.hotkey_str, width=12,
                  font=("Microsoft JhengHei", 11)).grid(row=r, column=1, sticky="w", pady=4)
        ttk.Label(mf, text="（在 KeyMacro 視窗按下，非遊戲視窗）",
                  font=("Microsoft JhengHei", 9)).grid(row=r, column=2, sticky="w", pady=4); r+=1
        
        ttk.Label(mf, text="停止熱鍵：", style="T.TLabel").grid(row=r, column=0, sticky="w", pady=4)
        ttk.Entry(mf, textvariable=self.stop_hotkey_str, width=12,
                  font=("Microsoft JhengHei", 11)).grid(row=r, column=1, sticky="w", pady=4); r+=1
        
        mode_frm = ttk.Frame(mf)
        mode_frm.grid(row=r, column=0, columnspan=3, sticky="w", pady=4)
        ttk.Checkbutton(mode_frm, text="🔄 Toggle 模式",
                        variable=self.toggle_mode).pack(side="left", padx=(0,12))
        ttk.Checkbutton(mode_frm, text="♾️ 無限循環",
                        variable=self.infinite_mode).pack(side="left"); r+=1
        
        ttk.Separator(mf, orient="horizontal").grid(
            row=r, column=0, columnspan=3, sticky="ew", pady=6); r+=1
        
        ttk.Label(mf, text="巨集序列：", style="T.TLabel").grid(row=r, column=0, sticky="nw", pady=4)
        ef = ttk.Frame(mf)
        ef.grid(row=r, column=1, columnspan=2, sticky="w", pady=4)
        self.tseq = tk.Text(ef, width=48, height=6, font=("Consolas", 10))
        self.tseq.pack(side="left", fill="both", expand=True)
        sy = ttk.Scrollbar(ef, orient="vertical", command=self.tseq.yview)
        sy.pack(side="right", fill="y")
        self.tseq.configure(yscrollcommand=sy.set)
        ttk.Label(mf, text="範例：a, b, c | space, enter | left, right, left, right",
                  font=("Microsoft JhengHei", 8), foreground="gray").grid(
                      row=r+1, column=1, columnspan=2, sticky="w"); r+=2
        
        ttk.Separator(mf, orient="horizontal").grid(
            row=r, column=0, columnspan=3, sticky="ew", pady=6); r+=1
        
        ff = ttk.Frame(mf)
        ff.grid(row=r, column=0, columnspan=3, sticky="w", pady=4)
        fields = [
            ("按鍵按住（ms）：", self.hold_ms, 0, 0),
            ("按鍵間隔（ms）：", self.interval_ms, 0, 2),
            ("♾️ 重複次數（-1=無限）：", self.repeat_count, 1, 0),
            ("啟動前延遲（ms）：", self.delay_before, 1, 2),
        ]
        for lbl, var, row, col in fields:
            ttk.Label(ff, text=lbl).grid(row=row, column=col, sticky="w", padx=5, pady=(4,0))
            ttk.Entry(ff, textvariable=var, width=9).grid(row=row, column=col+1, sticky="w", padx=5, pady=(4,0)); r+=1
        
        bf = ttk.Frame(mf)
        bf.grid(row=r, column=0, columnspan=3, pady=10)
        self.bstart = ttk.Button(bf, text="▶ 啟動監聽", command=self._toggle, width=18)
        self.bstart.pack(side="left", padx=5)
        ttk.Button(bf, text="🛑 立即停止", command=self._stop, width=14).pack(side="left", padx=5)
        ttk.Button(bf, text="💾 儲存設定", command=self._save_cfg, width=12).pack(side="left", padx=5)
        ttk.Button(bf, text="❓ 說明", command=self._show_help, width=8).pack(side="left", padx=5); r+=1
        
        self.slbl = tk.Label(mf, text="📴 未啟動", font=("Microsoft JhengHei", 10), fg="gray")
        self.slbl.grid(row=r, column=0, columnspan=3, sticky="w", pady=(5,0))
        self.albl = tk.Label(mf, text="", font=("Microsoft JhengHei", 9), fg="orange")
        self.albl.grid(row=r, column=1, columnspan=2, sticky="w", pady=(5,0))
    
    def _launch_browser(self):
        if self.macro.ready:
            messagebox.showinfo("提示", "瀏覽器已啟動，請確認遊戲已載入")
            return
        self.btn_launch.config(state="disabled")
        self.macro.launch(
            self.game_url.get(),
            headless=self.headless.get(),
            update_status=lambda s: self._upd_browser(s)
        )
    
    def _close_browser(self):
        self.macro.close()
        self.btn_launch.config(state="normal")
        self._upd_browser("📴 瀏覽器已關閉")
    
    def _upd_browser(self, txt):
        def f():
            self.status_browser.config(text=txt)
        self.root.after(0, f)
    
    def _upd_status(self, txt, color):
        def f():
            self.slbl.config(text=txt, fg=color)
        self.root.after(0, f)
    
    def _upd_active(self, txt):
        def f():
            self.albl.config(text=txt)
        self.root.after(0, f)
    
    def _toggle(self):
        if not self.is_running:
            t = self.hotkey_str.get().strip()
            s = self.stop_hotkey_str.get().strip()
            if not t:
                messagebox.showwarning("警告", "請輸入觸發熱鍵")
                return
            if not self.macro.ready:
                messagebox.showwarning("警告", "請先啟動遊戲瀏覽器")
                return
            self.is_running = True
            self.bstart.config(text="⏹ 停止監聽")
            parts = []
            if self.toggle_mode.get(): parts.append("Toggle")
            if self.infinite_mode.get(): parts.append("無限")
            desc = " / ".join(parts) if parts else "按住觸發"
            self._upd_status(f"📡 監聽中：{t}（{desc}）", "blue")
        else:
            self._stop()
            self.is_running = False
            self.bstart.config(text="▶ 啟動監聽")
            self._upd_status("📴 已停止", "gray")
    
    def _stop(self):
        self.stop_event.set()
        self._upd_status("⏹ 已中斷", "red")
        self._upd_active("")
    
    def _execute_macro(self):
        seq = [k.strip() for k in self.tseq.get("1.0","end").strip().split(',') if k.strip()]
        if not seq:
            return
        self.stop_event.clear()
        is_inf = self.infinite_mode.get() or self.repeat_count.get() < 0
        self._upd_active(f"{'♾️ 無限循環中' if is_inf else '🔄 執行中'}...")
        
        def run():
            time.sleep(self.delay_before.get() / 1000.0)
            self._upd_status("⚙️ 發送中...", "orange")
            run_macro(self.macro, seq,
                     self.hold_ms.get(), self.interval_ms.get(),
                     self.repeat_count.get(), self.stop_event,
                     self._upd_status)
            if self.stop_event.is_set():
                self._upd_status("⏹ 已中斷", "red")
            else:
                self._upd_status("✅ 發送完成", "green")
            time.sleep(0.5)
            if not self.stop_event.is_set():
                self._upd_status(f"📡 監聽中：{self.hotkey_str.get()}", "blue")
            self._upd_active("")
        
        threading.Thread(target=run, daemon=True).start()
    
    def _save_cfg(self):
        cfg = {
            "game_url": self.game_url.get(),
            "hotkey": self.hotkey_str.get(),
            "stop_hotkey": self.stop_hotkey_str.get(),
            "sequence": self.tseq.get("1.0","end").strip(),
            "hold_ms": self.hold_ms.get(),
            "interval_ms": self.interval_ms.get(),
            "repeat_count": self.repeat_count.get(),
            "delay_before": self.delay_before.get(),
            "toggle_mode": self.toggle_mode.get(),
            "infinite_mode": self.infinite_mode.get(),
            "headless": self.headless.get(),
        }
        with open("browser_macro_config.json", "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        self._upd_status("💾 已儲存", "green")
    
    def _load_config(self):
        p = "browser_macro_config.json"
        if not os.path.exists(p):
            return
        try:
            with open(p, encoding="utf-8") as f:
                cfg = json.load(f)
            self.game_url.set(cfg.get("game_url",""))
            self.hotkey_str.set(cfg.get("hotkey","f1"))
            self.stop_hotkey_str.set(cfg.get("stop_hotkey","f2"))
            self.tseq.insert("1.0", cfg.get("sequence","a, b, c"))
            self.hold_ms.set(cfg.get("hold_ms",50))
            self.interval_ms.set(cfg.get("interval_ms",200))
            self.repeat_count.set(cfg.get("repeat_count",-1))
            self.delay_before.set(cfg.get("delay_before",2000))
            self.toggle_mode.set(cfg.get("toggle_mode",False))
            self.infinite_mode.set(cfg.get("infinite_mode",True))
            self.headless.set(cfg.get("headless",False))
        except Exception:
            pass
    
    def _show_help(self):
        messagebox.showinfo("說明",
            "【KeyMacro Browser — 使用說明】\n\n"
            "專為 MapleStory World 等瀏覽器遊戲設計。\n\n"
            "【首次設定】\n"
            "1. pip install playwright\n"
            "2. playwright install chromium\n"
            "3. 執行 python browser_macro.py\n\n"
            "【使用方法】\n"
            "1. 填入遊戲網址，點「啟動遊戲瀏覽器」\n"
            "2. 在新瀏覽器中手動登入遊戲\n"
            "3. 確認遊戲載入後，切回 KeyMacro 視窗\n"
            "4. 設定巨集序列與熱鍵，啟動監聽\n"
            "5. 切到遊戲，按觸發熱鍵\n\n"
            "【注意】\n"
            "• 觸發熱鍵在 KeyMacro 視窗上按，不是遊戲視窗\n"
            "• 瀏覽器需要手動登入（我們無法自動登入）\n"
            "• 間隔建議 200ms 以上"
        )
    
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("KeyMacroBrowser.App")
    root = tk.Tk()
    app = BrowserMacroGUI(root)
    app.run()
