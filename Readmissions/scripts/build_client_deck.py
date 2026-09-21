"""
Build the three-slide client deck as a real .pptx.

WHY A SCRIPT AND NOT A HAND-MADE FILE
-------------------------------------
Every figure on these slides is traceable to docs/project_timeline.md or
docs/icd_codes_explained.md. Keeping the deck in code means a number can be
corrected in one place and the file rebuilt, instead of being retyped into a
shape and silently drifting from the documents it came from.

    .venv/bin/python scripts/build_client_deck.py

Writes docs/deliverables/Preventra_CMS_to_MIMIC.pptx (16:9).

Fonts are deliberately restricted to faces that ship with Office on Windows and
macOS - Georgia for display, Calibri for body, Consolas for figures. The web
version of this deck uses Newsreader and IBM Plex; those would silently fall
back to Calibri on a client machine, which is worse than choosing a good
available serif on purpose.
"""
from __future__ import annotations

import os

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

# ---------------------------------------------------------------------------
# Palette - the dashboard's own tokens, so the deck and the live product read
# as one thing when the presenter switches windows.
# ---------------------------------------------------------------------------
NAVY   = RGBColor.from_string("0F2A4A")   # --color-ns-navy
SIGNAL = RGBColor.from_string("C0392B")   # --color-risk-high
AMBER  = RGBColor.from_string("B8860B")
INK    = RGBColor.from_string("14293F")
MUTED  = RGBColor.from_string("5A6B7D")
FAINT  = RGBColor.from_string("8494A3")
PAPER  = RGBColor.from_string("EDEFF2")
WHITE  = RGBColor.from_string("FFFFFF")
RULE   = RGBColor.from_string("C9D2DB")
SOFT   = RGBColor.from_string("DEE4EA")
BARSOFT = RGBColor.from_string("B9C6D4")

DISPLAY = "Georgia"
BODY    = "Calibri"
MONO    = "Consolas"

W, H = 13.333, 7.5
L, R = 0.55, 0.55                      # page margins
COL3_W, COL3_GAP = 3.87, 0.28
COL3_X = [L, L + COL3_W + COL3_GAP, L + 2 * (COL3_W + COL3_GAP)]

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "docs", "deliverables", "Preventra_CMS_to_MIMIC.pptx")


# ---------------------------------------------------------------------------
# Primitives
# ---------------------------------------------------------------------------
def rect(slide, x, y, w, h, fill, line=None):
    s = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y),
                               Inches(w), Inches(h))
    s.shadow.inherit = False
    # An autoshape also carries <p:style> pointing at the theme's effectRef,
    # which some renderers honour even when effectLst is empty - that is where
    # the unwanted drop shadow comes from. Every colour here is set explicitly,
    # so the whole style reference goes.
    style = s._element.find(qn("p:style"))
    if style is not None:
        s._element.remove(style)
    if fill is None:
        s.fill.background()
    else:
        s.fill.solid()
        s.fill.fore_color.rgb = fill
    if line is None:
        s.line.fill.background()
    else:
        s.line.color.rgb = line
        s.line.width = Pt(0.75)
    return s


def rule(slide, x, y, w, color=RULE, thick=0.012):
    return rect(slide, x, y, w, thick, color)


def text(slide, x, y, w, h, paras, anchor=MSO_ANCHOR.TOP):
    """
    paras: list of paragraphs. Each is (runs, opts) where runs is a string or a
    list of (string, run-opts) and opts carries paragraph settings.
    """
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0

    for i, (runs, o) in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = o.get("align", PP_ALIGN.LEFT)
        p.line_spacing = o.get("line", 1.15)
        if o.get("space_before"):
            p.space_before = Pt(o["space_before"])
        if o.get("space_after"):
            p.space_after = Pt(o["space_after"])
        for chunk in ([(runs, {})] if isinstance(runs, str) else runs):
            s, ro = chunk
            r = p.add_run()
            r.text = s
            f = r.font
            f.name = ro.get("font", o.get("font", BODY))
            f.size = Pt(ro.get("size", o.get("size", 11)))
            f.bold = ro.get("bold", o.get("bold", False))
            f.italic = ro.get("italic", o.get("italic", False))
            f.color.rgb = ro.get("color", o.get("color", INK))
    return box


