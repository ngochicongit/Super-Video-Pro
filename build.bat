@echo off
setlocal
cd /d "%~dp0"

set "PNPM_CMD=pnpm"
where pnpm >nul 2>&1 || set "PNPM_CMD=npm exec --yes pnpm@11.19.0 --"

echo [Super Video Pro] Running production verification and build...
call %PNPM_CMD% verify
if errorlevel 1 (
  echo Build failed.
  exit /b %errorlevel%
)

if not exist ".venv\Scripts\python.exe" (
  where py >nul 2>&1 || (echo Python 3 is required to build the NewsVid backend. & exit /b 1)
  py -3 -m venv .venv || exit /b 1
)
.venv\Scripts\python.exe -c "import newsvid, uvicorn" >nul 2>&1
if errorlevel 1 .venv\Scripts\python.exe -m pip install -e .
if errorlevel 1 exit /b 1
.venv\Scripts\python.exe -m compileall -q packages
if errorlevel 1 exit /b 1
echo Build completed successfully.
pause
exit /b 0
