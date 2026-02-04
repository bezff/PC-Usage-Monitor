import sys
import os
import time
import signal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from server import web_server
from collector import collector

running = True

def handle_exit(sig, frame):
    global running
    running = False

if __name__ == "__main__":
    print("PC Usage Monitor")
    print("=" * 40)
    
    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)
    
    web_server.start()
    
    time.sleep(1)
    collector.start_session()
    
    time.sleep(0.5)
    web_server.open_browser()
    
    print("Мониторинг запущен. Ctrl+C для выхода.")
    
    try:
        while running:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    
    print("\nОстановка...")
    
    if collector._running:
        collector.stop_session()
    
    web_server.stop()
    print("Завершено.")
