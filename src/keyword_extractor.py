import spacy
import re

# Load the English language model
# This was downloaded on Day 2 setup
nlp = spacy.load("en_core_web_sm")


# ─────────────────────────────────────────────────────────────
# MASTER SKILLS LIST
# These are the tech skills we always want to detect
# even if spaCy misses them.
# Add more as you find them in real JDs!
# ─────────────────────────────────────────────────────────────
TECH_SKILLS = [
    # Programming languages
    "python", "java", "c++", "c#", "javascript", "typescript",
    "r", "golang", "kotlin", "swift", "ruby", "php", "scala",
    "bash", "shell scripting", "perl",

    # Web
    "html", "css", "react", "angular", "vue", "nodejs", "node.js",
    "django", "flask", "fastapi", "spring boot", "rest api",
    "restful api", "graphql", "bootstrap", "jquery",

    # Data & ML
    "machine learning", "deep learning", "artificial intelligence",
    "natural language processing", "nlp", "computer vision",
    "data analysis", "data science", "data engineering",
    "pandas", "numpy", "scikit-learn", "tensorflow", "pytorch",
    "keras", "matplotlib", "seaborn", "plotly", "tableau",
    "power bi", "excel", "statistics",

    # Databases
    "sql", "mysql", "postgresql", "mongodb", "sqlite",
    "nosql", "redis", "firebase", "oracle", "cassandra",

    # Cloud & DevOps
    "aws", "azure", "gcp", "google cloud", "docker", "kubernetes",
    "jenkins", "ci/cd", "terraform", "linux", "unix",
    "git", "github", "gitlab", "bitbucket", "version control",

    # Cybersecurity
    "cybersecurity", "network security", "ethical hacking",
    "penetration testing", "vapt", "vulnerability assessment",
    "kali linux", "metasploit", "nmap", "wireshark",
    "cryptography", "encryption", "firewall", "siem",
    "incident response", "risk assessment", "iso 27001",
    "nist", "owasp", "soc", "threat analysis",

    # Tools
    "vs code", "visual studio", "eclipse", "intellij",
    "jupyter", "postman", "jira", "confluence", "slack",
    "figma", "canva", "photoshop",

    # Concepts
    "object oriented programming", "oop", "data structures",
    "algorithms", "dsa", "system design", "api development",
    "agile", "scrum", "software development life cycle", "sdlc",
    "problem solving", "debugging", "unit testing",
]


def extract_keywords_from_text(text):
    """
    Main function — takes any text string,
    returns a list of skill keywords found in it.

    Works in two ways:
    1. Checks against our TECH_SKILLS master list
    2. Uses spaCy to find noun phrases we might have missed
    """

    text_lower = text.lower()
    found_skills = set()  # using set to avoid duplicates

    # ── Method 1: Match against master skills list ──────────────
    for skill in TECH_SKILLS:
        # Look for the skill as a whole word
        # (so "r" doesn't match inside "framework")
        pattern = r'\b' + re.escape(skill) + r'\b'
        if re.search(pattern, text_lower):
            found_skills.add(skill)

    # ── Method 2: spaCy noun phrase extraction ──────────────────
    doc = nlp(text[:10000])  # spaCy works best under 10000 chars

    for chunk in doc.noun_chunks:
        phrase = chunk.text.lower().strip()
        # Only keep phrases that are 1-3 words and look like skills
        words_in_phrase = phrase.split()
        if 1 <= len(words_in_phrase) <= 3:
            # Skip generic words that aren't skills
            skip_words = [
                'i', 'we', 'the', 'a', 'an', 'this', 'that',
                'my', 'our', 'your', 'their', 'its', 'is', 'are',
                'was', 'were', 'be', 'been', 'have', 'has', 'had',
                'will', 'would', 'could', 'should', 'may', 'might',
                'team', 'role', 'position', 'job', 'work', 'company',
                'year', 'years', 'month', 'day', 'time', 'experience',
                'knowledge', 'understanding', 'ability', 'skill',
                'candidate', 'applicant', 'looking', 'seeking',
            ]
            if phrase not in skip_words and len(phrase) > 2:
                found_skills.add(phrase)

    return sorted(list(found_skills))


