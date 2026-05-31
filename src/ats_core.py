# ─────────────────────────────────────────────────────────────
# ats_core.py
#
# THE MASTER PIPELINE — chains all 5 modules together.
# Give it a resume PDF path + JD text
# and it returns the complete ATS analysis report.
#
# This is the file that your Flask website will call later.
# ─────────────────────────────────────────────────────────────

import os
import sys
import json
from datetime import datetime

# Make sure Python can find all our src/ files
sys.path.append(os.path.dirname(__file__))

from pdf_parser        import extract_text
from section_extractor import extract_sections, extract_contact_info
from keyword_extractor import (extract_keywords_from_resume,
                                extract_keywords_from_jd)
from gap_analyzer      import (analyze_gap, analyze_section_strength,
                                generate_suggestions,
                                check_action_verbs,
                                calculate_match_score,
                                get_ats_grade)
from similarity_engine import (compute_similarity,
                                compute_section_similarities,
                                compute_final_ats_score,
                                analyse_skill_synonyms,
                                get_semantic_grade)


# ─────────────────────────────────────────────────────────────
# MASTER FUNCTION
# ─────────────────────────────────────────────────────────────

def run_full_analysis(resume_pdf_path, jd_text):
    """
    THE main function your website will call.

    Takes:
        resume_pdf_path → path to the uploaded PDF file
        jd_text         → the job description as a plain string

    Returns:
        A big dictionary with EVERYTHING:
        scores, keywords, gaps, suggestions, section grades
    """

    results = {}
    errors  = []

    # ── STEP 1: Parse the PDF ─────────────────────────────────
    print("  [1/6] Reading PDF...")
    try:
        raw_text = extract_text(resume_pdf_path)
        if not raw_text or len(raw_text) < 50:
            errors.append("Could not extract text from PDF. "
                          "Make sure it is not a scanned image.")
            return {"error": errors}
        results["raw_text_length"] = len(raw_text)
    except Exception as e:
        errors.append(f"PDF reading failed: {str(e)}")
        return {"error": errors}

    # ── STEP 2: Extract sections ──────────────────────────────
    print("  [2/6] Extracting resume sections...")
    try:
        sections     = extract_sections(raw_text)
        contact_info = extract_contact_info(raw_text)
        results["sections"]     = sections
        results["contact_info"] = contact_info
    except Exception as e:
        errors.append(f"Section extraction failed: {str(e)}")
        sections = {}

    # ── STEP 3: Extract keywords ──────────────────────────────
    print("  [3/6] Extracting keywords...")
    try:
        resume_kw_data = extract_keywords_from_resume(sections)
        jd_kw          = extract_keywords_from_jd(jd_text)
        resume_kw_all  = resume_kw_data.get("ALL_KEYWORDS", [])

        results["resume_keywords"]          = resume_kw_all
        results["resume_keywords_by_section"] = {
            k: v for k, v in resume_kw_data.items()
            if k != "ALL_KEYWORDS"
        }
        results["jd_keywords"] = jd_kw
    except Exception as e:
        errors.append(f"Keyword extraction failed: {str(e)}")
        resume_kw_all = []
        jd_kw         = []

    # ── STEP 4: Keyword gap analysis ─────────────────────────
    print("  [4/6] Analysing keyword gap...")
    try:
        gap_report     = analyze_gap(resume_kw_all, jd_kw)
        section_report = analyze_section_strength(sections)
        suggestions    = generate_suggestions(
                             gap_report["missing_keywords"],
                             section_report
                         )
        verb_check     = check_action_verbs(sections)
        keyword_score  = gap_report["match_score"]

        results["gap_report"]     = gap_report
        results["section_report"] = section_report
        results["suggestions"]    = suggestions
        results["verb_check"]     = verb_check
        results["keyword_score"]  = keyword_score
    except Exception as e:
        errors.append(f"Gap analysis failed: {str(e)}")
        keyword_score = 0

    # ── STEP 5: AI semantic similarity ───────────────────────
    print("  [5/6] Running AI semantic analysis...")
    try:
        # Combine all resume sections into one text block
        full_resume_text = " ".join([
            v for v in sections.values()
            if isinstance(v, str) and len(v) > 10
        ])

        semantic_score    = compute_similarity(
                                full_resume_text, jd_text
                            )
        section_sim       = compute_section_similarities(
                                sections, jd_text
                            )
        synonym_analysis  = analyse_skill_synonyms(
                                resume_kw_all, jd_kw
                            )

        results["semantic_score"]      = semantic_score
        results["semantic_grade"]      = get_semantic_grade(
                                             semantic_score
                                         )
        results["section_similarities"] = section_sim
        results["synonym_analysis"]     = synonym_analysis
    except Exception as e:
        errors.append(f"Semantic analysis failed: {str(e)}")
        semantic_score = 0

    # ── STEP 6: Calculate final ATS score ────────────────────
    print("  [6/6] Calculating final ATS score...")
    try:
        final_score = compute_final_ats_score(
                          semantic_score, keyword_score
                      )
        final_grade = get_ats_grade(final_score)

        results["final_score"] = final_score
        results["final_grade"] = final_grade

        # Score breakdown for display
        results["score_breakdown"] = {
            "semantic_score_pct"  : round(semantic_score * 100, 1),
            "keyword_score_pct"   : keyword_score,
            "final_score"         : final_score,
            "final_grade"         : final_grade,
            "semantic_weight"     : "50%",
            "keyword_weight"      : "50%",
        }
    except Exception as e:
        errors.append(f"Score calculation failed: {str(e)}")

    # ── Add metadata ──────────────────────────────────────────
    results["metadata"] = {
        "analysed_at"    : datetime.now().strftime("%d %b %Y, %I:%M %p"),
        "resume_file"    : os.path.basename(resume_pdf_path),
        "errors"         : errors,
    }

    return results


