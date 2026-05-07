@echo off
REM Quick launch the GUI without building an exe.
REM Double click to run if Python is installed.
cd /d "%~dp0"
start "" pythonw asvab_mock_exam.py
