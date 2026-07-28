"""Question bank linter.

Finds the ways a multiple choice bank can be gameable without knowing any
of the material. A test taker who can score well by pattern matching is
not being prepared for the real thing, and worse, they get a confidence
number that is not real.

Run:
    python lint_questions.py questions.json
    python lint_questions.py questions.json --verbose
"""

from __future__ import annotations

import argparse
import collections
import json
import sys

# On a 4-option test, an unknowing guesser should be right 25% of the
# time. Any signal that beats that without knowledge is a leak.
CHANCE = 0.25

# How far above chance a tell has to run before it is worth reporting.
# 35% is roughly where picking on that signal starts to beat guessing by
# enough to matter over a full test.
TELL_THRESHOLD = 0.35


def load(path: str) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["questions"] if isinstance(data, dict) else data


def check_structure(questions: list[dict]) -> list[str]:
    """Hard errors: things that will break the app or the scoring."""
    problems = []
    seen_ids = set()
    seen_text: dict[str, int] = {}

    for q in questions:
        qid = q.get("id")
        if qid in seen_ids:
            problems.append(f"id {qid}: duplicate id")
        seen_ids.add(qid)

        opts = q.get("options") or []
        if len(opts) != 4:
            problems.append(f"id {qid}: has {len(opts)} options, expected 4")
        if q.get("answer") not in opts:
            problems.append(f"id {qid}: answer is not one of the options")
        if len({o.strip().lower() for o in opts}) != len(opts):
            problems.append(f"id {qid}: duplicate options")

        key = (q.get("question") or "").strip().lower()
        if key in seen_text:
            problems.append(
                f"id {qid}: duplicate of question id {seen_text[key]}")
        else:
            seen_text[key] = qid

        if len(str(q.get("explanation") or "").strip()) < 25:
            problems.append(f"id {qid}: explanation is missing or too short")

    return problems


def check_position_bias(questions: list[dict]) -> tuple[float, dict]:
    """Is the correct answer clustered at one letter?"""
    counts = collections.Counter()
    for q in questions:
        opts, ans = q.get("options") or [], q.get("answer")
        if ans in opts:
            counts["ABCD"[opts.index(ans)]] += 1
    total = sum(counts.values()) or 1
    worst = max(counts.values()) / total if counts else 0.0
    return worst, dict(sorted(counts.items()))


def check_length_tell(questions: list[dict]) -> tuple[float, list[dict]]:
    """Can a test taker beat chance by always picking the longest option?

    This reports the practical exploit rate across the whole bank: what a
    know-nothing scores using that one rule. An earlier version measured
    the rate only among questions with a long option, which came out much
    higher and overstated the problem. The number that matters is the one
    a real test taker would actually get.
    """
    hits = 0
    offenders = []

    for q in questions:
        opts, ans = q.get("options") or [], q.get("answer")
        if ans not in opts or len(opts) != 4:
            continue
        # Same rule a test taker would use: pick the longest, first one
        # wins a tie.
        if max(opts, key=len) == ans:
            hits += 1

        lengths = sorted(len(o) for o in opts)
        # Only flag as an offender when the answer visibly towers over the
        # distractors. Numeric answers where "11" beats "9" are not a tell.
        if lengths[-1] >= 12 and len(ans) == lengths[-1]:
            runner_up = lengths[-2] or 1
            if len(ans) > 1.5 * runner_up:
                offenders.append({
                    "id": q.get("id"),
                    "category": q.get("category"),
                    "question": (q.get("question") or "")[:70],
                    "answer_len": len(ans),
                    "runner_up_len": runner_up,
                })

    rate = hits / len(questions) if questions else 0.0
    return rate, offenders


def check_absolutes(questions: list[dict]) -> list[dict]:
    """Distractors containing absolute words are usually wrong, and test
    takers learn to eliminate them. If absolutes appear almost only in
    wrong answers, that is another free signal."""
    words = ("always", "never", "all ", "none", "every", "only")
    in_wrong = in_right = 0
    flagged = []
    for q in questions:
        opts, ans = q.get("options") or [], q.get("answer")
        for o in opts:
            if any(w in o.lower() for w in words):
                if o == ans:
                    in_right += 1
                else:
                    in_wrong += 1
                    flagged.append({"id": q.get("id"), "option": o[:60]})
    total = in_wrong + in_right
    if total >= 10 and in_wrong / total > 0.9:
        return flagged
    return []


def report(path: str, verbose: bool = False) -> int:
    questions = load(path)
    print(f"\nQuestion bank: {path}")
    print(f"Questions:     {len(questions)}")
    by_cat = collections.Counter(q.get("category") for q in questions)
    print(f"Categories:    {len(by_cat)}")

    failures = 0

    print("\n" + "=" * 62)
    print(" STRUCTURE")
    print("=" * 62)
    problems = check_structure(questions)
    if problems:
        failures += len(problems)
        for p in problems[:20]:
            print(f"  ERROR  {p}")
        if len(problems) > 20:
            print(f"  ... and {len(problems) - 20} more")
    else:
        print("  OK  every question has 4 unique options, a valid answer,")
        print("      a real explanation, and no duplicates")

    print("\n" + "=" * 62)
    print(" GAMEABILITY")
    print("=" * 62)

    worst, dist = check_position_bias(questions)
    status = "FAIL" if worst > TELL_THRESHOLD else "OK  "
    if worst > TELL_THRESHOLD:
        failures += 1
    print(f"  {status} answer position: {dist}")
    print(f"       most common letter holds {worst:.0%} of answers "
          f"(chance {CHANCE:.0%})")
    if worst > TELL_THRESHOLD:
        print("       -> always guessing that letter beats chance. Shuffle "
              "option order at load time.")

    rate, offenders = check_length_tell(questions)
    status = "FAIL" if rate > TELL_THRESHOLD else "OK  "
    if rate > TELL_THRESHOLD:
        failures += 1
    print(f"\n  {status} always picking the longest option scores "
          f"{rate:.0%} (chance {CHANCE:.0%})")
    if rate > TELL_THRESHOLD:
        print(f"       -> a test taker can beat chance by picking the "
              f"longest answer.")
        print(f"       {len(offenders)} questions where the correct answer "
              f"is over 1.5x the next longest.")
        print("       Fix by expanding the distractors, not by trimming "
              "the answer.")
        if verbose:
            print()
            for o in offenders[:15]:
                print(f"         id {o['id']:>3} [{o['category'][:22]:<22}] "
                      f"{o['answer_len']:>3} vs {o['runner_up_len']:>3}  "
                      f"{o['question']}")

    absolutes = check_absolutes(questions)
    if absolutes:
        failures += 1
        print(f"\n  FAIL absolute words ('always', 'never', 'only') appear "
              f"almost exclusively in wrong answers")
        print(f"       {len(absolutes)} distractors. Test takers are taught "
              f"to eliminate these on sight.")
        if verbose:
            for a in absolutes[:10]:
                print(f"         id {a['id']:>3}  {a['option']}")
    else:
        print("\n  OK   absolute words are not a reliable signal")

    print("\n" + "=" * 62)
    if failures:
        print(f" {failures} issue(s) found")
        print("=" * 62 + "\n")
        return 1
    print(" Bank is clean")
    print("=" * 62 + "\n")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Lint a multiple choice bank.")
    ap.add_argument("path", nargs="?", default="questions.json")
    ap.add_argument("--verbose", "-v", action="store_true",
                    help="list the offending questions")
    args = ap.parse_args()
    try:
        return report(args.path, args.verbose)
    except FileNotFoundError:
        print(f"No such file: {args.path}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
