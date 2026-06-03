# ─────────────────────────────────────────────────────────────
# gap_analyzer.py
# Takes resume keywords + JD keywords
# Returns a full structured gap report
# ─────────────────────────────────────────────────────────────


def calculate_match_score(resume_keywords, jd_keywords):
    """
    Improved scoring — counts how many times
    each JD keyword appears (frequency matters).
    """
    if not jd_keywords:
        return 0.0

    resume_set = set(resume_keywords)
    jd_set     = set(jd_keywords)
    matched    = resume_set & jd_set

    # Base score: matched / total
    base_score = (len(matched) / len(jd_set)) * 100

    # Bonus: if more than 60% matched, give small boost
    if base_score > 60:
        base_score = min(base_score * 1.05, 100)

    return round(base_score, 1)


def get_ats_grade(score):
    """
    Converts a numeric score into an ATS grade label.
    """
    if score >= 80:
        return "🟢 Excellent — Very likely to pass ATS"
    elif score >= 60:
        return "🟡 Good — Likely to pass ATS with small improvements"
    elif score >= 40:
        return "🟠 Average — Needs improvement before applying"
    else:
        return "🔴 Poor — Resume needs significant keyword work"


def analyze_gap(resume_keywords, jd_keywords):
    """
    Core gap analysis function.
    Takes two lists of keywords and returns
    a complete structured report dictionary.
    """
    resume_set = set(resume_keywords)
    jd_set     = set(jd_keywords)

    matched = sorted(resume_set & jd_set)   # in both
    missing = sorted(jd_set  - resume_set)  # in JD  but NOT resume
    extra   = sorted(resume_set - jd_set)   # in resume but NOT JD

    score = calculate_match_score(resume_keywords, jd_keywords)
    grade = get_ats_grade(score)

    report = {
        "match_score"     : score,
        "grade"           : grade,
        "total_jd_keywords"    : len(jd_set),
        "total_resume_keywords": len(resume_set),
        "matched_count"   : len(matched),
        "missing_count"   : len(missing),
        "matched_keywords": matched,
        "missing_keywords": missing,
        "extra_keywords"  : extra,
    }

    return report


def analyze_section_strength(resume_sections):
    """
    Looks at each resume section and flags
    ones that are too short or empty.

    Returns a dict of section → strength label.
    """
    # Minimum recommended character counts per section
    thresholds = {
        "summary"        : 100,
        "skills"         : 80,
        "experience"     : 150,
        "projects"       : 150,
        "education"      : 80,
        "certifications" : 50,
    }

    section_report = {}

    for section, min_length in thresholds.items():
        content = resume_sections.get(section, "").strip()
        length  = len(content)

        if length == 0:
            section_report[section] = {
                "status" : "❌ Missing",
                "length" : 0,
                "note"   : f"Section not found in resume. "
                           f"Add a {section} section."
            }
        elif length < min_length:
            section_report[section] = {
                "status" : "⚠️  Weak",
                "length" : length,
                "note"   : f"Only {length} characters — too short. "
                           f"Expand this section."
            }
        else:
            section_report[section] = {
                "status" : "✅ Good",
                "length" : length,
                "note"   : f"Looks fine ({length} characters)"
            }

    return section_report


