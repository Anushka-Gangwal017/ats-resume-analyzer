# ─────────────────────────────────────────────────────────────
# suggestion_engine.py
#
# Dedicated suggestion engine.
# Takes gap analysis results and generates
# specific, actionable resume improvement advice.
# ─────────────────────────────────────────────────────────────


# ── Strong action verbs by category ──────────────────────────
STRONG_VERBS = {
    "built"       : ["developed", "created", "engineered",
                     "architected", "coded", "programmed"],
    "improved"    : ["optimised", "enhanced", "upgraded",
                     "streamlined", "accelerated"],
    "analysed"    : ["investigated", "evaluated", "assessed",
                     "examined", "benchmarked"],
    "led"         : ["managed", "directed", "coordinated",
                     "organised", "spearheaded"],
    "researched"  : ["investigated", "explored", "studied",
                     "published", "co-authored"],
    "implemented" : ["deployed", "integrated", "executed",
                     "launched", "shipped"],
    "designed"    : ["architected", "prototyped", "wireframed",
                     "modelled", "structured"],
    "tested"      : ["validated", "verified", "benchmarked",
                     "evaluated", "documented"],
}

# ── Weak verbs to replace ─────────────────────────────────────
WEAK_VERBS = {
    "helped"          : "Use 'assisted in developing' or "
                        "'contributed to building' instead",
    "assisted"        : "Say what you specifically did — "
                        "'implemented X' or 'built Y'",
    "worked on"       : "Be specific — 'developed', "
                        "'built', or 'implemented'",
    "was responsible" : "Start with action — "
                        "'led', 'managed', 'developed'",
    "participated"    : "Say your contribution — "
                        "'contributed to', 'built', 'designed'",
    "involved in"     : "Describe your role directly — "
                        "'developed', 'implemented', 'tested'",
    "did"             : "Use a specific verb — "
                        "'built', 'created', 'analysed'",
    "made"            : "Use 'developed', 'built', "
                        "or 'engineered' instead",
    "tried"           : "Remove uncertainty — "
                        "state what you achieved",
    "helped with"     : "Be specific about your contribution",
}

# ── Keyword priority tiers ────────────────────────────────────
# Tier 1 = critical skills that must be in resume
# Tier 2 = important but can be in projects
# Tier 3 = good to have
TIER_1_SKILLS = [
    "python", "sql", "java", "javascript", "c++",
    "machine learning", "deep learning", "nlp",
    "cybersecurity", "data analysis", "rest api",
    "git", "linux", "flask", "django", "react",
    "aws", "docker", "pandas", "numpy", "scikit-learn",
    "tensorflow", "pytorch", "mysql", "postgresql",
]

TIER_2_SKILLS = [
    "html", "css", "mongodb", "redis", "fastapi",
    "kubernetes", "jenkins", "tableau", "power bi",
    "github", "agile", "scrum", "vapt", "network security",
    "data structures", "algorithms",
]


def generate_keyword_suggestions(missing_keywords,
                                  soft_matches=None):
    """
    Generates tiered keyword suggestions.
    Tier 1 missing = critical, fix immediately.
    Tier 2 missing = important, fix soon.
    """
    suggestions     = []
    soft_covered    = set()

    if soft_matches:
        for m in soft_matches:
            soft_covered.add(m.get("jd_keyword", ""))

    tier1_missing = []
    tier2_missing = []
    other_missing = []

    for kw in missing_keywords:
        if kw in soft_covered:
            suggestions.append({
                "priority": "LOW",
                "type"    : "soft_match",
                "message" : f"'{kw}' is semantically covered "
                             f"but add the exact term too",
                "keyword" : kw,
            })
            continue

        if kw in TIER_1_SKILLS:
            tier1_missing.append(kw)
        elif kw in TIER_2_SKILLS:
            tier2_missing.append(kw)
        else:
            other_missing.append(kw)

    # Tier 1 — critical
    for kw in tier1_missing:
        suggestions.append({
            "priority": "HIGH",
            "type"    : "missing_keyword",
            "message" : f"🔴 CRITICAL: Add '{kw}' to your "
                         f"Skills section — this is a Tier 1 "
                         f"skill required by this JD",
            "keyword" : kw,
            "where"   : "Skills section",
        })

    # Tier 2 — important
    for kw in tier2_missing:
        suggestions.append({
            "priority": "MEDIUM",
            "type"    : "missing_keyword",
            "message" : f"🟡 IMPORTANT: Add '{kw}' to your "
                         f"resume — appears in JD",
            "keyword" : kw,
            "where"   : "Skills or Projects section",
        })

    # Other
    for kw in other_missing[:5]:
        suggestions.append({
            "priority": "LOW",
            "type"    : "missing_keyword",
            "message" : f"📝 Consider adding '{kw}' — "
                         f"mentioned in JD",
            "keyword" : kw,
            "where"   : "Anywhere relevant",
        })

    return suggestions


