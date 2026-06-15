# ─────────────────────────────────────────────────────────────
# report_generator.py  —  Clean professional style
# Inspired by Jobscan's approach:
# clean typography, organized tables, clear sections
# No over-decoration, just clear readable data
# ─────────────────────────────────────────────────────────────

from fpdf import FPDF, XPos, YPos
from datetime import datetime


# ── Colour palette ─────────────────────────────────────────────
NAVY      = (15,  23,  42)
BLUE      = (37,  99,  235)
BLUE_MID  = (191, 219, 254)
BLUE_PALE = (239, 246, 255)
GREEN     = (22,  163, 74)
GREEN_PALE= (240, 253, 244)
GREEN_MID = (187, 247, 208)
RED       = (220, 38,  38)
RED_PALE  = (254, 242, 242)
RED_MID   = (254, 202, 202)
AMBER     = (217, 119, 6)
AMBER_PALE= (255, 251, 235)
GRAY_DARK = (55,  65,  81)
GRAY_MID  = (107, 114, 128)
GRAY_LIGHT= (209, 213, 219)
GRAY_PALE = (249, 250, 251)
WHITE     = (255, 255, 255)
BLACK     = (0,   0,   0)


def ct(text):
    """Clean text for Helvetica / latin-1."""
    if not text:
        return ""
    subs = {
        "\u2014": "-", "\u2013": "-",
        "\u2018": "'", "\u2019": "'",
        "\u201c": '"', "\u201d": '"',
        "\u2022": "-", "\u2026": "...",
        "\u00a0": " ",
    }
    for c, r in subs.items():
        text = text.replace(c, r)
    out = ""
    for ch in text:
        try:
            ch.encode("latin-1")
            out += ch
        except Exception:
            out += " "
    while "  " in out:
        out = out.replace("  ", " ")
    return out.strip()


class ResumeIQPDF(FPDF):
    def header(self):
        pass

    def footer(self):
        self.set_y(-11)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(*GRAY_MID)
        self.cell(
            0, 6,
            f"ResumeIQ  |  AI-powered ATS Analyzer  |  "
            f"Page {self.page_no()}  |  "
            f"{datetime.now().strftime('%d %b %Y')}",
            align="C"
        )


