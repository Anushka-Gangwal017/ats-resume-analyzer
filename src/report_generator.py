# ─────────────────────────────────────────────────────────────
# report_generator.py
# ResumeIQ — Premium 3-page ATS Match Report
# Page 1: Executive Summary (donut score, cards, strengths/gaps)
# Page 2: Detailed Analysis (sections, keyword pills, smart matches)
# Page 3: Improvement Roadmap (critical/important/optional, writing quality)
# ─────────────────────────────────────────────────────────────

from fpdf import FPDF, XPos, YPos
from datetime import datetime
import math
import uuid


# ── Palette ───────────────────────────────────────────────────
NAVY        = (15, 23, 42)
NAVY_LIGHT  = (30, 41, 59)
INK         = (30, 41, 59)
SLATE       = (100, 116, 139)
SLATE_LIGHT = (148, 163, 184)
LINE        = (226, 232, 240)
PAGE_BG     = (255, 255, 255)
PANEL_BG    = (248, 250, 252)

GREEN       = (22, 163, 74)
GREEN_DARK  = (15, 118, 56)
GREEN_BG    = (240, 253, 244)
GREEN_BD    = (187, 247, 208)

AMBER       = (217, 119, 6)
AMBER_BG    = (255, 251, 235)
AMBER_BD    = (253, 230, 138)

RED         = (220, 38, 38)
RED_BG      = (254, 242, 242)
RED_BD      = (254, 202, 202)

BLUE        = (37, 99, 235)
BLUE_BG     = (239, 246, 255)
BLUE_BD     = (191, 219, 254)

PURPLE      = (109, 40, 217)
PURPLE_BG   = (245, 243, 255)
PURPLE_BD   = (221, 214, 254)

WHITE       = (255, 255, 255)
GRAY_TRACK  = (226, 232, 240)


def ct(text):
    """Clean text for Helvetica/latin-1 rendering."""
    if text is None:
        return ""
    text = str(text)
    subs = {
        "\u2014": "-", "\u2013": "-", "\u2018": "'",
        "\u2019": "'", "\u201c": '"', "\u201d": '"',
        "\u2022": "-", "\u2026": "...", "\u00a0": " ",
        "\u2192": "->", "\u2713": "v", "\u2717": "x",
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


def strip_prefix(text):
    t = ct(text)
    prefixes = [
        "CRITICAL: ", "IMPORTANT: ", "TIP: ",
    ]
    for p in prefixes:
        if t.startswith(p):
            t = t[len(p):]
    return t.strip()


def score_band(score):
    if score >= 75:
        return GREEN, GREEN_BG, GREEN_BD, "Strong Match"
    elif score >= 50:
        return AMBER, AMBER_BG, AMBER_BD, "Average Match"
    else:
        return RED, RED_BG, RED_BD, "Needs Work"

def build_strengths(results):
    """
    Builds a list of max 5 genuine strength strings
    from the results dict. Mirrors the Jinja2 logic
    in result.html so PDF and web show same content.
    """
    sec_rep      = results.get("section_report", {})
    verb_verdict = results.get("verb_verdict", "")
    quant_verdict= results.get("quant_verdict", "")
    matched_count= int(results.get("matched_count", 0))
    soft         = results.get("soft_matches", [])

    def sec_good(name):
        info = sec_rep.get(name, {})
        if not isinstance(info, dict):
            return False
        return "Good" in info.get("status", "")

    strengths = []

    # 1. Skills
    if sec_good("skills"):
        strengths.append(
            "Strong technical skills section - "
            "keywords and tools clearly listed"
        )

    # 2. Research OR Projects (not both)
    if sec_good("research"):
        strengths.append(
            "Research experience present - adds "
            "strong academic and technical credibility"
        )
    elif sec_good("projects"):
        strengths.append(
            "Well-documented project descriptions - "
            "shows practical hands-on experience"
        )

    # 3. Certifications
    if sec_good("certifications"):
        strengths.append(
            "Relevant certifications present - "
            "compensates for limited work experience"
        )

    # 4. Quantification OR verbs (better one wins)
    if quant_verdict and (
        "Good" in quant_verdict or "Excellent" in quant_verdict
    ):
        strengths.append(
            "Quantified achievements with real numbers - "
            "makes impact concrete and measurable"
        )
    elif verb_verdict and (
        "Good" in verb_verdict
        or "Excellent" in verb_verdict
        or "strong" in verb_verdict
    ):
        strengths.append(
            "Strong action verbs throughout - "
            "built, developed, implemented, designed"
        )

    # 5. Keyword alignment
    if matched_count >= 5:
        strengths.append(
            f"{matched_count} keywords already matched - "
            f"solid baseline alignment with this JD"
        )

    return strengths[:5]

def readiness_band(score):
    if score >= 75:
        return ("READY TO APPLY", GREEN, GREEN_BG, GREEN_BD,
                "Your resume is well aligned with this role. "
                "Minor polish could push it even further.")
    elif score >= 50:
        return ("NEEDS MINOR IMPROVEMENTS", AMBER, AMBER_BG, AMBER_BD,
                "You're on the right track. Addressing the gaps "
                "below will meaningfully improve your ATS ranking.")
    else:
        return ("NEEDS SIGNIFICANT IMPROVEMENTS", RED, RED_BG, RED_BD,
                "There is a meaningful gap between your resume and "
                "this job description. Focus on the critical fixes "
                "below before applying.")


class ResumeIQPDF(FPDF):
    def __init__(self, report_id):
        super().__init__()
        self.report_id = report_id
        self.total_pages_placeholder = "{nb}"

    def header(self):
        if self.page_no() == 1:
            return
        self.set_y(8)
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(*NAVY)
        self.cell(90, 6, "ResumeIQ", new_x=XPos.RIGHT, new_y=YPos.TOP)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*SLATE)
        page_titles = {2: "Detailed Analysis", 3: "Improvement Roadmap"}
        title = page_titles.get(self.page_no(), "")
        self.cell(96, 6, title, align="R")
        self.set_draw_color(*LINE)
        self.set_line_width(0.3)
        self.line(15, 15, 195, 15)
        self.set_y(19)

    def footer(self):
        self.set_y(-12)
        self.set_draw_color(*LINE)
        self.set_line_width(0.25)
        self.line(15, self.get_y(), 195, self.get_y())
        self.ln(1.8)
        self.set_font("Helvetica", "", 6.8)
        self.set_text_color(*SLATE_LIGHT)
        self.cell(95, 4.5, "Powered by ResumeIQ AI Engine")
        self.cell(80, 4.5,
           f"Page {self.page_no()} of {{nb}}",
           align="R")


