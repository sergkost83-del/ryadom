@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul
title RYADOM - upload changes to GitHub
cd /d "%~dp0"

where git >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Git not found. Install Git for Windows: https://git-scm.com/download/win
  pause
  exit /b 2
)
if not exist ".git" (
  echo [ERROR] This folder is not a Git repository. Run FIRST_PUSH.bat first.
  pause
  exit /b 2
)

if exist "ryadom\backend\manage.py" (
  echo [ERROR] Found a nested folder "ryadom" inside the project: update files were copied to the wrong place.
  echo         Delete that inner "ryadom" folder and copy the update files directly into this folder.
  pause
  exit /b 3
)

git add -A
git diff --cached --quiet
if not errorlevel 1 (
  echo Nothing to upload - no changes found.
  pause
  exit /b 0
)

echo Changed files:
git --no-pager diff --cached --stat
echo.
set "MSG="
set /p MSG=Short description of the change ^(Enter = update^): 
if "!MSG!"=="" set "MSG=update"

git commit -m "!MSG!"
git push
if errorlevel 1 (
  echo.
  echo [ERROR] Upload failed. Send me a screenshot of this window.
  pause
  exit /b 1
)
echo.
echo Done. On GitHub open the tab Actions - the check starts by itself.
pause
exit /b 0
