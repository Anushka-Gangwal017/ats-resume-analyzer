# ─────────────────────────────────────────────────────────────
# app.py  —  FIXED VERSION
# Key fixes:
#   1. sys.path uses abspath so it works from any directory
#   2. clean_results_for_template is bulletproof
#   3. Every key has a safe default — no KeyError in Jinja2
#   4. Dark mode CSS variable support added
# ─────────────────────────────────────────────────────────────
import os
import sys
import uuid
from flask import send_file
import tempfile

# ── MUST be before src imports ────────────────────────────────
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'src'
))
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'src'
))
from report_generator import generate_report

from flask import (
    Flask, render_template, request,
    redirect, url_for, flash, jsonify,
)
from werkzeug.utils import secure_filename
from ats_core import run_full_analysis

app = Flask(__name__)
app.secret_key = "resumeiq_secret_2026_change_in_prod"

UPLOAD_FOLDER      = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "uploads"
)
ALLOWED_EXTENSIONS = {"pdf"}
app.config["UPLOAD_FOLDER"]      = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5 MB


def allowed_file(filename):
    return (
        "." in filename and
        filename.rsplit(".", 1)[1].lower()
        in ALLOWED_EXTENSIONS
    )


def safe_get(d, *keys, default=None):
    """Safely traverse nested dict without KeyError."""
    for k in keys:
        if not isinstance(d, dict):
            return default
        d = d.get(k, default)
    return d if d is not None else default


