import spacy
import re
import json
import os

# Load the skill graph
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL_GRAPH_PATH = os.path.join(
    os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)
    )),
    "skill_graph.json"
)

def load_skill_graph():
    try:
        print(f"Loading skill graph from: {SKILL_GRAPH_PATH}")

        with open(SKILL_GRAPH_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    except FileNotFoundError:
        print("Warning: skill_graph.json not found.")
        return {}

    except json.JSONDecodeError as e:
        print(f"JSON Error: {e}")
        return {}

SKILL_GRAPH = load_skill_graph()

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


import re

def clean_text_for_extraction(text):
    """
    Cleans raw text before keyword extraction:
    - Replaces newlines/tabs with spaces
    - Collapses multiple spaces
    - Removes weird unicode artifacts
    """
    if not text:
        return ""
    # Replace newlines, tabs, carriage returns with space
    text = re.sub(r'[\n\r\t]+', ' ', text)
    # Remove non-ascii junk characters (â€~ etc)
    text = text.encode('ascii', errors='ignore').decode('ascii')
    # Collapse multiple spaces
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def is_valid_keyword(phrase):
    """
    Filters out garbage keywords:
    - Contains newline/tab characters
    - Too long (likely concatenated words)
    - Contains weird characters
    - Single very long word with no spaces (concatenation bug)
    """
    if not phrase or not phrase.strip():
        return False

    # Reject anything with newlines/tabs still in it
    if '\n' in phrase or '\t' in phrase or '\\' in phrase:
        return False

    words = phrase.split()

    # Reject phrases longer than 3 words
    if len(words) > 3:
        return False

    # Reject if any single word is unreasonably long
    # (concatenation bug produces words like
    # "developmentpostgresqlarchitectural" = 30+ chars)
    for w in words:
        if len(w) > 18:
            return False

    # Reject if phrase has weird symbols
    if re.search(r'[^\w\s\-\+\.#]', phrase):
        return False

    # Reject very short noise (single/double letters)
    if len(phrase.strip()) < 2:
        return False

    return True

# Common English words/phrases that are NEVER skills,
# even if spaCy thinks they're noun phrases
GENERIC_NOISE = {
    'build', 'design', 'service', 'services', 'support',
    'monitor', 'review', 'change', 'content', 'analysis',
    'analytics', 'reporting', 'tasks', 'features', 'feature',
    'requirements', 'implementation', 'maintenance',
    'documentation', 'education', 'quality', 'availability',
    'compliance', 'department', 'metrics', 'pipelines',
    'frameworks', 'libraries', 'techniques', 'concepts',
    'standards', 'practices', 'platforms', 'tools',
    'systems', 'applications', 'application', 'developers',
    'engineering', 'product', 'products', 'industry',
    'role', 'process', 'processes', 'performance',
    'optimization', 'collaboration', 'communication',
    'communication skills', 'good communication',
    'problem-solving', 'reliability', 'scalability',
    'security', 'monitoring', 'integration', 'deployment',
    'attitude', 'passion', 'ownership', 'curiosity',
    'comfort', 'exposure', 'familiarity', 'strong',
    'strong experience', 'deep knowledge', 'advanced proficiency',
    'hands-on experience', 'proficiency', 'expertise',
    'your expertise', 'deep expertise', 'minimum',
    'eg', 'co', 'date', 'general', 'others', 'other',
    'team', 'teams', 'clients', 'client', 'stakeholders',
    'developers', 'applicants', 'candidate', 'candidates',
}


def is_likely_real_skill(phrase, jd_or_resume_text=""):
    """
    Stricter check: returns True only if phrase looks
    like a genuine technical skill/tool/technology,
    not generic business English.

    A phrase passes if:
    - it's in TECH_SKILLS, OR
    - it contains a tech-sounding token (capitalised
      product name pattern, version number, or known
      tech suffix), OR
    - it's a known skill-graph canonical term
    """
    phrase_lower = phrase.lower().strip()

    if phrase_lower in GENERIC_NOISE:
        return False

    # Already in master tech list -> always valid
    if phrase_lower in TECH_SKILLS:
        return True

    # Check against skill graph canonical terms
    for domain_key, domain_data in SKILL_GRAPH.items():
        if domain_key == "_metadata":
            continue
        for mapping in domain_data.get("mappings", []):
            canonical = [
                c.lower() for c in
                mapping.get("canonical", [])
            ]
            if phrase_lower in canonical:
                return True

    # Tech-sounding patterns: contains digits, dots,
    # or known tech suffixes/prefixes
    tech_patterns = [
        r'\b(api|apis|sdk|sql|ai|ml|nlp|llm|llms|aws|gcp|'
        r'azure|css|html|js|ci|cd|jwt|oauth|orm|etl|ocr|'
        r'idp|nist|ceh|cve|cvss|sbom)\b',
        r'\d',                      # contains a digit
        r'\.(js|py|io|net)\b',      # file-extension-like
        r'(framework|library|platform|database|engine|'
        r'pipeline|architecture)$',
    ]
    for pat in tech_patterns:
        if re.search(pat, phrase_lower):
            # but still reject if it's a generic noise
            # phrase containing those words
            generic_with_tech = [
                'engineering - software', 'qa employment type',
            ]
            if phrase_lower not in generic_with_tech:
                return True

    return False


def extract_keywords_from_text(text):
    """
    Main function — takes any text string,
    returns a list of CLEAN skill keywords found in it.
    """

    # Step 0: CLEAN the text first
    text = clean_text_for_extraction(text)
    text_lower = text.lower()

    found_skills = set()

    # ── Method 1: Match against master skills list ──────────────
    for skill in TECH_SKILLS:
        pattern = r'\b' + re.escape(skill) + r'\b'
        if re.search(pattern, text_lower):
            found_skills.add(skill)

    # ── Method 2: spaCy noun phrase extraction (filtered) ────────
    doc = nlp(text[:10000])

    skip_words = {
        'i', 'we', 'the', 'a', 'an', 'this', 'that',
        'my', 'our', 'your', 'their', 'its', 'is', 'are',
        'was', 'were', 'be', 'been', 'have', 'has', 'had',
        'will', 'would', 'could', 'should', 'may', 'might',
        'team', 'role', 'position', 'job', 'work', 'company',
        'year', 'years', 'month', 'day', 'time', 'experience',
        'knowledge', 'understanding', 'ability', 'skill',
        'candidate', 'applicant', 'looking', 'seeking',
        'other', 'end', 'exp', 'law', 'this job posting',
        'the company website', 'the latest information',
        'job description', 'full time', 'part time',
        'preferred', 'related fields', 'the same',
        'a fast-paced environment', 'disclaimer',
        'external source', 'this position', 'permanent role category', 'qa employment type',
        'any graduate pg', 'consulting department',
        'management consulting department', 'it services',
        'engineering - software', 'role details',
        'key responsibilities', 'required skills',
        'required candidate profile', 'other education ug',
        'other industry type', 'any postgraduate doctorate',
        'any specialization', 'any specialization pg',
        'minimum qualifications', 'preferred qualifications',
        'minimum preferred qualifications', 'job description',
        'this job posting', 'this role', 'this position',
        'our growing team', 'our app', 'our mobile app',
        'a plus', 'a strong plus', 'good communication',
        'familiarity', 'proficiency', 'availability',
        'the ideal candidate', 'bachelors', 'bachelor s degree',
        'masters degree', 'diploma', 'freshers', 'fresher',
        '2yr', 'date', 'india office', 'our bengaluru'
    }

    for chunk in doc.noun_chunks:
        phrase = chunk.text.lower().strip()
        phrase = re.sub(r'\s+', ' ', phrase)  # collapse spaces

        if phrase in skip_words:
            continue

        if not is_valid_keyword(phrase):
            continue

        # NEW: only add if it's a likely real skill
        if is_likely_real_skill(phrase):
            found_skills.add(phrase)

    return sorted(list(found_skills))


def extract_keywords_from_resume(resume_sections):
    """
    Takes the sections dictionary from section_extractor.py
    and extracts keywords from the most important sections.
    NOW includes skill graph normalization automatically.
    Returns keywords per section AND a combined total list.
    """

    results      = {}
    all_keywords = set()

    # Most important sections for keyword matching
    important_sections = [
        'skills', 'experience', 'projects',
        'summary', 'certifications', 'research'
    ]

    for section in important_sections:
        section_text = resume_sections.get(section, '')
        if section_text.strip():
            # Step 1 — extract raw keywords using spaCy + master list
            raw_keywords = extract_keywords_from_text(section_text)

            # Step 2 — normalize using skill graph (NEW)
            normalized   = normalize_keywords(raw_keywords)

            results[section] = normalized
            all_keywords.update(normalized)

    results['ALL_KEYWORDS']            = sorted(list(all_keywords))
    results['ALL_KEYWORDS_RAW_COUNT']  = len(all_keywords)

    return results


def extract_keywords_from_jd(jd_text):
    """
    Takes a job description text string,
    extracts keywords AND normalizes them.
    """
    raw = extract_keywords_from_text(jd_text)
    return normalize_keywords(raw)


def extract_keywords_from_jd(jd_text):
    """
    Takes a job description text string
    and returns the keywords found.
    Simple wrapper around the main function.
    """
    return extract_keywords_from_text(jd_text)

def normalize_keywords(keywords):
    """
    Takes a list of keywords and expands them using
    the skill graph — informal terms get replaced
    with their canonical equivalents.

    Example:
        Input:  ['ml', 'used git', 'dsa']
        Output: ['machine learning', 'ml algorithms',
                 'git', 'version control', 'github',
                 'data structures', 'algorithms']
    """
    if not SKILL_GRAPH:
        return keywords

    expanded = set(keywords)

    for domain_key, domain_data in SKILL_GRAPH.items():
        if domain_key == "_metadata":
            continue

        mappings = domain_data.get("mappings", [])
        for mapping in mappings:
            informal = mapping.get("informal", "").lower()
            canonical = mapping.get("canonical", [])

            # Check if any keyword matches this informal term
            for kw in keywords:
                kw_lower = kw.lower()

                if (kw_lower == informal or
                        informal in kw_lower or
                        kw_lower in informal):

                    # Add all canonical terms
                    for c in canonical:
                        expanded.add(c)

    return sorted(list(expanded))

# ── Keyword category groups ───────────────────────────────────
KEYWORD_CATEGORIES = {
    "Cloud & DevOps": [
        "aws", "azure", "gcp", "google cloud", "docker",
        "kubernetes", "ci/cd", "devops", "terraform",
        "jenkins", "heroku", "render", "vercel", "cloud",
        "cloud platforms", "cloud computing",
    ],
    "Backend": [
        "flask", "django", "fastapi", "spring boot",
        "node.js", "express", "rest api", "api development",
        "backend development", "microservices", "graphql",
        "nginx", "redis", "celery", "rabbitmq",
    ],
    "Frontend": [
        "react", "angular", "vue", "vue.js", "javascript",
        "typescript", "html", "css", "bootstrap", "tailwind",
        "next.js", "jquery", "webpack",
    ],
    "Database": [
        "sql", "mysql", "postgresql", "mongodb", "sqlite",
        "oracle", "redis", "cassandra", "dynamodb", "orm",
        "database", "nosql", "firebase",
    ],
    "AI / ML": [
        "machine learning", "deep learning", "nlp",
        "natural language processing", "tensorflow",
        "pytorch", "scikit-learn", "keras", "transformers",
        "computer vision", "llm", "llms", "generative ai",
        "langchain", "openai api", "huggingface",
        "model training", "model deployment",
    ],
    "Data": [
        "pandas", "numpy", "matplotlib", "seaborn",
        "tableau", "power bi", "data analysis",
        "data science", "data visualization", "excel",
        "statistics", "etl", "spark", "hadoop",
        "data engineering", "dax", "looker",
    ],
    "Security": [
        "cybersecurity", "cyber security", "nist",
        "penetration testing", "vapt", "siem",
        "vulnerability management", "ceh", "ethical hacking",
        "network security", "owasp", "firewall", "soc",
    ],
    "Languages": [
        "python", "java", "javascript", "c++", "c",
        "golang", "rust", "kotlin", "swift", "php",
        "ruby", "scala", "r", "matlab",
    ],
    "Tools & Practices": [
        "git", "github", "jira", "agile", "scrum",
        "linux", "bash", "system design", "architecture",
        "oop", "dsa", "data structures", "algorithms",
        "unit testing", "tdd", "figma",
    ],
}


def categorize_keywords(keyword_list):
    """
    Takes a flat list of keywords and returns a dict of
    { category_name: [keywords] } with only non-empty
    categories. Keywords that don't match any category
    go into 'Other'.
    """
    categorized = {cat: [] for cat in KEYWORD_CATEGORIES}
    categorized["Other"] = []
    assigned = set()

    for kw in keyword_list:
        kw_lower = kw.strip().lower()
        found = False
        for cat, terms in KEYWORD_CATEGORIES.items():
            if kw_lower in terms:
                categorized[cat].append(kw)
                assigned.add(kw_lower)
                found = True
                break
        if not found:
            categorized["Other"].append(kw)

    # Remove empty categories and 'Other' if empty
    result = {
        cat: kws for cat, kws in categorized.items()
        if kws
    }
    return result

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