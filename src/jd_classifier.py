# ─────────────────────────────────────────────────────────────
# jd_classifier.py
# Detects seniority level of a job description
# Entry / Mid / Senior — from keyword patterns
# ─────────────────────────────────────────────────────────────

import re


# Keywords that signal each seniority level
ENTRY_SIGNALS = [
    "0-1 year", "0-2 year", "fresher", "freshers",
    "recent graduate", "entry level", "entry-level",
    "junior", "trainee", "intern", "internship",
    "no experience required", "0 year",
    "less than 1 year", "less than one year",
    "new graduate", "fresh graduate",
]

MID_SIGNALS = [
    "2-4 year", "2-5 year", "3-5 year",
    "2+ year", "3+ year", "4+ year",
    "mid level", "mid-level",
    "intermediate", "associate",
    "2 years", "3 years", "4 years",
]

SENIOR_SIGNALS = [
    "5+ year", "6+ year", "7+ year", "8+ year",
    "5-8 year", "5-10 year",
    "senior", "lead", "principal",
    "staff engineer", "tech lead",
    "5 years", "6 years", "7 years",
    "10 years", "8 years",
]


def classify_jd(jd_text):
    """
    Takes a job description string.
    Returns a dict with:
      - level: 'Entry' / 'Mid' / 'Senior' / 'Unknown'
      - confidence: 'High' / 'Medium' / 'Low'
      - signals_found: list of matched keywords
      - warning: message if student applying to wrong level
    """
    text_lower = jd_text.lower()

    entry_matches  = [s for s in ENTRY_SIGNALS  if s in text_lower]
    mid_matches    = [s for s in MID_SIGNALS    if s in text_lower]
    senior_matches = [s for s in SENIOR_SIGNALS if s in text_lower]

    entry_score  = len(entry_matches)
    mid_score    = len(mid_matches)
    senior_score = len(senior_matches)

    # Determine level by highest score
    if senior_score > mid_score and senior_score > entry_score:
        level      = "Senior"
        signals    = senior_matches
        confidence = "High" if senior_score >= 2 else "Medium"
    elif mid_score > entry_score and mid_score > 0:
        level      = "Mid"
        signals    = mid_matches
        confidence = "High" if mid_score >= 2 else "Medium"
    elif entry_score > 0:
        level      = "Entry"
        signals    = entry_matches
        confidence = "High" if entry_score >= 2 else "Medium"
    else:
        level      = "Unknown"
        signals    = []
        confidence = "Low"

    # Generate warning for student profiles
    warning = None
    if level == "Senior":
        warning = (
            "⚠️ This JD requires 5+ years experience. "
            "As a fresher, consider applying to entry-level "
            "roles first. Your application may be filtered "
            "by ATS before a human sees it."
        )
    elif level == "Mid":
        warning = (
            "📌 This JD requires 2-4 years experience. "
            "As a fresher, highlight projects and certifications "
            "strongly to compensate for experience gap."
        )

    # Also look for required degree
    degree_required = None
    if "b.tech" in text_lower or "b.e" in text_lower or \
       "bachelor" in text_lower:
        degree_required = "Bachelor's degree"
    if "m.tech" in text_lower or "master" in text_lower or \
       "mba" in text_lower:
        degree_required = "Master's degree"

    return {
        "level"          : level,
        "confidence"     : confidence,
        "signals_found"  : signals[:5],
        "warning"        : warning,
        "degree_required": degree_required,
        "entry_score"    : entry_score,
        "mid_score"      : mid_score,
        "senior_score"   : senior_score,
    }


def get_level_badge_colour(level):
    """Returns colour for UI badge."""
    colours = {
        "Entry"  : "#16A34A",
        "Mid"    : "#D97706",
        "Senior" : "#DC2626",
        "Unknown": "#6B7280",
    }
    return colours.get(level, "#6B7280")


# ── Test ──────────────────────────────────────────────────────
if __name__ == "__main__":

    test_jds = [
        ("Entry JD",
         "We are looking for freshers or 0-1 year "
         "experience Python developers. Recent graduates "
         "are welcome to apply."),
        ("Mid JD",
         "Requires 3+ years of experience in Python "
         "development. Mid-level engineers preferred."),
        ("Senior JD",
         "Looking for a Senior Software Engineer with "
         "5+ years of experience in backend development."),
    ]

    for name, jd in test_jds:
        result = classify_jd(jd)
        print(f"\n{name}:")
        print(f"  Level     : {result['level']} "
              f"({result['confidence']} confidence)")
        print(f"  Signals   : {result['signals_found']}")
        if result['warning']:
            print(f"  Warning   : {result['warning']}")