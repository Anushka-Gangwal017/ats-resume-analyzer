# ─────────────────────────────────────────────────────────────
# ats_core.py  —  FIXED VERSION
# Key fixes:
#   1. Step 4 runs BEFORE Step 5 (synonym analysis
#      needs semantic results but suggestions don't)
#   2. Every step wrapped in try/except with fallback
#   3. Step 6 guaranteed to complete with safe defaults
#   4. No step can hang the whole pipeline
# ─────────────────────────────────────────────────────────────

import os
import sys
import json
from datetime import datetime
from jd_classifier import classify_jd, get_level_badge_colour
from keyword_extractor import (
    extract_keywords_from_resume,
    extract_keywords_from_jd,
    extract_keywords_from_text,
    normalize_keywords,
)

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from pdf_parser        import extract_text
from section_extractor import extract_sections, extract_contact_info
from keyword_extractor import (
    extract_keywords_from_resume,
    extract_keywords_from_jd,
)
from gap_analyzer import (
    analyze_gap,
    analyze_section_strength,
    calculate_match_score,
    get_ats_grade,
)
from similarity_engine import (
    compute_similarity,
    compute_section_similarities,
    compute_final_ats_score,
    analyse_skill_synonyms,
    get_semantic_grade,
)

# Import suggestion engine if available, else use fallback
try:
    from suggestion_engine import generate_full_suggestions
    USE_SUGGESTION_ENGINE = True
except ImportError:
    USE_SUGGESTION_ENGINE = False


def _safe_generate_suggestions(gap_report,
                                section_report,
                                sections,
                                soft_matches=None):
    """
    Generates suggestions using the full engine if available,
    otherwise falls back to simple string list.
    Always returns a plain list of strings safe for Jinja2.
    """
    if USE_SUGGESTION_ENGINE:
        try:
            result = generate_full_suggestions(
                gap_report, section_report, sections,
                soft_matches=soft_matches
            )
            raw = result.get("suggestions", [])
            # Normalise to list of strings
            out = []
            for s in raw:
                if isinstance(s, dict):
                    out.append(s.get("message", str(s)))
                else:
                    out.append(str(s))
            return out, result.get("verb_analysis", {}), \
                   result.get("quant_analysis", {}), \
                   result.get("high_priority", 0)
        except Exception as e:
            print(f"  suggestion engine error: {e}")

    # Simple fallback
    suggestions = []
    for kw in gap_report.get("missing_keywords", [])[:8]:
        suggestions.append(
            f"➕ Add '{kw}' to your Skills section — "
            f"it appears in the job description"
        )
    for sec, info in section_report.items():
        if "Missing" in info.get("status", ""):
            suggestions.append(
                f"🚨 Add a {sec.upper()} section — "
                f"ATS systems look for this heading"
            )
        elif "Weak" in info.get("status", ""):
            suggestions.append(
                f"✏️  Expand your {sec.upper()} section — "
                f"currently too short"
            )
    return suggestions, {}, {}, 0


# ─────────────────────────────────────────────────────────────
# MASTER FUNCTION
# ─────────────────────────────────────────────────────────────

