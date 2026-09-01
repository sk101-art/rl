@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\verify-laptop1-only.ps1"
exit /b %ERRORLEVEL%
