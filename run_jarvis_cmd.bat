@echo off
setlocal
cd /d "%~dp0"

REM Jarvis launcher
REM Default: CMD/terminal mode (no external GUI)
REM Optional GUI: run_jarvis_cmd.bat --gui
REM Optional GUI with console logs: run_jarvis_cmd.bat --gui-debug

set "PYTHON_EXE=python"
if exist "%~dp0.venv\Scripts\python.exe" (
	set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"
)

if /I "%~1"=="--gui" (
	start "" "%PYTHON_EXE%" jarvis_gui.py
	goto :eof
)

if /I "%~1"=="--gui-debug" (
	"%PYTHON_EXE%" jarvis_gui.py
	goto :check_exit
)

set "JARVIS_DISABLE_SPINNER=1"
set "JARVIS_SPEAK_EXIT=0"
"%PYTHON_EXE%" main.py

:check_exit
if errorlevel 1 (
	echo.
	echo Jarvis exited with an error.
	pause
)

endlocal