def run_full_analysis(resume_pdf_path, jd_text):
    """
    Runs the complete ATS analysis pipeline.
    Returns a results dict safe to pass to Flask/Jinja2.
    """
    results = {}
    errors  = []

    # ── STEP 1: Parse PDF ─────────────────────────────────────
    print("  [1/6] Reading PDF...")
    try:
        raw_text = extract_text(resume_pdf_path)
        if not raw_text or len(raw_text.strip()) < 50:
            return {"error": [
                "Could not extract text from PDF. "
                "Make sure it is not a scanned image."
            ]}
        results["raw_text_length"] = len(raw_text)
    except Exception as e:
        return {"error": [f"PDF reading failed: {e}"]}

    # ── STEP 2: Extract sections ──────────────────────────────
    print("  [2/6] Extracting sections...")
    sections     = {}
    contact_info = {}
    try:
        sections     = extract_sections(raw_text)
        contact_info = extract_contact_info(raw_text)
    except Exception as e:
        errors.append(f"Section extraction warning: {e}")
    results["sections"]     = sections
    results["contact_info"] = contact_info

    # ── STEP 3: Keywords ──────────────────────────────────────
    print("  [3/6] Extracting keywords...")
    resume_kw_all = []
    jd_kw         = []
    try:
        resume_kw_data = extract_keywords_from_resume(sections)
        jd_kw          = extract_keywords_from_jd(jd_text)
        resume_kw_all  = resume_kw_data.get("ALL_KEYWORDS", [])
        results["resume_keywords"]             = resume_kw_all
        results["resume_keywords_by_section"]  = {
            k: v for k, v in resume_kw_data.items()
            if k not in ("ALL_KEYWORDS",
                         "ALL_KEYWORDS_RAW_COUNT")
        }
        results["jd_keywords"] = jd_kw
    except Exception as e:
        errors.append(f"Keyword extraction warning: {e}")

        # ── JD Classification ──────────────────────────────────
    print("  [3b/6] Classifying JD difficulty...")
    try:
        jd_classification = classify_jd(jd_text)
        results["jd_classification"] = jd_classification
    except Exception as e:
        results["jd_classification"] = {
            "level": "Unknown", "confidence": "Low",
            "signals_found": [], "warning": None,
            "degree_required": None,
        }

    # ── STEP 4: Gap analysis ──────────────────────────────────
    print("  [4/6] Analysing keyword gap...")
    gap_report     = {}
    section_report = {}
    keyword_score  = 0
    try:
        gap_report     = analyze_gap(resume_kw_all, jd_kw)
        section_report = analyze_section_strength(sections)
        keyword_score  = gap_report.get("match_score", 0)
        results["gap_report"]     = gap_report
        results["section_report"] = section_report
        results["keyword_score"]  = keyword_score
    except Exception as e:
        errors.append(f"Gap analysis warning: {e}")
        results["gap_report"]     = {
            "match_score": 0, "matched_keywords": [],
            "missing_keywords": [], "extra_keywords": [],
            "matched_count": 0, "missing_count": 0,
            "total_jd_keywords": 0,
            "total_resume_keywords": 0,
            "grade": "Could not calculate",
        }
        # ── Section-level keyword scores ─────────────────────
        section_keyword_scores = {}
        section_names = [
            'skills', 'experience', 'projects',
            'summary', 'certifications', 'research'
        ]
        for sec_name in section_names:
            sec_text = sections.get(sec_name, '').strip()
            if sec_text and len(sec_text) > 10:
                # Get keywords from just this section
                sec_kw = extract_keywords_from_text(sec_text)
                sec_kw_norm = normalize_keywords(sec_kw)
                # Score this section against JD
                if jd_kw:
                    sec_matched = set(sec_kw_norm) & set(jd_kw)
                    sec_score   = round(
                        len(sec_matched) / len(set(jd_kw)) * 100,
                        1
                    )
                else:
                    sec_score = 0
                section_keyword_scores[sec_name] = {
                    "score"  : sec_score,
                    "matched": sorted(sec_matched
                               if jd_kw else []),
                    "keywords_found": sorted(sec_kw_norm),
                }

        results["section_keyword_scores"] = section_keyword_scores
        results["section_report"] = {}
        results["keyword_score"]  = 0

    # ── STEP 5: AI semantic analysis ─────────────────────────
    print("  [5/6] Running AI semantic analysis...")
    semantic_score   = 0.0
    synonym_analysis = {
        "exact_matched": [], "soft_matches": [],
        "hard_missing": []
    }
    try:
        full_resume_text = " ".join([
            v for v in sections.values()
            if isinstance(v, str) and len(v) > 10
        ])
        semantic_score   = compute_similarity(
            full_resume_text, jd_text
        )
        section_sim      = compute_section_similarities(
            sections, jd_text
        )
        synonym_analysis = analyse_skill_synonyms(
            resume_kw_all, jd_kw
        )
        results["semantic_score"]       = semantic_score
        results["semantic_grade"]       = get_semantic_grade(
            semantic_score
        )
        results["section_similarities"] = section_sim
        results["synonym_analysis"]     = synonym_analysis
    except Exception as e:
        errors.append(f"Semantic analysis warning: {e}")
        results["semantic_score"]       = 0.0
        results["semantic_grade"]       = "Could not calculate"
        results["section_similarities"] = {}
        results["synonym_analysis"]     = synonym_analysis

    # ── STEP 6: Final score ───────────────────────────────────
    print("  [6/6] Calculating final score...")
    try:
        final_score = compute_final_ats_score(
            semantic_score, keyword_score
        )
        final_grade = get_ats_grade(final_score)
        results["final_score"] = final_score
        results["final_grade"] = final_grade
        results["score_breakdown"] = {
            "semantic_score_pct": round(
                float(semantic_score) * 100, 1
            ),
            "keyword_score_pct" : float(keyword_score),
            "final_score"       : final_score,
            "final_grade"       : final_grade,
            "semantic_weight"   : "50%",
            "keyword_weight"    : "50%",
        }
        print(f"  Done! Final score: {final_score}/100")
    except Exception as e:
        print(f"  [6/6] score error: {e}")
        results["final_score"]     = 0
        results["final_grade"]     = "Could not calculate"
        results["score_breakdown"] = {
            "semantic_score_pct": 0,
            "keyword_score_pct" : 0,
            "final_score"       : 0,
            "final_grade"       : "Error — see terminal",
            "semantic_weight"   : "50%",
            "keyword_weight"    : "50%",
        }

    # ── Generate suggestions ──────────────────────────────────
    soft_matches = synonym_analysis.get("soft_matches", [])
    suggestions, verb_analysis, quant_analysis, hi_count = \
        _safe_generate_suggestions(
            results.get("gap_report", {}),
            section_report,
            sections,
            soft_matches=soft_matches
        )
    results["suggestions"]         = suggestions
    results["verb_analysis"]       = verb_analysis
    results["quant_analysis"]      = quant_analysis
    results["high_priority_count"] = hi_count

    # ── Metadata ──────────────────────────────────────────────
    results["metadata"] = {
        "analysed_at" : datetime.now().strftime(
            "%d %b %Y, %I:%M %p"
        ),
        "resume_file" : os.path.basename(resume_pdf_path),
        "errors"      : errors,
    }

    return results


