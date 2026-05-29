# ─────────────────────────────────────────────────────────────
# similarity_engine.py
#
# Uses AI (sentence-transformers) to compute how semantically
# similar a resume and job description are — beyond keywords.
#
# Model used: all-MiniLM-L6-v2
# → Free, fast, runs on CPU, no GPU needed
# → Perfect for comparing resume vs JD text
# ─────────────────────────────────────────────────────────────

from sentence_transformers import SentenceTransformer, util

# Load the AI model once (takes ~5 seconds first time)
# After first load it gets cached — faster next time
print("Loading AI model... (takes a few seconds first time)")
model = SentenceTransformer('all-MiniLM-L6-v2')
print("AI model loaded successfully!")


def compute_similarity(text1, text2):
    """
    Takes two text strings.
    Returns a similarity score between 0.0 and 1.0

    0.0 = completely different
    1.0 = identical meaning

    Example:
        text1 = "Python developer with machine learning skills"
        text2 = "ML engineer experienced in Python"
        → returns ~0.82  (very similar)
    """
    # Convert both texts to embeddings (number vectors)
    embedding1 = model.encode(text1, convert_to_tensor=True)
    embedding2 = model.encode(text2, convert_to_tensor=True)

    # Calculate cosine similarity between the two vectors
    similarity = util.cos_sim(embedding1, embedding2)

    # Convert from tensor to a normal float number
    score = float(similarity[0][0])

    # Clamp between 0 and 1 just in case
    return round(max(0.0, min(1.0, score)), 4)


def compute_section_similarities(resume_sections, jd_text):
    """
    Compares each resume SECTION individually against the full JD.
    Shows which sections are most relevant to the job.

    Returns a dict like:
    {
        'skills':     0.72,
        'projects':   0.68,
        'experience': 0.45,
        'summary':    0.61,
        'education':  0.38
    }
    """
    section_scores = {}

    important_sections = [
        'skills', 'projects', 'experience',
        'summary', 'certifications', 'research'
    ]

    for section in important_sections:
        content = resume_sections.get(section, '').strip()
        if content and len(content) > 20:
            score = compute_similarity(content, jd_text)
            section_scores[section] = score

    return section_scores


def compute_final_ats_score(semantic_score, keyword_score):
    """
    Combines the semantic AI score and keyword match score
    into one final ATS score out of 100.

    Weights:
    - Semantic similarity = 50% (the AI understanding part)
    - Keyword match score = 50% (exact keyword matching)

    Both inputs should be 0–100 scale.
    """
    semantic_100 = semantic_score * 100   # convert 0-1 to 0-100

    final = (semantic_100 * 0.50) + (keyword_score * 0.50)
    return round(final, 1)


def get_semantic_grade(score):
    """
    Converts semantic similarity score (0-1) into a label.
    """
    if score >= 0.75:
        return "🟢 Highly relevant — strong semantic match"
    elif score >= 0.55:
        return "🟡 Moderately relevant — decent semantic match"
    elif score >= 0.35:
        return "🟠 Somewhat relevant — weak semantic match"
    else:
        return "🔴 Low relevance — resume content very different from JD"


def analyse_skill_synonyms(resume_keywords, jd_keywords):
    """
    Uses the AI model to find JD keywords that are
    SEMANTICALLY similar to resume keywords
    even if the exact words don't match.

    Example:
        JD has 'machine learning'
        Resume has 'ML'  or  'deep learning'
        → These are semantically similar → flag as soft match
    """
    soft_matches = []
    hard_missing = []

    resume_set = set(resume_keywords)
    jd_set     = set(jd_keywords)

    # Already exactly matched — skip these
    exact_matched = resume_set & jd_set
    truly_missing = jd_set - resume_set

    for jd_kw in truly_missing:
        best_score   = 0.0
        best_resume_kw = None

        for res_kw in resume_keywords:
            if res_kw in exact_matched:
                continue
            sim = compute_similarity(jd_kw, res_kw)
            if sim > best_score:
                best_score     = sim
                best_resume_kw = res_kw

        # If similarity > 0.6, it's a soft match
        if best_score >= 0.60 and best_resume_kw:
            soft_matches.append({
                "jd_keyword"    : jd_kw,
                "resume_keyword": best_resume_kw,
                "similarity"    : round(best_score, 2),
                "note": f"'{best_resume_kw}' in resume ≈ "
                        f"'{jd_kw}' in JD"
            })
        else:
            hard_missing.append(jd_kw)

    return {
        "exact_matched": sorted(exact_matched),
        "soft_matches" : soft_matches,
        "hard_missing" : sorted(hard_missing)
    }


