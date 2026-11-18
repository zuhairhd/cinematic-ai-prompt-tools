@echo off
setlocal
where py >nul 2>nul
if errorlevel 1 goto use_python
py -3 "%~dp0install_windows.py"
goto finished
:use_python
where python >nul 2>nul
if errorlevel 1 goto missing
python "%~dp0install_windows.py"
goto finished
:missing
echo Python was not found. Install Python 3.10 or newer from python.org.
echo Include Tcl/Tk and select Add Python to PATH, then run this installer again.
:finished
pause
