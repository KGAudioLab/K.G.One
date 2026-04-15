@echo off
setlocal

echo ==========================================
echo   KGOne Cleanup Script (Windows)
echo ==========================================
echo.
echo This will permanently delete:
echo   .venv\       (gateway Python environment)
echo   ace-step\    (submodule + venv + model checkpoints)
echo   foundation1\ (submodule + venv + model weights)
echo   separator\   (submodule + venv)
echo   outputs\     (all generated audio and MIDI files)
echo   uploads\     (all uploaded audio files)
echo.
echo Re-run init.bat to restore everything except outputs and uploads.
echo.

set /p CONFIRM=Type YES to confirm:
if /i not "%CONFIRM%"=="YES" (
    echo Cancelled.
    exit /b 0
)
echo.

if exist ".venv" (
    echo Removing .venv ...
    rmdir /s /q ".venv"
    echo   Done.
) else (
    echo .venv not found, skipping.
)

if exist "ace-step" (
    echo Removing ace-step ...
    rmdir /s /q "ace-step"
    echo   Done.
) else (
    echo ace-step not found, skipping.
)

if exist "foundation1" (
    echo Removing foundation1 ...
    rmdir /s /q "foundation1"
    echo   Done.
) else (
    echo foundation1 not found, skipping.
)

if exist "separator" (
    echo Removing separator ...
    rmdir /s /q "separator"
    echo   Done.
) else (
    echo separator not found, skipping.
)

if exist "outputs" (
    echo Removing outputs ...
    rmdir /s /q "outputs"
    echo   Done.
) else (
    echo outputs not found, skipping.
)

if exist "uploads" (
    echo Removing uploads ...
    rmdir /s /q "uploads"
    echo   Done.
) else (
    echo uploads not found, skipping.
)

echo.
echo ==========================================
echo   Cleanup complete.
echo   Run init.bat to set up again.
echo ==========================================
echo.
