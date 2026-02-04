import json
import threading
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
from datetime import datetime, date, timedelta
from pathlib import Path

from database import db
from collector import collector
from config import APP_CATEGORIES, BASE_DIR
import autostart

PORT = 52847

def format_duration(seconds):
    if seconds < 60:
        return f"{seconds}с"
    elif seconds < 3600:
        return f"{seconds // 60}м"
    else:
        h = seconds // 3600
        m = (seconds % 3600) // 60
        return f"{h}ч {m}м"

def get_category_name(cat_id):
    if cat_id in APP_CATEGORIES:
        return APP_CATEGORIES[cat_id]["name"]
    return "Прочее"

class APIHandler(SimpleHTTPRequestHandler):
    
    def __init__(self, *args, **kwargs):
        self.static_dir = BASE_DIR / "static"
        super().__init__(*args, directory=str(self.static_dir), **kwargs)
    
    def log_message(self, format, *args):
        pass
    
    def send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))
    
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        
        if path == "/api/status":
            self.handle_status()
        elif path == "/api/stats/today":
            self.handle_today_stats()
        elif path == "/api/stats/week":
            self.handle_week_stats()
        elif path == "/api/apps":
            self.handle_apps()
        elif path == "/api/hourly":
            self.handle_hourly()
        elif path == "/api/categories":
            self.handle_categories()
        elif path == "/api/week-comparison":
            self.handle_week_comparison()
        elif path == "/api/trend":
            self.handle_trend()
        elif path == "/api/autostart":
            self.handle_autostart_status()
        else:
            if path == "/":
                self.path = "/index.html"
            super().do_GET()
    
    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        
        if path == "/api/start":
            collector.start_session()
            self.send_json({"status": "started"})
        elif path == "/api/stop":
            collector.stop_session()
            self.send_json({"status": "stopped"})
        elif path == "/api/autostart/enable":
            result = autostart.add_to_startup()
            self.send_json({"enabled": result})
        elif path == "/api/autostart/disable":
            result = autostart.remove_from_startup()
            self.send_json({"disabled": result})
        else:
            self.send_json({"error": "not found"}, 404)
    
    def handle_autostart_status(self):
        enabled = autostart.is_in_startup()
        self.send_json({"enabled": enabled})
    
    def handle_status(self):
        stats = collector.get_current_stats()
        self.send_json({
            "running": collector._running,
            "session_id": stats["session_id"],
            "total_time": stats["total_time"],
            "active_time": stats["active_time"],
            "idle_time": stats["idle_time"],
            "current_app": stats["current_app"],
            "is_idle": stats["is_idle"],
            "apps_count": stats["apps_count"],
            "total_time_fmt": format_duration(stats["total_time"]),
            "active_time_fmt": format_duration(stats["active_time"]),
            "idle_time_fmt": format_duration(stats["idle_time"])
        })
    
    def handle_today_stats(self):
        today = date.today().strftime("%Y-%m-%d")
        stats = db.get_today_stats()
        
        total = stats.get("total_seconds", 0) or 1
        active = stats.get("active_seconds", 0)
        productivity = round((active / total) * 100) if total > 0 else 0
        
        self.send_json({
            "date": today,
            "total_seconds": stats.get("total_seconds", 0),
            "active_seconds": stats.get("active_seconds", 0),
            "idle_seconds": stats.get("idle_seconds", 0),
            "apps_used": stats.get("apps_used", 0),
            "productivity": productivity
        })
    
    def handle_week_stats(self):
        end = date.today()
        start = end - timedelta(days=6)
        
        daily_data = db.get_stats_for_period(
            start.strftime("%Y-%m-%d"),
            end.strftime("%Y-%m-%d")
        )
        
        total_active = sum(d.get("active_seconds", 0) for d in daily_data)
        total_time = sum(d.get("total_seconds", 0) for d in daily_data)
        
        self.send_json({
            "period": f"{start.strftime('%d.%m')} - {end.strftime('%d.%m.%Y')}",
            "total_seconds": total_time,
            "active_seconds": total_active,
            "avg_daily": total_active // 7 if daily_data else 0,
            "days_count": len(daily_data),
            "daily_data": daily_data
        })
    
    def handle_apps(self):
        qs = parse_qs(urlparse(self.path).query)
        period = qs.get("period", ["today"])[0]
        limit = int(qs.get("limit", ["10"])[0])
        
        if period == "today":
            date_str = date.today().strftime("%Y-%m-%d")
            apps = db.get_top_apps(date_str, limit)
        else:
            apps = db.get_top_apps(limit=limit)
        
        total = sum(a.get("total_time", 0) for a in apps) or 1
        
        result = []
        for app in apps:
            duration = app.get("total_time", 0)
            result.append({
                "name": app["app_name"],
                "category": app.get("category", "other"),
                "category_name": get_category_name(app.get("category", "other")),
                "duration": duration,
                "duration_fmt": format_duration(duration),
                "percent": round((duration / total) * 100, 1)
            })
        
        self.send_json(result)
    
    def handle_hourly(self):
        today = date.today().strftime("%Y-%m-%d")
        hourly = db.get_hourly_stats(today)
        
        hours = {h: 0 for h in range(24)}
        for item in hourly:
            hours[item.get("hour", 0)] = item.get("active_seconds", 0)
        
        self.send_json([{"hour": h, "seconds": s} for h, s in hours.items()])
    
    def handle_categories(self):
        qs = parse_qs(urlparse(self.path).query)
        period = qs.get("period", ["today"])[0]
        
        if period == "today":
            date_str = date.today().strftime("%Y-%m-%d")
            categories = db.get_category_stats(date_str)
        else:
            categories = db.get_category_stats()
        
        result = []
        for cat in categories:
            result.append({
                "id": cat["category"],
                "name": get_category_name(cat["category"]),
                "seconds": cat.get("total_time", 0),
                "formatted": format_duration(cat.get("total_time", 0))
            })
        
        self.send_json(result)
    
    def handle_week_comparison(self):
        data = db.get_week_comparison()
        result = []
        for d in data:
            result.append({
                "day": d["day_name"],
                "seconds": int(d.get("avg_active", 0)),
                "hours": round(d.get("avg_active", 0) / 3600, 1)
            })
        self.send_json(result)
    
    def handle_trend(self):
        end = date.today()
        start = end - timedelta(days=6)
        
        daily_data = db.get_stats_for_period(
            start.strftime("%Y-%m-%d"),
            end.strftime("%Y-%m-%d")
        )
        
        result = []
        for d in daily_data:
            total = d.get("total_seconds", 0) or 1
            active = d.get("active_seconds", 0)
            productivity = round((active / total) * 100)
            
            result.append({
                "date": d["date_str"],
                "productivity": productivity,
                "active_hours": round(active / 3600, 1)
            })
        
        self.send_json(result)


class WebServer:
    def __init__(self, port=PORT):
        self.port = port
        self.server = None
        self.thread = None
    
    def start(self):
        self.server = HTTPServer(("127.0.0.1", self.port), APIHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        print(f"Сервер запущен: http://127.0.0.1:{self.port}")
    
    def stop(self):
        if self.server:
            self.server.shutdown()
    
    def open_browser(self):
        webbrowser.open(f"http://127.0.0.1:{self.port}")


web_server = WebServer()
