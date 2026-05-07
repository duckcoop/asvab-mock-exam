# Changelog

## v3.0 - 2026-05-07

### Added
- 6 new ASVAB subtests with 130 new questions: Word Knowledge (25),
  Paragraph Comprehension (15), Auto Information (25), Shop Information (25),
  Mechanical Comprehension (25), Assembling Objects (15)
- StatsTracker class persisting lifetime per-category accuracy
- Performance Stats screen with colored bars per category
- Lifetime accuracy and Weakest Area shown on the welcome screen
- verify_install.bat for confirming which version is installed

### Changed
- Renamed everywhere: ASVAB only (AFOQT branding removed)
- Window now resizable (was fixed). Minimum 980x700, scales when maximized
- Question text wraplength updates dynamically with window width
- Answer cards expand to fill available width
- Refined color palette and typography hierarchy
- Bank size: 200 -> 330 questions

## v2.0 - 2026-05-06

### Added
- Tkinter GUI replacing the CLI menu
- Custom AnswerCard widget (fixed the all-selected radio button bug)
- Persistent MistakeTracker
- 100 new questions (200 total in original 4 categories)
- build_exe.bat for one-click .exe compilation
- launch.bat for quick testing without rebuild

## v1.0 - 2026-05-06

### Initial release
- CLI study system
- 100 questions across 4 categories (AR, MK, EI, GS)
- Quick review (20q) and full mock exam (200 total in original 4 categories)
- blind mode toggle
- final score report with explanations
