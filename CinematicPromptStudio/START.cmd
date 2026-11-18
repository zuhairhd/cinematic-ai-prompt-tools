@echo off
setlocal
set "STUDIO_PYTHON=%LOCALAPPDATA%\CinematicPromptStudio\venv\Scripts\python.exe"
if not exist "%STUDIO_PYTHON%" goto missing
"%STUDIO_PYTHON%" "%~dp0app.py"
if errorlevel 1 pause
exit /b
:missing
echo Run INSTALL_TO_Z_DRIVE.cmd first.
pause
