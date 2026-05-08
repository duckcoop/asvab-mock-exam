"""
ASVAB Mock Exam GUI  (v3.0)
============================
Built for Cooper Preston (Space Force Officer Candidate)
Last updated: 2026 05 07

What's new in v3.0
------------------
* Full ASVAB coverage: all 10 subtests now in the bank
* Lifetime Stats Memory: every question you answer is logged so you can see
  long term per category accuracy on the Performance screen
* Resizable window. Minimum 980 x 700. The whole layout scales when you
  maximize, including question text wrap and answer cards
* Cleaner visual design with refined typography, spacing, and a stronger
  hierarchy on every screen
* Mistake Tracker still works and is now shown next to lifetime stats

Single file plus questions.json. No third party dependencies.
"""

from __future__ import annotations

import json
import os
import random
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import tkinter as tk
from tkinter import ttk, messagebox

# ============================================================================
# Constants
# ============================================================================

APP_TITLE   = "ASVAB Mock Exam"
APP_VERSION = "v3.0"
QUICK_LEN   = 20
FULL_LEN    = 100

# Order used everywhere the categories are listed
CATEGORY_ORDER = [
    "General Science",
    "Arithmetic Reasoning",
    "Word Knowledge",
    "Paragraph Comprehension",
    "Mathematics Knowledge",
    "Electronics Information",
    "Auto Information",
    "Shop Information",
    "Mechanical Comprehension",
    "Assembling Objects",
]

CATEGORY_INFO = {
    "General Science":         {"per_q": 30, "code": "GS",
        "blurb": "Life science, earth science, chemistry, and physics fundamentals."},
    "Arithmetic Reasoning":    {"per_q": 72, "code": "AR",
        "blurb": "Word problems involving arithmetic, ratios, percents, and applied algebra."},
    "Word Knowledge":          {"per_q": 25, "code": "WK",
        "blurb": "Vocabulary. Identify the word that most nearly means the underlined term."},
    "Paragraph Comprehension": {"per_q": 60, "code": "PC",
        "blurb": "Read short passages and answer questions about main idea, detail, or inference."},
    "Mathematics Knowledge":   {"per_q": 60, "code": "MK",
        "blurb": "Direct math: algebra, geometry, exponents, factoring, basic trig."},
    "Electronics Information": {"per_q": 30, "code": "EI",
        "blurb": "Electrical principles, components, circuits, and Ohm's Law."},
    "Auto Information":        {"per_q": 30, "code": "AI",
        "blurb": "Vehicle systems, engine layout, drivetrain, and basic automotive concepts."},
    "Shop Information":        {"per_q": 30, "code": "SI",
        "blurb": "Hand tools, power tools, materials, and basic shop safety."},
    "Mechanical Comprehension":{"per_q": 35, "code": "MC",
        "blurb": "Simple machines, levers, pulleys, gears, hydraulics, and applied physics."},
    "Assembling Objects":      {"per_q": 35, "code": "AO",
        "blurb": "Spatial reasoning. Visualize how shapes fit together or rotate in space."},
}

# Color palette (refined)
C_BG          = "#F5F7FA"
C_PANEL       = "#FFFFFF"
C_HEADER      = "#0B1F3A"
C_HEADER_FG   = "#FFFFFF"
C_GOLD        = "#D4AF37"
C_TEXT        = "#0F172A"
C_TEXT_MUTED  = "#64748B"
C_CARD        = "#FFFFFF"
C_CARD_BORDER = "#CBD5E1"
C_CARD_HOVER  = "#EFF6FF"
C_CARD_HOVER_BORDER = "#3B82F6"
C_CARD_SEL    = "#0B1F3A"
C_CARD_SEL_FG = "#FFFFFF"
C_DANGER      = "#DC2626"
C_SUCCESS     = "#16A34A"
C_WARN        = "#F59E0B"
C_PROGRESS    = "#0B1F3A"
C_PROGRESS_BG = "#E2E8F0"

MISTAKE_LOG_PATH = os.path.join(os.path.expanduser("~"), ".asvab_mistakes.json")
STATS_LOG_PATH   = os.path.join(os.path.expanduser("~"), ".asvab_stats.json")


def resource_path(rel_path: str) -> str:
    """Resolve a bundled resource for both script and PyInstaller --onefile."""
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, rel_path)
    return os.path.join(os.path.abspath(os.path.dirname(__file__)), rel_path)


# ============================================================================
# Data classes
# ============================================================================

@dataclass
class Question:
    id: int
    category: str
    question: str
    options: List[str]
    answer: str
    explanation: str

    def correct_letter(self) -> str:
        return "ABCD"[self.options.index(self.answer)]


@dataclass
class TestResult:
    question: Question
    user_choice: Optional[str]
    is_correct: bool
    time_expired: bool = False


@dataclass
class TestSession:
    mode_label: str
    blind: bool
    started_at: datetime = field(default_factory=datetime.now)
    results: List[TestResult] = field(default_factory=list)

    @property
    def score(self) -> int:
        return sum(1 for r in self.results if r.is_correct)

    @property
    def total(self) -> int:
        return len(self.results)


def load_questions(filename: str = "questions.json") -> List[Question]:
    path = resource_path(filename)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    out: List[Question] = []
    for entry in data["questions"]:
        q = Question(
            id=entry["id"], category=entry["category"],
            question=entry["question"], options=list(entry["options"]),
            answer=entry["answer"], explanation=entry["explanation"],
        )
        if q.answer not in q.options or len(q.options) != 4:
            raise ValueError(f"Bad question entry id={q.id}")
        out.append(q)
    return out


# ============================================================================
# Mistake tracker (persistent, removes on mastery)
# ============================================================================

