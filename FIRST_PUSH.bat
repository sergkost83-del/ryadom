@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul
title RYADOM - upload to GitHub
cd /d "%~dp0"

set "REMOTE=https://github.com/sergkost83-del/ryadom.git"

where git >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Git not found. Install Git for Windows: https://git-scm.com/download/win
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

if not exist ".git" (
  git init -b main
  git add -A
  git commit -m "chore: initial skeleton v0.8.0.dev1"
  git tag v0.8.0.dev1
)

git remote remove origin >nul 2>&1
git remote add origin %REMOTE%
echo.
echo Uploading to %REMOTE%
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
