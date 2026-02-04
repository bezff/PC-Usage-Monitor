import os
import sys
import winreg
from pathlib import Path

APP_NAME = "PCUsageMonitor"
MAIN_SCRIPT = Path(__file__).parent / "main.py"


def get_python_path():
    return sys.executable


def get_startup_command():
    python = get_python_path()
    script = str(MAIN_SCRIPT.absolute())
    return f'"{python}" "{script}"'


def add_to_startup():
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE
        )
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, get_startup_command())
        winreg.CloseKey(key)
        print(f"Автозапуск добавлен: {APP_NAME}")
        return True
    except Exception as e:
        print(f"Ошибка добавления автозапуска: {e}")
        return False


def remove_from_startup():
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE
        )
        winreg.DeleteValue(key, APP_NAME)
        winreg.CloseKey(key)
        print(f"Автозапуск удалён: {APP_NAME}")
        return True
    except FileNotFoundError:
        print("Автозапуск не был настроен")
        return False
    except Exception as e:
        print(f"Ошибка удаления автозапуска: {e}")
        return False


def is_in_startup():
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_READ
        )
        winreg.QueryValueEx(key, APP_NAME)
        winreg.CloseKey(key)
        return True
    except FileNotFoundError:
        return False
    except Exception:
        return False


if __name__ == "__main__":
    if len(sys.argv) > 1:
        cmd = sys.argv[1].lower()
        if cmd == "add":
            add_to_startup()
        elif cmd == "remove":
            remove_from_startup()
        elif cmd == "status":
            if is_in_startup():
                print("Автозапуск: включён")
            else:
                print("Автозапуск: выключен")
    else:
        print("Использование:")
        print("  python autostart.py add     - добавить в автозапуск")
        print("  python autostart.py remove  - убрать из автозапуска")
        print("  python autostart.py status  - проверить статус")
