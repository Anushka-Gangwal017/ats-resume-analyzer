# ─────────────────────────────────────────────────────────────
# test_summary.py
# Reads batch_test_results.csv and prints a
# clean summary for your professor report
# ─────────────────────────────────────────────────────────────

import csv
import json
from collections import defaultdict

CSV_FILE = "batch_test_results.csv"

try:
    rows = []
    with open(CSV_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                score = float(row.get("final_score", 0))
                if score > 0:
                    rows.append(row)
            except Exception:
                pass

    if not rows:
        print("No valid rows found in CSV.")
        raise SystemExit

    scores = [float(r["final_score"]) for r in rows]
    avg    = round(sum(scores) / len(scores), 1)
    high   = max(scores)
    low    = min(scores)

    print("\n" + "="*55)
    print("  BATCH TEST SUMMARY REPORT")
    print("="*55)
    print(f"\n  Total test cases  : {len(rows)}")
    print(f"  Average ATS score : {avg}/100")
    print(f"  Highest score     : {high}/100")
    print(f"  Lowest score      : {low}/100")

    # Score distribution
    bands = {"0-40": 0, "41-60": 0, "61-80": 0, "81-100": 0}
    for s in scores:
        if s <= 40:
            bands["0-40"] += 1
        elif s <= 60:
            bands["41-60"] += 1
        elif s <= 80:
            bands["61-80"] += 1
        else:
            bands["81-100"] += 1

    print(f"\n  Score distribution:")
    for band, count in bands.items():
        pct = round(count / len(rows) * 100)
        bar = "█" * (pct // 5)
        print(f"    {band:>8}  {bar:<20} {count} tests ({pct}%)")

    # Per-resume averages
    by_resume = defaultdict(list)
    for r in rows:
        by_resume[r["resume"]].append(
            float(r["final_score"])
        )

    print(f"\n  Per-resume averages:")
    for resume, sc_list in by_resume.items():
        avg_r = round(sum(sc_list) / len(sc_list), 1)
        print(f"    {resume:<30} avg: {avg_r}/100")

    # Most common missing keywords
    missing_all = []
    for r in rows:
        missing_str = r.get("top_missing", "")
        if missing_str:
            for kw in missing_str.split(","):
                kw = kw.strip().strip("[]'\" ")
                if kw:
                    missing_all.append(kw)

    if missing_all:
        from collections import Counter
        top_missing = Counter(missing_all).most_common(10)
        print(f"\n  Most frequently missing skills:")
        for kw, count in top_missing:
            print(f"    {kw:<25} missing in "
                  f"{count} test cases")

    print("\n" + "="*55)
    print("  Summary complete — use these numbers")
    print("  in your project report!")
    print("="*55 + "\n")

except FileNotFoundError:
    print(f"\nFile not found: {CSV_FILE}")
    print("Run 'python src/batch_test.py' first.\n")