def label(slide, x, y, w, s, color=FAINT, size=8):
    """Uppercase mono eyebrow/section label."""
    return text(slide, x, y, w, 0.2,
                [(s.upper(), {"font": MONO, "size": size, "color": color, "bold": True})])


def stats(slide, x, y, w, rows, row_h=0.245, size=10, label_frac=0.60):
    """
    Label-left / figure-right rows separated by hairlines.

    `label_frac` splits the width. Short figures ("13,633") do not need 40% of
    the row, and a long label that wraps lands on top of the row beneath it.
    """
    cy = y
    for i, (dt, dd, style) in enumerate(rows):
        col = {"hi": NAVY, "warn": SIGNAL}.get(style, INK)
        bold = style in ("hi", "warn")
        text(slide, x, cy + 0.03, w * label_frac, row_h,
             [(dt, {"size": size, "color": MUTED})])
        text(slide, x + w * label_frac, cy + 0.03, w * (1 - label_frac), row_h,
             [(dd, {"font": MONO, "size": size, "color": col, "bold": bold,
                    "align": PP_ALIGN.RIGHT})])
        if i < len(rows) - 1:
            rule(slide, x, cy + row_h, w, SOFT, 0.008)
        cy += row_h
    return cy


def bars(slide, x, y, w, rows, row_h=0.235, lab_w=0.62, val_w=0.5):
    """Horizontal bar rows: (label, pct-of-max, value-text, colour)."""
    track_x = x + lab_w + 0.1
    track_w = w - lab_w - val_w - 0.2
    cy = y
    for lab, frac, val, color in rows:
        text(slide, x, cy + 0.015, lab_w, row_h,
             [(lab, {"font": MONO, "size": 8.5, "color": MUTED})])
        rect(slide, track_x, cy + 0.035, track_w, 0.135, SOFT)
        if frac > 0:
            rect(slide, track_x, cy + 0.035, track_w * frac, 0.135, color)
        text(slide, x + w - val_w, cy + 0.015, val_w, row_h,
             [(val, {"font": MONO, "size": 8.5, "color": INK, "bold": True,
                     "align": PP_ALIGN.RIGHT})])
        cy += row_h
    return cy


def legend(slide, x, y, w, runs, h=0.6):
    rule(slide, x, y, w, SOFT, 0.008)
    return text(slide, x, y + 0.09, w, h,
                [(runs, {"size": 9.5, "color": MUTED, "line": 1.22})])


def items(slide, x, y, w, entries, gap=0.14, accent=RULE):
    """Left-ruled blocks: (bold lead, supporting sentence, height)."""
    cy = y
    for head, sub, h in entries:
        rect(slide, x, cy, 0.028, h, accent)
        text(slide, x + 0.16, cy, w - 0.16, 0.22,
             [(head, {"size": 10.5, "bold": True, "color": INK})])
        text(slide, x + 0.16, cy + 0.235, w - 0.16, h - 0.235,
             [(sub, {"size": 9.5, "color": MUTED, "line": 1.2})])
        cy += h + gap
    return cy


def slide_frame(prs, step, topic):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    rect(s, 0, 0, W, H, PAPER)
    text(s, L, 0.30, 9.6, 0.22,
         [([(step.upper(), {"color": NAVY}), ("   ·   " + topic.upper(), {})],
           {"font": MONO, "size": 8, "color": FAINT, "bold": True})])
    text(s, W - R - 2.0, 0.30, 2.0, 0.22,
         [("PREVENTRA", {"font": MONO, "size": 8, "color": FAINT, "bold": True,
                         "align": PP_ALIGN.RIGHT})])
    rule(s, L, 0.58, W - L - R)
    return s


BODY_Y = 2.36          # where every slide's content columns start
FOOT_Y = 7.05          # and the lowest they may reach


def heading(slide, headline, dek_runs, h_size=25, dek_w=10.6):
    """
    Headline gets a fixed two-line budget whether or not it uses both.

    Sizing the box to the text means a headline that wraps one line further
    than expected lands on top of the deck underneath it - which is exactly
    what happened on the first build. A reserved block cannot collide.
    """
    text(slide, L, 0.72, W - L - R, 1.00,
         [(headline, {"font": DISPLAY, "size": h_size, "color": INK, "line": 1.03})])
    text(slide, L, 1.78, dek_w, 0.52,
         [(dek_runs, {"size": 10.5, "color": MUTED, "line": 1.22})])


