@echo off
setlocal
set "PYTHONPATH=%~dp0src;%PYTHONPATH%"
where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    py -3 -m rl_engine.cli %*
    exit /b %ERRORLEVEL%
)
python -m rl_engine.cli %*
exit /b %ERRORLEVEL%
