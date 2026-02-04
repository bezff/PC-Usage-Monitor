import time
from datetime import datetime, date
from typing import Dict, Optional
import threading

from database import db
from tracker import tracker
from config import SAVE_INTERVAL_SEC


class UsageCollector:
    def __init__(self):
        self.session_id: Optional[int] = None
        self._current_usage_id: Optional[int] = None
        self._current_app_start: float = 0
        self._current_app_name: str = ""
        self._session_start: float = 0
        self._total_time: float = 0
        self._active_time: float = 0
        self._idle_time: float = 0
        self._save_timer: Optional[threading.Timer] = None
        self._apps_used_today: set = set()
        self._running = False
        tracker.on_app_change = self._handle_app_change
        tracker.on_tick = self._handle_tick
    
    def start_session(self):
        if self._running:
            return
        self._running = True
        self._session_start = time.time()
        self.session_id = db.create_session()
        tracker.start()
        self._schedule_save()
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Session #{self.session_id} started")
    
    def stop_session(self):
        if not self._running:
            return
        self._running = False
        tracker.stop()
        if self._save_timer:
            self._save_timer.cancel()
        if self._current_usage_id:
            duration = int(time.time() - self._current_app_start)
            db.close_app_usage(self._current_usage_id, duration)
        self._save_stats()
        if self.session_id:
            db.close_session(self.session_id, int(self._total_time), int(self._active_time), int(self._idle_time))
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Session stopped")
    
    def _handle_app_change(self, old_app, old_duration, new_app, exe_name, title, category):
        if self._current_usage_id and old_duration > 0:
            db.close_app_usage(self._current_usage_id, int(old_duration))
        self._current_app_name = new_app
        self._current_app_start = time.time()
        self._apps_used_today.add(new_app)
        self._current_usage_id = db.log_app_start(self.session_id, new_app, exe_name, title, category)
    
    def _handle_tick(self, delta: float, is_idle: bool):
        self._total_time += delta
        if is_idle:
            self._idle_time += delta
        else:
            self._active_time += delta
            now = datetime.now()
            db.update_hourly_stats(now.strftime("%Y-%m-%d"), now.hour, int(delta))
        if self._current_usage_id:
            duration = int(time.time() - self._current_app_start)
            db.update_app_usage(self._current_usage_id, duration)
    
    def _schedule_save(self):
        if not self._running:
            return
        self._save_timer = threading.Timer(SAVE_INTERVAL_SEC, self._periodic_save)
        self._save_timer.daemon = True
        self._save_timer.start()
    
    def _periodic_save(self):
        if self._running:
            self._save_stats()
            self._schedule_save()
    
    def _save_stats(self):
        today = date.today().strftime("%Y-%m-%d")
        db.update_daily_stats(today, int(self._total_time), int(self._active_time), int(self._idle_time), len(self._apps_used_today))
        if self.session_id:
            db.update_session(self.session_id, int(self._total_time), int(self._active_time), int(self._idle_time))
    
    def get_current_stats(self) -> Dict:
        return {
            "session_id": self.session_id,
            "total_time": int(self._total_time),
            "active_time": int(self._active_time),
            "idle_time": int(self._idle_time),
            "current_app": self._current_app_name,
            "is_idle": tracker.is_idle,
            "apps_count": len(self._apps_used_today)
        }


collector = UsageCollector()
