@echo off
setlocal
rem ego-browser launcher (local copy).
rem   ego-browser.cmd --status
rem   ego-browser.cmd < script.js
set "NODE=%ProgramFiles%\nodejs\node.exe"
if not exist "%NODE%" set "NODE=%LOCALAPPDATA%\Programs\nodejs\node.exe"
if not exist "%NODE%" set "NODE=%USERPROFILE%\.workbuddy\binaries\node\versions\22.22.2-3\node.exe"
if not exist "%NODE%" (
  echo [ego-browser] node.exe not found; install Node.js or edit NODE in this script 1>&2
  exit /b 1
)
"%NODE%" "%~dp0runtime\ego-linux\bin\ego-browser.mjs" %*