class MistakeTracker:
    def __init__(self, path: str = MISTAKE_LOG_PATH) -> None:
        self.path = path
        self.items: Dict[str, dict] = {}
        self._load()

    def _load(self) -> None:
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                self.items = (json.load(f) or {}).get("items", {})
        except Exception:
            self.items = {}

    def save(self) -> None:
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump({"version": 1, "items": self.items}, f, indent=2)
        except Exception:
            pass

    def record_wrong(self, q: Question, user_choice: Optional[str]) -> None:
        key = str(q.id)
        now = datetime.now().isoformat(timespec="seconds")
        e = self.items.get(key) or {"wrong_count": 0, "last_choice": None,
                                    "first_seen": now, "last_seen": now}
        e["wrong_count"] = int(e.get("wrong_count", 0)) + 1
        e["last_choice"] = user_choice
        e["last_seen"] = now
        self.items[key] = e
        self.save()

    def mark_correct(self, q: Question) -> None:
        if str(q.id) in self.items:
            del self.items[str(q.id)]
            self.save()

    def count(self) -> int:
        return len(self.items)

    def ids(self) -> List[int]:
        return [int(k) for k in self.items.keys()]

    def clear(self) -> None:
        self.items = {}
        self.save()


# ============================================================================
# Lifetime stats memory (persistent, never decays)
# ============================================================================

class StatsTracker:
    """
    Tracks lifetime per category accuracy plus a session history.

    File at ~/.asvab_stats.json:
      {
        "version": 1,
        "categories": {
           "<cat>": {"answered": int, "correct": int, "last_seen": iso8601}
        },
        "sessions": [
           {"started": iso8601, "mode": str, "score": int, "total": int,
            "blind": bool, "categories": {"<cat>": {"correct": int, "total": int}}}
        ]
      }
    """

    MAX_SESSIONS_KEPT = 50

    def __init__(self, path: str = STATS_LOG_PATH) -> None:
        self.path = path
        self.categories: Dict[str, dict] = {}
        self.sessions: List[dict] = []
        self._load()

    def _load(self) -> None:
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f) or {}
            self.categories = data.get("categories", {}) or {}
            self.sessions = data.get("sessions", []) or []
        except Exception:
            self.categories = {}
            self.sessions = []

    def save(self) -> None:
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump({
                    "version": 1,
                    "categories": self.categories,
                    "sessions": self.sessions[-self.MAX_SESSIONS_KEPT:],
                }, f, indent=2)
        except Exception:
            pass

    def record_answer(self, category: str, is_correct: bool) -> None:
        e = self.categories.get(category) or {"answered": 0, "correct": 0,
                                              "last_seen": ""}
        e["answered"] = int(e.get("answered", 0)) + 1
        if is_correct:
            e["correct"] = int(e.get("correct", 0)) + 1
        e["last_seen"] = datetime.now().isoformat(timespec="seconds")
        self.categories[category] = e

    def record_session(self, sess: TestSession) -> None:
        cat_break: Dict[str, dict] = {}
        for r in sess.results:
            slot = cat_break.setdefault(r.question.category,
                                        {"correct": 0, "total": 0})
            slot["total"] += 1
            if r.is_correct:
                slot["correct"] += 1
        self.sessions.append({
            "started": sess.started_at.isoformat(timespec="seconds"),
            "mode": sess.mode_label,
            "score": sess.score,
            "total": sess.total,
            "blind": sess.blind,
            "categories": cat_break,
        })
        self.save()

    def overall(self) -> tuple[int, int]:
        ans = sum(int(e.get("answered", 0)) for e in self.categories.values())
        cor = sum(int(e.get("correct", 0)) for e in self.categories.values())
        return cor, ans

    def per_category(self) -> List[tuple[str, int, int, float]]:
        out = []
        for cat in CATEGORY_ORDER:
            e = self.categories.get(cat, {"answered": 0, "correct": 0})
            ans = int(e.get("answered", 0))
            cor = int(e.get("correct", 0))
            pct = (cor / ans * 100) if ans else 0.0
            out.append((cat, cor, ans, pct))
        return out

    def weakest_category(self) -> Optional[str]:
        per = [t for t in self.per_category() if t[2] >= 5]
        if not per:
            return None
        per.sort(key=lambda t: t[3])
        return per[0][0]

    def clear(self) -> None:
        self.categories = {}
        self.sessions = []
        self.save()


# ============================================================================
# Question selection
# ============================================================================

def select_questions(bank: List[Question], count: int) -> List[Question]:
    """Even category coverage. Within categories, randomized. Sections grouped."""
    by_cat: Dict[str, List[Question]] = {}
    for q in bank:
        by_cat.setdefault(q.category, []).append(q)

    if count >= len(bank):
        sample = list(bank)
    else:
        cats = [c for c in CATEGORY_ORDER if c in by_cat]
        per = count // len(cats)
        rem = count % len(cats)
        sample = []
        for i, cat in enumerate(cats):
            share = per + (1 if i < rem else 0)
            pool = list(by_cat[cat])
            random.shuffle(pool)
            sample.extend(pool[:share])

    grouped: List[Question] = []
    for cat in CATEGORY_ORDER:
        section = [q for q in sample if q.category == cat]
        random.shuffle(section)
        grouped.extend(section)
    return grouped


def select_review_questions(bank: List[Question], ids: List[int]) -> List[Question]:
    id_set = set(ids)
    pool = [q for q in bank if q.id in id_set]
    random.shuffle(pool)
    return pool


# ============================================================================
# Custom answer card widget (resizable)
# ============================================================================