def anchor_figure(slide, x, y, w, fig, cap, size=40):
    """
    The one number a client reads first, with its caption tucked under it.

    The caption offset is derived from the figure size rather than fixed, so
    changing how big the number is does not leave the caption stranded.
    """
    cap_y = y + size / 72 * 0.92 + 0.14
    text(slide, x, y, w, 0.95,
         [(fig, {"font": DISPLAY, "size": size, "color": NAVY, "line": 0.92})])
    text(slide, x, cap_y, w, 0.22,
         [(cap.upper(), {"font": MONO, "size": 8, "color": FAINT})])


B = lambda t: (t, {"bold": True, "color": INK})          # noqa: E731
I = lambda t: (t, {"italic": True})                      # noqa: E731


# ---------------------------------------------------------------------------
# Slide 0 - the diabetes baseline
# ---------------------------------------------------------------------------
def slide_zero(prs):
    s = slide_frame(prs, "Stage 0",
                    "UCI Diabetes 130-US Hospitals — where this started")
    heading(s, "It began with one disease and one hospital visit.",
            [("A readmission model on the ", {}), B("UCI Diabetes 130-US Hospitals"),
             (" dataset — 101,766 encounters, diabetic inpatients only. Four approaches were "
              "built and validated against a pass mark of 0.65.", {})])

    lx, lw = L, 4.75
    rx, rw = 5.85, 6.93

    anchor_figure(s, lx, BODY_Y, lw, "0.7063",
                  "ROC-AUC on the approach that shipped", size=40)

    # First appearance of the metric in the deck, so it is defined here.
    text(s, lx, 3.36, lw, 0.92,
         [([("AUC-ROC", {"bold": True, "color": INK}),
            (" stands for ", {}),
            ("Area Under the Receiver Operating Characteristic curve", {"italic": True}),
            (". In plain terms it is a mark out of 1 for how well the model sorts patients "
             "riskiest-first. 0.50 is random guessing, 1.00 is perfect. This one gets the "
             "order right 71% of the time.", {})],
           {"size": 9.5, "color": MUTED, "line": 1.22})])

    rect(s, lx, 4.34, 0.032, 1.00, SIGNAL)
    text(s, lx + 0.17, 4.34, lw - 0.17, 0.30,
         [("A working model, on a single disease.",
           {"font": DISPLAY, "size": 14, "color": SIGNAL, "line": 1.1})])
    text(s, lx + 0.17, 4.68, lw - 0.17, 0.68,
         [("It proved the pipeline worked. It could not be the product — the hospital needed "
           "every patient, not the diabetic ones.",
           {"size": 9.5, "color": MUTED, "line": 1.22})])

    rect(s, lx, 5.42, lw, 1.63, WHITE, SOFT)
    label(s, lx + 0.16, 5.58, lw - 0.32, "What was built")
    stats(s, lx + 0.16, 5.80, lw - 0.32, [
        ("Encounters",                "101,766",            "hi"),
        ("Features",                  "34",                 ""),
        ("Who it covered",            "diabetic inpatients", ""),
        ("Approaches trained",        "4",                  ""),
        ("Pass mark",                 "ROC-AUC 0.65",       ""),
    ], row_h=0.21, size=9.5)

    label(s, rx, BODY_Y, rw, "Four approaches, one pass mark of 0.65")
    inner = rw
    c_a, c_b, c_c = rx, rx + inner * 0.56, rx + inner * 0.74
    w_a, w_b, w_c = inner * 0.56, inner * 0.18, inner * 0.26
    for c, w, h in ((c_b, w_b, "ROC-AUC"), (c_c, w_c, "VERDICT")):
        text(s, c, BODY_Y + 0.26, w, 0.2,
             [(h, {"font": MONO, "size": 7.5, "color": FAINT, "bold": True})])
    rule(s, rx, BODY_Y + 0.44, rw, RULE, 0.008)

    cy = BODY_Y + 0.54
    tracks = [("Decision tree, plain",                  "0.6463", "did not pass",    MUTED,  False),
              ("Decision tree, balanced",               "0.6893", "passed",          MUTED,  False),
              ("Decision tree, balanced + importance",  "0.7063", "shipped",         NAVY,   True),
              ("XGBoost",                               "0.6702", "passed",          MUTED,  False)]
    for name, auc, verdict, col, strong in tracks:
        text(s, c_a, cy, w_a, 0.24,
             [(name, {"size": 10.5, "color": INK if strong else MUTED,
                      "bold": strong})])
        text(s, c_b, cy, w_b, 0.24,
             [(auc, {"font": MONO, "size": 10.5, "color": NAVY if strong else MUTED,
                     "bold": strong})])
        text(s, c_c, cy, w_c, 0.24,
             [(verdict, {"size": 10, "color": col, "bold": strong})])
        cy += 0.30
    rule(s, rx, cy - 0.04, rw, SOFT, 0.008)
    text(s, rx, cy + 0.08, rw, 0.4,
         [("Trained on the earliest 80% of encounters and tested on the most recent 20%, so "
           "every approach was judged on visits it had never seen.",
           {"size": 9, "color": FAINT, "line": 1.2})])

    label(s, rx, 4.66, rw, "What it established")
    items(s, rx, 4.90, rw, [
        ("The pipeline worked end to end.",
         "Cohort building, feature engineering, training, validation and a shipped model — all "
         "proven on real hospital records.", 0.66),
        ("It set the yardstick.",
         "0.7063 became the number every later model was measured against, and the CMS work "
         "reused its comorbidity weights so the scores stayed comparable.", 0.66),
        ("It framed the next question.",
         "Diabetes is one condition. The product needed all-cause adult inpatients, so the "
         "search moved to data with a wider population.", 0.66),
    ], gap=0.08, accent=NAVY)
    return s