def filled_rect(pdf, x, y, w, h, rgb, border_rgb=None, border_w=0.3):
    pdf.set_fill_color(*rgb)
    if border_rgb:
        pdf.set_draw_color(*border_rgb)
        pdf.set_line_width(border_w)
        pdf.rect(x, y, w, h, style="DF")
    else:
        pdf.rect(x, y, w, h, style="F")


def draw_donut(pdf, cx, cy, r_outer, r_inner, pct, fg, bg=GRAY_TRACK, segments=120):
    """Draws a donut/ring chart using small filled polygon wedges."""
    pdf.set_fill_color(*bg)
    _draw_ring_arc(pdf, cx, cy, r_outer, r_inner, 0, 360, bg, segments)
    sweep = max(0, min(pct, 100)) / 100 * 360
    if sweep > 0:
        _draw_ring_arc(pdf, cx, cy, r_outer, r_inner, -90, -90 + sweep, fg, segments)


def _draw_ring_arc(pdf, cx, cy, r_outer, r_inner, start_deg, end_deg, rgb, segments):
    pdf.set_fill_color(*rgb)
    total = end_deg - start_deg
    if total <= 0:
        return
    n = max(2, int(segments * abs(total) / 360))
    step = total / n
    for i in range(n):
        a0 = math.radians(start_deg + i * step)
        a1 = math.radians(start_deg + (i + 1) * step)
        x0o = cx + r_outer * math.cos(a0)
        y0o = cy + r_outer * math.sin(a0)
        x1o = cx + r_outer * math.cos(a1)
        y1o = cy + r_outer * math.sin(a1)
        x1i = cx + r_inner * math.cos(a1)
        y1i = cy + r_inner * math.sin(a1)
        x0i = cx + r_inner * math.cos(a0)
        y0i = cy + r_inner * math.sin(a0)
        pdf.polygon = getattr(pdf, "polygon", None)
        _poly(pdf, [(x0o, y0o), (x1o, y1o), (x1i, y1i), (x0i, y0i)], rgb)


def _poly(pdf, pts, rgb):
    """Draw a filled polygon using fpdf2's polygon support via lines (manual fill)."""
    # fpdf2 has no native filled polygon < v2.7, so we approximate
    # using thin triangles via the 'ellipse'-less manual approach:
    # use bezier-free straight-edge fill through path drawing.
    pdf.set_fill_color(*rgb)
    # Use a simple approach: draw a filled triangle fan instead
    if len(pts) < 3:
        return
    with pdf.local_context():
        pdf.set_draw_color(*rgb)
        pdf.set_line_width(0.01)
        # draw two triangles to cover the quad
        _filled_triangle(pdf, pts[0], pts[1], pts[2], rgb)
        _filled_triangle(pdf, pts[0], pts[2], pts[3], rgb)


def _filled_triangle(pdf, p1, p2, p3, rgb):
    try:
        pdf.set_fill_color(*rgb)
        with pdf.new_path() as path:
            path.style.fill_color = None
    except Exception:
        pass
    # fpdf2 supports polygon natively via Shape API in v2.7+:
    try:
        from fpdf.drawing import PaintedPath
        pp = PaintedPath()
        pp.move_to(*p1)
        pp.line_to(*p2)
        pp.line_to(*p3)
        pp.close()
        pp.style.fill_color = "#%02x%02x%02x" % rgb
        pp.style.stroke_color = "#%02x%02x%02x" % rgb
        pp.style.stroke_width = 0.01
        pdf.draw_path(pp)
    except Exception:
        # fallback: tiny rect approx (rare path)
        x = min(p1[0], p2[0], p3[0])
        y = min(p1[1], p2[1], p3[1])
        w = max(p1[0], p2[0], p3[0]) - x
        h = max(p1[1], p2[1], p3[1]) - y
        if w > 0 and h > 0:
            pdf.set_fill_color(*rgb)
            pdf.rect(x, y, w, h, style="F")


