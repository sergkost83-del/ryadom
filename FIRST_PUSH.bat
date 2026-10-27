@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul
title RYADOM - first upload to GitHub
cd /d "%~dp0"

where git >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Git not found. Install Git for Windows: https://git-scm.com/download/win
  pause
  exit /b 2
)
if exist ".git" (
  echo This folder is already a Git repository. Nothing to do.
  pause
  exit /b 0
)

echo Step 1. On GitHub create a NEW PRIVATE repository named ryadom.
echo         Do NOT add README, .gitignore or license - it must be empty.
echo.
set /p REMOTE=Step 2. Paste the repository URL ^(https://github.com/USER/ryadom.git^): 
if "!REMOTE!"=="" (
  echo URL is empty.
  pause
  exit /b 2
)

git config --get user.name >nul 2>&1
if errorlevel 1 (
  set /p GNAME=Your name for commit history: 
  git config --global user.name "!GNAME!"
)
git config --get user.email >nul 2>&1
if errorlevel 1 (
  set /p GMAIL=Your e-mail for commit history: 
  git config --global user.email "!GMAIL!"
)

git init -b main
git add -A
git commit -m "chore: initial skeleton v0.8.0.dev1"
git tag v0.8.0.dev1
git remote add origin "!REMOTE!"
git push -u origin main --tags
if errorlevel 1 (
  echo.
  echo [ERROR] Upload failed. Send me a screenshot of this window.
  pause
  exit /b 1
)
echo.
echo Done. Open the repository on GitHub - tab Actions - the first check starts by itself.
pause
exit /b 0
