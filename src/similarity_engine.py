# ─────────────────────────────────────────────────────────────
# similarity_engine.py  —  FIXED VERSION
# Key fix: analyse_skill_synonyms is now limited to
# prevent infinite hanging in Flask
# ─────────────────────────────────────────────────────────────

SentenceTransformer = None
util = None
_model = None


def get_model():
    """Load model only when first needed."""
    global _model, SentenceTransformer, util

    if _model is None:
        print("Loading AI model...")

        from sentence_transformers import SentenceTransformer as ST
        from sentence_transformers import util as st_util

        SentenceTransformer = ST
        util = st_util

        _model = SentenceTransformer('all-MiniLM-L6-v2')

        print("Model loaded!")

    return _model


def compute_similarity(text1, text2):
    """
    Returns cosine similarity score between
    two texts — 0.0 (different) to 1.0 (identical).
    """
    try:
        e1 = get_model().encode(
            str(text1)[:2000],   # cap length
            convert_to_tensor=True
        )
        e2 = get_model().encode(
            str(text2)[:2000],
            convert_to_tensor=True
        )
        score = float(util.cos_sim(e1, e2)[0][0])
        return round(max(0.0, min(1.0, score)), 4)
    except Exception as ex:
        print(f"  similarity error: {ex}")
        return 0.0


def compute_section_similarities(resume_sections, jd_text):
    """
    Compares each resume section against the JD.
    Returns dict of section → similarity score.
    """
    section_scores = {}
    important = [
        'skills', 'projects', 'experience',
        'summary', 'certifications', 'research'
    ]
    for section in important:
        content = resume_sections.get(section, '').strip()
        if content and len(content) > 20:
            try:
                score = compute_similarity(content, jd_text)
                section_scores[section] = score
            except Exception:
                pass
    return section_scores


def compute_final_ats_score(semantic_score, keyword_score):
    """
    Combines semantic (0-1) and keyword (0-100) scores.
    Returns final score out of 100.
    """
    try:
        sem_100 = float(semantic_score) * 100
        kw_100  = float(keyword_score)
        final   = (sem_100 * 0.50) + (kw_100 * 0.50)
        return round(min(100.0, max(0.0, final)), 1)
    except Exception:
        return 0.0


def get_semantic_grade(score):
    """Grade label for semantic similarity score (0-1)."""
    if score >= 0.75:
        return "🟢 Highly relevant — strong semantic match"
    elif score >= 0.55:
        return "🟡 Moderately relevant — decent semantic match"
    elif score >= 0.35:
        return "🟠 Somewhat relevant — weak semantic match"
    else:
        return "🔴 Low relevance — resume very different from JD"


def analyse_skill_synonyms(resume_keywords, jd_keywords):
    """
    Finds JD keywords that are semantically similar
    to resume keywords even when exact words differ.

    FIXED: limited to 10 JD keywords × 15 resume keywords
    to prevent hanging in Flask.
    """
    soft_matches = []
    hard_missing = []

    resume_set    = set(resume_keywords)
    jd_set        = set(jd_keywords)
    exact_matched = resume_set & jd_set
    truly_missing = jd_set - resume_set

    # ── CRITICAL LIMIT — prevents hanging ────────────────────
    missing_list = list(truly_missing)[:10]
    resume_list  = [
        k for k in list(resume_keywords)[:15]
        if k not in exact_matched
    ]

    for jd_kw in missing_list:
        best_score     = 0.0
        best_resume_kw = None

        for res_kw in resume_list:
            try:
                sim = compute_similarity(jd_kw, res_kw)
                if sim > best_score:
                    best_score     = sim
                    best_resume_kw = res_kw
            except Exception:
                continue

        if best_score >= 0.60 and best_resume_kw:
            soft_matches.append({
                "jd_keyword"    : jd_kw,
                "resume_keyword": best_resume_kw,
                "similarity"    : round(best_score, 2),
                "note"          : (
                    f"'{best_resume_kw}' in resume ≈ "
                    f"'{jd_kw}' in JD"
                ),
            })
        else:
            hard_missing.append(jd_kw)

    return {
        "exact_matched": sorted(exact_matched),
        "soft_matches" : soft_matches,
        "hard_missing" : sorted(hard_missing),
    }


# ── Quick self-test ────────────────────────────────────────────
if __name__ == "__main__":
    print("Testing similarity engine...")
    s = compute_similarity(
        "Python developer with machine learning skills",
        "ML engineer experienced in Python"
    )
    print(f"Test similarity: {s}  (expect ~0.75–0.85)")
    print("Done!")