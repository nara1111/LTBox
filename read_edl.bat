@echo off
chcp 65001 > nul
setlocal

echo --- Initializing... ---
call "%~dp0tools\install.bat"
if errorlevel 1 (
    echo [!] Dependency installation failed. Aborting.
    pause
    exit /b 1
)
echo.

set "PYTHON_EXE=%~dp0python3\python.exe"
set "MAIN_PY=%~dp0main.py"

echo --- Starting EDL Read Process ---
echo.

"%PYTHON_EXE%" "%MAIN_PY%" read_edl

endlocal
pause

endlocal
pause