@echo off
echo ========================================
echo   PC Usage Monitor - Build Script
echo ========================================
echo.

echo [1/4] Installing dependencies...
pip install pyinstaller pillow

echo.
echo [2/4] Creating icon...
python create_icon.py

echo.
echo [3/4] Cleaning previous build...
rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul
del /q *.spec 2>nul

echo.
echo [4/4] Building application...
pyinstaller --onefile --noconsole --add-data "static;static" --icon=icon.ico --name "PC Usage Monitor" main.py

echo.
echo ========================================
if exist "dist\PC Usage Monitor.exe" (
    echo   BUILD SUCCESSFUL!
    echo   File: dist\PC Usage Monitor.exe
) else (
    echo   BUILD FAILED!
)
echo ========================================
echo.
pause