class AnswerCard(tk.Frame):
    """Clickable answer with hover and selected states. Resizes wraplength."""

    def __init__(self, parent, letter: str, text: str, on_select):
        super().__init__(parent, bg=C_CARD,
                         highlightbackground=C_CARD_BORDER,
                         highlightthickness=2, bd=0)
        self.letter = letter
        self.text = text
        self.on_select = on_select
        self.selected = False

        self.badge = tk.Label(self, text=letter, width=3,
                              font=("Segoe UI", 14, "bold"),
                              bg=C_GOLD, fg=C_HEADER)
        self.badge.pack(side="left", padx=(12, 16), pady=12)

        self.text_label = tk.Label(self, text=text, anchor="w",
                                   justify="left",
                                   font=("Segoe UI", 13),
                                   bg=C_CARD, fg=C_TEXT,
                                   wraplength=600)
        self.text_label.pack(side="left", fill="both", expand=True,
                             pady=12, padx=(0, 12))

        for w in (self, self.badge, self.text_label):
            w.bind("<Button-1>", self._click)
            w.bind("<Enter>", self._enter)
            w.bind("<Leave>", self._leave)
            w.configure(cursor="hand2")

        # Update wraplength when the card itself resizes
        self.bind("<Configure>", self._on_resize)

    def _on_resize(self, evt) -> None:
        new_wl = max(200, evt.width - 100)
        self.text_label.configure(wraplength=new_wl)

    def _click(self, _evt) -> None:
        self.on_select(self)

    def _enter(self, _evt) -> None:
        if not self.selected:
            self.configure(bg=C_CARD_HOVER,
                           highlightbackground=C_CARD_HOVER_BORDER)
            self.text_label.configure(bg=C_CARD_HOVER)

    def _leave(self, _evt) -> None:
        if not self.selected:
            self.configure(bg=C_CARD,
                           highlightbackground=C_CARD_BORDER)
            self.text_label.configure(bg=C_CARD)

    def set_selected(self, selected: bool) -> None:
        self.selected = selected
        if selected:
            self.configure(bg=C_CARD_SEL,
                           highlightbackground=C_GOLD,
                           highlightthickness=3)
            self.text_label.configure(bg=C_CARD_SEL, fg=C_CARD_SEL_FG)
            self.badge.configure(bg=C_CARD_SEL_FG, fg=C_CARD_SEL)
        else:
            self.configure(bg=C_CARD,
                           highlightbackground=C_CARD_BORDER,
                           highlightthickness=2)
            self.text_label.configure(bg=C_CARD, fg=C_TEXT)
            self.badge.configure(bg=C_GOLD, fg=C_HEADER)


# ============================================================================
# Main app
# ============================================================================