def progress_bar(pdf, x, y, w, h, pct, fg, bg=GRAY_TRACK, radius=1.0):
    filled_rect(pdf, x, y, w, h, bg)
    fw = max(0, min(float(pct), 100)) / 100 * w
    if fw > 0:
        filled_rect(pdf, x, y, fw, h, fg)


def chip(pdf, x, y, text, fg, bg, font_sz=8, h=5.5, pad=2.6):
    txt = ct(text)
    pdf.set_font("Helvetica", "", font_sz)
    w = pdf.get_string_width(txt) + pad * 2
    filled_rect(pdf, x, y, w, h, bg)
    pdf.set_text_color(*fg)
    pdf.set_xy(x, y + 0.3)
    pdf.cell(w, h - 0.5, txt, align="C")
    return w


def chip_row(pdf, items, x0, y0, max_w, fg, bg, font_sz=8, h=5.5, gap=1.8, max_items=None):
    x, y = x0, y0
    count = 0
    for item in items:
        if max_items and count >= max_items:
            break
        txt = ct(str(item))
        pdf.set_font("Helvetica", "", font_sz)
        w = pdf.get_string_width(txt) + 2.6 * 2
        if x + w > x0 + max_w:
            x = x0
            y += h + gap
        chip(pdf, x, y, txt, fg, bg, font_sz, h)
        x += w + gap
        count += 1
    return y + h


def section_eyebrow(pdf, text, x, y, color=BLUE):
    pdf.set_font("Helvetica", "B", 8.5)
    pdf.set_text_color(*color)
    pdf.set_xy(x, y)
    pdf.cell(0, 5, ct(text).upper())
    return y + 6


def card_title(pdf, text, x, y, w=180, size=12, color=NAVY):
    pdf.set_font("Helvetica", "B", size)
    pdf.set_text_color(*color)
    pdf.set_xy(x, y)
    pdf.cell(w, 7, ct(text))
    return y + 8