def generate_suggestions(missing_keywords,
                          section_report,
                          soft_matches=None):
    """
    Generates specific actionable suggestions.
    Now also accounts for soft matches from
    the AI similarity engine so we don't
    suggest things that are already covered
    semantically.
    """
    suggestions = []

    # Keywords covered by soft matches — don't re-suggest
    soft_covered = set()
    if soft_matches:
        for m in soft_matches:
            soft_covered.add(m.get("jd_keyword", ""))

    # Skills that belong in the Skills section
    skill_keywords = [
        "python", "sql", "java", "javascript", "html",
        "css", "flask", "django", "react", "git", "github",
        "linux", "docker", "aws", "machine learning",
        "deep learning", "nlp", "pandas", "numpy",
        "scikit-learn", "tensorflow", "cybersecurity",
        "vapt", "tableau", "power bi", "mysql",
        "postgresql", "mongodb", "rest api", "fastapi",
    ]

    # Skills better mentioned in Projects section
    project_keywords = [
        "api", "backend", "frontend", "web scraping",
        "automation", "testing", "deployment", "database",
        "data pipeline", "model training",
    ]

    for kw in missing_keywords[:12]:
        # Skip if already covered by a soft match
        if kw in soft_covered:
            suggestions.append(
                f"✅ '{kw}' is semantically covered by "
                f"your resume — but consider adding the "
                f"exact term for ATS keyword matching"
            )
            continue

        if kw in skill_keywords:
            suggestions.append(
                f"➕ Add '{kw}' to your Skills section — "
                f"it appears in the job description"
            )
        elif kw in project_keywords:
            suggestions.append(
                f"🔧 Mention '{kw}' in your Projects "
                f"section — describe how you used it"
            )
        else:
            suggestions.append(
                f"📝 Include '{kw}' somewhere in your "
                f"resume — it is required by this JD"
            )

    # Section-level suggestions
    for section, info in section_report.items():
        if "Missing" in info["status"]:
            suggestions.append(
                f"🚨 Your resume has NO "
                f"{section.upper()} section — add one"
            )
        elif "Weak" in info["status"]:
            suggestions.append(
                f"✏️  Your {section.upper()} section is "
                f"too short ({info['length']} chars) — "
                f"expand it"
            )

    return suggestions


def check_action_verbs(resume_sections):
    """
    Checks if experience and project bullet points
    start with strong action verbs.
    Flags weak verbs like 'helped', 'assisted', 'worked on'.
    """
    weak_verbs = [
        "helped", "assisted", "worked", "did", "made",
        "was responsible", "participated", "involved",
        "contributed to", "tried", "attempted",
    ]

    strong_verbs = [
        "built", "developed", "designed", "implemented",
        "created", "led", "managed", "optimised", "improved",
        "automated", "deployed", "integrated", "analysed",
        "researched", "published", "collaborated", "engineered",
    ]

    text_to_check = (
        resume_sections.get("experience", "") + " " +
        resume_sections.get("projects",   "")
    ).lower()

    found_weak   = [v for v in weak_verbs   if v in text_to_check]
    found_strong = [v for v in strong_verbs if v in text_to_check]

    result = {
        "weak_verbs_found"  : found_weak,
        "strong_verbs_found": found_strong,
    }

    if found_weak:
        result["verdict"] = (
            f"⚠️  Found {len(found_weak)} weak verb(s): "
            f"{found_weak}. Replace with stronger action verbs."
        )
    else:
        result["verdict"] = "✅ No weak verbs detected. Good job!"

    return result


def full_analysis(resume_keywords, jd_keywords, resume_sections):
    """
    Master function — runs ALL analysis in one call.
    Returns one big results dictionary.
    Use this from ats_core.py later.
    """
    gap_report      = analyze_gap(resume_keywords, jd_keywords)
    section_report  = analyze_section_strength(resume_sections)
    suggestions     = generate_suggestions(
                          gap_report["missing_keywords"],
                          section_report
                      )
    verb_check      = check_action_verbs(resume_sections)

    return {
        "gap_report"    : gap_report,
        "section_report": section_report,
        "suggestions"   : suggestions,
        "verb_check"    : verb_check,
    }