# ══════════════════════════════════════════════════════════════
# TEST — run this file directly
# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":

    import sys
    import os
    sys.path.append(os.path.dirname(__file__))

    from pdf_parser        import extract_text
    from section_extractor import extract_sections
    from keyword_extractor import (extract_keywords_from_resume,
                                   extract_keywords_from_jd)
    from gap_analyzer      import calculate_match_score

    # ── Load resume ───────────────────────────────────────────
    print("\n" + "="*60)
    print("  SIMILARITY ENGINE — AI SEMANTIC ANALYSIS")
    print("="*60)

    resume_path = "data/resumes/resume1.pdf"
    print(f"\n📄 Loading resume: {resume_path}")
    raw_text  = extract_text(resume_path)
    sections  = extract_sections(raw_text)
    resume_kw = extract_keywords_from_resume(sections)

    # ── Load JD ───────────────────────────────────────────────
    jd_path = "data/jds/jd_01.txt"
    print(f"📋 Loading JD    : {jd_path}")
    with open(jd_path, "r", encoding="utf-8") as f:
        jd_text = f.read()
    jd_kw = extract_keywords_from_jd(jd_text)

    # ── Test 1: Overall semantic similarity ──────────────────
    print("\n" + "-"*60)
    print("TEST 1: Overall Resume vs JD Semantic Similarity")
    print("-"*60)

    # Combine all resume sections into one text
    full_resume_text = " ".join([
        v for v in sections.values() if isinstance(v, str)
    ])

    overall_score = compute_similarity(full_resume_text, jd_text)
    print(f"\n  🤖 Semantic similarity score : {overall_score}")
    print(f"  {get_semantic_grade(overall_score)}")

    # ── Test 2: Keyword match score (from Day 5) ──────────────
    print("\n" + "-"*60)
    print("TEST 2: Keyword Match Score (Day 5 method)")
    print("-"*60)

    keyword_score = calculate_match_score(
        resume_kw["ALL_KEYWORDS"], jd_kw
    )
    print(f"\n  🔑 Keyword match score : {keyword_score}%")

    # ── Test 3: Final combined ATS score ─────────────────────
    print("\n" + "-"*60)
    print("TEST 3: FINAL COMBINED ATS SCORE")
    print("-"*60)

    final_score = compute_final_ats_score(overall_score, keyword_score)
    print(f"\n  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"  🤖 Semantic score  : {round(overall_score*100,1)}%  (AI)")
    print(f"  🔑 Keyword score   : {keyword_score}%  (exact match)")
    print(f"  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"  🏆 FINAL ATS SCORE : {final_score} / 100")
    print(f"  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    # ── Test 4: Section-level similarity ─────────────────────
    print("\n" + "-"*60)
    print("TEST 4: Which resume sections match JD best?")
    print("-"*60)

    section_scores = compute_section_similarities(sections, jd_text)
    print()
    for section, score in sorted(
        section_scores.items(), key=lambda x: x[1], reverse=True
    ):
        bar_length = int(score * 30)
        bar        = "█" * bar_length + "░" * (30 - bar_length)
        print(f"  {section:<18} {bar} {round(score*100,1)}%")

    # ── Test 5: Smart synonym matching ───────────────────────
    print("\n" + "-"*60)
    print("TEST 5: Smart Synonym Matching (the IP component)")
    print("-"*60)

    synonym_results = analyse_skill_synonyms(
        resume_kw["ALL_KEYWORDS"], jd_kw
    )

    print(f"\n  ✅ Exact matches  : "
          f"{synonym_results['exact_matched']}")

    print(f"\n  🔄 Soft matches (semantically similar but "
          f"different words):")
    if synonym_results["soft_matches"]:
        for match in synonym_results["soft_matches"]:
            print(f"     → {match['note']}  "
                  f"(similarity: {match['similarity']})")
    else:
        print("     None found")

    print(f"\n  ❌ Hard missing   : "
          f"{synonym_results['hard_missing']}")

    # ── Test 6: Quick test across all JDs ────────────────────
    print("\n" + "-"*60)
    print("TEST 6: Final ATS scores across ALL your JD files")
    print("-"*60 + "\n")

    jd_folder = "data/jds/"
    jd_files  = sorted([
        f for f in os.listdir(jd_folder) if f.endswith(".txt")
    ])

    for jd_file in jd_files:
        path = os.path.join(jd_folder, jd_file)
        with open(path, "r", encoding="utf-8") as f:
            jd_content = f.read()

        jd_keywords   = extract_keywords_from_jd(jd_content)
        sem_score     = compute_similarity(full_resume_text,
                                           jd_content)
        kw_score      = calculate_match_score(
                            resume_kw["ALL_KEYWORDS"],
                            jd_keywords
                        )
        final         = compute_final_ats_score(sem_score, kw_score)

        print(f"  📄 {jd_file:<20} "
              f"Semantic: {round(sem_score*100,1)}%  "
              f"Keywords: {kw_score}%  "
              f"→ FINAL: {final}/100")