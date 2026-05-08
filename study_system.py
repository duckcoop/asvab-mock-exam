"""
ASVAB / AFOQT Study System
==========================
Author: Built for Cooper Preston (Space Force Officer Candidate Track)
Last Updated: 2026 05 06

Purpose
-------
A self contained CLI study tool that loads a JSON question bank and runs either
a quick 20 question review or a full 100 question mock exam. Supports a
"Blind Mode" where no feedback is shown until the test is complete, mimicking
real ASVAB / AFOQT testing conditions. The final score report identifies every
missed question along with the correct answer and a verified explanation.

Modify Notes for IT Students
----------------------------
1. Question bank lives in questions.json. Add or edit entries there. The schema
   for each question is shown in the QuestionBank class docstring below.
2. To change the number of questions in quick or full mode, edit the constants
   QUICK_LEN and FULL_LEN.
3. To add new categories, simply use a new category string in the JSON. The
   loader will pick them up automatically.
4. The script uses only the Python standard library, so no pip install required.
   Tested on Python 3.10 and later.
"""

import json
import os
import random
import sys
import textwrap
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional

# -----------------------------------------------------------------------------
# Configuration constants
# -----------------------------------------------------------------------------

QUESTIONS_FILE = "questions.json"   # Default path relative to this script
QUICK_LEN = 20                      # Number of questions in Quick Review
FULL_LEN = 100                      # Number of questions in Full Mock Exam
LINE_WIDTH = 78                     # Terminal width for clean wrapping


# -----------------------------------------------------------------------------
# Data model
# -----------------------------------------------------------------------------

@dataclass
class Question:
    """
    Represents a single multiple choice question.

    JSON schema:
        id (int): unique identifier
        category (str): subject area
        question (str): the prompt text
        options (list of 4 str): the four choices A through D
        answer (str): the correct option text (must match an entry in options)
        explanation (str): logical reasoning for the correct answer
    """
    id: int
    category: str
    question: str
    options: List[str]
    answer: str
    explanation: str

    def correct_letter(self) -> str:
        """Return the letter (A, B, C, D) of the correct answer."""
        idx = self.options.index(self.answer)
        return "ABCD"[idx]


@dataclass
class TestResult:
    """Stores the user's response for a single question."""
    question: Question
    user_choice: Optional[str]   # The letter the user selected, or None if skipped
    is_correct: bool


@dataclass
class TestSession:
    """Aggregates results for an entire test."""
    mode: str
    blind: bool
    started_at: datetime = field(default_factory=datetime.now)
    results: List[TestResult] = field(default_factory=list)

    @property
    def score(self) -> int:
        return sum(1 for r in self.results if r.is_correct)

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def percentage(self) -> float:
        if self.total == 0:
            return 0.0
        return (self.score / self.total) * 100


# -----------------------------------------------------------------------------
# Loader
# -----------------------------------------------------------------------------

def load_questions(json_path: str) -> List[Question]:
    """Read and validate the question bank from disk."""
    path = Path(json_path)
    if not path.exists():
        # Fall back to looking next to the script itself
        path = Path(__file__).parent / json_path
    if not path.exists():
        raise FileNotFoundError(
            f"Could not find {json_path}. Place it next to study_system.py."
        )

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    questions: List[Question] = []
    for entry in data.get("questions", []):
        q = Question(
            id=entry["id"],
            category=entry["category"],
            question=entry["question"],
            options=list(entry["options"]),
            answer=entry["answer"],
            explanation=entry["explanation"],
        )
        # Sanity check: the listed answer must be one of the options
        if q.answer not in q.options:
            raise ValueError(
                f"Question {q.id} has answer '{q.answer}' that is not in options."
            )
        if len(q.options) != 4:
            raise ValueError(f"Question {q.id} must have exactly 4 options.")
        questions.append(q)
    return questions


# -----------------------------------------------------------------------------
# UI helpers
# -----------------------------------------------------------------------------

def clear_screen() -> None:
    """Clear the terminal in a cross platform way."""
    os.system("cls" if os.name == "nt" else "clear")


def print_banner(text: str, char: str = "=") -> None:
    """Print a centered banner for section headers."""
    print(char * LINE_WIDTH)
    print(text.center(LINE_WIDTH))
    print(char * LINE_WIDTH)


def wrap(text: str, indent: str = "") -> str:
    """Wrap long text neatly for terminal display."""
    return textwrap.fill(
        text,
        width=LINE_WIDTH,
        initial_indent=indent,
        subsequent_indent=indent,
    )


def prompt(question: str, valid: List[str]) -> str:
    """Prompt for input restricted to a set of valid uppercase answers."""
    valid_set = {v.upper() for v in valid}
    while True:
        try:
            raw = input(question).strip().upper()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            sys.exit(0)
        if raw in valid_set:
            return raw
        print(f"  Please enter one of: {', '.join(sorted(valid_set))}")


# -----------------------------------------------------------------------------
# Test runner
# -----------------------------------------------------------------------------

def select_questions(bank: List[Question], count: int) -> List[Question]:
    """
    Pull a randomized slice of `count` questions from the bank. Tries to
    distribute evenly across categories so the user is not slammed with one
    subject. Falls back to pure random if the bank is too small.
    """
    if count >= len(bank):
        sample = list(bank)
        random.shuffle(sample)
        return sample

    # Group by category
    by_category: dict[str, List[Question]] = {}
    for q in bank:
        by_category.setdefault(q.category, []).append(q)

    # Take a proportional share from each category
    selected: List[Question] = []
    categories = list(by_category.keys())
    base_per_cat = count // len(categories)
    remainder = count % len(categories)

    for i, cat in enumerate(categories):
        share = base_per_cat + (1 if i < remainder else 0)
        pool = by_category[cat]
        random.shuffle(pool)
        selected.extend(pool[:share])

    random.shuffle(selected)
    return selected