def print_full_report(results):
    """
    Prints the full analysis in a clean,
    readable format in the terminal.
    """
    gap     = results["gap_report"]
    sec     = results["section_report"]
    sugg    = results["suggestions"]
    verbs   = results["verb_check"]

    print("\n" + "=" * 60)
    print("          ATS GAP ANALYSIS REPORT")
    print("=" * 60)

    # ── Score block ───────────────────────────────────────────
    print(f"\n  📊 ATS MATCH SCORE : {gap['match_score']}%")
    print(f"  {gap['grade']}")
    print(f"\n  Resume keywords   : {gap['total_resume_keywords']}")
    print(f"  JD keywords       : {gap['total_jd_keywords']}")
    print(f"  Matched           : {gap['matched_count']}")
    print(f"  Missing           : {gap['missing_count']}")

    # ── Keywords ─────────────────────────────────────────────
    print("\n" + "-" * 60)
    print("  ✅ MATCHED KEYWORDS (in both resume and JD):")
    if gap["matched_keywords"]:
        print(f"     {gap['matched_keywords']}")
    else:
        print("     None found")

    print("\n  ❌ MISSING KEYWORDS (in JD but NOT in resume):")
    if gap["missing_keywords"]:
        print(f"     {gap['missing_keywords']}")
    else:
        print("     None — great match!")

    print("\n  ➕ EXTRA KEYWORDS (in resume but not required by JD):")
    if gap["extra_keywords"]:
        print(f"     {gap['extra_keywords'][:8]}...")
    else:
        print("     None")

    # ── Section strength ──────────────────────────────────────
    print("\n" + "-" * 60)
    print("  📋 SECTION STRENGTH REPORT:")
    for section, info in sec.items():
        print(f"     {info['status']}  {section.upper():<18}"
              f" — {info['note']}")

    # ── Action verbs ──────────────────────────────────────────
    print("\n" + "-" * 60)
    print("  🔤 ACTION VERB CHECK:")
    print(f"     {verbs['verdict']}")
    if verbs["strong_verbs_found"]:
        print(f"     Strong verbs found: {verbs['strong_verbs_found']}")

    # ── Suggestions ───────────────────────────────────────────
    print("\n" + "-" * 60)
    print("  💡 SUGGESTIONS TO IMPROVE YOUR RESUME:")
    if sugg:
        for i, s in enumerate(sugg, 1):
            print(f"     {i}. {s}")
    else:
        print("     Resume looks strong for this JD!")

    print("\n" + "=" * 60)


# ══════════════════════════════════════════════════════════════
# TEST — run this file directly
# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":

    import sys
    import os
    sys.path.append(os.path.dirname(__file__))

    from pdf_parser         import extract_text
    from section_extractor  import extract_sections
    from keyword_extractor  import (extract_keywords_from_resume,
                                    extract_keywords_from_jd)

    print("Loading your resume...")
    resume_path = "data/resumes/resume1.pdf"
    raw_text    = extract_text(resume_path)
    sections    = extract_sections(raw_text)
    resume_kw   = extract_keywords_from_resume(sections)

    # Use a real JD from your data/jds folder
    jd_path = "data/jds/jd_01.txt"
    print(f"Loading JD: {jd_path}...")
    with open(jd_path, "r", encoding="utf-8") as f:
        jd_text = f.read()
    jd_kw = extract_keywords_from_jd(jd_text)

    print("Running full analysis...")

    # Run the full analysis
    results = full_analysis(
        resume_kw["ALL_KEYWORDS"],
        jd_kw,
        sections
    )

    # Print the report
    print_full_report(results)

    # ── Bonus: test against multiple JDs ──────────────────────
    print("\n\n" + "=" * 60)
    print("  📂 TESTING AGAINST ALL YOUR JD FILES")
    print("=" * 60)

    jd_folder = "data/jds/"
    jd_files  = sorted([
        f for f in os.listdir(jd_folder) if f.endswith('.txt')
    ])

    for jd_file in jd_files:
        jd_path = os.path.join(jd_folder, jd_file)
        with open(jd_path, "r", encoding="utf-8") as f:
            jd_content = f.read()

        jd_keywords  = extract_keywords_from_jd(jd_content)
        gap          = analyze_gap(
                           resume_kw["ALL_KEYWORDS"],
                           jd_keywords
                       )

        print(f"\n  📄 {jd_file}")
        print(f"     Score : {gap['match_score']}%  "
              f"{get_ats_grade(gap['match_score'])}")
        print(f"     Matched : {gap['matched_keywords']}")
        print(f"     Missing : {gap['missing_keywords'][:5]}...")