class MockExamApp(tk.Tk):

    INITIAL_W, INITIAL_H = 1080, 760
    MIN_W, MIN_H = 980, 700

    def __init__(self) -> None:
        super().__init__()
        self.title(APP_TITLE)
        self.configure(bg=C_BG)
        self.geometry(f"{self.INITIAL_W}x{self.INITIAL_H}")
        self.minsize(self.MIN_W, self.MIN_H)
        self.resizable(True, True)
        self._set_icon()

        try:
            self.bank = load_questions("questions.json")
        except Exception as e:
            messagebox.showerror(
                "Question bank error",
                f"Could not load questions.json next to this app.\n\n{e}",
            )
            self.destroy()
            return

        self.tracker = MistakeTracker()
        self.stats = StatsTracker()

        self.session: Optional[TestSession] = None
        self.questions: List[Question] = []
        self.current_idx = 0
        self.section_seconds_left = 0
        self.section_timer_id: Optional[str] = None
        self.current_section: Optional[str] = None
        self.blind_mode = True
        self.review_mode = False
        self.cards: List[AnswerCard] = []
        self.selected_card: Optional[AnswerCard] = None
        self._right_label: Optional[tk.Label] = None
        self._q_text_label: Optional[tk.Label] = None

        # Outer container fills the whole window and expands
        self.container = tk.Frame(self, bg=C_BG)
        self.container.pack(fill="both", expand=True)

        self.show_welcome()

    def _set_icon(self) -> None:
        try:
            ico = resource_path("icon.ico")
            if os.path.exists(ico):
                self.iconbitmap(ico)
        except Exception:
            pass

    # --------------------------------------------------------------- utility helpers

    def _clear(self) -> None:
        if self.section_timer_id is not None:
            try:
                self.after_cancel(self.section_timer_id)
            except Exception:
                pass
            self.section_timer_id = None
        for w in self.container.winfo_children():
            w.destroy()
        self.cards = []
        self.selected_card = None
        self._right_label = None
        self._q_text_label = None

    def _header(self, parent, left_text: str, right_text: str = "") -> tk.Frame:
        bar = tk.Frame(parent, bg=C_HEADER, height=72)
        bar.pack(fill="x", side="top")
        bar.pack_propagate(False)

        tk.Label(bar, text=left_text, fg=C_HEADER_FG, bg=C_HEADER,
                 font=("Segoe UI", 17, "bold"),
                 padx=28).pack(side="left")

        if right_text:
            self._right_label = tk.Label(
                bar, text=right_text, fg=C_HEADER_FG, bg=C_HEADER,
                font=("Consolas", 15, "bold"), padx=28,
            )
            self._right_label.pack(side="right")

        gold = tk.Frame(parent, bg=C_GOLD, height=3)
        gold.pack(fill="x", side="top")
        return bar

    def _btn(self, parent, text, command, primary=True, width=18,
             danger=False, success=False, disabled=False) -> tk.Button:
        if disabled:
            bg, hover = "#9CA3AF", "#9CA3AF"
        elif danger:
            bg, hover = C_DANGER, "#991B1B"
        elif success:
            bg, hover = C_SUCCESS, "#15803D"
        elif primary:
            bg, hover = C_HEADER, "#16315E"
        else:
            bg, hover = "#475569", "#334155"
        b = tk.Button(parent, text=text, command=command,
                      bg=bg, fg="white", activebackground=hover,
                      activeforeground="white",
                      font=("Segoe UI", 12, "bold"),
                      relief="flat", padx=20, pady=11,
                      width=width, cursor="hand2", borderwidth=0)
        if disabled:
            b.configure(state="disabled")
        return b

    # --------------------------------------------------------------- welcome screen

    def show_welcome(self) -> None:
        self._clear()
        self.review_mode = False
        self._header(self.container, APP_TITLE)

        # Scrollable content not needed; use grid to allow scaling
        body = tk.Frame(self.container, bg=C_BG)
        body.pack(fill="both", expand=True)
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(99, weight=1)

        inner = tk.Frame(body, bg=C_BG)
        inner.grid(row=0, column=0, sticky="ew", padx=44, pady=(28, 0))
        inner.grid_columnconfigure(0, weight=1)

        tk.Label(inner, text="Armed Services Vocational Aptitude Battery",
                 font=("Segoe UI", 26, "bold"),
                 fg=C_TEXT, bg=C_BG).grid(row=0, column=0, sticky="w")
        tk.Label(inner, text="Practice and study system",
                 font=("Segoe UI", 12),
                 fg=C_TEXT_MUTED, bg=C_BG).grid(row=1, column=0, sticky="w",
                                                pady=(0, 18))

        # Stats row
        cor, ans = self.stats.overall()
        overall_pct = (cor / ans * 100) if ans else 0.0
        weakest = self.stats.weakest_category() or "—"

        stats_row = tk.Frame(inner, bg=C_BG)
        stats_row.grid(row=2, column=0, sticky="ew", pady=(0, 22))
        for i in range(4):
            stats_row.grid_columnconfigure(i, weight=1, uniform="stat")

        self._stat_card(stats_row, "Question Bank",
                        f"{len(self.bank)}",
                        "verified items").grid(row=0, column=0, sticky="ew",
                                               padx=(0, 8))
        self._stat_card(stats_row, "Lifetime Accuracy",
                        f"{overall_pct:.0f}%" if ans else "—",
                        f"{cor} of {ans} answered"
                        ).grid(row=0, column=1, sticky="ew", padx=8)
        self._stat_card(stats_row, "Weakest Area",
                        weakest if weakest != "—" else "—",
                        "needs review",
                        accent=C_DANGER if weakest != "—" else None
                        ).grid(row=0, column=2, sticky="ew", padx=8)
        self._stat_card(stats_row, "Mistake Log",
                        f"{self.tracker.count()}",
                        "items pending review",
                        accent=C_DANGER if self.tracker.count() else None
                        ).grid(row=0, column=3, sticky="ew", padx=(8, 0))

        # Mode picker section
        tk.Label(inner, text="Choose a Mode",
                 font=("Segoe UI", 13, "bold"),
                 fg=C_TEXT, bg=C_BG).grid(row=3, column=0, sticky="w",
                                          pady=(0, 8))

        opts = tk.Frame(inner, bg=C_BG)
        opts.grid(row=4, column=0, sticky="ew", pady=(0, 14))
        self.blind_var = tk.BooleanVar(value=True)
        tk.Checkbutton(opts, text="Blind Mode (no in test feedback)",
                       variable=self.blind_var,
                       font=("Segoe UI", 11),
                       bg=C_BG, fg=C_TEXT,
                       activebackground=C_BG).pack(side="left")

        actions = tk.Frame(inner, bg=C_BG)
        actions.grid(row=5, column=0, sticky="w", pady=(0, 8))

        self._btn(actions, f"Quick Review ({QUICK_LEN})",
                  lambda: self.start_test(QUICK_LEN),
                  primary=True, width=20).pack(side="left", padx=(0, 12))
        self._btn(actions, f"Full Mock Exam ({FULL_LEN})",
                  lambda: self.start_test(FULL_LEN),
                  primary=True, width=22).pack(side="left", padx=(0, 12))

        review_label = f"Review Mistakes ({self.tracker.count()})"
        self._btn(actions, review_label, self.start_review,
                  danger=(self.tracker.count() > 0),
                  primary=False, width=22,
                  disabled=(self.tracker.count() == 0)
                  ).pack(side="left", padx=(0, 12))

        # Secondary actions
        sec = tk.Frame(inner, bg=C_BG)
        sec.grid(row=6, column=0, sticky="w", pady=(20, 0))
        self._btn(sec, "Performance Stats", self.show_stats,
                  primary=False, width=20).pack(side="left", padx=(0, 10))
        self._btn(sec, "Clear Mistake Log", self._clear_mistakes,
                  primary=False, width=18).pack(side="left", padx=(0, 10))
        self._btn(sec, "Reset Lifetime Stats", self._clear_stats,
                  primary=False, width=20).pack(side="left", padx=(0, 10))
        self._btn(sec, "Quit", self.destroy,
                  primary=False, width=10).pack(side="left")

        # Footer
        tk.Label(self.container,
                 text=f"{APP_TITLE} {APP_VERSION}  |  {len(self.bank)} questions across {len(CATEGORY_ORDER)} subtests",
                 font=("Segoe UI", 9), fg=C_TEXT_MUTED,
                 bg=C_BG).pack(side="bottom", pady=10)

    def _stat_card(self, parent, title: str, value: str, sub: str,
                   accent: Optional[str] = None) -> tk.Frame:
        card = tk.Frame(parent, bg=C_PANEL,
                        highlightbackground=C_CARD_BORDER,
                        highlightthickness=1, bd=0)
        tk.Label(card, text=title.upper(),
                 font=("Segoe UI", 9, "bold"),
                 fg=C_TEXT_MUTED,
                 bg=C_PANEL).pack(anchor="w", padx=16, pady=(14, 0))
        tk.Label(card, text=value,
                 font=("Segoe UI", 22, "bold"),
                 fg=accent or C_HEADER,
                 bg=C_PANEL).pack(anchor="w", padx=16)
        tk.Label(card, text=sub,
                 font=("Segoe UI", 9),
                 fg=C_TEXT_MUTED,
                 bg=C_PANEL).pack(anchor="w", padx=16, pady=(0, 14))
        return card

    def _clear_mistakes(self) -> None:
        if self.tracker.count() == 0:
            messagebox.showinfo("Mistake Log", "Already empty.")
            return
        if messagebox.askyesno("Clear Mistake Log",
                               f"Permanently clear all {self.tracker.count()} entries? "
                               "This cannot be undone."):
            self.tracker.clear()
            self.show_welcome()

    def _clear_stats(self) -> None:
        if not self.stats.categories and not self.stats.sessions:
            messagebox.showinfo("Lifetime Stats", "Already empty.")
            return
        if messagebox.askyesno("Reset Lifetime Stats",
                               "Permanently erase all lifetime accuracy data and "
                               "session history? This cannot be undone."):
            self.stats.clear()
            self.show_welcome()

    # --------------------------------------------------------------- stats screen

    def show_stats(self) -> None:
        self._clear()
        self._header(self.container, "Performance Stats")

        body = tk.Frame(self.container, bg=C_BG)
        body.pack(fill="both", expand=True, padx=44, pady=24)
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(2, weight=1)

        cor, ans = self.stats.overall()
        pct = (cor / ans * 100) if ans else 0.0
        weakest = self.stats.weakest_category() or "—"

        # Top stat row
        top = tk.Frame(body, bg=C_BG)
        top.grid(row=0, column=0, sticky="ew", pady=(0, 18))
        for i in range(3):
            top.grid_columnconfigure(i, weight=1, uniform="t")
        self._stat_card(top, "Lifetime Answered", f"{ans}",
                        "questions across all subtests"
                        ).grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self._stat_card(top, "Lifetime Accuracy",
                        f"{pct:.1f}%" if ans else "—",
                        f"{cor} correct"
                        ).grid(row=0, column=1, sticky="ew", padx=8)
        self._stat_card(top, "Weakest Area", weakest,
                        "based on at least 5 attempts",
                        accent=C_DANGER if weakest != "—" else None
                        ).grid(row=0, column=2, sticky="ew", padx=(8, 0))

        # Per category breakdown header
        tk.Label(body, text="Per Category Lifetime Accuracy",
                 font=("Segoe UI", 13, "bold"),
                 fg=C_TEXT, bg=C_BG).grid(row=1, column=0, sticky="w",
                                          pady=(6, 8))

        # Scrollable list of category rows
        list_frame = tk.Frame(body, bg=C_PANEL,
                              highlightbackground=C_CARD_BORDER,
                              highlightthickness=1)
        list_frame.grid(row=2, column=0, sticky="nsew")
        list_frame.grid_columnconfigure(0, weight=1)
        list_frame.grid_rowconfigure(0, weight=1)

        canvas = tk.Canvas(list_frame, bg=C_PANEL, highlightthickness=0)
        canvas.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(list_frame, orient="vertical",
                               command=canvas.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        canvas.configure(yscrollcommand=scroll.set)

        inner = tk.Frame(canvas, bg=C_PANEL)
        inner_id = canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>",
                   lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",
                    lambda e: canvas.itemconfigure(inner_id, width=e.width))

        for cat, c, a, p in self.stats.per_category():
            self._category_row(inner, cat, c, a, p).pack(fill="x",
                                                         padx=18, pady=8)

        # Footer
        footer = tk.Frame(body, bg=C_BG)
        footer.grid(row=3, column=0, sticky="ew", pady=(16, 0))
        self._btn(footer, "Back to Menu", self.show_welcome,
                  primary=True, width=18).pack(side="right")

    def _category_row(self, parent, cat: str, correct: int,
                      total: int, pct: float) -> tk.Frame:
        row = tk.Frame(parent, bg=C_PANEL)
        # Title row
        head = tk.Frame(row, bg=C_PANEL)
        head.pack(fill="x")
        info = CATEGORY_INFO.get(cat, {})
        code = info.get("code", "")
        tk.Label(head, text=f"{cat}  ({code})",
                 font=("Segoe UI", 12, "bold"),
                 fg=C_TEXT, bg=C_PANEL).pack(side="left")
        if total == 0:
            txt = "No data yet"
            color = C_TEXT_MUTED
        else:
            txt = f"{correct} / {total}   ({pct:.1f}%)"
            if pct >= 80:
                color = C_SUCCESS
            elif pct >= 60:
                color = C_WARN
            else:
                color = C_DANGER
        tk.Label(head, text=txt,
                 font=("Consolas", 11, "bold"),
                 fg=color, bg=C_PANEL).pack(side="right")

        # Bar track
        track = tk.Frame(row, bg=C_PROGRESS_BG, height=10)
        track.pack(fill="x", pady=(6, 0))
        track.pack_propagate(False)
        if total > 0:
            fill = tk.Frame(track,
                            bg=(C_SUCCESS if pct >= 80 else
                                C_WARN if pct >= 60 else C_DANGER),
                            height=10)
            fill.place(x=0, y=0, relwidth=pct / 100, relheight=1)

        # Blurb
        blurb = info.get("blurb", "")
        if blurb:
            tk.Label(row, text=blurb,
                     font=("Segoe UI", 9),
                     fg=C_TEXT_MUTED, bg=C_PANEL,
                     wraplength=900,
                     justify="left", anchor="w"
                     ).pack(fill="x", pady=(4, 0))
        return row

    # --------------------------------------------------------------- test start

    def start_test(self, length: int) -> None:
        self.blind_mode = bool(self.blind_var.get())
        self.questions = select_questions(self.bank, length)
        mode_label = (f"{length} Question "
                      f"{'Mock Exam' if length >= FULL_LEN else 'Review'}")
        self.session = TestSession(mode_label=mode_label, blind=self.blind_mode)
        self.current_idx = 0
        self.current_section = None
        self.review_mode = False
        self.show_section_intro_or_question()

    def start_review(self) -> None:
        ids = self.tracker.ids()
        if not ids:
            messagebox.showinfo("Mistake Log", "No mistakes to review.")
            return
        self.questions = select_review_questions(self.bank, ids)
        self.session = TestSession(
            mode_label=f"Mistake Review ({len(self.questions)})",
            blind=False)
        self.current_idx = 0
        self.current_section = "Mistake Review"
        self.blind_mode = False
        self.review_mode = True
        self.section_seconds_left = 999999
        self.show_question()

    # --------------------------------------------------------------- section flow

    def show_section_intro_or_question(self) -> None:
        if self.current_idx >= len(self.questions):
            self.show_results()
            return
        q = self.questions[self.current_idx]
        if q.category != self.current_section:
            self.current_section = q.category
            self._show_section_intro(q.category)
        else:
            self.show_question()

    def _show_section_intro(self, category: str) -> None:
        self._clear()
        self._header(self.container, APP_TITLE)

        count = sum(1 for j in range(self.current_idx, len(self.questions))
                    if self.questions[j].category == category)
        info = CATEGORY_INFO.get(category, {"per_q": 30, "blurb": "", "code": ""})
        per_q = info["per_q"]
        seconds = count * per_q

        body = tk.Frame(self.container, bg=C_BG)
        body.pack(fill="both", expand=True)
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(0, weight=1)

        center = tk.Frame(body, bg=C_BG)
        center.grid(row=0, column=0)

        tk.Label(center, text="SECTION",
                 font=("Segoe UI", 11, "bold"),
                 fg=C_GOLD, bg=C_BG).pack(anchor="center")
        tk.Label(center, text=category,
                 font=("Segoe UI", 30, "bold"),
                 fg=C_TEXT, bg=C_BG).pack(anchor="center", pady=(4, 16))

        if info.get("blurb"):
            tk.Label(center, text=info["blurb"],
                     font=("Segoe UI", 12),
                     fg=C_TEXT_MUTED, bg=C_BG,
                     wraplength=720,
                     justify="center"
                     ).pack(anchor="center", pady=(0, 22))

        stats_row = tk.Frame(center, bg=C_BG)
        stats_row.pack(anchor="center")
        self._stat_card(stats_row, "Questions", str(count),
                        "in this section").pack(side="left", padx=8)
        self._stat_card(stats_row, "Time Limit",
                        f"{seconds // 60}:{seconds % 60:02d}",
                        "min:sec").pack(side="left", padx=8)

        tk.Label(center,
                 text="\nThe clock starts when you click Begin Section.\n"
                      "You cannot return to a question once you advance.",
                 justify="center",
                 font=("Segoe UI", 11),
                 fg=C_TEXT_MUTED, bg=C_BG).pack(anchor="center", pady=(28, 22))

        self._btn(center, "Begin Section",
                  lambda: self._start_section_clock(seconds),
                  primary=True, success=True, width=22).pack()

    def _start_section_clock(self, seconds: int) -> None:
        self.section_seconds_left = seconds
        self.show_question()

    # --------------------------------------------------------------- question screen

    def show_question(self) -> None:
        if self.current_idx >= len(self.questions):
            self.show_results()
            return
        q = self.questions[self.current_idx]
        if not self.review_mode and q.category != self.current_section:
            self.current_section = q.category
            self._show_section_intro(q.category)
            return

        self._clear()

        if self.review_mode:
            left = (f"Mistake Review  |  Question "
                    f"{self.current_idx + 1} of {len(self.questions)}")
            right = ""
        else:
            sec_idx = sum(1 for j in range(self.current_idx + 1)
                          if self.questions[j].category == q.category)
            sec_total = sum(1 for x in self.questions
                            if x.category == q.category)
            left = f"{q.category}  |  Question {sec_idx} of {sec_total}"
            right = self._format_time(self.section_seconds_left)
        self._header(self.container, left, right)

        body = tk.Frame(self.container, bg=C_BG)
        body.pack(fill="both", expand=True, padx=44, pady=16)
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(2, weight=1)

        # Progress bar
        pb = tk.Frame(body, bg=C_BG)
        pb.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        tk.Label(pb,
                 text=f"Overall  {self.current_idx + 1} / {len(self.questions)}",
                 font=("Segoe UI", 9, "bold"),
                 fg=C_TEXT_MUTED, bg=C_BG).pack(anchor="w")
        track = tk.Frame(pb, bg=C_PROGRESS_BG, height=8)
        track.pack(fill="x", pady=(4, 0))
        track.pack_propagate(False)
        prog = (self.current_idx + 1) / max(1, len(self.questions))
        tk.Frame(track, bg=C_PROGRESS, height=8).place(
            x=0, y=0, relwidth=prog, relheight=1)

        # Question
        self._q_text_label = tk.Label(body, text=q.question,
                                      wraplength=900, justify="left",
                                      font=("Segoe UI", 15),
                                      fg=C_TEXT, bg=C_BG)
        self._q_text_label.grid(row=1, column=0, sticky="ew", pady=(0, 16))

        # Resize wraplength dynamically
        body.bind("<Configure>", self._on_body_resize)

        # Answer cards
        cards_frame = tk.Frame(body, bg=C_BG)
        cards_frame.grid(row=2, column=0, sticky="nsew")
        cards_frame.grid_columnconfigure(0, weight=1)
        self.cards = []
        self.selected_card = None
        for i, (letter, opt) in enumerate(zip("ABCD", q.options)):
            card = AnswerCard(cards_frame, letter, opt,
                              on_select=self._on_card_select)
            card.grid(row=i, column=0, sticky="ew", pady=5)
            self.cards.append(card)

        # Footer
        footer = tk.Frame(self.container, bg=C_BG)
        footer.pack(fill="x", side="bottom", padx=44, pady=14)

        is_last = self.current_idx == len(self.questions) - 1
        btn_text = "Submit Exam" if is_last else "Next Question"
        self._btn(footer, btn_text, self._on_next,
                  primary=True, width=18).pack(side="right")

        if self.review_mode:
            self._btn(footer, "Exit Review", self.show_welcome,
                      primary=False, width=14).pack(side="left")

        if not self.review_mode:
            self._tick_clock()

    def _on_body_resize(self, evt) -> None:
        if self._q_text_label is not None:
            self._q_text_label.configure(wraplength=max(400, evt.width - 60))

    def _on_card_select(self, card: AnswerCard) -> None:
        for c in self.cards:
            c.set_selected(c is card)
        self.selected_card = card

    def _tick_clock(self) -> None:
        if self._right_label is not None:
            self._right_label.config(
                text=self._format_time(self.section_seconds_left))
            if 0 < self.section_seconds_left <= 30:
                color = C_DANGER if self.section_seconds_left % 2 else "#FFCCCC"
                self._right_label.config(fg=color)
            else:
                self._right_label.config(fg=C_HEADER_FG)
        if self.section_seconds_left <= 0:
            self._on_section_time_out()
            return
        self.section_seconds_left -= 1
        self.section_timer_id = self.after(1000, self._tick_clock)

    @staticmethod
    def _format_time(seconds: int) -> str:
        m, s = divmod(max(0, seconds), 60)
        return f"TIME  {m:02d}:{s:02d}"

    def _on_next(self) -> None:
        q = self.questions[self.current_idx]
        if self.selected_card is None:
            if not messagebox.askyesno(
                "No answer selected",
                "You have not selected an answer. Advance anyway? "
                "This question will be marked incorrect."):
                return
            user_letter = None
            is_correct = False
        else:
            user_letter = self.selected_card.letter
            user_text = q.options["ABCD".index(user_letter)]
            is_correct = (user_text == q.answer)

        result = TestResult(question=q, user_choice=user_letter,
                            is_correct=is_correct)
        self.session.results.append(result)

        # Persistent state updates
        self.stats.record_answer(q.category, is_correct)
        if is_correct:
            self.tracker.mark_correct(q)
        else:
            self.tracker.record_wrong(q, user_letter)

        if not self.blind_mode:
            self._show_inline_feedback(result)
            return
        self._advance()

    def _show_inline_feedback(self, r: TestResult) -> None:
        q = r.question
        if r.is_correct:
            messagebox.showinfo("Correct",
                f"Right answer.\n\nReasoning: {q.explanation}")
        elif r.user_choice is None:
            messagebox.showwarning("Skipped",
                f"Correct answer was {q.correct_letter()}: {q.answer}\n\n"
                f"Reasoning: {q.explanation}")
        else:
            messagebox.showwarning("Incorrect",
                f"Correct answer was {q.correct_letter()}: {q.answer}\n\n"
                f"Reasoning: {q.explanation}")
        self._advance()

    def _on_section_time_out(self) -> None:
        cat = self.current_section
        while (self.current_idx < len(self.questions)
               and self.questions[self.current_idx].category == cat):
            q = self.questions[self.current_idx]
            self.session.results.append(
                TestResult(question=q, user_choice=None,
                           is_correct=False, time_expired=True))
            self.tracker.record_wrong(q, None)
            self.stats.record_answer(q.category, False)
            self.current_idx += 1
        self.stats.save()
        messagebox.showwarning("Time Expired",
            f"Section time has run out for {cat}. "
            "Remaining questions in this section have been auto skipped.")
        self.show_section_intro_or_question()

    def _advance(self) -> None:
        self.current_idx += 1
        if self.current_idx >= len(self.questions):
            self.stats.record_session(self.session)
            self.show_results()
            return
        if self.review_mode:
            self.show_question()
            return
        next_q = self.questions[self.current_idx]
        if next_q.category != self.current_section:
            if self.section_timer_id is not None:
                try:
                    self.after_cancel(self.section_timer_id)
                except Exception:
                    pass
                self.section_timer_id = None
            self.show_section_intro_or_question()
        else:
            self.show_question()

    # --------------------------------------------------------------- results screen

    def show_results(self) -> None:
        self._clear()
        self._header(self.container, "Final Score Report")

        body = tk.Frame(self.container, bg=C_BG)
        body.pack(fill="both", expand=True, padx=36, pady=20)
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(2, weight=1)

        sess = self.session
        score, total = sess.score, sess.total
        pct = (score / total * 100) if total else 0

        # Top summary
        summary = tk.Frame(body, bg=C_BG)
        summary.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        tk.Label(summary, text=f"{score} / {total}",
                 font=("Segoe UI", 44, "bold"),
                 fg=(C_SUCCESS if pct >= 70 else C_DANGER),
                 bg=C_BG).pack(side="left")
        tk.Label(summary,
                 text=(f"  ({pct:.1f}%)\n{sess.mode_label}\n"
                       f"Blind Mode: {'ON' if sess.blind else 'OFF'}\n"
                       f"Mistake Log: {self.tracker.count()} items"),
                 font=("Segoe UI", 12),
                 fg=C_TEXT, bg=C_BG,
                 justify="left").pack(side="left", padx=20)

        # Category breakdown for this session
        if not self.review_mode:
            cat_frame = tk.LabelFrame(body, text=" This Session by Category ",
                                      font=("Segoe UI", 11, "bold"),
                                      bg=C_BG, fg=C_TEXT, padx=14, pady=6)
            cat_frame.grid(row=1, column=0, sticky="ew", pady=8)
            cats: Dict[str, list] = {}
            for r in sess.results:
                cats.setdefault(r.question.category, []).append(r)
            for cat in CATEGORY_ORDER:
                if cat not in cats:
                    continue
                items = cats[cat]
                correct = sum(1 for x in items if x.is_correct)
                n = len(items)
                cat_pct = (correct / n * 100) if n else 0
                row = tk.Frame(cat_frame, bg=C_BG)
                row.pack(fill="x", pady=2)
                tk.Label(row, text=cat, width=28, anchor="w",
                         font=("Segoe UI", 11), bg=C_BG).pack(side="left")
                tk.Label(row, text=f"{correct} / {n}",
                         width=10, anchor="w",
                         font=("Consolas", 11), bg=C_BG).pack(side="left")
                tk.Label(row, text=f"{cat_pct:.1f}%",
                         font=("Consolas", 11),
                         fg=(C_SUCCESS if cat_pct >= 70 else C_DANGER),
                         bg=C_BG).pack(side="left")

        # Missed list
        missed = [r for r in sess.results if not r.is_correct]
        miss_frame = tk.LabelFrame(body,
            text=f" Missed Questions ({len(missed)}) ",
            font=("Segoe UI", 11, "bold"),
            bg=C_BG, fg=C_TEXT, padx=8, pady=4)
        miss_frame.grid(row=2, column=0, sticky="nsew", pady=8)
        miss_frame.grid_columnconfigure(0, weight=1)
        miss_frame.grid_rowconfigure(0, weight=1)

        text_box = tk.Text(miss_frame, wrap="word", font=("Segoe UI", 10),
                           bg="#FFFFFF", fg=C_TEXT, height=10, relief="flat")
        scroll = ttk.Scrollbar(miss_frame, command=text_box.yview)
        text_box.configure(yscrollcommand=scroll.set)
        scroll.grid(row=0, column=1, sticky="ns")
        text_box.grid(row=0, column=0, sticky="nsew")

        if not missed:
            text_box.insert("end", "Perfect score. No missed questions.\n")
        else:
            for n, r in enumerate(missed, start=1):
                q = r.question
                text_box.insert("end", f"[{n}] Q{q.id}  ({q.category})\n", "head")
                text_box.insert("end", f"    {q.question}\n")
                if r.user_choice is None:
                    your = "(skipped or time expired)"
                else:
                    your = f"{r.user_choice}. {q.options['ABCD'.index(r.user_choice)]}"
                text_box.insert("end", f"    Your answer : {your}\n")
                text_box.insert("end",
                    f"    Correct     : {q.correct_letter()}. {q.answer}\n")
                text_box.insert("end", f"    Reasoning   : {q.explanation}\n\n")
        text_box.tag_configure("head", font=("Segoe UI", 10, "bold"),
                               foreground=C_DANGER)
        text_box.configure(state="disabled")

        # Footer
        footer = tk.Frame(body, bg=C_BG)
        footer.grid(row=3, column=0, sticky="ew", pady=(8, 0))
        self._btn(footer, "Save Report", self._save_report,
                  primary=False, width=14).pack(side="left")
        self._btn(footer, "View Lifetime Stats", self.show_stats,
                  primary=False, width=20).pack(side="left", padx=(8, 0))
        self._btn(footer, "Return to Menu", self.show_welcome,
                  primary=True, width=18).pack(side="right")

    def _save_report(self) -> None:
        if not self.session:
            return
        try:
            ts = self.session.started_at.strftime("%Y%m%d_%H%M%S")
            fn = f"asvab_report_{ts}.txt"
            outpath = os.path.join(os.path.expanduser("~"), fn)
            with open(outpath, "w", encoding="utf-8") as f:
                f.write(f"{APP_TITLE} {APP_VERSION} Score Report\n")
                f.write(f"Mode    : {self.session.mode_label}\n")
                f.write(f"Started : {self.session.started_at}\n")
                f.write(f"Score   : {self.session.score} / {self.session.total}\n")
                f.write(f"Mistake log size: {self.tracker.count()}\n\n")
                for r in self.session.results:
                    q = r.question
                    f.write(f"Q{q.id} ({q.category})\n")
                    f.write(f"  {q.question}\n")
                    if r.user_choice is None:
                        your = "(skipped)"
                    else:
                        your = f"{r.user_choice}. {q.options['ABCD'.index(r.user_choice)]}"
                    f.write(f"  Your answer : {your}\n")
                    f.write(f"  Correct     : {q.correct_letter()}. {q.answer}\n")
                    verdict = "CORRECT" if r.is_correct else "INCORRECT"
                    f.write(f"  Result      : {verdict}\n")
                    f.write(f"  Reasoning   : {q.explanation}\n\n")
            messagebox.showinfo("Saved", f"Report saved to:\n{outpath}")
        except Exception as e:
            messagebox.showerror("Save failed", str(e))


# ============================================================================
# Entry point
# ============================================================================

def main() -> None:
    app = MockExamApp()
    if not app.winfo_exists():
        return
    app.mainloop()


if __name__ == "__main__":
    main()
