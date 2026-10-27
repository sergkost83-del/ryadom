@echo off
setlocal EnableExtensions
chcp 65001 >nul
title RYADOM - full local check
cd /d "%~dp0"

echo ==============================================
echo  RYADOM: local check
echo ==============================================
echo.

set "PYEXE="
where py >nul 2>&1 && set "PYEXE=py -3"
if not defined PYEXE (
  where python >nul 2>&1 && set "PYEXE=python"
)
if not defined PYEXE (
  echo [ERROR] Python not found. Install Python 3 from https://www.python.org/downloads/
  pause
  exit /b 2
)

%PYEXE% "%~dp0tools\local_check.py"
set "RC=%ERRORLEVEL%"

echo.
echo Report: %~dp0reports\REPORT.md
if exist "%~dp0reports\REPORT.md" start "" notepad "%~dp0reports\REPORT.md"
echo Exit code: %RC%  ^(0 = OK, 1 = problems found^)
pause
exit /b %RC%
