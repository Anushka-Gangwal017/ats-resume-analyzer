# ─────────────────────────────────────────────────────────────
# evaluate.py
#
# Compares the ATS system's "missing keywords" output
# against manually labelled ground truth.
# Calculates Precision, Recall, F1 Score.
# ─────────────────────────────────────────────────────────────

import os
import sys
import json

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from pdf_parser        import extract_text
from section_extractor import extract_sections
from keyword_extractor import (extract_keywords_from_resume,
                                extract_keywords_from_jd)
from gap_analyzer      import analyze_gap


def normalize_for_comparison(keyword_list):
    """
    Lowercases and strips keywords so comparisons
    aren't broken by minor formatting differences.
    """
    return set(
        k.strip().lower()
        for k in keyword_list
        if k.strip()
    )


def calculate_metrics(predicted, actual):
    """
    predicted = set of keywords system said are missing
    actual    = set of keywords human says are truly missing

    Returns precision, recall, f1, and the
    true positives / false positives / false negatives
    """
    predicted = normalize_for_comparison(predicted)
    actual    = normalize_for_comparison(actual)

    true_positives  = predicted & actual
    false_positives = predicted - actual
    false_negatives = actual - predicted

    precision = (
        len(true_positives) / len(predicted)
        if predicted else 0
    )
    recall = (
        len(true_positives) / len(actual)
        if actual else 0
    )
    f1 = (
        2 * precision * recall / (precision + recall)
        if (precision + recall) > 0 else 0
    )

    return {
        "precision"      : round(precision * 100, 1),
        "recall"         : round(recall * 100, 1),
        "f1"             : round(f1 * 100, 1),
        "true_positives" : sorted(true_positives),
        "false_positives": sorted(false_positives),
        "false_negatives": sorted(false_negatives),
    }


def run_evaluation(ground_truth_path="ground_truth.json"):
    """
    Runs the full evaluation across all
    ground truth test cases.
    """

    with open(ground_truth_path, "r",
              encoding="utf-8") as f:
        test_cases = json.load(f)

    print("\n" + "="*65)
    print("  EVALUATION FRAMEWORK")
    print(f"  Testing against {len(test_cases)} "
          f"manually labelled cases")
    print("="*65)

    all_results = []

    for case in test_cases:
        case_id     = case["id"]
        resume_path = case["resume_file"]
        jd_path     = case["jd_file"]
        truly_missing = case["truly_missing_keywords"]

        # Skip if files don't exist
        if not os.path.exists(resume_path):
            print(f"\n  [Case {case_id}] SKIPPED — "
                  f"resume not found: {resume_path}")
            continue
        if not os.path.exists(jd_path):
            print(f"\n  [Case {case_id}] SKIPPED — "
                  f"JD not found: {jd_path}")
            continue

        # Run the system
        raw_text = extract_text(resume_path)
        sections = extract_sections(raw_text)
        resume_kw_data = extract_keywords_from_resume(
            sections
        )
        resume_kw = resume_kw_data.get("ALL_KEYWORDS", [])

        with open(jd_path, "r", encoding="utf-8") as f:
            jd_text = f.read()

# Clean the text before processing
        from keyword_extractor import clean_text_for_extraction
        jd_text = clean_text_for_extraction(jd_text)
        jd_kw = extract_keywords_from_jd(jd_text)

        gap = analyze_gap(resume_kw, jd_kw)
        system_missing = gap.get("missing_keywords", [])

        # Calculate metrics
        metrics = calculate_metrics(
            system_missing, truly_missing
        )

        print(f"\n  [Case {case_id}] "
              f"{os.path.basename(resume_path)} vs "
              f"{os.path.basename(jd_path)}")
        print(f"    System said missing : "
              f"{system_missing}")
        print(f"    Human says missing  : "
              f"{truly_missing}")
        print(f"    Precision: {metrics['precision']}%  "
              f"Recall: {metrics['recall']}%  "
              f"F1: {metrics['f1']}%")

        all_results.append({
            "case_id"  : case_id,
            "resume"   : os.path.basename(resume_path),
            "jd"       : os.path.basename(jd_path),
            "metrics"  : metrics,
        })

    # ── Overall averages ───────────────────────────────────
    if all_results:
        avg_precision = round(
            sum(r["metrics"]["precision"]
                for r in all_results)
            / len(all_results), 1
        )
        avg_recall = round(
            sum(r["metrics"]["recall"]
                for r in all_results)
            / len(all_results), 1
        )
        avg_f1 = round(
            sum(r["metrics"]["f1"]
                for r in all_results)
            / len(all_results), 1
        )

        print("\n" + "="*65)
        print("  OVERALL RESULTS")
        print("="*65)
        print(f"\n  Test cases evaluated : "
              f"{len(all_results)}")
        print(f"  Average Precision    : "
              f"{avg_precision}%")
        print(f"  Average Recall       : "
              f"{avg_recall}%")
        print(f"  Average F1 Score     : "
              f"{avg_f1}%")

        # Interpretation
        print(f"\n  Interpretation:")
        if avg_precision >= 70:
            print(f"    ✅ Precision {avg_precision}% — "
                  f"system's 'missing' calls are reliable")
        else:
            print(f"    ⚠️  Precision {avg_precision}% — "
                  f"system sometimes flags keywords "
                  f"that aren't truly missing")

        if avg_recall >= 70:
            print(f"    ✅ Recall {avg_recall}% — "
                  f"system catches most truly "
                  f"missing keywords")
        else:
            print(f"    ⚠️  Recall {avg_recall}% — "
                  f"system misses some truly "
                  f"missing keywords")

        # Save summary
        summary = {
            "total_cases"   : len(all_results),
            "avg_precision" : avg_precision,
            "avg_recall"    : avg_recall,
            "avg_f1"        : avg_f1,
            "per_case_results": all_results,
        }

        with open("evaluation_report.json", "w") as f:
            json.dump(summary, f, indent=2)

        print(f"\n  ✅ Full report saved to "
              f"evaluation_report.json")

    print("\n" + "="*65 + "\n")


# ── Run ─────────────────────────────────────────────────────
if __name__ == "__main__":
    run_evaluation()