def generate_report(results, output_path):
    pdf = ResumeIQPDF()
    pdf.set_margins(15, 15, 15)
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()

    PW = 180   # printable width (210 - 15*2)

    # ── Extract data ──────────────────────────────────────────
    score       = float(results.get("final_score",    0))
    sem_score   = float(results.get("semantic_score", 0))
    kw_score    = float(results.get("keyword_score",  0))
    grade       = ct(results.get("final_grade",   ""))
    resume_fn   = ct(results.get("resume_filename","resume.pdf"))
    analysed_at = ct(results.get("analysed_at",   ""))
    jd_level    = ct(results.get("jd_level",      "Unknown"))
    jd_warning  = results.get("jd_warning")
    matched_kw  = [ct(str(k)) for k in
                   results.get("matched_keywords", [])]
    missing_kw  = [ct(str(k)) for k in
                   results.get("missing_keywords", [])]
    m_count     = int(results.get("matched_count", len(matched_kw)))
    x_count     = int(results.get("missing_count", len(missing_kw)))
    soft        = results.get("soft_matches", [])
    sec_kw      = results.get("section_keyword_scores", {})
    sec_report  = results.get("section_report", {})
    suggestions = results.get("suggestions", [])
    hp_count    = int(results.get("high_priority_count", 0))
    verb        = ct(results.get("verb_verdict",  ""))
    quant       = ct(results.get("quant_verdict", ""))

    if score >= 75:
        sc_fg, sc_bg = GREEN, GREEN_PALE
    elif score >= 50:
        sc_fg, sc_bg = AMBER, AMBER_PALE
    else:
        sc_fg, sc_bg = RED, RED_PALE

    level_colours = {
        "Entry":  (GREEN, GREEN_PALE),
        "Mid":    (AMBER, AMBER_PALE),
        "Senior": (RED,   RED_PALE),
        "Unknown":(GRAY_MID, GRAY_PALE),
    }
    lv_fg, lv_bg = level_colours.get(jd_level, (GRAY_MID, GRAY_PALE))

    # ── Helpers ───────────────────────────────────────────────

    def rule(thick=False, color=GRAY_LIGHT):
        pdf.set_draw_color(*color)
        pdf.set_line_width(0.6 if thick else 0.2)
        pdf.line(15, pdf.get_y(), 195, pdf.get_y())
        pdf.set_line_width(0.2)
        pdf.ln(3)

    def section_title(text, count=None):
        """Bold section heading like Jobscan uses."""
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(*NAVY)
        title = ct(text)
        if count is not None:
            pdf.cell(PW - 30, 7, title,
                     new_x=XPos.RIGHT, new_y=YPos.TOP)
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(*GRAY_MID)
            pdf.cell(30, 7, f"{count} items", align="R",
                     new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        else:
            pdf.cell(PW, 7, title,
                     new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        rule(thick=True, color=BLUE_MID)

    def row_2col(label, value,
                 label_w=70, row_h=5.5,
                 label_color=GRAY_DARK,
                 value_color=NAVY,
                 fill=False, fill_color=GRAY_PALE,
                 bold_value=False):
        """Two-column info row like Jobscan's tables."""
        if fill:
            pdf.set_fill_color(*fill_color)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*label_color)
        pdf.cell(label_w, row_h, ct(label),
                 fill=fill, border=0,
                 new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.set_font("Helvetica", "B" if bold_value else "", 9)
        pdf.set_text_color(*value_color)
        pdf.multi_cell(PW - label_w, row_h,
                       ct(str(value)),
                       fill=fill, border=0)
        if not ct(str(value)).count("\n"):
            pass  # multi_cell handles newlines

    def bar_row(label, pct, color,
                label_w=55, bar_w=90, row_h=6):
        """Horizontal bar row for scores."""
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*GRAY_DARK)
        y = pdf.get_y()
        pdf.cell(label_w, row_h, ct(label),
                 new_x=XPos.RIGHT, new_y=YPos.TOP)
        bx = pdf.get_x()
        by = y + 1.8
        # track
        pdf.set_fill_color(*GRAY_LIGHT)
        pdf.rect(bx, by, bar_w, 3, style="F")
        # fill
        fw = max(0, min(float(pct) / 100, 1)) * bar_w
        if fw > 0:
            pdf.set_fill_color(*color)
            pdf.rect(bx, by, fw, 3, style="F")
        # pct label
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*NAVY)
        pdf.set_xy(bx + bar_w + 3, y)
        pdf.cell(20, row_h, f"{pct}%",
                 new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def kw_table(keywords, fg, bg, cols=3):
        """Keyword table similar to Jobscan's skill table."""
        if not keywords:
            pdf.set_font("Helvetica", "I", 9)
            pdf.set_text_color(*GRAY_MID)
            pdf.cell(PW, 6, "None found",
                     new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            return
        col_w = PW / cols
        row_h = 5.8
        for i, kw in enumerate(keywords):
            col = i % cols
            if col == 0 and i > 0:
                pdf.ln(0)
            if col == 0:
                x = 15
            else:
                x = 15 + col * col_w

            row_num = i // cols
            fill = (row_num % 2 == 0)
            fill_c = GRAY_PALE if fill else WHITE

            pdf.set_fill_color(*fill_c)
            pdf.set_font("Helvetica", "", 8.5)
            pdf.set_text_color(*fg)
            pdf.set_xy(x, pdf.get_y())
            pdf.cell(col_w, row_h, f"  {ct(kw)}",
                     fill=True, border=0,
                     new_x=XPos.RIGHT if col < cols-1
                     else XPos.LMARGIN,
                     new_y=YPos.TOP if col < cols-1
                     else YPos.NEXT)
        pdf.ln(1)

    def status_icon(status):
        if "Good" in status:   return "[OK]"
        if "Weak" in status:   return "[!] "
        if "Missing" in status:return "[X] "
        return "[ ] "

    # ═══════════════════════════════════════════════════════════
    # PAGE 1 STARTS
    # ═══════════════════════════════════════════════════════════

    # ── TOP HEADER ────────────────────────────────────────────
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(*NAVY)
    pdf.cell(PW - 60, 10, "Match Report",
             new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*GRAY_MID)
    pdf.cell(60, 5, analysed_at, align="R",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*GRAY_MID)
    pdf.cell(60, 5, resume_fn[:50],
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(1)
    rule(thick=True, color=NAVY)

    # ── SCORE OVERVIEW (4 boxes like Jobscan top cards) ───────
    box_w   = PW / 4
    box_h   = 20
    y_boxes = pdf.get_y()

    box_data = [
        ("ATS Score",   f"{int(score)}/100", sc_fg, sc_bg),
        ("AI Semantic", f"{sem_score}%",      (109,40,217), (237,233,254)),
        ("Keywords",    f"{kw_score}%",        BLUE, BLUE_PALE),
        ("JD Level",    jd_level,              lv_fg, lv_bg),
    ]
    for i, (lbl, val, fg, bg) in enumerate(box_data):
        bx = 15 + i * box_w
        pdf.set_fill_color(*bg)
        pdf.rect(bx, y_boxes, box_w - 1, box_h, style="F")
        # value
        pdf.set_font("Helvetica", "B", 16)
        pdf.set_text_color(*fg)
        pdf.set_xy(bx + 2, y_boxes + 2)
        pdf.cell(box_w - 4, 9, val, align="C")
        # label
        pdf.set_font("Helvetica", "", 7.5)
        pdf.set_text_color(*GRAY_MID)
        pdf.set_xy(bx + 2, y_boxes + 12)
        pdf.cell(box_w - 4, 5, lbl, align="C")

    pdf.set_y(y_boxes + box_h + 3)

    # Grade text
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*GRAY_DARK)
    pdf.cell(PW, 6, grade, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # JD warning if present
    if jd_warning:
        pdf.set_fill_color(*AMBER_PALE)
        pdf.set_font("Helvetica", "", 8.5)
        pdf.set_text_color(*AMBER)
        pdf.multi_cell(PW, 5, f"  Note: {ct(jd_warning)}", fill=True)
        pdf.ln(1)

    rule()

    # ── SECTION 1: HARD SKILLS ────────────────────────────────
    section_title("Hard Skills", x_count)

    # Table header
    pdf.set_fill_color(*NAVY)
    pdf.set_font("Helvetica", "B", 8.5)
    pdf.set_text_color(*WHITE)
    col1 = 100; col2 = 40; col3 = 40
    pdf.cell(col1, 6, "  Skill", fill=True,
             new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.cell(col2, 6, "In Resume", align="C", fill=True,
             new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.cell(col3, 6, "In JD", align="C", fill=True,
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # Matched skills rows
    if matched_kw:
        for i, kw in enumerate(matched_kw[:20]):
            fill = (i % 2 == 0)
            pdf.set_fill_color(*(GREEN_PALE if fill else WHITE))
            pdf.set_font("Helvetica", "", 8.5)
            pdf.set_text_color(*GREEN)
            pdf.cell(col1, 5.5, f"  {kw}", fill=True,
                     new_x=XPos.RIGHT, new_y=YPos.TOP)
            pdf.set_text_color(*GRAY_DARK)
            pdf.cell(col2, 5.5, "Yes", align="C", fill=True,
                     new_x=XPos.RIGHT, new_y=YPos.TOP)
            pdf.cell(col3, 5.5, "Yes", align="C", fill=True,
                     new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # Missing skills rows
    if missing_kw:
        pdf.ln(1)
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(*RED)
        pdf.cell(PW, 5, "  Missing from resume:", fill=False,
                 new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        for i, kw in enumerate(missing_kw[:20]):
            fill = (i % 2 == 0)
            pdf.set_fill_color(*(RED_PALE if fill else WHITE))
            pdf.set_font("Helvetica", "", 8.5)
            pdf.set_text_color(*RED)
            pdf.cell(col1, 5.5, f"  {kw}", fill=True,
                     new_x=XPos.RIGHT, new_y=YPos.TOP)
            pdf.set_text_color(*GRAY_MID)
            pdf.cell(col2, 5.5, "No",  align="C", fill=True,
                     new_x=XPos.RIGHT, new_y=YPos.TOP)
            pdf.set_text_color(*GRAY_DARK)
            pdf.cell(col3, 5.5, "Yes", align="C", fill=True,
                     new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        if x_count > 20:
            pdf.set_font("Helvetica", "I", 8)
            pdf.set_text_color(*GRAY_MID)
            pdf.cell(PW, 5,
                     f"  ... and {x_count-20} more missing keywords",
                     new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.ln(2)
    rule()

    # ── SECTION 2: SMART MATCHES ──────────────────────────────
    if soft:
        section_title("Smart Synonym Matches", len(soft))
        pdf.set_font("Helvetica", "", 8.5)
        pdf.set_text_color(*GRAY_MID)
        pdf.cell(PW, 5,
            "AI detected these as semantically equivalent "
            "even though exact words differ.",
            new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(1)

        # header
        pdf.set_fill_color(*NAVY)
        pdf.set_font("Helvetica", "B", 8.5)
        pdf.set_text_color(*WHITE)
        pdf.cell(70, 6, "  In Your Resume", fill=True,
                 new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.cell(20, 6, "", fill=True,
                 new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.cell(70, 6, "  Required in JD", fill=True,
                 new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.cell(20, 6, "Match", align="C", fill=True,
                 new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        for i, m in enumerate(soft[:6]):
            rk  = ct(str(m.get("resume_keyword", "")))
            jk  = ct(str(m.get("jd_keyword",     "")))
            sim = int(float(m.get("similarity",   0)) * 100)
            fill = (i % 2 == 0)
            fc = (237, 233, 254) if fill else WHITE
            pdf.set_fill_color(*fc)
            pdf.set_font("Helvetica", "", 8.5)
            pdf.set_text_color(109, 40, 217)
            pdf.cell(70, 5.5, f"  {rk}", fill=True,
                     new_x=XPos.RIGHT, new_y=YPos.TOP)
            pdf.set_text_color(*GRAY_MID)
            pdf.cell(20, 5.5, "~", align="C", fill=True,
                     new_x=XPos.RIGHT, new_y=YPos.TOP)
            pdf.set_text_color(*GREEN)
            pdf.cell(70, 5.5, f"  {jk}", fill=True,
                     new_x=XPos.RIGHT, new_y=YPos.TOP)
            pdf.set_text_color(*GRAY_DARK)
            pdf.cell(20, 5.5, f"{sim}%", align="C", fill=True,
                     new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(2)
        rule()

    # ── SECTION 3: SCORE BREAKDOWN ────────────────────────────
    section_title("Score Breakdown")
    bar_row("Overall ATS Score",   score,     sc_fg)
    bar_row("AI Semantic Matching", sem_score, (109, 40, 217))
    bar_row("Keyword Match",        kw_score,  BLUE)
    if sec_kw:
        pdf.ln(1)
        pdf.set_font("Helvetica", "I", 8)
        pdf.set_text_color(*GRAY_MID)
        pdf.cell(PW, 5, "Section-level keyword scores:",
                 new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        for name, data in sec_kw.items():
            sc2 = float(data.get("score", 0))
            c2  = GREEN if sc2 >= 65 else (AMBER if sc2 >= 40 else RED)
            bar_row(f"  {name.capitalize()}", sc2, c2,
                    label_w=55, bar_w=70)
    pdf.ln(2)
    rule()

    # ── SECTION 4: SEARCHABILITY / SECTION CHECKS ─────────────
    if sec_report:
        section_title("Searchability", len(sec_report))
        for i, (sec_name, info) in enumerate(sec_report.items()):
            status = info.get("status", "") if isinstance(info, dict) else ""
            note   = info.get("note",   "") if isinstance(info, dict) else str(info)
            icon   = status_icon(status)

            if "Good" in status:
                fg = GREEN
            elif "Missing" in status:
                fg = RED
            else:
                fg = AMBER

            fill = (i % 2 == 0)
            pdf.set_fill_color(*(GRAY_PALE if fill else WHITE))
            pdf.set_font("Helvetica", "B", 8.5)
            pdf.set_text_color(*fg)
            pdf.cell(6, 7, icon, fill=True,
                     new_x=XPos.RIGHT, new_y=YPos.TOP)
            pdf.set_font("Helvetica", "B", 8.5)
            pdf.cell(34, 7,
                     sec_name.upper(), fill=True,
                     new_x=XPos.RIGHT, new_y=YPos.TOP)
            pdf.set_font("Helvetica", "", 8.5)
            pdf.set_text_color(*GRAY_DARK)
            pdf.multi_cell(PW - 40, 7, ct(note),
                           fill=True, border=0)
        pdf.ln(2)
        rule()

    # ── SECTION 5: RECRUITER TIPS / SUGGESTIONS ───────────────
    if suggestions:
        section_title("Recruiter Tips", len(suggestions))
        for i, s in enumerate(suggestions[:10]):
            txt       = ct(str(s))
            is_crit   = (i < hp_count) if hp_count else False
            fill      = (i % 2 == 0)
            fill_c    = (RED_PALE if is_crit
                         else (GRAY_PALE if fill else WHITE))
            pdf.set_fill_color(*fill_c)

            # icon
            icon = "[!!]" if is_crit else "[ i]"
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_text_color(*RED if is_crit else GRAY_MID)
            pdf.cell(10, 7, icon, fill=True,
                     new_x=XPos.RIGHT, new_y=YPos.TOP)

            # strip emoji/symbol prefix from text
            clean = txt
            for prefix in [
                "CRITICAL: ", "🔴 CRITICAL: ", "🟡 IMPORTANT: ",
                "➕ ", "✏️  ", "🚨 ", "📝 ", "🔧 ", "✅ ",
            ]:
                if clean.startswith(prefix):
                    clean = clean[len(prefix):]

            pdf.set_font("Helvetica", "B" if is_crit else "", 8.5)
            pdf.set_text_color(*RED if is_crit else GRAY_DARK)
            pdf.multi_cell(PW - 10, 7, ct(clean),
                           fill=True, border=0)
        pdf.ln(2)
        rule()

    # ── SECTION 6: ACTION VERBS + QUANTIFICATION ──────────────
    if verb or quant:
        section_title("Writing Quality")
        if verb:
            row_2col("Action Verbs", verb,
                     label_w=38,
                     fill=True, fill_color=GRAY_PALE)
        if quant:
            row_2col("Quantification", quant,
                     label_w=38,
                     fill=False)
        pdf.ln(2)
        rule()

    # ── DISCLAIMER ────────────────────────────────────────────
    pdf.ln(1)
    pdf.set_font("Helvetica", "I", 7)
    pdf.set_text_color(*GRAY_MID)
    pdf.multi_cell(PW, 3.8,
        "This report was generated by ResumeIQ, an AI-powered ATS resume analyzer "
        "built at MIT-ADT University, Pune. Scores combine sentence-transformer "
        "semantic similarity and normalized keyword matching (custom skill graph, "
        "150+ mappings). Results are indicative and not a guarantee of outcomes "
        "from any specific ATS vendor.")

    pdf.output(output_path)
    return output_path


# ── Test ──────────────────────────────────────────────────────
if __name__ == "__main__":
    sample = {
        "final_score": 67.5, "semantic_score": 71.2,
        "keyword_score": 63.8,
        "final_grade": "Average Match - needs improvement before applying",
        "score_label": "Average Match",
        "resume_filename": "Anushka_Gangwal_Resume.pdf",
        "analysed_at": "14 Jun 2026, 07:13 PM",
        "jd_level": "Senior",
        "jd_warning": (
            "This JD requires 5+ years experience. "
            "As a fresher, highlight projects and "
            "certifications strongly."
        ),
        "matched_keywords": [
            "python", "sql", "git", "linux",
            "cybersecurity", "html", "figma", "dsa",
        ],
        "missing_keywords": [
            "flask", "docker", "pandas", "numpy",
            "machine learning", "fastapi", "azure", "aws",
            "react", "postgresql", "llms", "generative ai",
            "openai api", "computer vision", "ci/cd",
            "devops", "backend development", "graphql",
            "redis", "system design",
        ],
        "matched_count": 8, "missing_count": 20,
        "soft_matches": [
            {"resume_keyword": "dsa",
             "jd_keyword": "data structures",
             "similarity": 0.73},
            {"resume_keyword": "cybersecurity",
             "jd_keyword": "cyber security",
             "similarity": 0.91},
        ],
        "section_report": {
            "skills":     {"status": "Good",
                           "note": "Skills section found with 189 characters. Good length.",
                           "length": 189},
            "experience": {"status": "Missing",
                           "note": "No Experience section found. ATS systems specifically "
                                   "look for this section heading. Add one immediately.",
                           "length": 0},
            "projects":   {"status": "Good",
                           "note": "Projects section found with 445 characters. Good length.",
                           "length": 445},
            "education":  {"status": "Good",
                           "note": "Education section found. Good.",
                           "length": 198},
            "summary":    {"status": "Weak",
                           "note": "Summary section is short (89 chars). Expand with "
                                   "3-4 lines covering your strongest skill and goals.",
                           "length": 89},
        },
        "section_keyword_scores": {
            "skills":     {"score": 78.0, "matched": ["python", "sql"]},
            "projects":   {"score": 55.0, "matched": ["git"]},
            "experience": {"score":  0.0, "matched": []},
            "summary":    {"score": 22.0, "matched": []},
        },
        "suggestions": [
            "CRITICAL: Add 'flask' to your Skills section - appears in JD",
            "CRITICAL: Add 'docker' to your Skills section - appears in JD",
            "Add an Experience section - ATS systems look for this heading",
            "Expand your Summary section - currently too short (89 chars)",
            "Add 'aws' to your Skills section - appears in JD",
            "Include quantified metrics in your project bullet points",
        ],
        "verb_verdict": (
            "Good - no weak verbs detected. Strong verbs found: "
            "built, developed, designed, implemented."
        ),
        "quant_verdict": (
            "Some quantification found (3 metrics). Add more numbers - "
            "e.g. 'tested on 100+ samples', '95% accuracy'."
        ),
        "high_priority_count": 2,
    }
    out = generate_report(sample, "test_report.pdf")
    print(f"Saved: {out}")