def generate_section_suggestions(section_report):
    """
    Generates suggestions for weak or missing sections.
    """
    suggestions = []

    priority_order = [
        "skills", "experience", "projects",
        "summary", "education", "certifications"
    ]

    for section in priority_order:
        if section not in section_report:
            continue

        info = section_report[section]

        if "Missing" in info["status"]:
            suggestions.append({
                "priority": "HIGH",
                "type"    : "missing_section",
                "message" : f"🚨 NO {section.upper()} SECTION "
                             f"found — add one immediately. "
                             f"ATS systems specifically look "
                             f"for this section heading.",
                "section" : section,
            })

        elif "Weak" in info["status"]:
            length = info["length"]
            tips   = {
                "skills"    : "List at least 10–15 skills "
                               "with specific tools and "
                               "technologies",
                "experience": "Add bullet points describing "
                               "what you built, not just "
                               "where you worked",
                "projects"  : "Each project needs: what you "
                               "built, tech used, and one "
                               "measurable outcome",
                "summary"   : "Write 3–4 lines: who you are, "
                               "your strongest skill, and "
                               "what you are looking for",
            }
            tip = tips.get(section,
                           "Expand with more detail")
            suggestions.append({
                "priority": "MEDIUM",
                "type"    : "weak_section",
                "message" : f"⚠️  {section.upper()} section "
                             f"is too short ({length} chars). "
                             f"Tip: {tip}",
                "section" : section,
            })

    return suggestions


def check_action_verbs_detailed(resume_sections):
    """
    Detailed action verb analysis.
    Checks bullet points in Experience and Projects.
    Returns specific rewrite suggestions.
    """
    results = {
        "weak_found"     : [],
        "strong_found"   : [],
        "rewrites"       : [],
        "overall_verdict": "",
    }

    text = (
        resume_sections.get("experience", "") + " " +
        resume_sections.get("projects",   "")
    ).lower()

    # Check for weak verbs
    for weak_verb, advice in WEAK_VERBS.items():
        if weak_verb in text:
            results["weak_found"].append(weak_verb)
            results["rewrites"].append({
                "weak_verb": weak_verb,
                "advice"   : advice,
            })

    # Check for strong verbs
    for category, verb_list in STRONG_VERBS.items():
        if category in text:
            results["strong_found"].append(category)
        for v in verb_list:
            if v in text:
                results["strong_found"].append(v)

    results["strong_found"] = list(set(results["strong_found"]))

    # Overall verdict
    weak_count   = len(results["weak_found"])
    strong_count = len(results["strong_found"])

    if weak_count == 0 and strong_count >= 3:
        results["overall_verdict"] = (
            "✅ Excellent — strong action verbs throughout"
        )
    elif weak_count == 0:
        results["overall_verdict"] = (
            "🟡 Good — no weak verbs, but add more "
            "strong action verbs to bullet points"
        )
    elif weak_count <= 2:
        results["overall_verdict"] = (
            f"🟠 Needs work — found {weak_count} weak "
            f"verb(s). See rewrites below."
        )
    else:
        results["overall_verdict"] = (
            f"🔴 Poor — found {weak_count} weak verbs. "
            f"Rewrite bullet points with strong action verbs."
        )

    return results


def check_quantification(resume_sections):
    """
    Checks if resume has measurable outcomes.
    e.g. '100+ samples', '9.08 CGPA', '600M+ records'
    Recruiters and ATS both prefer quantified claims.
    """
    import re

    text = " ".join([
        v for v in resume_sections.values()
        if isinstance(v, str)
    ])

    # Look for numbers + units
    number_pattern = r'\b\d+[\+\%\w]*\b'
    numbers_found  = re.findall(number_pattern, text)

    # Filter out years (2024, 2025 etc)
    metrics = [
        n for n in numbers_found
        if not (len(n) == 4 and n.startswith("20"))
    ]

    result = {
        "metrics_found" : metrics,
        "count"         : len(metrics),
    }

    if len(metrics) >= 5:
        result["verdict"] = (
            f"✅ Good quantification — {len(metrics)} "
            f"numbers/metrics found: {metrics[:6]}"
        )
    elif len(metrics) >= 2:
        result["verdict"] = (
            f"🟡 Some quantification ({len(metrics)} "
            f"metrics). Add more numbers — e.g. "
            f"'tested on 100+ samples', '95% accuracy'"
        )
    else:
        result["verdict"] = (
            "🔴 No quantification found. Add numbers "
            "to your bullet points — metrics make "
            "your resume 40% more impactful."
        )

    return result


