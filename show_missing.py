# ─────────────────────────────────────────────────────────────
# show_missing.py
# Shows the system's "missing keywords" list for each
# resume+JD pair, so you can pick the TRUE ones for
# ground_truth.json
# ─────────────────────────────────────────────────────────────

import sys
import os
import json

sys.path.append("src")

from pdf_parser import extract_text
from section_extractor import extract_sections
from keyword_extractor import (
    extract_keywords_from_resume,
    extract_keywords_from_jd,
    clean_text_for_extraction
)
from gap_analyzer import analyze_gap

with open("ground_truth.json", "r", encoding="utf-8") as f:
    cases = json.load(f)

for case in cases:
    resume_path = case["resume_file"]
    jd_path = case["jd_file"]

    raw_text = extract_text(resume_path)
    sections = extract_sections(raw_text)

    resume_kw = extract_keywords_from_resume(sections)
    resume_kw_all = resume_kw.get("ALL_KEYWORDS", [])

    with open(jd_path, "r", encoding="utf-8") as f:
        jd_text = clean_text_for_extraction(f.read())

    jd_kw = extract_keywords_from_jd(jd_text)

    gap = analyze_gap(resume_kw_all, jd_kw)
    missing = gap.get("missing_keywords", [])

    print(f"\n{'=' * 60}")
    print(
        f"Case {case['id']}: "
        f"{os.path.basename(resume_path)} vs "
        f"{os.path.basename(jd_path)}"
    )
    print(f"{'=' * 60}")

    print(
        f"System extracted {len(missing)} "
        f"'missing' keywords:"
    )

    for kw in sorted(missing):
        print(f"  - {kw}")
