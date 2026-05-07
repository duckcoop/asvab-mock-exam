@echo off
REM Quick verifier so you can prove which version you actually have.
setlocal
cd /d "%~dp0"

echo ============================================================
echo  ASVAB Mock Exam : Install Verifier
echo ============================================================
echo.

if not exist asvab_mock_exam.py (
    echo MISSING: asvab_mock_exam.py is not in this folder.
    pause
    exit /b 1
)
if not exist questions.json (
    echo MISSING: questions.json is not in this folder.
    pause
    exit /b 1
)

echo Found asvab_mock_exam.py
echo Found questions.json
echo.
echo --- Version evidence from asvab_mock_exam.py ---
findstr /C:"APP_VERSION" asvab_mock_exam.py
findstr /C:"APP_TITLE" asvab_mock_exam.py
echo.
echo --- Category and question count from questions.json ---
where python >nul 2>&1
if errorlevel 1 (
    echo Python not on PATH. Skipping deep checks.
) else (
    python -c "import json; d=json.load(open('questions.json')); print('  Total questions:', len(d['questions'])); from collections import Counter; cnt=Counter(q['category'] for q in d['questions']); [print(f'  {c}: {n}') for c,n in sorted(cnt.items())]"
)
echo.
echo --- Build artifact (the .exe) ---
if exist ASVABMockExam.exe (
    for %%I in (ASVABMockExam.exe) do echo   ASVABMockExam.exe last built: %%~tI
    echo.
    echo If the date above is OLDER than the .py file modification date,
    echo you are running a stale .exe. Run build_exe.bat to rebuild.
) else (
    echo   ASVABMockExam.exe not found yet. Run build_exe.bat to create it.
)
echo.
echo --- Source file modified date ---
for %%I in (asvab_mock_exam.py) do echo   asvab_mock_exam.py: %%~tI
for %%I in (questions.json)    do echo   questions.json    : %%~tI
echo.
echo ============================================================
echo Expected for v3.0:
echo   APP_VERSION = "v3.0"
echo   APP_TITLE   = "ASVAB Mock Exam"
echo   Total questions: 330
echo   10 categories including Word Knowledge, Paragraph Comprehension,
echo     Auto Information, Shop Information, Mechanical Comprehension,
echo     Assembling Objects
echo ============================================================
pause