# ---------------------------------------------------------------------------
# Slide 1 - CMS
# ---------------------------------------------------------------------------
def slide_one(prs):
    s = slide_frame(prs, "Stage 1",
                    "CMS DE-SynPUF — analysis, and the decision to leave it")
    heading(s, "Synthetic claims data could not support a clinical product.",
            [("Twenty CMS sample files were pulled, cleaned, linked and enriched into a single "
              "modelling table, then trained with ", {}),
             B("5-fold validation grouped by patient"),
             (". The score did not justify the compromises the data forced.", {})])

    # The five reasons ARE the slide - the score is context for them, so the
    # argument column is the wide one and the evidence column supports it.
    lx, lw = L, 4.75
    rx, rw = 5.85, 6.93

    anchor_figure(s, lx, BODY_Y, lw, "0.6893",
                  "ROC-AUC on CMS claims  ·  5-fold, grouped by patient", size=40)

    # A client is not expected to know what an AUC is, and a number nobody can
    # interpret is worse than no number.
    text(s, lx, 3.36, lw, 0.92,
         [([("AUC-ROC", {"bold": True, "color": INK}),
            (" stands for ", {}),
            ("Area Under the Receiver Operating Characteristic curve", {"italic": True}),
            (". In plain terms it is a mark out of 1 for how well the model sorts patients "
             "riskiest-first. 0.50 is random guessing, 1.00 is perfect. This one gets the "
             "order right 69% of the time.", {})],
           {"size": 9.5, "color": MUTED, "line": 1.22})])

    rect(s, lx, 4.34, 0.032, 1.00, SIGNAL)
    text(s, lx + 0.17, 4.34, lw - 0.17, 0.30,
         [("A weak score, on data that is not real.",
           {"font": DISPLAY, "size": 14, "color": SIGNAL, "line": 1.1})])
    text(s, lx + 0.17, 4.68, lw - 0.17, 0.68,
         [("DE-SynPUF is generated data. CMS publishes it for building and testing software, "
           "not for drawing conclusions about real beneficiaries.",
           {"size": 9.5, "color": MUTED, "line": 1.22})])

    rect(s, lx, 5.42, lw, 1.63, WHITE, SOFT)
    label(s, lx + 0.16, 5.58, lw - 0.32, "What was built")
    stats(s, lx + 0.16, 5.80, lw - 0.32, [
        ("Encounters",                     "1,332,755",       "hi"),
        ("Features",                       "58",              ""),
        ("Readmitted within 30 days",      "133,477 · 10.02%", ""),
        ("Laboratory results in the file", "0",               "warn"),
        ("Vital signs in the file",        "0",               "warn"),
    ], row_h=0.21, size=9.5)

    label(s, rx, BODY_Y, rw, "Why we moved to real clinical data — in order of weight")
    reasons = [
        ("It is synthetic, so the score cannot transfer to a real patient.",
         "A score on generated data is not a claim anyone can make in a clinic.", 0.62),
        ("No clinical measurements at all.",
         "All 58 columns are administrative — what was billed, paid and claimed. Not one "
         "laboratory result, not one vital sign.", 0.84),
        ("The explanations are unusable at the bedside.",
         "The dashboard names three reasons per patient. From claims those read “prior "
         "outpatient payment sum” — which held 54% of the prototype's importance, and which "
         "no coordinator can act on.", 1.06),
        ("ICD-9 only.",
         "No ICD-10 anywhere in the file, so the disease coding is frozen in an edition the "
         "United States stopped using in 2015.", 0.84),
        ("Medicare-only, and claims settle too late.",
         "65+ and disability, where our product is all-cause adult inpatients. A claim arrives "
         "weeks after the care it describes — weekly monitoring is structurally impossible.",
         0.84),
    ]
    cy = BODY_Y + 0.30
    for i, (head, sub, h) in enumerate(reasons, start=1):
        text(s, rx, cy, 0.28, 0.24,
             [(str(i), {"font": MONO, "size": 12, "color": NAVY, "bold": True})])
        text(s, rx + 0.36, cy - 0.02, rw - 0.36, 0.26,
             [(head, {"size": 12.5, "bold": True, "color": INK})])
        text(s, rx + 0.36, cy + 0.26, rw - 0.36, h - 0.26,
             [(sub, {"size": 10.5, "color": MUTED, "line": 1.22})])
        cy += h
        if i < len(reasons):
            rule(s, rx, cy - 0.06, rw, SOFT, 0.008)

    return s