def ask_question(q: Question, idx: int, total: int, blind: bool) -> TestResult:
    """
    Display one question and capture the user's answer.

    Blind Mode: no feedback is shown after the answer. The result is recorded
    silently and revealed only in the final score report.
    Practice Mode: immediate correct/incorrect feedback after each answer.
    """
    print()
    print_banner(f"Question {idx} of {total}  |  Category: {q.category}", "-")
    print(wrap(q.question))
    print()
    letters = "ABCD"
    for letter, option in zip(letters, q.options):
        print(f"  {letter}. {option}")
    print()

    user_letter = prompt("Your answer (A/B/C/D, or X to skip): ", list(letters) + ["X"])

    if user_letter == "X":
        result = TestResult(question=q, user_choice=None, is_correct=False)
    else:
        user_answer_text = q.options[letters.index(user_letter)]
        is_correct = (user_answer_text == q.answer)
        result = TestResult(question=q, user_choice=user_letter, is_correct=is_correct)

    if not blind:
        # Practice mode feedback is shown right away
        if result.is_correct:
            print("\n  Correct.")
        elif result.user_choice is None:
            print(f"\n  Skipped. Correct answer was {q.correct_letter()}: {q.answer}")
        else:
            print(f"\n  Incorrect. Correct answer was {q.correct_letter()}: {q.answer}")
        print(wrap(f"Reasoning: {q.explanation}", indent="  "))
        input("\nPress Enter to continue...")

    return result


def run_test(bank: List[Question], length: int, blind: bool) -> TestSession:
    """Drive the test loop and return a TestSession with all results."""
    session = TestSession(
        mode=f"{length} question {'mock exam' if length == FULL_LEN else 'review'}",
        blind=blind,
    )
    questions = select_questions(bank, length)

    for i, q in enumerate(questions, start=1):
        result = ask_question(q, i, len(questions), blind)
        session.results.append(result)

    return session


# -----------------------------------------------------------------------------
# Score report
# -----------------------------------------------------------------------------

def score_report(session: TestSession) -> None:
    """Print a full breakdown of performance, missed items, and explanations."""
    clear_screen()
    print_banner("FINAL SCORE REPORT")
    print(f"  Mode      : {session.mode}")
    print(f"  Blind Mode: {'ON' if session.blind else 'OFF'}")
    print(f"  Started   : {session.started_at.strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    print(f"  Score     : {session.score} / {session.total}  ({session.percentage:.1f}%)")
    print()

    # Per category breakdown
    cats: dict[str, List[TestResult]] = {}
    for r in session.results:
        cats.setdefault(r.question.category, []).append(r)

    print_banner("Category Breakdown", "-")
    for cat, items in cats.items():
        correct = sum(1 for r in items if r.is_correct)
        total = len(items)
        pct = (correct / total) * 100 if total else 0
        print(f"  {cat:<28}  {correct} / {total}   ({pct:.1f}%)")
    print()

    # Missed questions detail
    missed = [r for r in session.results if not r.is_correct]
    if not missed:
        print_banner("Perfect Score. No Missed Questions.", "-")
        return

    print_banner(f"Missed Questions ({len(missed)})", "-")
    for n, r in enumerate(missed, start=1):
        q = r.question
        print(f"\n  [{n}] Q{q.id} ({q.category})")
        print(wrap(q.question, indent="      "))
        if r.user_choice is None:
            print("      Your answer : (skipped)")
        else:
            user_text = q.options["ABCD".index(r.user_choice)]
            print(f"      Your answer : {r.user_choice}. {user_text}")
        print(f"      Correct     : {q.correct_letter()}. {q.answer}")
        print(wrap(f"Reasoning   : {q.explanation}", indent="      "))


# -----------------------------------------------------------------------------
# Main menu
# -----------------------------------------------------------------------------

def main_menu(bank: List[Question]) -> None:
    """Top level menu loop."""
    while True:
        clear_screen()
        print_banner("ASVAB / AFOQT Study System")
        print(f"  Total questions in bank: {len(bank)}")
        print()
        print("  1. Quick Review (20 questions)")
        print("  2. Full Mock Exam (100 questions)")
        print("  3. Quit")
        print()

        choice = prompt("Select an option (1, 2, or 3): ", ["1", "2", "3"])
        if choice == "3":
            print("Good luck, Guardian.")
            return

        length = QUICK_LEN if choice == "1" else FULL_LEN
        blind_choice = prompt(
            "Enable Blind Mode? Real test simulation, no in line feedback. (Y/N): ",
            ["Y", "N"],
        )
        blind = (blind_choice == "Y")

        session = run_test(bank, length, blind)
        score_report(session)

        again = prompt("\nReturn to main menu? (Y/N): ", ["Y", "N"])
        if again == "N":
            return


# -----------------------------------------------------------------------------
# Entry point
# -----------------------------------------------------------------------------

def main() -> None:
    try:
        bank = load_questions(QUESTIONS_FILE)
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as e:
        print(f"Error loading question bank: {e}")
        sys.exit(1)

    main_menu(bank)


if __name__ == "__main__":
    main()
