@echo off
setlocal
cd /d "%~dp0"

set "PNPM_CMD=pnpm"
where pnpm >nul 2>&1 || set "PNPM_CMD=npm exec --yes pnpm@11.19.0 --"

if not exist ".venv\Scripts\python.exe" (
  where py >nul 2>&1 || (echo Python 3 is required to run the NewsVid backend. & pause & exit /b 1)
  py -3 -m venv .venv || exit /b 1
)
.venv\Scripts\python.exe -c "import newsvid, uvicorn" >nul 2>&1
if errorlevel 1 .venv\Scripts\python.exe -m pip install -e .
if errorlevel 1 (echo Backend dependency setup failed. & pause & exit /b 1)

echo [Super Video Pro] Starting development environment...
call %PNPM_CMD% dev
if errorlevel 1 (
  echo Development server exited with an error.
  pause
)
exit /b %errorlevel%