# ---------------------------------------------------------------------------
# Slide 2 - MIMIC
# ---------------------------------------------------------------------------
def slide_two(prs):
    s = slide_frame(prs, "Stages 2–3",
                    "MIMIC-IV — acquisition, cohort and demographics")
    heading(s, "Real patients, real measurements, and almost nobody with one disease.",
            [("MIMIC-IV hosp — Beth Israel Deaconess, de-identified, credentialed access. ", {}),
             B("545,497 admissions across 223,291 patients"),
             (" and 6,364,488 diagnosis records. A lower score than CMS, made of things a "
              "clinician can act on.", {})])

    x1, x2, x3 = COL3_X
    cw = COL3_W

    # --- column 1: the model -------------------------------------------
    anchor_figure(s, x1, BODY_Y, cw, "0.7229", "AUC-ROC  ·  isotonically calibrated", size=36)
    text(s, x1, 3.40, cw, 0.66,
         [([("AUC-ROC", {"bold": True, "color": INK}),
            (" — Area Under the Receiver Operating Characteristic curve. A mark out of 1 for "
             "sorting patients riskiest-first: 0.50 is guessing, 1.00 is perfect. This gets "
             "the order right 72% of the time.", {})],
           {"size": 9.5, "color": MUTED, "line": 1.22})])
    rect(s, x1, 4.16, cw, 2.70, WHITE, SOFT)
    label(s, x1 + 0.16, 4.32, cw - 0.32, "The discharge model")
    stats(s, x1 + 0.16, 4.56, cw - 0.32, [
        ("Features  (48 are labs)", "94", ""),
        ("30-day prevalence", "19.63%", ""),
        # Just the mean: it is 6,364,488 / 545,497, both of which are on this
        # slide, so a client can check it. The median came from a different
        # population and pairing them invited an arithmetic question.
        ("Diagnoses per stay", "11.7 on average", ""),
        ("AUC-PR", "0.3921", ""),
        ("Brier score", "0.1404", ""),
        ("Calibration ratio", "1.01", "hi"),
    ], row_h=0.225, size=9.5)
    rule(s, x1 + 0.16, 5.94, cw - 0.32, SOFT, 0.008)
    text(s, x1 + 0.16, 6.04, cw - 0.32, 0.75,
         [("Split by patient, so nobody appears in two folds. Calibrated, so a 40% score "
           "means a real 40% chance — which is what lets a cost model sit on top of it.",
           {"size": 9, "color": MUTED, "line": 1.2})])

    # --- column 2: who they are -----------------------------------------
    label(s, x2, BODY_Y, cw, "Who the patients are")
    bars(s, x2, BODY_Y + 0.24, cw, [
        ("18–39", 1.00, "24%", NAVY), ("40–54", 0.79, "19%", NAVY),
        ("55–64", 0.75, "18%", NAVY), ("65–74", 0.71, "17%", NAVY),
        ("75–84", 0.58, "14%", NAVY), ("85+",   0.33, "8%",  NAVY),
    ])
    legend(s, x2, 4.06, cw,
           [("A ", {}), B("broad adult population, not an elderly one"),
            (" — a quarter are under 40. 61.1% come in once and never return; "
             "7.2% have five stays or more.", {})])

    label(s, x2, 4.86, cw, "Readmission peaks in middle age")
    bars(s, x2, 5.10, cw, [
        ("18–39", 0.70, "15.1%", BARSOFT), ("40–54", 1.00, "21.4%", SIGNAL),
        ("55–64", 1.00, "21.5%", SIGNAL),  ("65–74", 0.97, "20.8%", BARSOFT),
        ("75–84", 0.93, "20.0%", BARSOFT), ("85+",   0.87, "18.8%", BARSOFT),
    ])
    legend(s, x2, 6.56, cw,
           [("Diagnoses per stay almost double from youngest to oldest — ", {}),
            B("readmission does not follow"), (". Age alone is a poor triage signal.", {})])

    # --- column 3: how sick they are ------------------------------------
    label(s, x3, BODY_Y, cw, "30-day readmission rate, by conditions recorded")
    bars(s, x3, BODY_Y + 0.24, cw, [
        ("1 only", 0.30, "8.5%",  NAVY), ("2–4",   0.37, "10.4%", NAVY),
        ("5–9",    0.55, "15.4%", NAVY), ("10–14", 0.74, "20.8%", NAVY),
        ("15–19",  0.87, "24.4%", NAVY), ("20+",   1.00, "28.2%", SIGNAL),
    ])
    legend(s, x3, 4.06, cw,
           [("Stays grouped by how many conditions were coded, then the share of each "
             "readmitted within 30 days.", {})])

    rect(s, x3, 4.70, cw, 2.35, WHITE, SOFT)
    label(s, x3 + 0.16, 4.86, cw - 0.32, "What CMS could not supply")
    cy = 5.10
    # Columns measured against the CARD's inner width, not the grid column -
    # using the wider one pushed "MIMIC-IV" past the card edge.
    inner = cw - 0.32
    c_lab, c_cms, c_mim = x3 + 0.16, x3 + 0.16 + inner * 0.28, x3 + 0.16 + inner * 0.58
    w_lab, w_cms, w_mim = inner * 0.28, inner * 0.30, inner * 0.42
    text(s, c_cms, cy, w_cms, 0.2,
         [("CMS", {"font": MONO, "size": 7.5, "color": FAINT, "bold": True})])
    text(s, c_mim, cy, w_mim, 0.2,
         [("MIMIC-IV", {"font": MONO, "size": 7.5, "color": FAINT, "bold": True})])
    rule(s, x3 + 0.16, cy + 0.18, inner, RULE, 0.008)
    cy += 0.26
    for lab, cms, mim in [
        ("Nature",      "synthetic",     "real, de-identified"),
        ("Lab results", "none",          "48 features"),
        ("Medications", "how many filled", "drugs at discharge"),
        ("Coding",      "ICD-9 only",    "ICD-9 + ICD-10"),
        ("Timeliness",  "weeks late",    "during the stay"),
    ]:
        text(s, c_lab, cy, w_lab, 0.2, [(lab, {"size": 8.5, "color": MUTED})])
        text(s, c_cms, cy, w_cms, 0.2, [(cms, {"size": 8.5, "color": SIGNAL})])
        text(s, c_mim, cy, w_mim, 0.2, [(mim, {"size": 8.5, "color": INK, "bold": True})])
        cy += 0.235
    rule(s, x3 + 0.16, cy - 0.02, inner, SOFT, 0.008)
    text(s, x3 + 0.16, cy + 0.07, inner, 0.5,
         [([("MIMIC codes in ", {}),
            ("both editions — 45.7% ICD-9, 54.3% ICD-10", {"bold": True, "color": INK}),
            (".", {})],
           {"size": 8.5, "color": FAINT, "line": 1.2})])
    return s