# ─────────────────────────────────────────────────────────────
# PRINT HELPER
# ─────────────────────────────────────────────────────────────

def print_report(results):
    if "error" in results:
        print(f"\n❌ Analysis failed: {results['error']}")
        return

    score = results.get("score_breakdown", {})
    gap   = results.get("gap_report", {})
    sugg  = results.get("suggestions", [])

    print("\n" + "="*55)
    print("  ATS ANALYSIS REPORT")
    print("="*55)
    print(f"  🏆 Final score    : "
          f"{score.get('final_score', 0)}/100")
    print(f"  🤖 Semantic       : "
          f"{score.get('semantic_score_pct', 0)}%")
    print(f"  🔑 Keywords       : "
          f"{score.get('keyword_score_pct', 0)}%")
    print(f"  ✅ Matched        : "
          f"{gap.get('matched_keywords', [])}")
    print(f"  ❌ Missing        : "
          f"{gap.get('missing_keywords', [])}")
    print("\n  💡 Suggestions:")
    for i, s in enumerate(sugg[:5], 1):
        print(f"     {i}. {s}")
    print("="*55)


# ─────────────────────────────────────────────────────────────
# SAVE RESULT
# ─────────────────────────────────────────────────────────────

def save_result_to_json(results,
                        output_path="results_log.json"):
    def clean(obj):
        if isinstance(obj, (int, float, str,
                             bool, type(None))):
            return obj
        if isinstance(obj, dict):
            return {k: clean(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [clean(i) for i in obj]
        return str(obj)

    cleaned  = clean(results)
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
    print(f"  Saved to {output_path}")


# ─────────────────────────────────────────────────────────────
# TEST
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":

    import glob

    resume_files = glob.glob("data/resumes/*.pdf")
    jd_files     = sorted(glob.glob("data/jds/*.txt"))

    if not resume_files:
        print("No resume PDFs found in data/resumes/")
        raise SystemExit

    if not jd_files:
        print("No JD files found in data/jds/")
        raise SystemExit

    resume_path = resume_files[0]
    jd_path     = jd_files[0]

    print(f"\nResume : {resume_path}")
    print(f"JD     : {jd_path}\n")

    with open(jd_path, "r", encoding="utf-8") as f:
        jd_text = f.read()

    results = run_full_analysis(resume_path, jd_text)
    print_report(results)
    save_result_to_json(results)