def clean_for_template(raw):
    """Converts pipeline output to Jinja2-safe flat dict."""
    
    # Start with ALL keys having safe defaults
    # This prevents any KeyError or scoping issues
    r = {
        "final_score"           : 0.0,
        "semantic_score"        : 0.0,
        "keyword_score"         : 0.0,
        "final_grade"           : "",
        "score_colour"          : "#DC2626",
        "score_label"           : "Needs Work",
        "matched_keywords"      : [],
        "missing_keywords"      : [],
        "extra_keywords"        : [],
        "matched_count"         : 0,
        "missing_count"         : 0,
        "soft_matches"          : [],
        "section_report"        : {},
        "section_similarities"  : {},
        "section_keyword_scores": {},
        "suggestions"           : [],
        "high_priority_count"   : 0,
        "verb_verdict"          : "",
        "weak_verbs"            : [],
        "strong_verbs"          : [],
        "quant_verdict"         : "",
        "resume_filename"       : "resume.pdf",
        "analysed_at"           : "",
        "jd_level"              : "Unknown",
        "jd_confidence"         : "Low",
        "jd_warning"            : None,
        "jd_signals"            : [],
        "jd_level_colour"       : "#6B7280",
        "analysis_id"           : None,
        "saved_to_db"           : False,
    }

    try:
        # ── Scores ───────────────────────────────────────────
        sb = safe_get(raw, "score_breakdown", default={})
        r["final_score"]    = float(
            safe_get(sb, "final_score",         default=0) or 0
        )
        r["semantic_score"] = float(
            safe_get(sb, "semantic_score_pct",  default=0) or 0
        )
        r["keyword_score"]  = float(
            safe_get(sb, "keyword_score_pct",   default=0) or 0
        )
        r["final_grade"] = str(
            safe_get(raw, "final_grade", default="") or ""
        )

        sc = r["final_score"]
        if sc >= 75:
            r["score_colour"] = "#16A34A"
            r["score_label"]  = "Strong Match"
        elif sc >= 50:
            r["score_colour"] = "#D97706"
            r["score_label"]  = "Average Match"
        else:
            r["score_colour"] = "#DC2626"
            r["score_label"]  = "Needs Work"

        # ── Keywords ─────────────────────────────────────────
        gap = safe_get(raw, "gap_report", default={})
        r["matched_keywords"] = list(
            safe_get(gap, "matched_keywords", default=[]) or []
        )
        r["missing_keywords"] = list(
            safe_get(gap, "missing_keywords", default=[]) or []
        )
        r["extra_keywords"] = list(
            safe_get(gap, "extra_keywords", default=[]) or []
        )[:8]
        r["matched_count"] = int(
            safe_get(gap, "matched_count", default=0) or 0
        )
        r["missing_count"] = int(
            safe_get(gap, "missing_count", default=0) or 0
        )

        # ── Soft matches ─────────────────────────────────────
        syns     = safe_get(raw, "synonym_analysis", default={})
        raw_soft = safe_get(syns, "soft_matches",    default=[])
        r["soft_matches"] = [
            {
                "resume_keyword": str(
                    m.get("resume_keyword", "")
                ),
                "jd_keyword"    : str(m.get("jd_keyword", "")),
                "similarity"    : float(
                    m.get("similarity", 0) or 0
                ),
                "note"          : str(m.get("note", "")),
            }
            for m in (raw_soft or [])
            if isinstance(m, dict)
        ]

        # ── Section report ────────────────────────────────────
        raw_sec = safe_get(raw, "section_report", default={})
        r["section_report"] = {
            str(k): {
                "status": str(
                    v.get("status", "")
                    if isinstance(v, dict) else ""
                ),
                "length": int(
                    v.get("length", 0)
                    if isinstance(v, dict) else 0
                ),
                "note": str(
                    v.get("note", "")
                    if isinstance(v, dict) else str(v)
                ),
            }
            for k, v in (raw_sec or {}).items()
        }

        # ── Section similarities ──────────────────────────────
        raw_sim = safe_get(
            raw, "section_similarities", default={}
        )
        r["section_similarities"] = {
            str(k): round(float(v or 0) * 100, 1)
            for k, v in (raw_sim or {}).items()
        }

        # ── Section keyword scores (Day 14) ───────────────────
        raw_sks = safe_get(
            raw, "section_keyword_scores", default={}
        )
        r["section_keyword_scores"] = {
            str(k): {
                "score"  : float(
                    v.get("score", 0) or 0
                    if isinstance(v, dict) else 0
                ),
                "matched": list(
                    v.get("matched", []) or []
                    if isinstance(v, dict) else []
                ),
            }
            for k, v in (raw_sks or {}).items()
        }

        # ── Suggestions ───────────────────────────────────────
        raw_sugg = safe_get(raw, "suggestions", default=[])
        if isinstance(raw_sugg, list):
            r["suggestions"] = [
                str(s.get("message", s))
                if isinstance(s, dict) else str(s)
                for s in raw_sugg
            ]
        else:
            r["suggestions"] = []

        r["high_priority_count"] = int(
            safe_get(raw, "high_priority_count", default=0)
            or 0
        )

        # ── Verb analysis ─────────────────────────────────────
        verb = safe_get(raw, "verb_analysis", default={})
        r["verb_verdict"] = str(
            safe_get(verb, "overall_verdict", default="") or ""
        )
        r["weak_verbs"]   = list(
            safe_get(verb, "weak_found",   default=[]) or []
        )
        r["strong_verbs"] = list(
            safe_get(verb, "strong_found", default=[]) or []
        )

        # ── Quantification ────────────────────────────────────
        quant = safe_get(raw, "quant_analysis", default={})
        r["quant_verdict"] = str(
            safe_get(quant, "verdict", default="") or ""
        )

        # ── Metadata ──────────────────────────────────────────
        meta = safe_get(raw, "metadata", default={})
        r["resume_filename"] = str(
            safe_get(
                meta, "resume_file", default="resume.pdf"
            ) or "resume.pdf"
        )
        r["analysed_at"] = str(
            safe_get(meta, "analysed_at", default="") or ""
        )

        # ── JD classification ─────────────────────────────────
        jd_cls = safe_get(
            raw, "jd_classification", default={}
        )
        r["jd_level"]      = str(
            jd_cls.get("level",      "Unknown")
            if isinstance(jd_cls, dict) else "Unknown"
        )
        r["jd_confidence"] = str(
            jd_cls.get("confidence", "Low")
            if isinstance(jd_cls, dict) else "Low"
        )
        r["jd_warning"]    = (
            jd_cls.get("warning", None)
            if isinstance(jd_cls, dict) else None
        )
        r["jd_signals"]    = list(
            jd_cls.get("signals_found", []) or []
            if isinstance(jd_cls, dict) else []
        )
        colours = {
            "Entry"  : "#16A34A",
            "Mid"    : "#D97706",
            "Senior" : "#DC2626",
            "Unknown": "#6B7280",
        }
        r["jd_level_colour"] = colours.get(
            r["jd_level"], "#6B7280"
        )

    except Exception as e:
        # If anything goes wrong, log it but
        # always return r with safe defaults
        print(f"  clean_for_template warning: {e}")
        import traceback
        traceback.print_exc()

        # Categorized missing keywords for grouped display
    try:
        from keyword_extractor import categorize_keywords
        r["missing_by_category"] = categorize_keywords(
            r["missing_keywords"]
        )
    except Exception:
        r["missing_by_category"] = {}

    return r