def extract_keywords_from_resume(resume_sections):
    """
    Takes the sections dictionary from section_extractor.py
    and extracts keywords from the most important sections.
    Returns keywords per section AND a combined total list.
    """

    results = {}
    all_keywords = set()

    # We care most about these sections for keyword matching
    important_sections = ['skills', 'experience', 'projects',
                          'summary', 'certifications', 'research']

    for section in important_sections:
        section_text = resume_sections.get(section, '')
        if section_text.strip():
            keywords = extract_keywords_from_text(section_text)
            results[section] = keywords
            all_keywords.update(keywords)

    results['ALL_KEYWORDS'] = sorted(list(all_keywords))
    return results


def extract_keywords_from_jd(jd_text):
    """
    Takes a job description text string
    and returns the keywords found.
    Simple wrapper around the main function.
    """
    return extract_keywords_from_text(jd_text)


# ══════════════════════════════════════════════════════════════
# TEST — run this file directly to see it working
# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":

    import sys
    import os
    sys.path.append(os.path.dirname(__file__))

    from pdf_parser import extract_text
    from section_extractor import extract_sections

    print("=" * 55)
    print("   KEYWORD EXTRACTOR — TEST RUN")
    print("=" * 55)

    # ── Test 1: Extract from YOUR resume ──────────────────────
    print("\n📄 Testing on YOUR resume...\n")
    resume_path = "data/resumes/resume1.pdf"
    raw_text = extract_text(resume_path)
    sections = extract_sections(raw_text)
    resume_keywords = extract_keywords_from_resume(sections)

    for section, keywords in resume_keywords.items():
        if keywords and section != 'ALL_KEYWORDS':
            print(f"\n  📌 {section.upper()} section keywords:")
            print(f"     {keywords}")

    print(f"\n  ✅ TOTAL unique keywords in resume: "
          f"{len(resume_keywords['ALL_KEYWORDS'])}")
    print(f"  📋 Full list: {resume_keywords['ALL_KEYWORDS']}")

    # ── Test 2: Extract from a sample Job Description ─────────
    print("\n" + "=" * 55)
    print("📋 Testing on a SAMPLE JOB DESCRIPTION...\n")

    sample_jd = """
    We are looking for a Python Developer Intern.

    Requirements:
    - Strong knowledge of Python and SQL
    - Experience with Flask or Django
    - Understanding of REST APIs and Git
    - Knowledge of machine learning basics
    - Familiarity with Linux and Docker
    - Good understanding of data structures and algorithms
    - Experience with pandas and numpy is a plus
    - Knowledge of cybersecurity fundamentals preferred

    Responsibilities:
    - Build and maintain Python-based web applications
    - Work with databases using SQL and PostgreSQL
    - Collaborate using Git and GitHub
    - Write clean, well-documented code
    """

    jd_keywords = extract_keywords_from_jd(sample_jd)
    print(f"  ✅ Keywords found in JD: {len(jd_keywords)}")
    print(f"  📋 JD Keywords: {jd_keywords}")

    # ── Test 3: Quick comparison ────────────────────────────────
    print("\n" + "=" * 55)
    print("🔍 QUICK COMPARISON: Resume vs JD\n")

    resume_set = set(resume_keywords['ALL_KEYWORDS'])
    jd_set = set(jd_keywords)

    matched = resume_set.intersection(jd_set)
    missing = jd_set - resume_set

    print(f"  ✅ MATCHED keywords: {sorted(matched)}")
    print(f"  ❌ MISSING from resume: {sorted(missing)}")
    print(f"\n  📊 Match score: "
          f"{round(len(matched)/len(jd_set)*100, 1)}% "
          f"({len(matched)} out of {len(jd_set)} JD keywords)")
    

    # ── Test 4: Test on your real JD files ─────────────────────
    print("\n" + "=" * 55)
    print("📁 Testing on YOUR real JD files...\n")

    import os
    jd_folder = "data/jds/"
    jd_files = [f for f in os.listdir(jd_folder) if f.endswith('.txt')]

    for jd_file in jd_files[:3]:   # test first 3 JDs
        jd_path = os.path.join(jd_folder, jd_file)
        with open(jd_path, 'r', encoding='utf-8') as f:
            jd_content = f.read()

        jd_kw = extract_keywords_from_jd(jd_content)
        print(f"  📄 {jd_file}: {len(jd_kw)} keywords → {jd_kw[:8]}...")