# ─────────────────────────────────────────────────────────────
# PRINT HELPER — clean terminal display
# ─────────────────────────────────────────────────────────────

def print_report(results):
    """
    Prints the full ATS report in a clean,
    readable format in the terminal.
    """

    if "error" in results:
        print(f"\n❌ Analysis failed: {results['error']}")
        return

    meta  = results.get("metadata", {})
    score = results.get("score_breakdown", {})
    gap   = results.get("gap_report", {})
    sec   = results.get("section_report", {})
    sugg  = results.get("suggestions", [])
    verbs = results.get("verb_check", {})
    syns  = results.get("synonym_analysis", {})

    print("\n" + "═"*62)
    print("           FULL ATS ANALYSIS REPORT")
    print("═"*62)

    # ── Metadata ──────────────────────────────────────────────
    print(f"\n  📄 Resume   : {meta.get('resume_file','')}")
    print(f"  🕐 Analysed : {meta.get('analysed_at','')}")

    # ── Score block ───────────────────────────────────────────
    print("\n" + "─"*62)
    print("  📊 SCORES")
    print("─"*62)
    print(f"  🤖 AI Semantic score  : "
          f"{score.get('semantic_score_pct', 0)}%")
    print(f"  🔑 Keyword match score: "
          f"{score.get('keyword_score_pct', 0)}%")
    print(f"  ─────────────────────────────────────────────")
    print(f"  🏆 FINAL ATS SCORE    : "
          f"{score.get('final_score', 0)} / 100")
    print(f"  {score.get('final_grade', '')}")

    # ── Keywords ──────────────────────────────────────────────
    print("\n" + "─"*62)
    print("  🔍 KEYWORD ANALYSIS")
    print("─"*62)
    print(f"\n  ✅ Matched   : {gap.get('matched_keywords', [])}")
    print(f"  ❌ Missing   : {gap.get('missing_keywords', [])}")
    print(f"  ➕ Extra     : "
          f"{gap.get('extra_keywords', [])[:5]}")

    # ── Soft matches ──────────────────────────────────────────
    soft = syns.get("soft_matches", [])
    if soft:
        print(f"\n  🔄 SMART MATCHES (AI detected synonyms):")
        for m in soft:
            print(f"     → {m['note']}  "
                  f"({int(m['similarity']*100)}% similar)")

    # ── Section report ────────────────────────────────────────
    print("\n" + "─"*62)
    print("  📋 SECTION STRENGTH")
    print("─"*62)
    for section, info in sec.items():
        print(f"  {info['status']:<6}  "
              f"{section.upper():<18} {info['note']}")

    # ── Section AI similarity ─────────────────────────────────
    sec_sim = results.get("section_similarities", {})
    if sec_sim:
        print("\n  📈 SECTION RELEVANCE TO THIS JD:")
        for section, sim_score in sorted(
            sec_sim.items(), key=lambda x: x[1], reverse=True
        ):
            bar = "█" * int(sim_score * 25) + \
                  "░" * (25 - int(sim_score * 25))
            print(f"     {section:<18} {bar} "
                  f"{round(sim_score*100,1)}%")

    # ── Verb check ────────────────────────────────────────────
    print("\n" + "─"*62)
    print("  🔤 ACTION VERB CHECK")
    print("─"*62)
    print(f"  {verbs.get('verdict','')}")

    # ── Suggestions ───────────────────────────────────────────
    print("\n" + "─"*62)
    print("  💡 SUGGESTIONS TO IMPROVE")
    print("─"*62)
    for i, s in enumerate(sugg, 1):
        print(f"  {i:>2}. {s}")
    if not sugg:
        print("  Resume looks strong for this JD!")

    # ── Errors ────────────────────────────────────────────────
    if meta.get("errors"):
        print("\n" + "─"*62)
        print("  ⚠️  WARNINGS:")
        for err in meta["errors"]:
            print(f"     {err}")

    print("\n" + "═"*62 + "\n")