def generate_full_suggestions(gap_report,
                               section_report,
                               resume_sections,
                               soft_matches=None):
    """
    Master function — generates ALL suggestions
    from all checks in one call.
    Returns a structured list sorted by priority.
    """

    all_suggestions = []

    # 1. Keyword suggestions
    kw_sugg = generate_keyword_suggestions(
        gap_report.get("missing_keywords", []),
        soft_matches
    )
    all_suggestions.extend(kw_sugg)

    # 2. Section suggestions
    sec_sugg = generate_section_suggestions(section_report)
    all_suggestions.extend(sec_sugg)

    # 3. Action verb check
    verb_results = check_action_verbs_detailed(resume_sections)
    if verb_results["rewrites"]:
        for rw in verb_results["rewrites"]:
            all_suggestions.append({
                "priority": "MEDIUM",
                "type"    : "weak_verb",
                "message" : f"✏️  Replace '{rw['weak_verb']}' "
                             f"— {rw['advice']}",
                "verb"    : rw["weak_verb"],
            })

    # 4. Quantification check
    quant = check_quantification(resume_sections)
    if "🔴" in quant["verdict"] or "🟡" in quant["verdict"]:
        all_suggestions.append({
            "priority": "MEDIUM",
            "type"    : "quantification",
            "message" : quant["verdict"],
        })

    # Sort: HIGH first, then MEDIUM, then LOW
    priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    all_suggestions.sort(
        key=lambda x: priority_order.get(
            x.get("priority", "LOW"), 2
        )
    )

    return {
        "suggestions"   : all_suggestions,
        "verb_analysis" : verb_results,
        "quant_analysis": quant,
        "total_count"   : len(all_suggestions),
        "high_priority" : sum(
            1 for s in all_suggestions
            if s.get("priority") == "HIGH"
        ),
    }


# ══════════════════════════════════════════════════════════════
# TEST
# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":

    import sys
    import os
    sys.path.append(os.path.dirname(__file__))

    from pdf_parser        import extract_text
    from section_extractor import extract_sections
    from keyword_extractor import (extract_keywords_from_resume,
                                   extract_keywords_from_jd)
    from gap_analyzer      import (analyze_gap,
                                   analyze_section_strength)

    print("\n" + "="*60)
    print("  SUGGESTION ENGINE TEST")
    print("="*60)

    resume_path = "data/resumes/resume1.pdf"
    jd_path     = "data/jds/jd_01.txt"

    raw_text   = extract_text(resume_path)
    sections   = extract_sections(raw_text)
    resume_kw  = extract_keywords_from_resume(sections)

    with open(jd_path, "r", encoding="utf-8") as f:
        jd_text = f.read()
    jd_kw = extract_keywords_from_jd(jd_text)

    gap_report     = analyze_gap(
        resume_kw["ALL_KEYWORDS"], jd_kw
    )
    section_report = analyze_section_strength(sections)

    full = generate_full_suggestions(
        gap_report, section_report, sections
    )

    print(f"\n  Total suggestions : {full['total_count']}")
    print(f"  High priority     : {full['high_priority']}")

    print("\n" + "-"*60)
    print("  ALL SUGGESTIONS (sorted by priority):")
    print("-"*60)
    for i, s in enumerate(full["suggestions"], 1):
        p = s.get("priority","")
        print(f"\n  [{p}] {i}. {s['message']}")

    print("\n" + "-"*60)
    print("  VERB ANALYSIS:")
    print("-"*60)
    va = full["verb_analysis"]
    print(f"  {va['overall_verdict']}")
    print(f"  Strong verbs: {va['strong_found']}")

    print("\n" + "-"*60)
    print("  QUANTIFICATION CHECK:")
    print("-"*60)
    print(f"  {full['quant_analysis']['verdict']}")

    print("\n" + "="*60 + "\n")