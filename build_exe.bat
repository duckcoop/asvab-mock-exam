@echo off
REM ============================================================
REM  ASVAB / AFOQT Mock Exam - Windows EXE Builder
REM  Double click this file to compile asvab_mock_exam.py into a
REM  single ASVABMockExam.exe in the same folder.
REM ============================================================

setlocal
cd /d "%~dp0"

echo.
echo ============================================================
echo  ASVAB Mock Exam : Building Windows executable
echo ============================================================
echo.

REM --- 1. Verify Python is installed -------------------------------
where python >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not on PATH.
    echo.
    echo Install Python 3.10 or newer from https://www.python.org/downloads/
    echo During install, check the box that says "Add Python to PATH".
    echo Then re run this script.
    pause
    exit /b 1
)

python --version

REM --- 2. Make sure pip works and install PyInstaller --------------
echo.
echo Installing PyInstaller (silent if already installed)...
python -m pip install --quiet --upgrade pip
python -m pip install --quiet pyinstaller
if errorlevel 1 (
    echo ERROR: Could not install PyInstaller. Check your internet.
    pause
    exit /b 1
)

REM --- 3. Compile the script into a single windowed exe ------------
echo.
echo Compiling. This usually takes 30 to 90 seconds...
echo.
python -m PyInstaller ^
    --noconfirm ^
    --onefile ^
    --windowed ^
    --name "ASVABMockExam" ^
    --add-data "questions.json;." ^
    asvab_mock_exam.py

if errorlevel 1 (
    echo.
    echo BUILD FAILED. See the error message above.
    pause
    exit /b 1
)

REM --- 4. Move the exe up next to this script ----------------------
if exist "dist\ASVABMockExam.exe" (
    copy /Y "dist\ASVABMockExam.exe" "ASVABMockExam.exe" >nul
    echo.
    echo ============================================================
    echo  BUILD SUCCESS
    echo ============================================================
    echo.
    echo  Your test app is ready: ASVABMockExam.exe
    echo  Double click it any time to start a mock exam.
    echo.
    echo  You can delete the build, dist, and __pycache__ folders if
    echo  you want to clean up. The exe is fully self contained.
    echo.
) else (
    echo BUILD FAILED: dist\ASVABMockExam.exe was not produced.
)

pause
