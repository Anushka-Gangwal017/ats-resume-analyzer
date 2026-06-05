# ─────────────────────────────────────────────────────────────
# app.py  —  Flask website for the ATS Resume Analyzer
#
# Routes:
#   GET  /          → home page (upload form)
#   POST /analyze   → runs analysis, shows results
#   GET  /result    → results page
#   GET  /about     → about the project
# ─────────────────────────────────────────────────────────────

import os
import sys
import uuid
from flask import (Flask, render_template, request,
                   redirect, url_for, session, flash,
                   jsonify)
from werkzeug.utils import secure_filename

# So Flask can find our src/ modules
sys.path.insert(0, os.path.join(
    os.path.dirname(__file__), 'src'
))

from ats_core import run_full_analysis

# ── App config ────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = "ats_analyzer_secret_key_2026"

UPLOAD_FOLDER   = "uploads"
ALLOWED_EXTENSIONS = {"pdf"}

app.config["UPLOAD_FOLDER"]    = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5MB max


# ── Helper ────────────────────────────────────────────────────
def allowed_file(filename):
    """Check if uploaded file is a PDF."""
    return (
        "." in filename and
        filename.rsplit(".", 1)[1].lower()
        in ALLOWED_EXTENSIONS
    )


def clean_results_for_template(results):
    """
    Makes the results dictionary safe to
    pass into HTML templates.
    Converts any non-serialisable objects to strings.
    """
    cleaned = {}

    # Score breakdown
    score_bd = results.get("score_breakdown", {})
    cleaned["final_score"]     = score_bd.get(
        "final_score", 0
    )
    cleaned["semantic_score"]  = score_bd.get(
        "semantic_score_pct", 0
    )
    cleaned["keyword_score"]   = score_bd.get(
        "keyword_score_pct", 0
    )
    cleaned["final_grade"]     = results.get(
        "final_grade", ""
    )

    # Determine score colour for UI
    score = cleaned["final_score"]
    if score >= 75:
        cleaned["score_colour"] = "#27AE60"   # green
        cleaned["score_label"]  = "Strong Match"
    elif score >= 50:
        cleaned["score_colour"] = "#F39C12"   # amber
        cleaned["score_label"]  = "Average Match"
    else:
        cleaned["score_colour"] = "#E74C3C"   # red
        cleaned["score_label"]  = "Needs Work"

    # Keywords
    gap = results.get("gap_report", {})
    cleaned["matched_keywords"] = gap.get(
        "matched_keywords", []
    )
    cleaned["missing_keywords"] = gap.get(
        "missing_keywords", []
    )
    cleaned["extra_keywords"]   = gap.get(
        "extra_keywords", []
    )[:8]
    cleaned["matched_count"]    = gap.get(
        "matched_count", 0
    )
    cleaned["missing_count"]    = gap.get(
        "missing_count", 0
    )

    # Smart synonym matches
    syns = results.get("synonym_analysis", {})
    cleaned["soft_matches"] = syns.get(
        "soft_matches", []
    )

    # Section report
    sec = results.get("section_report", {})
    cleaned["section_report"] = sec

    # Section similarities (bar chart data)
    sec_sim = results.get("section_similarities", {})
    cleaned["section_similarities"] = {
        k: round(v * 100, 1)
        for k, v in sec_sim.items()
    }

    # Suggestions
    sugg_data = results.get("suggestions", [])
    if isinstance(sugg_data, list):
        # Could be list of dicts or list of strings
        if sugg_data and isinstance(sugg_data[0], dict):
            cleaned["suggestions"] = [
                s.get("message", str(s))
                for s in sugg_data
            ]
        else:
            cleaned["suggestions"] = sugg_data
    else:
        cleaned["suggestions"] = []

    cleaned["high_priority_count"] = results.get(
        "high_priority_count", 0
    )

    # Verb analysis
    verb = results.get("verb_analysis", {})
    cleaned["verb_verdict"]  = verb.get(
        "overall_verdict", ""
    )
    cleaned["weak_verbs"]    = verb.get("weak_found", [])
    cleaned["strong_verbs"]  = verb.get("strong_found", [])

    # Quantification
    quant = results.get("quant_analysis", {})
    cleaned["quant_verdict"] = quant.get("verdict", "")

    # Contact info
    contact = results.get("contact_info", {})
    cleaned["contact_info"] = contact

    # Resume filename
    meta = results.get("metadata", {})
    cleaned["resume_filename"] = meta.get(
        "resume_file", "resume.pdf"
    )
    cleaned["analysed_at"] = meta.get("analysed_at", "")

    return cleaned


# ── ROUTES ────────────────────────────────────────────────────

@app.route("/")
def home():
    """Home page — shows the upload form."""
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    """
    Handles the form submission.
    1. Gets uploaded PDF
    2. Gets JD text
    3. Runs full analysis
    4. Passes results to result.html
    """

    # ── Validate PDF upload ───────────────────────────────────
    if "resume" not in request.files:
        flash("Please upload a resume PDF file.")
        return redirect(url_for("home"))

    file = request.files["resume"]

    if file.filename == "":
        flash("No file selected. Please choose a PDF.")
        return redirect(url_for("home"))

    if not allowed_file(file.filename):
        flash("Only PDF files are allowed.")
        return redirect(url_for("home"))

    # ── Validate JD text ──────────────────────────────────────
    jd_text = request.form.get("jd_text", "").strip()

    if len(jd_text) < 50:
        flash("Please paste a job description "
              "(at least 50 characters).")
        return redirect(url_for("home"))

    # ── Save uploaded PDF ─────────────────────────────────────
    # Give it a unique name so multiple users don't clash
    original_name  = secure_filename(file.filename)
    unique_name    = f"{uuid.uuid4().hex}_{original_name}"
    save_path      = os.path.join(
        app.config["UPLOAD_FOLDER"], unique_name
    )

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    file.save(save_path)

    # ── Run the full ATS analysis ─────────────────────────────
    try:
        print(f"\n[WEB] Analysing: {original_name}")
        raw_results = run_full_analysis(save_path, jd_text)

        if "error" in raw_results:
            flash(f"Analysis error: {raw_results['error']}")
            return redirect(url_for("home"))

        # Clean results for template
        results = clean_results_for_template(raw_results)

    except Exception as e:
        flash(f"Something went wrong: {str(e)}")
        return redirect(url_for("home"))

    finally:
        # Delete the uploaded file after analysis
        if os.path.exists(save_path):
            os.remove(save_path)

    return render_template("result.html", **results)


@app.route("/about")
def about():
    """About page — explains the project."""
    return render_template("about.html")


@app.route("/health")
def health():
    """
    Simple health check endpoint.
    Useful to confirm the server is running.
    """
    return jsonify({
        "status" : "running",
        "project": "ATS Resume Analyzer",
        "author" : "Anushka Gangwal",
        "version": "1.0"
    })


# ── Run the app ───────────────────────────────────────────────
if __name__ == "__main__":
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    print("\n" + "="*50)
    print("  ATS Resume Analyzer — Web Server")
    print("="*50)
    print("  Open your browser and go to:")
    print("  http://localhost:5000")
    print("="*50 + "\n")
    app.run(debug=True, host="0.0.0.0", port=5000)