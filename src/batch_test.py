# ─────────────────────────────────────────────────────────────
# batch_test.py
#
# Runs the full pipeline on multiple resumes
# against all JDs. Saves results to CSV.
# Use this to show your professor real test data.
# ─────────────────────────────────────────────────────────────

import sys
import os
import csv
import json
from datetime import datetime

sys.path.append(os.path.dirname(__file__))

from ats_core import run_full_analysis

# ── Config ────────────────────────────────────────────────────
RESUMES_FOLDER = "data/resumes/"
JDS_FOLDER     = "data/jds/"
OUTPUT_CSV     = "batch_test_results.csv"
OUTPUT_JSON    = "batch_test_summary.json"

# ── Find all resume PDFs ──────────────────────────────────────
resume_files = sorted([
    f for f in os.listdir(RESUMES_FOLDER)
    if f.endswith(".pdf")
])

# ── Find all JD text files ────────────────────────────────────
jd_files = sorted([
    f for f in os.listdir(JDS_FOLDER)
    if f.endswith(".txt")
])

print("\n" + "="*65)
print("  BATCH TEST — Full Pipeline on All Resumes x All JDs")
print("="*65)
print(f"\n  Resumes found : {len(resume_files)} "
      f"→ {resume_files}")
print(f"  JDs found     : {len(jd_files)}")
print(f"  Total runs    : "
      f"{len(resume_files) * len(jd_files)}\n")

# ── Run all combinations ──────────────────────────────────────
all_rows    = []
run_number  = 0
total_runs  = len(resume_files) * len(jd_files)

for resume_file in resume_files:
    resume_path = os.path.join(RESUMES_FOLDER, resume_file)

    for jd_file in jd_files:
        jd_path = os.path.join(JDS_FOLDER, jd_file)
        run_number += 1

        print(f"  [{run_number:>2}/{total_runs}] "
              f"{resume_file} vs {jd_file}...",
              end=" ", flush=True)

        try:
            with open(jd_path, "r",
                      encoding="utf-8") as f:
                jd_text = f.read()

            result = run_full_analysis(
                resume_path, jd_text
            )

            final_score  = result.get("final_score", 0)
            sem_score    = result.get(
                "score_breakdown", {}
            ).get("semantic_score_pct", 0)
            kw_score     = result.get("keyword_score", 0)
            matched      = result.get(
                "gap_report", {}
            ).get("matched_keywords", [])
            missing      = result.get(
                "gap_report", {}
            ).get("missing_keywords", [])
            high_pri     = result.get(
                "high_priority_count", 0
            )
            grade        = result.get("final_grade", "")

            print(f"Score: {final_score}/100  ✓")

            all_rows.append({
                "resume"             : resume_file,
                "jd"                 : jd_file,
                "final_score"        : final_score,
                "semantic_score_pct" : sem_score,
                "keyword_score_pct"  : kw_score,
                "grade"              : grade,
                "matched_count"      : len(matched),
                "missing_count"      : len(missing),
                "matched_keywords"   : ", ".join(
                    matched[:5]
                ),
                "top_missing"        : ", ".join(
                    missing[:5]
                ),
                "high_priority_fixes": high_pri,
                "timestamp"          : datetime.now(
                ).strftime("%Y-%m-%d %H:%M"),
            })

        except Exception as e:
            print(f"ERROR: {e}")
            all_rows.append({
                "resume"     : resume_file,
                "jd"         : jd_file,
                "final_score": "ERROR",
                "error"      : str(e),
            })

# ── Save to CSV ───────────────────────────────────────────────
if all_rows:
    fieldnames = all_rows[0].keys()
    with open(OUTPUT_CSV, "w",
              newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f,
                                fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)
    print(f"\n  ✅ CSV saved → {OUTPUT_CSV}")

# ── Summary stats ─────────────────────────────────────────────
valid_rows = [
    r for r in all_rows
    if isinstance(r.get("final_score"), (int, float))
]

print("\n" + "="*65)
print("  BATCH TEST SUMMARY")
print("="*65)

if valid_rows:
    scores = [r["final_score"] for r in valid_rows]
    avg    = round(sum(scores) / len(scores), 1)
    high   = max(scores)
    low    = min(scores)

    best  = max(valid_rows,
                key=lambda x: x["final_score"])
    worst = min(valid_rows,
                key=lambda x: x["final_score"])

    print(f"\n  Total runs      : {len(valid_rows)}")
    print(f"  Average score   : {avg}/100")
    print(f"  Highest score   : {high}/100 "
          f"({best['resume']} vs {best['jd']})")
    print(f"  Lowest score    : {low}/100 "
          f"({worst['resume']} vs {worst['jd']})")

    # Per-resume summary
    print("\n  PER-RESUME AVERAGE SCORES:")
    for resume in resume_files:
        resume_rows = [
            r for r in valid_rows
            if r["resume"] == resume
        ]
        if resume_rows:
            avg_score = round(
                sum(r["final_score"]
                    for r in resume_rows) /
                len(resume_rows), 1
            )
            print(f"    {resume:<25} avg: "
                  f"{avg_score}/100 across "
                  f"{len(resume_rows)} JDs")

    # Per-JD summary
    print("\n  PER-JD AVERAGE SCORES "
          "(which JD matches resumes best):")
    for jd in jd_files:
        jd_rows = [
            r for r in valid_rows
            if r["jd"] == jd
        ]
        if jd_rows:
            avg_score = round(
                sum(r["final_score"]
                    for r in jd_rows) /
                len(jd_rows), 1
            )
            print(f"    {jd:<25} avg: "
                  f"{avg_score}/100")

    # Save JSON summary
    summary = {
        "test_date"    : datetime.now().strftime(
            "%d %b %Y"
        ),
        "total_runs"   : len(valid_rows),
        "avg_score"    : avg,
        "highest_score": high,
        "lowest_score" : low,
        "best_match"   : {
            "resume": best["resume"],
            "jd"    : best["jd"],
            "score" : best["final_score"],
        },
        "worst_match"  : {
            "resume": worst["resume"],
            "jd"    : worst["jd"],
            "score" : worst["final_score"],
        },
    }

    with open(OUTPUT_JSON, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\n  ✅ Summary saved → {OUTPUT_JSON}")

print("\n" + "="*65 + "\n")