# ---------------------------------------------------------------------------
# Slide 3 - the product
# ---------------------------------------------------------------------------
def slide_three(prs):
    s = slide_frame(prs, "Stage 3",
                    "MIMIC-IV — disease burden and the coding behind it")
    heading(s, "Nobody here has one illness in one place.",
            [("When a patient is discharged, the record lists everything they were treated "
              "for. On an average stay that is ", {}), B("11.7 separate problems"),
             (" — and they are spread across the body rather than concentrated in one place.",
              {})])

    x1, x2, x3 = COL3_X
    cw = COL3_W

    # ---- column 1: how scattered one stay is ---------------------------
    # The anchor has to be the number a client can read without a footnote.
    # 6.1 chapters needed a paragraph of explanation before it meant anything;
    # "11.7 diagnoses on the average stay" needs none, and makes the same point.
    anchor_figure(s, x1, BODY_Y, cw, "11.7",
                  "Diagnoses recorded on the average stay", size=36)

    label(s, x1, 3.52, cw, "How many different areas one stay involves")
    bars(s, x1, 3.76, cw, [
        ("1 only",  0.112, "3.9%",  BARSOFT), ("2–4",   0.859, "29.9%", NAVY),
        ("5–7",     1.000, "34.8%", NAVY),    ("8–10",  0.667, "23.2%", NAVY),
        ("11+",     0.236, "8.2%",  NAVY),
    ])
    legend(s, x1, 4.98, cw,
           [("Every diagnosis is sorted into one of 20 groups — mostly body areas like heart, "
             "lungs and kidneys, some not. ", {}),
            B("96.1% of stays involve two or more"), (".", {})],
           h=0.62)

    rect(s, x1, 5.78, cw, 1.27, WHITE, SOFT)
    label(s, x1 + 0.16, 5.90, cw - 0.32, "Men return more often")
    inner1 = cw - 0.32
    # Two columns, no score: the Charlson chart in the next column already
    # explains what it measures, and a bare "CHARLSON" header here was one
    # more term of art on a slide that can carry none.
    cols1 = [(0.00, 0.42, ""), (0.42, 0.28, "SHARE"), (0.70, 0.30, "READMITTED")]
    for off, wid, head in cols1:
        if head:
            text(s, x1 + 0.16 + inner1 * off, 6.08, inner1 * wid, 0.2,
                 [(head, {"font": MONO, "size": 7, "color": FAINT, "bold": True})])
    rule(s, x1 + 0.16, 6.24, inner1, RULE, 0.008)
    for i, (who, share, rd) in enumerate([("Female", "53%", "18.2%"),
                                          ("Male",   "47%", "21.4%")]):
        cy = 6.31 + i * 0.195
        for (off, wid, _), v in zip(cols1, [who, share, rd]):
            bold = (who == "Male" and v == "21.4%")
            text(s, x1 + 0.16 + inner1 * off, cy, inner1 * wid, 0.2,
                 [(v, {"size": 9, "color": SIGNAL if bold else (MUTED if v is who else INK),
                       "bold": bold})])
    text(s, x1 + 0.16, 6.78, inner1, 0.22,
         [("They also carry more long-term illness.",
           {"size": 8.5, "color": FAINT, "line": 1.2})])

    # ---- column 2: long-term illness -----------------------------------
    label(s, x2, BODY_Y, cw, "30-day readmission, by Charlson score")
    bars(s, x2, BODY_Y + 0.24, cw, [
        ("0",     0.387, "12.5%", BARSOFT), ("1",   0.511, "16.5%", NAVY),
        ("2",     0.681, "22.0%", NAVY),    ("3–4", 0.780, "25.2%", NAVY),
        ("5–7",   0.885, "28.6%", NAVY),    ("8+",  1.000, "32.3%", SIGNAL),
    ])
    legend(s, x2, 4.06, cw,
           [("Charlson counts only ", {}), B("17 serious long-term conditions"),
            (", weighting severe ones higher. 31.9% of stays score zero.", {})], h=0.52)

    rect(s, x2, 4.78, cw, 2.27, WHITE, SOFT)
    label(s, x2 + 0.16, 4.94, cw - 0.32, "Conditions travel together")
    # All six, not a selection: showing four of the top six reads as a top-four
    # list. And the kidney pair is TWO kidney conditions - shortening it to
    # "hypertensive + kidney disease" changed what it claims.
    stats(s, x2 + 0.16, 5.18, cw - 0.32, [
        ("Cholesterol + high blood pressure",     "13,633", ""),
        ("Cholesterol + history of smoking",      "9,062",  ""),
        ("Type 2 diabetes + blood pressure",      "8,487",  ""),
        ("Major depression + anxiety",            "5,306",  ""),
        ("Hypertensive kidney + chronic kidney",  "4,984",  ""),
        ("Irregular heartbeat + heart failure",   "4,951",  ""),
    ], row_h=0.20, size=8.5, label_frac=0.74)
    rule(s, x2 + 0.16, 6.42, cw - 0.32, SOFT, 0.008)
    text(s, x2 + 0.16, 6.52, cw - 0.32, 0.45,
         [("Hospital stays where both were coded on the same record. The last two are "
           "recognised combinations where each makes the other harder to treat.",
           {"size": 8.5, "color": FAINT, "line": 1.2})])

    # ---- column 3: what the cohort actually carries ---------------------
    label(s, x3, BODY_Y, cw, "Most common long-term conditions")
    bars(s, x3, BODY_Y + 0.24, cw, [
        ("Lung",     1.000, "20.3%", NAVY), ("Heart fail", 0.828, "16.8%", NAVY),
        ("Kidney",   0.823, "16.7%", NAVY), ("Diabetes",   0.818, "16.6%", NAVY),
        ("Cancer",   0.493, "10.0%", NAVY), ("Prior MI",   0.448, "9.1%",  NAVY),
        ("Vascular", 0.399, "8.1%",  NAVY), ("Stroke",     0.379, "7.7%",  NAVY),
    ], lab_w=0.78)
    legend(s, x3, 4.54, cw,
           [("Share of stays carrying each condition. A stay usually carries several of them "
             "at once.", {})], h=0.40)

    rect(s, x3, 5.10, cw, 1.95, WHITE, SOFT)
    label(s, x3 + 0.16, 5.26, cw - 0.32, "The coding itself")
    stats(s, x3 + 0.16, 5.50, cw - 0.32, [
        ("Diagnosis records",              "6,364,488", ""),
        ("Distinct codes used",            "28,562",    "hi"),
        ("Codes used on exactly one stay", "6,160",     ""),
        ("Codes covering half of records", "250",       "hi"),
    ], row_h=0.235, size=9)
    rule(s, x3 + 0.16, 6.46, cw - 0.32, SOFT, 0.008)
    text(s, x3 + 0.16, 6.56, cw - 0.32, 0.55,
         [("Under 1% of the codes account for half of every diagnosis ever recorded; a fifth "
           "of them appear on a single stay.", {"size": 8.5, "color": FAINT, "line": 1.2})])
    return s


def main() -> None:
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(W), Inches(H)

    slide_zero(prs)
    slide_one(prs)
    slide_two(prs)
    slide_three(prs)

    core = prs.core_properties
    core.title = "From CMS to MIMIC"
    core.subject = "Preventra — readmission risk programme"
    core.author = "Preventra"

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    prs.save(OUT)
    print(f"wrote {OUT}")
    print(f"  {len(prs.slides._sldIdLst)} slides, {W}in x {H}in (16:9)")


if __name__ == "__main__":
    main()
