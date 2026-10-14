@echo off
rem ego-resume-fill browser launcher (ASCII only).
rem Starts the ego Chrome instance via the vendored client; keep the window open.
rem Preflight: Node.js >= 22 on PATH or a common install location.
setlocal
set "HERE=%~dp0.."
if not exist "%HERE%runtime\ego-browser.cmd" (
  echo [launch] vendored ego client missing: %HERE%runtime\ego-browser.cmd 1>&2
  pause
  exit /b 1
)
"%HERE%runtime\ego-browser.cmd" --open
if errorlevel 1 (
  echo [launch] ego-browser --open failed: check preflight in SKILL.md section 1.0 ^(Node / instance / system browser / profile^) 1>&2
  pause
  exit /b 1
)
echo [launch] ego browser started - keep the window open.
pause
