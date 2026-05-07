# ASVAB Mock Exam

Native Windows GUI ASVAB practice test for Space Force Officer candidate prep.

## What's in v3.0

- All 10 ASVAB subtests in the bank: 330 verified questions
- Lifetime Stats Memory tracks per-category accuracy across every test you take
- Persistent Mistake Tracker so you can review only the questions you got wrong
- Resizable window (minimum 980x700) that scales when maximized
- Build script that compiles a single Windows .exe via PyInstaller

## Quick Start

```
1. Double click verify_install.bat   (proves which version you have)
2. Double click build_exe.bat         (creates ASVABMockExam.exe)
3. Double click ASVABMockExam.exe     (the test)
```

Requires Python 3.10+ on the build machine. The .exe itself runs without Python.

## Subtests Covered

| Code | Subtest                    | Questions |
|------|----------------------------|-----------|
| GS   | General Science            | 50        |
| AR   | Arithmetic Reasoning       | 50        |
| WK   | Word Knowledge             | 25        |
| PC   | Paragraph Comprehension    | 15        |
| MK   | Mathematics Knowledge      | 50        |
| EI   | Electronics Information    | 50        |
| AI   | Auto Information           | 25        |
| SI   | Shop Information           | 25        |
| MC   | Mechanical Comprehension   | 25        |
| AO   | Assembling Objects         | 15        |
| **Total** |                       | **330**   |

## Files

- `asvab_mock_exam.py` - Main Tkinter GUI application
- `questions.json` - Verified question bank
- `build_exe.bat` - PyInstaller build script
- `launch.bat` - Quick launcher (no .exe build)
- `verify_install.bat` - Confirms which version is on disk
- `study_system.py` - Original v1 CLI version (kept for reference)

## Persistent Files

The app writes two files to your home folder. They survive rebuilds.

- `~/.asvab_mistakes.json` - Mistake Tracker
- `~/.asvab_stats.json` - Lifetime Stats

## Version History

- v3.0 (2026-05-07) - All 10 subtests, lifetime stats, resizable UI
- v2.0 (2026-05-06) - GUI rewrite, mistake tracker, 200 questions
- v1.0 (2026-05-06) - CLI tool, 100 questions in 4 categories
