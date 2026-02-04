import ctypes
from ctypes import wintypes
import time
from typing import Optional, Tuple, Callable
import threading
import re

from config import IDLE_THRESHOLD_SEC, POLL_INTERVAL_SEC, BLACKLIST_WINDOWS, PRIVACY_MODE, APP_CATEGORIES

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
psapi = ctypes.windll.psapi


class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [('cbSize', wintypes.UINT), ('dwTime', wintypes.DWORD)]


def get_idle_duration() -> float:
    lii = LASTINPUTINFO()
    lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
    if user32.GetLastInputInfo(ctypes.byref(lii)):
        millis = kernel32.GetTickCount() - lii.dwTime
        return millis / 1000.0
    return 0.0


def get_foreground_window_info() -> Optional[Tuple[str, str, str, int]]:
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return None
    
    length = user32.GetWindowTextLengthW(hwnd)
    if length == 0:
        return None
    
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buf, length + 1)
    window_title = buf.value
    
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    
    h_process = kernel32.OpenProcess(0x0400 | 0x0010, False, pid.value)
    if not h_process:
        return None
    
    try:
        exe_buf = ctypes.create_unicode_buffer(512)
        psapi.GetModuleBaseNameW(h_process, None, exe_buf, 512)
        exe_name = exe_buf.value
        app_name = exe_name.replace('.exe', '').replace('.EXE', '').title()
        return (app_name, exe_name, window_title, hwnd)
    finally:
        kernel32.CloseHandle(h_process)


def categorize_app(app_name: str, exe_name: str, window_title: str) -> str:
    check_text = f"{app_name} {exe_name} {window_title}".lower()
    for cat_id, cat_info in APP_CATEGORIES.items():
        for keyword in cat_info["keywords"]:
            if keyword in check_text:
                return cat_id
    return "other"


def mask_sensitive_data(title: str) -> str:
    title = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', '[email]', title)
    title = re.sub(r'\+?\d{10,12}', '[phone]', title)
    title = re.sub(r'\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}', '[card]', title)
    return title


def should_skip_window(title: str) -> bool:
    title_lower = title.lower()
    for blocked in BLACKLIST_WINDOWS:
        if blocked.lower() in title_lower:
            return True
    return False


def process_window_title(title: str, app_name: str) -> str:
    if should_skip_window(title):
        return f"[{app_name}]"
    if PRIVACY_MODE == "anonymous":
        return app_name
    elif PRIVACY_MODE == "masked":
        return mask_sensitive_data(title)
    return title


class WindowTracker:
    def __init__(self):
        self.running = False
        self._thread = None
        self._current_app = None
        self._current_hwnd = None
        self._app_start_time = None
        self._total_idle = 0.0
        self._total_active = 0.0
        self._is_idle = False
        self._last_poll_time = None
        self.on_app_change: Optional[Callable] = None
        self.on_idle_change: Optional[Callable] = None
        self.on_tick: Optional[Callable] = None
    
    def start(self):
        if self.running:
            return
        self.running = True
        self._last_poll_time = time.time()
        self._thread = threading.Thread(target=self._tracking_loop, daemon=True)
        self._thread.start()
    
    def stop(self):
        self.running = False
        if self._thread:
            self._thread.join(timeout=2)
    
    def _tracking_loop(self):
        while self.running:
            try:
                self._poll()
            except Exception as e:
                print(f"Tracker error: {e}")
            time.sleep(POLL_INTERVAL_SEC)
    
    def _poll(self):
        now = time.time()
        delta = now - self._last_poll_time if self._last_poll_time else 0
        self._last_poll_time = now
        
        idle_time = get_idle_duration()
        was_idle = self._is_idle
        self._is_idle = idle_time >= IDLE_THRESHOLD_SEC
        
        if self._is_idle:
            self._total_idle += delta
        else:
            self._total_active += delta
        
        if was_idle != self._is_idle and self.on_idle_change:
            self.on_idle_change(self._is_idle)
        
        window_info = get_foreground_window_info()
        if window_info:
            app_name, exe_name, title, hwnd = window_info
            
            if hwnd != self._current_hwnd:
                old_app = self._current_app
                old_duration = 0
                if self._app_start_time:
                    old_duration = now - self._app_start_time
                
                self._current_app = app_name
                self._current_hwnd = hwnd
                self._app_start_time = now
                
                processed_title = process_window_title(title, app_name)
                category = categorize_app(app_name, exe_name, title)
                
                if self.on_app_change:
                    self.on_app_change(old_app, old_duration, app_name, exe_name, processed_title, category)
        
        if self.on_tick:
            self.on_tick(delta, self._is_idle)
    
    @property
    def total_active_time(self) -> float:
        return self._total_active
    
    @property
    def total_idle_time(self) -> float:
        return self._total_idle
    
    @property
    def current_app(self) -> Optional[str]:
        return self._current_app
    
    @property
    def is_idle(self) -> bool:
        return self._is_idle
    
    def reset_stats(self):
        self._total_idle = 0.0
        self._total_active = 0.0


tracker = WindowTracker()