# ── ROUTES ────────────────────────────────────────────────────

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    # Validate file
    if "resume" not in request.files:
        flash("Please upload a resume PDF.")
        return redirect(url_for("home"))

    f = request.files["resume"]
    if not f or f.filename == "":
        flash("No file selected.")
        return redirect(url_for("home"))

    if not allowed_file(f.filename):
        flash("Only PDF files are allowed.")
        return redirect(url_for("home"))
    

    # Validate JD text
    jd_text = request.form.get("jd_text", "").strip()
    if len(jd_text) < 50:
        flash("Please paste a job description "
              "(at least 50 characters).")
        return redirect(url_for("home"))

    # Save PDF
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    safe_name   = secure_filename(f.filename)
    unique_name = f"{uuid.uuid4().hex}_{safe_name}"
    save_path   = os.path.join(UPLOAD_FOLDER, unique_name)
    f.save(save_path)

    # Run pipeline
    try:
        print(f"\n[WEB] Analysing: {safe_name}")
        raw = run_full_analysis(save_path, jd_text)

        if "error" in raw:
            flash(f"Analysis failed: {raw['error']}")
            return redirect(url_for("home"))

        cleaned = clean_for_template(raw)

    except Exception as e:
        import traceback
        traceback.print_exc()
        flash(f"Something went wrong: {e}")
        return redirect(url_for("home"))

    finally:
        if os.path.exists(save_path):
            try:
                os.remove(save_path)
            except Exception:
                pass

    return render_template("result.html", **cleaned)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/health")
def health():
    return jsonify({
        "status" : "ok",
        "project": "ResumeIQ",
        "version": "1.0",
    })

@app.route("/sample-report")
def sample_report():
    return render_template("sample_report.html")

# ─────────────────────────────────────────────────────────────
# PASTE THIS INTO app.py — replace the existing
# /download-report route entirely with this version
# ─────────────────────────────────────────────────────────────

@app.route("/download-report", methods=["POST"])
def download_report():
    """Generates PDF report from posted form data."""
    try:
        import json
        import tempfile

        def safe_json(key, default):
            raw = request.form.get(key, "")
            if not raw or raw.strip() in ("", "None", "null", "undefined"):
                return default
            try:
                parsed = json.loads(raw)
                return parsed if parsed is not None else default
            except Exception as e:
                print(f"  JSON parse failed for '{key}': {e}")
                print(f"  Raw value was: {raw[:200]}")
                return default

        def safe_float(key, default=0.0):
            try:
                val = request.form.get(key, default)
                return float(val) if val not in (None, "", "None") else default
            except Exception:
                return default

        def safe_int(key, default=0):
            try:
                val = request.form.get(key, default)
                return int(float(val)) if val not in (None, "", "None") else default
            except Exception:
                return default

        def safe_str(key, default=""):
            val = request.form.get(key, default)
            return val if val and val != "None" else default

        results = {
            "final_score"    : safe_float("final_score"),
            "semantic_score" : safe_float("semantic_score"),
            "keyword_score"  : safe_float("keyword_score"),
            "final_grade"    : safe_str("final_grade"),
            "score_label"    : safe_str("score_label"),
            "resume_filename": safe_str("resume_filename", "resume.pdf"),
            "analysed_at"    : safe_str("analysed_at"),
            "jd_level"       : safe_str("jd_level", "Unknown"),
            "jd_warning"     : safe_str("jd_warning") or None,
            "matched_keywords": safe_json("matched_keywords", []),
            "missing_keywords": safe_json("missing_keywords", []),
            "matched_count"  : safe_int("matched_count"),
            "missing_count"  : safe_int("missing_count"),
            "soft_matches"   : safe_json("soft_matches", []),
            "section_report" : safe_json("section_report", {}),
            "section_keyword_scores": safe_json("section_keyword_scores", {}),
            "suggestions"    : safe_json("suggestions", []),
            "verb_verdict"   : safe_str("verb_verdict"),
            "quant_verdict"  : safe_str("quant_verdict"),
            "high_priority_count": safe_int("high_priority_count"),
        }

        # Debug print — check terminal when you click download
        print("\n[PDF DEBUG] Data received for report:")
        print(f"  final_score: {results['final_score']}")
        print(f"  matched_keywords: {len(results['matched_keywords'])} items")
        print(f"  missing_keywords: {len(results['missing_keywords'])} items")
        print(f"  section_report: {len(results['section_report'])} sections")
        print(f"  suggestions: {len(results['suggestions'])} items")

        tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        tmp.close()
        generate_report(results, tmp.name)

        # Clean filename for download (strip UUID prefix if present)
        clean_name = results["resume_filename"]
        if "_" in clean_name and len(clean_name.split("_")[0]) == 32:
            clean_name = "_".join(clean_name.split("_")[1:])
        clean_name = clean_name.replace(".pdf", "")

        download_name = f"ResumeIQ_{clean_name}_Report.pdf"

        return send_file(
            tmp.name,
            as_attachment=True,
            download_name=download_name,
            mimetype="application/pdf"
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        flash(f"Could not generate report: {e}")
        return redirect(url_for("home"))
    
if __name__ == "__main__":
    print("\n" + "="*50)
    print("  ResumeIQ — Web Server")
    print("="*50)
    print("  http://localhost:5000")
    print("="*50 + "\n")

    app.run(debug=True, host="0.0.0.0", port=5000)