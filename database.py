import sqlite3
from datetime import datetime, date, timedelta
from contextlib import contextmanager
from typing import List, Dict
import threading

from config import DB_PATH


class DatabaseManager:
    _lock = threading.Lock()
    
    def __init__(self):
        self.db_path = str(DB_PATH)
        self._init_database()
    
    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def _init_database(self):
        with self._get_connection() as conn:
            cur = conn.cursor()
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    start_time TIMESTAMP NOT NULL,
                    end_time TIMESTAMP,
                    total_seconds INTEGER DEFAULT 0,
                    active_seconds INTEGER DEFAULT 0,
                    idle_seconds INTEGER DEFAULT 0
                )
            """)
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS app_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER,
                    app_name TEXT NOT NULL,
                    exe_name TEXT,
                    window_title TEXT,
                    category TEXT DEFAULT 'other',
                    start_time TIMESTAMP NOT NULL,
                    end_time TIMESTAMP,
                    duration_seconds INTEGER DEFAULT 0,
                    is_active INTEGER DEFAULT 1,
                    FOREIGN KEY (session_id) REFERENCES sessions(id)
                )
            """)
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS app_launches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    app_name TEXT NOT NULL,
                    exe_name TEXT,
                    launch_time TIMESTAMP NOT NULL,
                    date_str TEXT NOT NULL
                )
            """)
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS daily_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date_str TEXT UNIQUE NOT NULL,
                    total_seconds INTEGER DEFAULT 0,
                    active_seconds INTEGER DEFAULT 0,
                    idle_seconds INTEGER DEFAULT 0,
                    apps_used INTEGER DEFAULT 0
                )
            """)
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS hourly_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date_str TEXT NOT NULL,
                    hour INTEGER NOT NULL,
                    active_seconds INTEGER DEFAULT 0,
                    UNIQUE(date_str, hour)
                )
            """)
            
            cur.execute("CREATE INDEX IF NOT EXISTS idx_app_usage_session ON app_usage(session_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_app_usage_name ON app_usage(app_name)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_app_usage_time ON app_usage(start_time)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_daily_date ON daily_stats(date_str)")
    
    def create_session(self) -> int:
        with self._lock:
            with self._get_connection() as conn:
                cur = conn.cursor()
                cur.execute("INSERT INTO sessions (start_time) VALUES (?)", (datetime.now(),))
                return cur.lastrowid
    
    def update_session(self, session_id: int, total_sec: int, active_sec: int, idle_sec: int):
        with self._lock:
            with self._get_connection() as conn:
                cur = conn.cursor()
                cur.execute("""
                    UPDATE sessions 
                    SET total_seconds = ?, active_seconds = ?, idle_seconds = ?, end_time = ?
                    WHERE id = ?
                """, (total_sec, active_sec, idle_sec, datetime.now(), session_id))
    
    def close_session(self, session_id: int, total_sec: int, active_sec: int, idle_sec: int):
        self.update_session(session_id, total_sec, active_sec, idle_sec)
    
    def log_app_start(self, session_id: int, app_name: str, exe_name: str, 
                      window_title: str, category: str) -> int:
        with self._lock:
            with self._get_connection() as conn:
                cur = conn.cursor()
                now = datetime.now()
                cur.execute("""
                    INSERT INTO app_usage 
                    (session_id, app_name, exe_name, window_title, category, start_time, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, 1)
                """, (session_id, app_name, exe_name, window_title, category, now))
                
                cur.execute("""
                    INSERT INTO app_launches (app_name, exe_name, launch_time, date_str)
                    VALUES (?, ?, ?, ?)
                """, (app_name, exe_name, now, now.strftime("%Y-%m-%d")))
                
                return cur.lastrowid
    
    def update_app_usage(self, usage_id: int, duration: int, is_active: bool = True):
        with self._lock:
            with self._get_connection() as conn:
                cur = conn.cursor()
                cur.execute("""
                    UPDATE app_usage 
                    SET duration_seconds = ?, end_time = ?, is_active = ?
                    WHERE id = ?
                """, (duration, datetime.now(), 1 if is_active else 0, usage_id))
    
    def close_app_usage(self, usage_id: int, duration: int):
        self.update_app_usage(usage_id, duration, is_active=False)
    
    def update_daily_stats(self, date_str: str, total: int, active: int, idle: int, apps: int):
        with self._lock:
            with self._get_connection() as conn:
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO daily_stats (date_str, total_seconds, active_seconds, idle_seconds, apps_used)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(date_str) DO UPDATE SET
                        total_seconds = ?, active_seconds = ?, idle_seconds = ?, apps_used = ?
                """, (date_str, total, active, idle, apps, total, active, idle, apps))
    
    def update_hourly_stats(self, date_str: str, hour: int, active_seconds: int):
        with self._lock:
            with self._get_connection() as conn:
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO hourly_stats (date_str, hour, active_seconds)
                    VALUES (?, ?, ?)
                    ON CONFLICT(date_str, hour) DO UPDATE SET
                        active_seconds = active_seconds + ?
                """, (date_str, hour, active_seconds, active_seconds))
    
    def get_today_stats(self) -> Dict:
        today = date.today().strftime("%Y-%m-%d")
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM daily_stats WHERE date_str = ?", (today,))
            row = cur.fetchone()
            if row:
                return dict(row)
            return {"total_seconds": 0, "active_seconds": 0, "idle_seconds": 0, "apps_used": 0}
    
    def get_stats_for_period(self, start_date: str, end_date: str) -> List[Dict]:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT * FROM daily_stats 
                WHERE date_str BETWEEN ? AND ?
                ORDER BY date_str
            """, (start_date, end_date))
            return [dict(row) for row in cur.fetchall()]
    
    def get_hourly_stats(self, date_str: str) -> List[Dict]:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT hour, active_seconds FROM hourly_stats
                WHERE date_str = ? ORDER BY hour
            """, (date_str,))
            return [dict(row) for row in cur.fetchall()]
    
    def get_top_apps(self, date_str: str = None, limit: int = 10) -> List[Dict]:
        with self._get_connection() as conn:
            cur = conn.cursor()
            if date_str:
                cur.execute("""
                    SELECT app_name, category, SUM(duration_seconds) as total_time, COUNT(*) as usage_count
                    FROM app_usage WHERE DATE(start_time) = ?
                    GROUP BY app_name ORDER BY total_time DESC LIMIT ?
                """, (date_str, limit))
            else:
                cur.execute("""
                    SELECT app_name, category, SUM(duration_seconds) as total_time, COUNT(*) as usage_count
                    FROM app_usage GROUP BY app_name ORDER BY total_time DESC LIMIT ?
                """, (limit,))
            return [dict(row) for row in cur.fetchall()]
    
    def get_category_stats(self, date_str: str = None) -> List[Dict]:
        with self._get_connection() as conn:
            cur = conn.cursor()
            if date_str:
                cur.execute("""
                    SELECT category, SUM(duration_seconds) as total_time
                    FROM app_usage WHERE DATE(start_time) = ?
                    GROUP BY category ORDER BY total_time DESC
                """, (date_str,))
            else:
                cur.execute("""
                    SELECT category, SUM(duration_seconds) as total_time
                    FROM app_usage GROUP BY category ORDER BY total_time DESC
                """)
            return [dict(row) for row in cur.fetchall()]
    
    def get_app_launches_count(self, date_str: str = None) -> Dict[str, int]:
        with self._get_connection() as conn:
            cur = conn.cursor()
            if date_str:
                cur.execute("""
                    SELECT app_name, COUNT(*) as launches FROM app_launches
                    WHERE date_str = ? GROUP BY app_name
                """, (date_str,))
            else:
                cur.execute("SELECT app_name, COUNT(*) as launches FROM app_launches GROUP BY app_name")
            return {row["app_name"]: row["launches"] for row in cur.fetchall()}
    
    def get_week_comparison(self) -> List[Dict]:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT 
                    CASE CAST(strftime('%w', date_str) AS INTEGER)
                        WHEN 0 THEN 'Вс' WHEN 1 THEN 'Пн' WHEN 2 THEN 'Вт'
                        WHEN 3 THEN 'Ср' WHEN 4 THEN 'Чт' WHEN 5 THEN 'Пт' WHEN 6 THEN 'Сб'
                    END as day_name,
                    CAST(strftime('%w', date_str) AS INTEGER) as day_num,
                    AVG(active_seconds) as avg_active
                FROM daily_stats GROUP BY day_num ORDER BY day_num
            """)
            return [dict(row) for row in cur.fetchall()]


db = DatabaseManager()
