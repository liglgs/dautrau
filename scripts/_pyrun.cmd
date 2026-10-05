@echo off
REM Cross-platform Python launcher for AI log hooks (Windows cmd.exe).
REM Tries python -> python3 -> py -3 in order, runs the given script with all args.
REM Exits 0 silently if no Python is found - hooks must never block the AI tool.

python --version >nul 2>nul
if %ERRORLEVEL%==0 goto run_python

python3 --version >nul 2>nul
if %ERRORLEVEL%==0 goto run_python3

py -3 --version >nul 2>nul
if %ERRORLEVEL%==0 goto run_py

exit /b 0

:run_python
python %*
exit /b %ERRORLEVEL%

:run_python3
python3 %*
exit /b %ERRORLEVEL%

:run_py
py -3 %*
exit /b %ERRORLEVEL%