# ─────────────────────────────────────────────────────────────
# SAVE RESULT TO JSON
# ─────────────────────────────────────────────────────────────

def save_result_to_json(results, output_path="results_log.json"):
    """
    Saves the full result dictionary to a JSON file.
    Useful for keeping a log of all analyses done.
    """
    # results may contain non-serialisable objects — clean them
    def clean(obj):
        if isinstance(obj, (int, float, str, bool, type(None))):
            return obj
        if isinstance(obj, dict):
            return {k: clean(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [clean(i) for i in obj]
        return str(obj)

    cleaned = clean(results)

    # Load existing log if it exists
    existing = []
    if os.path.exists(output_path):
        try:
            with open(output_path, "r") as f:
                existing = json.load(f)
        except Exception:
            existing = []

    existing.append(cleaned)

    with open(output_path, "w") as f:
        json.dump(existing, f, indent=2)

    print(f"  ✅ Result saved to {output_path}")


# ─────────────────────────────────────────────────────────────
# TEST — run the full pipeline
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":

    print("\n" + "═"*62)
    print("  ATS CORE — FULL PIPELINE TEST")
    print("═"*62)

    # ── Single resume vs single JD ────────────────────────────
    RESUME_PATH = "data/resumes/resume2.pdf"
    JD_PATH     = "data/jds/jd_01.txt"

    with open(JD_PATH, "r", encoding="utf-8") as f:
        jd_text = f.read()

    print(f"\nRunning full analysis...")
    print(f"  Resume : {RESUME_PATH}")
    print(f"  JD     : {JD_PATH}\n")

    results = run_full_analysis(RESUME_PATH, jd_text)
    print_report(results)

    # Save to JSON log
    save_result_to_json(results)

    # ── Batch test: one resume vs ALL JDs ─────────────────────
    print("\n" + "═"*62)
    print("  BATCH TEST — Resume vs ALL JD files")
    print("═"*62 + "\n")

    jd_folder = "data/jds/"
    jd_files  = sorted([
        f for f in os.listdir(jd_folder)
        if f.endswith(".txt")
    ])

    batch_results = []

    for jd_file in jd_files:
        jd_path = os.path.join(jd_folder, jd_file)
        with open(jd_path, "r", encoding="utf-8") as f:
            jd_content = f.read()

        print(f"  Analysing vs {jd_file}...")
        r = run_full_analysis(RESUME_PATH, jd_content)

        score = r.get("final_score", 0)
        grade = r.get("final_grade", "")
        missing = r.get("gap_report", {}).get(
                      "missing_keywords", []
                  )[:3]

        batch_results.append({
            "jd_file"        : jd_file,
            "final_score"    : score,
            "top_3_missing"  : missing,
        })

        print(f"     Score: {score}/100  "
              f"| Top missing: {missing}")

    # Print batch summary table
    print("\n" + "─"*62)
    print("  BATCH SUMMARY")
    print("─"*62)
    print(f"  {'JD File':<22} {'Score':>8}  {'Grade'}")
    print(f"  {'─'*20:<22} {'─'*6:>8}  {'─'*20}")

    for br in sorted(
        batch_results, key=lambda x: x["final_score"], reverse=True
    ):
        print(f"  {br['jd_file']:<22} "
              f"{br['final_score']:>6}/100  "
              f"{br['top_3_missing']}")

    print("\n  Best matching JD: " +
          max(batch_results,
              key=lambda x: x["final_score"])["jd_file"])
    print("  Worst matching JD: " +
          min(batch_results,
              key=lambda x: x["final_score"])["jd_file"])
    print()