def generate_report(results, output_path):
    """
    Main entry point. `results` is the cleaned dict from
    clean_for_template() in app.py. Writes a 3-page PDF to
    output_path.
    """

    report_id = uuid.uuid4().hex[:10].upper()
    pdf = ResumeIQPDF(report_id)
    pdf.alias_nb_pages()
    pdf.set_margins(15, 15, 15)
    pdf.set_auto_page_break(auto=True, margin=20)

    # ── Pull + normalise data ──────────────────────────────────
    score        = float(results.get("final_score", 0))
    sem          = float(results.get("semantic_score", 0))
    kw           = float(results.get("keyword_score", 0))
    grade        = ct(results.get("final_grade", ""))
    resume_fn    = ct(results.get("resume_filename", "resume.pdf"))
    analysed_at  = ct(results.get("analysed_at", datetime.now().strftime("%d %b %Y, %I:%M %p")))
    jd_level     = ct(results.get("jd_level", "Unknown"))
    jd_warning   = results.get("jd_warning")
    matched_kw   = [ct(k) for k in results.get("matched_keywords", [])]
    missing_kw   = [ct(k) for k in results.get("missing_keywords", [])]
    m_count      = int(results.get("matched_count", len(matched_kw)))
    x_count      = int(results.get("missing_count", len(missing_kw)))
    soft         = results.get("soft_matches", [])
    sec_kw       = results.get("section_keyword_scores", {})
    sec_rep      = results.get("section_report", {})
    suggestions  = [strip_prefix(s) for s in results.get("suggestions", [])]
    raw_sugg     = results.get("suggestions", [])
    hp_count     = int(results.get("high_priority_count", 0))
    verb_verdict = ct(results.get("verb_verdict", ""))
    quant_verdict= ct(results.get("quant_verdict", ""))
    strong_verbs = [ct(v) for v in results.get("strong_verbs", [])]
    weak_verbs   = [ct(v) for v in results.get("weak_verbs", [])]

    sc_fg, sc_bg, sc_bd, sc_label_auto = score_band(score)
    score_label = ct(results.get("score_label", sc_label_auto))

    # ════════════════════════════════════════════════════════
    # PAGE 1 — EXECUTIVE SUMMARY
    # ════════════════════════════════════════════════════════
    pdf.add_page()

    # ── Header band ──────────────────────────────────────────
    filled_rect(pdf, 0, 0, 210, 30, NAVY)
    pdf.set_font("Helvetica", "B", 17)
    pdf.set_text_color(*WHITE)
    pdf.set_xy(15, 8)
    pdf.cell(100, 8, "ResumeIQ")
    pdf.set_font("Helvetica", "", 8.5)
    pdf.set_text_color(180, 190, 215)
    pdf.set_xy(15, 17)
    pdf.cell(100, 5, "ATS Match Report")

    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(180, 190, 215)
    pdf.set_xy(95, 8)
    pdf.cell(100, 5, analysed_at, align="R")
    pdf.set_xy(95, 13.5)
    pdf.cell(100, 5, resume_fn[:48], align="R")
    pdf.set_xy(95, 19)
    pdf.cell(100, 5, f"Report ID: {report_id}", align="R")

    y = 38

    # ── Donut + headline ────────────────────────────────────
    cx, cy = 38, y + 24
    draw_donut(pdf, cx, cy, r_outer=22, r_inner=15, pct=score, fg=sc_fg)
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(*sc_fg)
    pdf.set_xy(cx - 16, cy - 6)
    pdf.cell(32, 9, f"{int(score)}", align="C")
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(*SLATE)
    pdf.set_xy(cx - 16, cy + 3)
    pdf.cell(32, 5, "/ 100", align="C")

    # headline text beside donut
    hx = 68
    pdf.set_font("Helvetica", "B", 15)
    pdf.set_text_color(*NAVY)
    pdf.set_xy(hx, y + 6)
    pdf.cell(130, 8, f"ATS Score: {int(score)}/100")
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*sc_fg)
    pdf.set_xy(hx, y + 15)
    pdf.cell(130, 6, score_label)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*SLATE)
    pdf.set_xy(hx, y + 22)
    pdf.multi_cell(122, 4.6, grade)

    y = y + 52

    # ── Three metric cards ───────────────────────────────────
    card_w = (180 - 8) / 3
    card_h = 24
    metrics = [
        ("ATS SCORE", f"{int(score)}%", sc_fg, sc_bg, sc_bd),
        ("AI SEMANTIC MATCH", f"{int(sem)}%", PURPLE, PURPLE_BG, PURPLE_BD),
        ("KEYWORD MATCH", f"{int(kw)}%", BLUE, BLUE_BG, BLUE_BD),
    ]
    for i, (label, val, fg, bg, bd) in enumerate(metrics):
        cx0 = 15 + i * (card_w + 4)
        filled_rect(pdf, cx0, y, card_w, card_h, bg, border_rgb=bd, border_w=0.4)
        pdf.set_font("Helvetica", "B", 18)
        pdf.set_text_color(*fg)
        pdf.set_xy(cx0, y + 4)
        pdf.cell(card_w, 9, val, align="C")
        pdf.set_font("Helvetica", "B", 7)
        pdf.set_text_color(*SLATE)
        pdf.set_xy(cx0, y + 15)
        pdf.cell(card_w, 5, label, align="C")

    y += card_h + 8

    # ── Executive assessment ─────────────────────────────────
    y = section_eyebrow(pdf, "Executive Assessment", 15, y)
    filled_rect(pdf, 15, y, 180, 22, PANEL_BG, border_rgb=LINE, border_w=0.3)

    top_strengths = matched_kw[:5]
    top_gaps = missing_kw[:5]
    strengths_txt = ", ".join(top_strengths) if top_strengths else "core fundamentals"
    gaps_txt = ", ".join(top_gaps) if top_gaps else "a few specific tools"

    if score >= 75:
        verdict = "demonstrates strong alignment with this role"
        closer = "this resume is highly competitive for this position."
    elif score >= 50:
        verdict = "shows reasonable alignment with this role"
        closer = "with the improvements below, this resume becomes competitive."
    else:
        verdict = "shows limited alignment with this role as written"
        closer = "addressing the gaps below would meaningfully improve ATS performance."

    summary_text = (
        f"Your resume {verdict}. Core skills such as "
        f"{strengths_txt} are present and recognised by the system. "
        f"The primary gaps involve {gaps_txt}. "
        f"{closer[0].upper() + closer[1:]}"
    )
    pdf.set_font("Helvetica", "", 8.7)
    pdf.set_text_color(*INK)
    pdf.set_xy(18, y + 3)
    pdf.multi_cell(174, 4.6, ct(summary_text))

    y += 22 + 6

    # ── Resume Strengths (page 1) ──────────────────────────────
    strengths = build_strengths(results)
    if strengths:
        # Manual page break check
        if y + len(strengths) * 8 + 20 > pdf.h - pdf.b_margin:
           pdf.add_page()
           y = pdf.get_y()
        y = section_eyebrow(pdf, "Resume Strengths", 15, y,
                            GREEN_DARK)
        for s in strengths:
            # Green circle check icon (drawn as filled circle
            # + white dot approximation)
            pdf.set_fill_color(*GREEN_BG)
            pdf.set_draw_color(*GREEN_BD)
            pdf.set_line_width(0.3)
            pdf.ellipse(17, y + 0.8, 4, 4, style="DF")
            pdf.set_font("Helvetica", "B", 7)
            pdf.set_text_color(*GREEN)
            pdf.set_xy(17.8, y + 0.6)
            pdf.cell(2.5, 4, "v")

            # Strength text
            pdf.set_font("Helvetica", "", 8.5)
            pdf.set_text_color(*INK)
            pdf.set_xy(24, y)
            pdf.multi_cell(166, 5, ct(s))
            y = pdf.get_y() + 2

        y += 2

    # ── Top strengths / top gaps (two columns) ───────────────
    col_w = (180 - 6) / 2
    y_strengths = section_eyebrow(pdf, "Top Strengths", 15, y, GREEN_DARK)
    y_gaps      = section_eyebrow(pdf, "Top Skill Gaps", 15 + col_w + 6, y, RED)

    sy = y_strengths
    if top_strengths:
        for s in top_strengths:
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_text_color(*GREEN)
            pdf.set_xy(15, sy)
            pdf.cell(6, 5.5, "v")
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(*INK)
            pdf.set_xy(21, sy)
            pdf.cell(col_w - 6, 5.5, ct(s))
            sy += 6
    else:
        pdf.set_font("Helvetica", "I", 8.5)
        pdf.set_text_color(*SLATE)
        pdf.set_xy(15, sy)
        pdf.cell(col_w, 5.5, "No strong matches found")
        sy += 6

    gy = y_gaps
    if top_gaps:
        for g in top_gaps:
            gx = 15 + col_w + 6
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_text_color(*RED)
            pdf.set_xy(gx, gy)
            pdf.cell(6, 5.5, "x")
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(*INK)
            pdf.set_xy(gx + 6, gy)
            pdf.cell(col_w - 6, 5.5, ct(g))
            gy += 6
    else:
        gx = 15 + col_w + 6
        pdf.set_font("Helvetica", "I", 8.5)
        pdf.set_text_color(*GREEN)
        pdf.set_xy(gx, gy)
        pdf.cell(col_w, 5.5, "No major gaps - great job!")
        gy += 6

    y = max(sy, gy) + 6

    # ── Hiring readiness box ──────────────────────────────────
    readiness_label, r_fg, r_bg, r_bd, r_desc = readiness_band(score)
    box_h = 24
    filled_rect(pdf, 15, y, 180, box_h, r_bg, border_rgb=r_bd, border_w=0.5)
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(*r_fg)
    pdf.set_xy(20, y + 4)
    pdf.cell(170, 7, readiness_label)
    pdf.set_font("Helvetica", "", 8.5)
    pdf.set_text_color(*INK)
    pdf.set_xy(20, y + 12)
    pdf.multi_cell(166, 4.4, ct(r_desc))

    if jd_warning:
        y += box_h + 4
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(*AMBER)
        pdf.set_xy(15, y)
        pdf.cell(20, 5, f"JD Level: {jd_level}")
        pdf.set_font("Helvetica", "", 8)
        pdf.set_xy(40, y)
        pdf.multi_cell(155, 4.3, ct(jd_warning))

    # ════════════════════════════════════════════════════════
    # PAGE 2 — DETAILED ANALYSIS
    # ════════════════════════════════════════════════════════
    pdf.add_page()
    y = pdf.get_y() + 2

    y = card_title(pdf, "Section Performance", 15, y)

    sec_order = ["summary", "education", "experience", "projects",
                 "skills", "certifications", "research"]
    sections_present = [s for s in sec_order if s in sec_rep or s in sec_kw]
    for s in sec_rep:
        if s not in sections_present:
            sections_present.append(s)

    col_w2 = (180 - 6) / 2
    col_x = [15, 15 + col_w2 + 6]
    col_y = [y, y]

    for idx, sec_name in enumerate(sections_present):
        info = sec_rep.get(sec_name, {})
        status = info.get("status", "") if isinstance(info, dict) else ""
        note   = info.get("note", "")   if isinstance(info, dict) else str(info)
        sc2    = float(sec_kw.get(sec_name, {}).get("score", 0)) if sec_name in sec_kw else None

        if "Good" in status:
            s_fg, s_bg, s_bd = GREEN, GREEN_BG, GREEN_BD
        elif "Missing" in status:
            s_fg, s_bg, s_bd = RED, RED_BG, RED_BD
        else:
            s_fg, s_bg, s_bd = AMBER, AMBER_BG, AMBER_BD

        col = idx % 2
        x = col_x[col]
        cy0 = col_y[col]
        card_h2 = 26

        filled_rect(pdf, x, cy0, col_w2, card_h2, PANEL_BG, border_rgb=LINE, border_w=0.3)
        pdf.set_font("Helvetica", "B", 9.5)
        pdf.set_text_color(*NAVY)
        pdf.set_xy(x + 3, cy0 + 2.5)
        pdf.cell(col_w2 - 30, 5, ct(sec_name.upper()))

        if sc2 is not None:
            pdf.set_font("Helvetica", "B", 9.5)
            pdf.set_text_color(*s_fg)
            pdf.set_xy(x + col_w2 - 27, cy0 + 2.5)
            pdf.cell(24, 5, f"{int(sc2)}% Match", align="R")
            progress_bar(pdf, x + 3, cy0 + 9, col_w2 - 6, 2.6, sc2, s_fg)
            note_y = cy0 + 14
        else:
            chip(pdf, x + col_w2 - 22, cy0 + 2, status[:10] or "N/A", s_fg, s_bg, font_sz=7, h=5)
            note_y = cy0 + 10

        pdf.set_font("Helvetica", "", 7.6)
        pdf.set_text_color(*SLATE)
        pdf.set_xy(x + 3, note_y)
        pdf.multi_cell(col_w2 - 6, 3.7, ct(note)[:140])

        col_y[col] = cy0 + card_h2 + 4

    y = max(col_y) + 4

    # ── Keyword analysis (two columns of pills) ───────────────
    y = card_title(pdf, "Keyword Analysis", 15, y)
    pdf.set_font("Helvetica", "", 8.5)
    pdf.set_text_color(*SLATE)
    pdf.set_xy(15, y)
    pdf.cell(180, 5, f"Matched: {m_count}      Missing: {x_count}")
    y += 7

    col_w3 = (180 - 6) / 2
    left_x, right_x = 15, 15 + col_w3 + 6

    pdf.set_font("Helvetica", "B", 8.5)
    pdf.set_text_color(*GREEN_DARK)
    pdf.set_xy(left_x, y)
    pdf.cell(col_w3, 5, f"MATCHED ({m_count})")
    pdf.set_text_color(*RED)
    pdf.set_xy(right_x, y)
    pdf.cell(col_w3, 5, f"MISSING ({x_count})")
    y += 6

    y_left  = chip_row(pdf, matched_kw, left_x, y, col_w3, GREEN_DARK, GREEN_BG, font_sz=7.5, h=5, max_items=24) if matched_kw else y + 5
    y_right = chip_row(pdf, missing_kw, right_x, y, col_w3, RED, RED_BG, font_sz=7.5, h=5, max_items=24) if missing_kw else y + 5

    if not matched_kw:
        pdf.set_font("Helvetica", "I", 8)
        pdf.set_text_color(*SLATE)
        pdf.set_xy(left_x, y)
        pdf.cell(col_w3, 5, "None found")
    if not missing_kw:
        pdf.set_font("Helvetica", "I", 8)
        pdf.set_text_color(*GREEN)
        pdf.set_xy(right_x, y)
        pdf.cell(col_w3, 5, "Great match!")

    y = max(y_left, y_right) + 6

    # ── Smart matches ──────────────────────────────────────────
    if soft:
        y = card_title(pdf, "Smart Matches", 15, y, size=11)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(*SLATE)
        pdf.set_xy(15, y)
        pdf.cell(180, 4.5, "AI recognised these as equivalent skills even though the wording differs.")
        y += 6
        for m in soft[:6]:
            rk = ct(str(m.get("resume_keyword", "")))
            jk = ct(str(m.get("jd_keyword", "")))
            sim = int(float(m.get("similarity", 0)) * 100)
            pdf.set_font("Helvetica", "B", 8.5)
            x = 15
            w1 = chip(pdf, x, y, rk, BLUE, BLUE_BG, font_sz=8, h=5.5)
            pdf.set_font("Helvetica", "", 8.5)
            pdf.set_text_color(*SLATE)
            pdf.set_xy(x + w1 + 2, y + 0.3)
            pdf.cell(10, 5, "->")
            w2 = chip(pdf, x + w1 + 13, y, jk, GREEN_DARK, GREEN_BG, font_sz=8, h=5.5)
            pdf.set_font("Helvetica", "", 7.5)
            pdf.set_text_color(*SLATE)
            pdf.set_xy(x + w1 + 13 + w2 + 3, y + 0.5)
            pdf.cell(30, 5, f"{sim}% similar")
            y += 7.5

    # ════════════════════════════════════════════════════════
    # PAGE 3 — IMPROVEMENT ROADMAP
    # ════════════════════════════════════════════════════════
    pdf.add_page()
    y = pdf.get_y() + 2

    pdf.set_font("Helvetica", "B", 15)
    pdf.set_text_color(*NAVY)
    pdf.set_xy(15, y)
    pdf.cell(180, 8, "Action Plan to Improve ATS Score")
    y += 11

    # Split suggestions into 3 groups
    n_sugg = len(raw_sugg)
    critical = suggestions[:hp_count] if hp_count else suggestions[:max(1, n_sugg // 3)]
    remaining = suggestions[len(critical):]
    important = remaining[:max(0, len(remaining) - max(1, len(remaining) // 3))]
    optional = remaining[len(important):]

    groups = [
        ("GROUP 1 - CRITICAL FIXES", critical, RED, RED_BG, RED_BD),
        ("GROUP 2 - IMPORTANT IMPROVEMENTS", important, AMBER, AMBER_BG, AMBER_BD),
        ("GROUP 3 - OPTIONAL ENHANCEMENTS", optional, BLUE, BLUE_BG, BLUE_BD),
    ]

    for title, items, fg, bg, bd in groups:
        if not items:
            continue
        pdf.set_font("Helvetica", "B", 9.5)
        pdf.set_text_color(*fg)
        pdf.set_xy(15, y)
        pdf.cell(180, 6, ct(title))
        y += 7
        for i, item in enumerate(items[:8], 1):
            filled_rect(pdf, 15, y - 0.5, 5, 5, bg, border_rgb=bd, border_w=0.3)
            pdf.set_font("Helvetica", "B", 7.5)
            pdf.set_text_color(*fg)
            pdf.set_xy(15, y)
            pdf.cell(5, 4.5, str(i), align="C")
            pdf.set_font("Helvetica", "", 8.7)
            pdf.set_text_color(*INK)
            pdf.set_xy(23, y - 0.5)
            pdf.multi_cell(172, 4.4, ct(item))
            y = pdf.get_y() + 1.5
        y += 3

    y += 2
    pdf.set_draw_color(*LINE)
    pdf.set_line_width(0.3)
    pdf.line(15, y, 195, y)
    y += 6

    # ── Writing quality ──────────────────────────────────────
    y = card_title(pdf, "Writing Quality Analysis", 15, y, size=12)

    col_w4 = (180 - 6) / 2
    # Action verbs box
    filled_rect(pdf, 15, y, col_w4, 34, PANEL_BG, border_rgb=LINE, border_w=0.3)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*NAVY)
    pdf.set_xy(18, y + 2.5)
    pdf.cell(col_w4 - 6, 5, "Action Verbs")
    pdf.set_font("Helvetica", "", 7.8)
    pdf.set_text_color(*SLATE)
    pdf.set_xy(18, y + 8)
    pdf.multi_cell(col_w4 - 6, 3.9, ct(verb_verdict)[:160])

    vy = y + 8 + 8
    if strong_verbs:
        pdf.set_font("Helvetica", "B", 7)
        pdf.set_text_color(*GREEN_DARK)
        pdf.set_xy(18, vy)
        pdf.cell(col_w4 - 6, 4, "Strong: " + ", ".join(strong_verbs[:5]))
        vy += 4.5
    if weak_verbs:
        pdf.set_font("Helvetica", "B", 7)
        pdf.set_text_color(*RED)
        pdf.set_xy(18, vy)
        pdf.cell(col_w4 - 6, 4, "Weak: " + ", ".join(weak_verbs[:5]))

    # Quantification box
    qx = 15 + col_w4 + 6
    filled_rect(pdf, qx, y, col_w4, 34, PANEL_BG, border_rgb=LINE, border_w=0.3)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*NAVY)
    pdf.set_xy(qx + 3, y + 2.5)
    pdf.cell(col_w4 - 6, 5, "Quantification")
    pdf.set_font("Helvetica", "", 7.8)
    pdf.set_text_color(*SLATE)
    pdf.set_xy(qx + 3, y + 8)
    pdf.multi_cell(col_w4 - 6, 3.9, ct(quant_verdict)[:200])

    y += 34 + 6

    # ── Recruiter Snapshot ────────────────────────────────────
    if y + 65 > pdf.h - pdf.b_margin:
        pdf.add_page()
        y = pdf.get_y()

    # Section heading
    pdf.set_font("Helvetica", "B", 9.5)
    pdf.set_text_color(*NAVY)
    pdf.set_xy(15, y)
    pdf.cell(180, 7, "RECRUITER SNAPSHOT",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    y += 8
    pdf.set_draw_color(*LINE)
    pdf.set_line_width(0.3)
    pdf.line(15, y, 195, y)
    y += 4

    # Calculate ratings
    if kw >= 65:
        tech_fit, tech_color = "Strong",   GREEN
    elif kw >= 40:
        tech_fit, tech_color = "Moderate", AMBER
    else:
        tech_fit, tech_color = "Low",      RED

    has_exp = (
        isinstance(sec_rep.get("experience"), dict)
        and "Good" in sec_rep.get(
            "experience", {}
        ).get("status", "")
    )
    if has_exp and score >= 65:
        exp_fit, exp_color = "Strong",   GREEN
    elif has_exp or score >= 50:
        exp_fit, exp_color = "Moderate", AMBER
    else:
        exp_fit, exp_color = "Low",      RED

    if score >= 75:
        prob, prob_color = "High",   GREEN
    elif score >= 50:
        prob, prob_color = "Medium", AMBER
    else:
        prob, prob_color = "Low",    RED

    rows = [
        ("Technical Fit",         tech_fit,       tech_color),
        ("Experience Fit",        exp_fit,        exp_color),
        ("Keyword Coverage",      f"{int(kw)}%",  BLUE),
        ("Interview Probability", prob,            prob_color),
    ]

    ROW_H = 10
    for i, (label, value, color) in enumerate(rows):
        row_bg = PANEL_BG if i % 2 == 0 else WHITE

        # Row background
        filled_rect(pdf, 15, y, 180, ROW_H, row_bg)

        # Label
        pdf.set_font("Helvetica", "", 8.5)
        pdf.set_text_color(*SLATE)
        pdf.set_xy(20, y + 1.8)
        pdf.cell(90, 6, ct(label))

        # Coloured value — right aligned
        pdf.set_font("Helvetica", "B", 8.5)
        pdf.set_text_color(*color)
        pdf.set_xy(20, y + 1.8)
        pdf.cell(170, 6, ct(value), align="R")

        y += ROW_H

    # Border around the whole table
    pdf.set_draw_color(*LINE)
    pdf.set_line_width(0.3)
    pdf.rect(15, y - ROW_H * len(rows),
             180, ROW_H * len(rows))

    y += 8

    # ── Final recommendation ──────────────────────────────────
    y = section_eyebrow(pdf, "Final Recommendation", 15, y, NAVY)
    filled_rect(pdf, 15, y, 180, 26, NAVY_LIGHT)
    if score >= 75:
        final_text = (
            "Based on this analysis, the resume demonstrates strong "
            "technical alignment with this role's requirements. "
            "The candidate shows solid command of the core skills "
            "this position demands. Minor refinements to the gaps "
            "noted above would further strengthen ATS performance."
        )
    elif score >= 50:
        final_text = (
            "Based on this analysis, the resume demonstrates a "
            "reasonable technical foundation with partial alignment "
            "to this role. The most impactful improvements involve "
            "the skill gaps identified above. Addressing these "
            "could meaningfully improve ATS ranking for this position."
        )
    else:
        final_text = (
            "Based on this analysis, the resume currently shows "
            "limited alignment with this specific role's requirements. "
            "The candidate's existing skills are a foundation to build "
            "on, but the critical gaps identified above should be "
            "addressed before applying to similar roles."
        )
    pdf.set_font("Helvetica", "", 8.8)
    pdf.set_text_color(*WHITE)
    pdf.set_xy(19, y + 4)
    pdf.multi_cell(172, 4.6, ct(final_text))

    y += 26 + 6

    # ── Tech stack footer note ─────────────────────────────────
    pdf.set_font("Helvetica", "B", 7.5)
    pdf.set_text_color(*SLATE)
    pdf.set_xy(15, y)
    pdf.cell(180, 4.5, "TECHNOLOGY STACK")
    y += 5
    pdf.set_font("Helvetica", "", 7.5)
    pdf.set_text_color(*SLATE_LIGHT)
    pdf.set_xy(15, y)
    pdf.multi_cell(180, 4,
        "Sentence Transformers Semantic Matching   |   "
        "Skill Graph Normalization (150+ mappings)   |   "
        "Custom ATS Scoring Engine   |   spaCy NLP Pipeline")

    pdf.output(output_path)
    return output_path


# ── Standalone test ──────────────────────────────────────────
if __name__ == "__main__":
    sample = {
        "final_score": 67.5, "semantic_score": 71.2, "keyword_score": 63.8,
        "final_grade": "Average Match - needs improvement before applying",
        "score_label": "Average Match",
        "resume_filename": "Anushka_Gangwal_Resume.pdf",
        "analysed_at": "16 Jun 2026, 06:08 PM",
        "jd_level": "Senior",
        "jd_warning": "This JD requires 5+ years experience. As a fresher, highlight projects and certifications strongly.",
        "matched_keywords": ["python", "sql", "git", "linux", "cybersecurity", "html", "figma", "dsa"],
        "missing_keywords": ["flask", "docker", "pandas", "numpy", "machine learning", "fastapi",
                              "azure", "aws", "react", "postgresql", "llms", "generative ai",
                              "openai api", "computer vision", "ci/cd", "devops",
                              "backend development", "graphql", "redis", "system design"],
        "matched_count": 8, "missing_count": 20,
        "soft_matches": [
            {"resume_keyword": "dsa", "jd_keyword": "data structures", "similarity": 0.73},
            {"resume_keyword": "cybersecurity", "jd_keyword": "cyber security", "similarity": 0.91},
        ],
        "section_report": {
            "summary": {"status": "Weak", "note": "Summary section too short (89 chars). Expand to 3-4 lines.", "length": 89},
            "education": {"status": "Good", "note": "Education section found and complete.", "length": 198},
            "experience": {"status": "Missing", "note": "No Experience section found. Add one immediately.", "length": 0},
            "projects": {"status": "Good", "note": "Projects section found with 445 characters.", "length": 445},
            "skills": {"status": "Good", "note": "Skills section found with 189 characters.", "length": 189},
            "certifications": {"status": "Good", "note": "Certifications section looks fine.", "length": 1028},
        },
        "section_keyword_scores": {
            "summary": {"score": 22.0}, "skills": {"score": 78.0},
            "projects": {"score": 55.0}, "experience": {"score": 0.0},
        },
        "suggestions": [
            "CRITICAL: Add 'flask' to your Skills section - it appears in the JD",
            "CRITICAL: Add 'docker' to your Skills section - it appears in the JD",
            "Add an Experience section - ATS systems specifically look for this heading",
            "Expand your Summary section - currently too short at 89 characters",
            "Add 'aws' to your Skills section - it appears in the JD",
            "Include quantified metrics in your project bullet points",
            "Consider adding 'redis' - mentioned in the JD",
        ],
        "verb_verdict": "Good - no weak verbs detected. Strong verbs found: built, developed, designed, implemented.",
        "quant_verdict": "Good quantification - 22 numbers/metrics found: 600M+, 100+, 95%.",
        "strong_verbs": ["built", "developed", "designed", "implemented"],
        "weak_verbs": [],
        "high_priority_count": 2,
    }
    out = generate_report(sample, "test_report.pdf")
    print(f"Saved: {out}")