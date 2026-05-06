"""
GMCAudit.io — PDF Report Generator
Produces a professional, branded compliance report
"""

import os
import asyncio
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, KeepTogether
)
from reportlab.graphics.shapes import Drawing, Rect, String, Circle
from reportlab.graphics import renderPDF
from reportlab.pdfgen import canvas
from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate


# ─────────────────────────────────────────────
# BRAND COLORS
# ─────────────────────────────────────────────

C_BG        = colors.HexColor("#0A0A0F")       # near black background
C_SURFACE   = colors.HexColor("#13131A")       # card surface
C_BORDER    = colors.HexColor("#1E1E2E")       # subtle border
C_PRIMARY   = colors.HexColor("#6366F1")       # indigo accent
C_PRIMARY_L = colors.HexColor("#818CF8")       # lighter indigo
C_WHITE     = colors.HexColor("#FFFFFF")
C_MUTED     = colors.HexColor("#6B7280")
C_BODY      = colors.HexColor("#D1D5DB")
C_FAIL      = colors.HexColor("#EF4444")       # red
C_FAIL_BG   = colors.HexColor("#1F0A0A")
C_WARN      = colors.HexColor("#F59E0B")       # amber
C_WARN_BG   = colors.HexColor("#1F1500")
C_PASS      = colors.HexColor("#10B981")       # emerald
C_PASS_BG   = colors.HexColor("#071A12")

W, H = A4   # 210 x 297 mm


# ─────────────────────────────────────────────
# STYLES
# ─────────────────────────────────────────────

def make_styles():
    return {
        "h1": ParagraphStyle("h1",
            fontName="Helvetica-Bold", fontSize=28, leading=34,
            textColor=C_WHITE, spaceAfter=4),
        "h2": ParagraphStyle("h2",
            fontName="Helvetica-Bold", fontSize=16, leading=20,
            textColor=C_WHITE, spaceAfter=8),
        "h3": ParagraphStyle("h3",
            fontName="Helvetica-Bold", fontSize=12, leading=16,
            textColor=C_WHITE, spaceAfter=4),
        "h4": ParagraphStyle("h4",
            fontName="Helvetica-Bold", fontSize=10, leading=13,
            textColor=C_WHITE, spaceAfter=2),
        "body": ParagraphStyle("body",
            fontName="Helvetica", fontSize=9, leading=14,
            textColor=C_BODY, spaceAfter=4),
        "body_white": ParagraphStyle("body_white",
            fontName="Helvetica", fontSize=9, leading=14,
            textColor=C_WHITE, spaceAfter=4),
        "muted": ParagraphStyle("muted",
            fontName="Helvetica", fontSize=8, leading=11,
            textColor=C_MUTED, spaceAfter=2),
        "label": ParagraphStyle("label",
            fontName="Helvetica-Bold", fontSize=7, leading=10,
            textColor=C_MUTED, spaceAfter=1),
        "score_big": ParagraphStyle("score_big",
            fontName="Helvetica-Bold", fontSize=64, leading=72,
            textColor=C_WHITE, alignment=TA_CENTER),
        "center": ParagraphStyle("center",
            fontName="Helvetica", fontSize=9, leading=13,
            textColor=C_BODY, alignment=TA_CENTER),
        "center_bold": ParagraphStyle("center_bold",
            fontName="Helvetica-Bold", fontSize=10, leading=14,
            textColor=C_WHITE, alignment=TA_CENTER),
        "fix_step": ParagraphStyle("fix_step",
            fontName="Helvetica", fontSize=8.5, leading=13,
            textColor=C_BODY, leftIndent=0, spaceAfter=2),
        "category_label": ParagraphStyle("category_label",
            fontName="Helvetica-Bold", fontSize=7, leading=9,
            textColor=C_PRIMARY_L, spaceAfter=2),
        "issue_name": ParagraphStyle("issue_name",
            fontName="Helvetica-Bold", fontSize=10, leading=13,
            textColor=C_WHITE, spaceAfter=2),
        "issue_desc": ParagraphStyle("issue_desc",
            fontName="Helvetica", fontSize=8.5, leading=13,
            textColor=C_BODY, spaceAfter=4),
    }


# ─────────────────────────────────────────────
# PAGE CANVAS — header/footer on every page
# ─────────────────────────────────────────────

class ReportCanvas(canvas.Canvas):
    def __init__(self, *args, domain="", scanned_at="", **kwargs):
        super().__init__(*args, **kwargs)
        self._doc_domain = domain
        self._doc_scanned_at = scanned_at
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for i, state in enumerate(self._saved_page_states):
            self.__dict__.update(state)
            self._draw_page(i + 1, num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def _draw_page(self, page_num, total_pages):
        self.saveState()
        # Dark background
        self.setFillColor(C_BG)
        self.rect(0, 0, W, H, fill=1, stroke=0)

        if page_num == 1:
            self._draw_cover_bg()
        else:
            self._draw_inner_bg()

        # Top bar
        self.setFillColor(colors.HexColor("#0D0D14"))
        self.rect(0, H - 14*mm, W, 14*mm, fill=1, stroke=0)

        # Logo text in top bar
        self.setFillColor(C_PRIMARY_L)
        self.setFont("Helvetica-Bold", 9)
        self.drawString(15*mm, H - 9*mm, "GMCAudit.io")

        # Domain in top bar
        self.setFillColor(C_MUTED)
        self.setFont("Helvetica", 8)
        self.drawString(50*mm, H - 9*mm, self._doc_domain)

        # Page number top right
        self.setFillColor(C_MUTED)
        self.setFont("Helvetica", 8)
        self.drawRightString(W - 15*mm, H - 9*mm, f"Page {page_num} of {total_pages}")

        # Bottom bar
        self.setFillColor(colors.HexColor("#0D0D14"))
        self.rect(0, 0, W, 10*mm, fill=1, stroke=0)
        self.setFillColor(C_MUTED)
        self.setFont("Helvetica", 7)
        self.drawString(15*mm, 3.5*mm, f"Scanned on {self._doc_scanned_at}  •  GMCAudit.io  •  Confidential")
        self.drawRightString(W - 15*mm, 3.5*mm, "gmcaudit.io")

        self.restoreState()

    def _draw_cover_bg(self):
        # Subtle gradient-like left accent bar
        self.setFillColor(C_PRIMARY)
        self.rect(0, 0, 3, H, fill=1, stroke=0)
        # Decorative circle
        self.setFillColor(colors.HexColor("#1A1A2E"))
        self.circle(W + 20*mm, H * 0.6, 80*mm, fill=1, stroke=0)
        self.setFillColor(colors.HexColor("#16162A"))
        self.circle(W + 5*mm, H * 0.6, 60*mm, fill=1, stroke=0)

    def _draw_inner_bg(self):
        # Left accent bar
        self.setFillColor(C_PRIMARY)
        self.rect(0, 0, 2, H, fill=1, stroke=0)


# ─────────────────────────────────────────────
# HELPER FLOWABLES
# ─────────────────────────────────────────────

def spacer(h=4):
    return Spacer(1, h*mm)

def divider(color=C_BORDER):
    return HRFlowable(width="100%", thickness=0.5, color=color, spaceAfter=4, spaceBefore=4)

def score_color(score):
    if score < 50:
        return C_FAIL
    elif score < 75:
        return C_WARN
    return C_PASS

def status_color(status):
    return {
        "FAIL": C_FAIL,
        "WARNING": C_WARN,
        "PASS": C_PASS,
        "SKIP": C_MUTED,
    }.get(status, C_MUTED)

def status_bg(status):
    return {
        "FAIL": C_FAIL_BG,
        "WARNING": C_WARN_BG,
        "PASS": C_PASS_BG,
        "SKIP": colors.HexColor("#111111"),
    }.get(status, colors.HexColor("#111111"))


# ─────────────────────────────────────────────
# PAGE 1: COVER / STORE INTELLIGENCE
# ─────────────────────────────────────────────

def build_cover_page(result: dict, styles: dict) -> list:
    story = []
    s = styles
    intel = result.get("store_intelligence", {})
    domain = result.get("domain", "")
    score = result.get("score", 0)
    risk = result.get("risk_level", "high").upper()
    scanned_at = result.get("scanned_at", "")[:10]

    # Top spacing (below header bar)
    story.append(spacer(6))

    # ── SCORE HERO SECTION ──
    score_col = score_color(score)

    # Risk badge
    risk_color_map = {"HIGH": C_FAIL, "MEDIUM": C_WARN, "LOW": C_PASS}
    risk_bg_map = {"HIGH": C_FAIL_BG, "MEDIUM": C_WARN_BG, "LOW": C_PASS_BG}
    rc = risk_color_map.get(risk, C_MUTED)
    rb = risk_bg_map.get(risk, colors.HexColor("#111"))

    badge_data = [[Paragraph(f"● {risk} RISK · SCAN COMPLETE", ParagraphStyle(
        "badge", fontName="Helvetica-Bold", fontSize=8, textColor=rc, alignment=TA_CENTER
    ))]]
    badge = Table(badge_data, colWidths=[80*mm])
    badge.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), rb),
        ("ROUNDEDCORNERS", [4]),
        ("TOPPADDING", (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
    ]))

    story.append(Table([[badge]], colWidths=[W - 30*mm]))
    story.append(spacer(5))

    # Big score number
    score_para = Paragraph(f'<font color="{score_col.hexval()}">{score}%</font>', s["score_big"])
    story.append(score_para)
    story.append(Paragraph(f"GMC Compliance Score for <b>{domain}</b>", s["center"]))
    story.append(spacer(6))

    # ── 3 STAT BOXES ──
    def stat_box(label, value, color):
        return Table(
            [[Paragraph(str(value), ParagraphStyle("sv", fontName="Helvetica-Bold",
                fontSize=28, textColor=color, alignment=TA_CENTER))],
             [Paragraph(label, ParagraphStyle("sl", fontName="Helvetica-Bold",
                fontSize=7, textColor=C_MUTED, alignment=TA_CENTER))]],
            colWidths=[52*mm]
        )

    boxes = Table(
        [[stat_box("CRITICAL ISSUES", result["failed"], C_FAIL),
          stat_box("WARNINGS", result["warnings"], C_WARN),
          stat_box("CHECKS PASSED", result["passed"], C_PASS)]],
        colWidths=[56*mm, 56*mm, 56*mm]
    )
    boxes.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (0,0), C_FAIL_BG),
        ("BACKGROUND", (1,0), (1,0), C_WARN_BG),
        ("BACKGROUND", (2,0), (2,0), C_PASS_BG),
        ("TOPPADDING", (0,0), (-1,-1), 8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("ROUNDEDCORNERS", [4]),
        ("LEFTPADDING", (0,0), (-1,-1), 4),
        ("RIGHTPADDING", (0,0), (-1,-1), 4),
        ("LINEBEFORE", (1,0), (1,0), 1, C_BORDER),
        ("LINEBEFORE", (2,0), (2,0), 1, C_BORDER),
    ]))
    story.append(boxes)
    story.append(spacer(8))
    story.append(divider())

    # ── STORE INTELLIGENCE ──
    story.append(spacer(3))
    story.append(Paragraph("STORE INTELLIGENCE", s["category_label"]))
    story.append(spacer(2))

    # Business metrics row
    def intel_cell(label, value):
        return [
            Paragraph(label, s["label"]),
            Paragraph(str(value) if value else "—", s["body_white"]),
        ]

    domain_age = intel.get("domain_age_days", "—")
    if domain_age != "—":
        domain_age = f"{domain_age} days"

    metrics = [
        ["Domain", domain],
        ["Products Found", intel.get("product_count", "—")],
        ["Collections", intel.get("collection_count", "—")],
        ["Pages", intel.get("page_count", "—")],
        ["Theme", intel.get("theme", "Not detected")],
        ["Language", intel.get("language", "en")],
        ["Scan Time", intel.get("scan_time", "—")],
        ["Shopify", "Yes" if intel.get("is_shopify") else "Unconfirmed"],
    ]

    left_metrics = metrics[:4]
    right_metrics = metrics[4:]

    def build_metric_col(items):
        rows = []
        for label, value in items:
            rows.append([
                Paragraph(label.upper(), s["label"]),
                Paragraph(str(value), s["body_white"]),
            ])
        t = Table(rows, colWidths=[30*mm, 52*mm])
        t.setStyle(TableStyle([
            ("TOPPADDING", (0,0), (-1,-1), 3),
            ("BOTTOMPADDING", (0,0), (-1,-1), 3),
            ("VALIGN", (0,0), (-1,-1), "TOP"),
            ("LINEBELOW", (0,0), (-1,-2), 0.3, C_BORDER),
        ]))
        return t

    metrics_table = Table(
        [[build_metric_col(left_metrics), build_metric_col(right_metrics)]],
        colWidths=[86*mm, 86*mm]
    )
    metrics_table.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 0),
        ("RIGHTPADDING", (0,0), (-1,-1), 8),
    ]))
    story.append(metrics_table)
    story.append(spacer(5))
    story.append(divider())

    # ── CONTACT INFO ──
    story.append(spacer(3))
    story.append(Paragraph("CONTACT INFORMATION", s["category_label"]))
    story.append(spacer(2))

    contact_rows = [
        ["EMAIL", intel.get("email", "Not found")],
        ["PHONE", intel.get("phone", "Not found")],
        ["SOCIAL", ", ".join(intel.get("social_platforms", [])) or "Not found"],
    ]

    for label, val in contact_rows:
        row_color = C_FAIL if val == "Not found" else C_BODY
        ct = Table([[
            Paragraph(label, s["label"]),
            Paragraph(str(val), ParagraphStyle("cv", fontName="Helvetica",
                fontSize=9, textColor=row_color)),
        ]], colWidths=[30*mm, 140*mm])
        ct.setStyle(TableStyle([
            ("TOPPADDING", (0,0), (-1,-1), 3),
            ("BOTTOMPADDING", (0,0), (-1,-1), 3),
            ("LINEBELOW", (0,0), (-1,-1), 0.3, C_BORDER),
        ]))
        story.append(ct)

    story.append(spacer(5))
    story.append(divider())

    # ── CATEGORY SCORE SUMMARY ──
    story.append(spacer(3))
    story.append(Paragraph("CHECK SUMMARY BY CATEGORY", s["category_label"]))
    story.append(spacer(3))

    checks = result.get("checks", [])
    by_cat = {}
    for c in checks:
        cat = c["category"]
        if cat not in by_cat:
            by_cat[cat] = {"pass": 0, "fail": 0, "warn": 0}
        if c["status"] == "PASS":
            by_cat[cat]["pass"] += 1
        elif c["status"] == "FAIL":
            by_cat[cat]["fail"] += 1
        elif c["status"] == "WARNING":
            by_cat[cat]["warn"] += 1

    summary_data = [
        [
            Paragraph("CATEGORY", s["label"]),
            Paragraph("PASS", ParagraphStyle("ph", fontName="Helvetica-Bold", fontSize=7, textColor=C_PASS, alignment=TA_CENTER)),
            Paragraph("WARN", ParagraphStyle("ph", fontName="Helvetica-Bold", fontSize=7, textColor=C_WARN, alignment=TA_CENTER)),
            Paragraph("FAIL", ParagraphStyle("ph", fontName="Helvetica-Bold", fontSize=7, textColor=C_FAIL, alignment=TA_CENTER)),
        ]
    ]
    for cat, counts in by_cat.items():
        summary_data.append([
            Paragraph(cat, s["body"]),
            Paragraph(str(counts["pass"]), ParagraphStyle("pv", fontName="Helvetica-Bold", fontSize=9, textColor=C_PASS, alignment=TA_CENTER)),
            Paragraph(str(counts["warn"]), ParagraphStyle("wv", fontName="Helvetica-Bold", fontSize=9, textColor=C_WARN, alignment=TA_CENTER)),
            Paragraph(str(counts["fail"]), ParagraphStyle("fv", fontName="Helvetica-Bold", fontSize=9, textColor=C_FAIL, alignment=TA_CENTER)),
        ])

    summary_table = Table(summary_data, colWidths=[110*mm, 20*mm, 20*mm, 20*mm])
    ts = [
        ("BACKGROUND", (0,0), (-1,0), C_BORDER),
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("LEFTPADDING", (0,0), (-1,-1), 6),
        ("RIGHTPADDING", (0,0), (-1,-1), 6),
        ("ALIGN", (1,0), (-1,-1), "CENTER"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("LINEBELOW", (0,0), (-1,-2), 0.3, C_BORDER),
    ]
    # Highlight rows with failures
    for i, (cat, counts) in enumerate(by_cat.items(), 1):
        if counts["fail"] > 0:
            ts.append(("BACKGROUND", (0,i), (-1,i), C_FAIL_BG))
        elif counts["warn"] > 0:
            ts.append(("BACKGROUND", (0,i), (-1,i), C_WARN_BG))
    summary_table.setStyle(TableStyle(ts))
    story.append(summary_table)

    return story


# ─────────────────────────────────────────────
# ISSUE BLOCK — each failed/warning check
# ─────────────────────────────────────────────

def build_issue_block(check: dict, styles: dict) -> list:
    s = styles
    status = check["status"]
    sc = status_color(status)
    sb = status_bg(status)

    elements = []

    # Status badge + check name header
    badge_text = f"● {status}"
    badge_para = Paragraph(badge_text, ParagraphStyle(
        "bp", fontName="Helvetica-Bold", fontSize=7.5,
        textColor=sc, alignment=TA_CENTER
    ))
    badge_cell = Table([[badge_para]], colWidths=[22*mm])
    badge_cell.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), sb),
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("LEFTPADDING", (0,0), (-1,-1), 4),
        ("RIGHTPADDING", (0,0), (-1,-1), 4),
    ]))

    cat_para = Paragraph(check["category"].upper(), s["category_label"])
    name_para = Paragraph(check["name"], s["issue_name"])

    header_table = Table([
        [badge_cell, Table([[cat_para], [name_para]], colWidths=[140*mm])]
    ], colWidths=[26*mm, 146*mm])
    header_table.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING", (0,0), (-1,-1), 0),
        ("RIGHTPADDING", (0,0), (-1,-1), 0),
        ("TOPPADDING", (0,0), (-1,-1), 2),
        ("BOTTOMPADDING", (0,0), (-1,-1), 2),
    ]))

    # Full block with left border color
    issue_content = [
        [header_table],
    ]

    # Description
    if check.get("description"):
        issue_content.append([Paragraph(check["description"], s["issue_desc"])])

    # URLs affected
    if check.get("urls"):
        url_text = "PAGES AFFECTED: " + "  •  ".join(check["urls"][:4])
        issue_content.append([Paragraph(url_text, ParagraphStyle(
            "url", fontName="Helvetica", fontSize=7.5,
            textColor=C_MUTED, spaceAfter=3
        ))])

    # Fix guide
    if check.get("fix"):
        issue_content.append([Paragraph("ACTION REQUIRED", ParagraphStyle(
            "fix_label", fontName="Helvetica-Bold", fontSize=7.5,
            textColor=sc, spaceAfter=2
        ))])
        for line in check["fix"].split("\n"):
            line = line.strip()
            if line:
                issue_content.append([Paragraph(line, s["fix_step"])])

    block_table = Table(issue_content, colWidths=[172*mm])
    block_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), sb),
        ("TOPPADDING", (0,0), (-1,-1), 3),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
        ("LEFTPADDING", (0,0), (-1,-1), 8),
        ("RIGHTPADDING", (0,0), (-1,-1), 8),
        ("LINEBEFORE", (0,0), (0,-1), 3, sc),
    ]))

    elements.append(KeepTogether([block_table, spacer(3)]))
    return elements


# ─────────────────────────────────────────────
# ISSUE PAGES
# ─────────────────────────────────────────────

def build_issues_pages(result: dict, styles: dict) -> list:
    story = []
    s = styles
    checks = result.get("checks", [])

    # Sort: FAIL first, then WARNING
    fails = [c for c in checks if c["status"] == "FAIL"]
    warnings = [c for c in checks if c["status"] == "WARNING"]
    passes = [c for c in checks if c["status"] == "PASS"]

    story.append(PageBreak())
    story.append(spacer(4))

    total_issues = len(fails) + len(warnings)
    story.append(Paragraph(
        f"{total_issues} STORE COMPLIANCE ISSUES DETECTED",
        ParagraphStyle("big_header", fontName="Helvetica-Bold", fontSize=18,
            textColor=C_FAIL if total_issues > 5 else C_WARN, alignment=TA_CENTER)
    ))
    story.append(spacer(6))
    story.append(divider(C_BORDER))
    story.append(spacer(4))

    # CRITICAL ISSUES
    if fails:
        story.append(Paragraph(f"CRITICAL ISSUES ({len(fails)})", s["category_label"]))
        story.append(Paragraph(
            "These issues will block GMC approval or cause suspension. Fix all before submitting.",
            ParagraphStyle("warn_note", fontName="Helvetica", fontSize=8.5,
                textColor=C_FAIL, spaceAfter=8)
        ))
        for check in fails:
            story.extend(build_issue_block(check, s))
        story.append(spacer(4))

    # WARNINGS
    if warnings:
        story.append(divider())
        story.append(spacer(2))
        story.append(Paragraph(f"WARNINGS ({len(warnings)})", s["category_label"]))
        story.append(Paragraph(
            "These issues may trigger GMC flags or reduce your trust score. Fix them after critical issues.",
            ParagraphStyle("warn_note2", fontName="Helvetica", fontSize=8.5,
                textColor=C_WARN, spaceAfter=8)
        ))
        for check in warnings:
            story.extend(build_issue_block(check, s))

    return story


# ─────────────────────────────────────────────
# FINAL SUMMARY PAGE
# ─────────────────────────────────────────────

def build_summary_page(result: dict, styles: dict) -> list:
    story = []
    s = styles
    checks = result.get("checks", [])

    fails = [c for c in checks if c["status"] == "FAIL"]
    warnings = [c for c in checks if c["status"] == "WARNING"]

    story.append(PageBreak())
    story.append(spacer(4))
    story.append(Paragraph("REMEDIATION SUMMARY", s["h2"]))
    story.append(Paragraph(
        "Complete these fixes in order. Critical issues first, then warnings.",
        s["body"]
    ))
    story.append(spacer(4))
    story.append(divider())
    story.append(spacer(3))

    all_issues = [(c, "FAIL") for c in fails] + [(c, "WARNING") for c in warnings]

    for i, (check, severity) in enumerate(all_issues, 1):
        sc = C_FAIL if severity == "FAIL" else C_WARN
        sb = C_FAIL_BG if severity == "FAIL" else C_WARN_BG

        num_para = Paragraph(str(i), ParagraphStyle(
            "num", fontName="Helvetica-Bold", fontSize=11,
            textColor=sc, alignment=TA_CENTER
        ))
        num_cell = Table([[num_para]], colWidths=[10*mm])
        num_cell.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,-1), sb),
            ("TOPPADDING", (0,0), (-1,-1), 3),
            ("BOTTOMPADDING", (0,0), (-1,-1), 3),
            ("ALIGN", (0,0), (-1,-1), "CENTER"),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ]))

        content_cell = Table([
            [Paragraph(f'<font color="{sc.hexval()}">[{severity}]</font> {check["name"]}',
                ParagraphStyle("sn", fontName="Helvetica-Bold", fontSize=9, textColor=C_WHITE))],
            [Paragraph(check["description"][:120] + ("..." if len(check["description"]) > 120 else ""),
                ParagraphStyle("sd", fontName="Helvetica", fontSize=8, textColor=C_BODY))],
        ], colWidths=[155*mm])
        content_cell.setStyle(TableStyle([
            ("TOPPADDING", (0,0), (-1,-1), 2),
            ("BOTTOMPADDING", (0,0), (-1,-1), 2),
            ("LEFTPADDING", (0,0), (-1,-1), 0),
        ]))

        row = Table([[num_cell, content_cell]], colWidths=[14*mm, 158*mm])
        row.setStyle(TableStyle([
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ("LEFTPADDING", (0,0), (-1,-1), 0),
            ("RIGHTPADDING", (0,0), (-1,-1), 0),
            ("TOPPADDING", (0,0), (-1,-1), 0),
            ("BOTTOMPADDING", (0,0), (-1,-1), 0),
        ]))
        story.append(KeepTogether([row, spacer(2)]))

    story.append(spacer(6))
    story.append(divider())
    story.append(spacer(4))

    # Footer note
    footer_note = Table([[
        Paragraph(
            f"This report was generated by GMCAudit.io on {result.get('scanned_at', '')[:10]}. "
            f"After fixing all issues, run a re-scan to verify your store's compliance before submitting to Google Merchant Center. "
            f"Your re-scan is included with this report.",
            ParagraphStyle("fn", fontName="Helvetica", fontSize=8, textColor=C_MUTED, alignment=TA_CENTER)
        )
    ]], colWidths=[172*mm])
    footer_note.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), C_SURFACE),
        ("TOPPADDING", (0,0), (-1,-1), 8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
        ("LEFTPADDING", (0,0), (-1,-1), 10),
        ("RIGHTPADDING", (0,0), (-1,-1), 10),
    ]))
    story.append(footer_note)

    return story


# ─────────────────────────────────────────────
# MAIN GENERATOR
# ─────────────────────────────────────────────

async def generate_pdf(result: dict, scan_id: str) -> str:
    """Generate PDF report and return file path."""
    os.makedirs("/tmp/gmcaudit_reports", exist_ok=True)
    output_path = f"/tmp/gmcaudit_reports/{scan_id}.pdf"

    domain = result.get("domain", "store")
    scanned_at = result.get("scanned_at", "")[:10]

    styles = make_styles()

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=15*mm,
        rightMargin=15*mm,
        topMargin=20*mm,
        bottomMargin=15*mm,
        title=f"GMC Compliance Report — {domain}",
        author="GMCAudit.io",
        subject="Google Merchant Center Compliance Audit",
    )

    story = []
    story.extend(build_cover_page(result, styles))
    story.extend(build_issues_pages(result, styles))
    story.extend(build_summary_page(result, styles))

    def make_canvas(filename, doc=None, **kwargs):
        return ReportCanvas(
            filename,
            pagesize=A4,
            domain=domain,
            scanned_at=scanned_at,
        )

    doc.build(story, canvasmaker=make_canvas)
    return output_path


# ─────────────────────────────────────────────
# TEST
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import sys, json, asyncio

    # Use mock data if no scan result provided
    mock_result = {
        "url": "https://makfool.com",
        "domain": "makfool.com",
        "scanned_at": "2026-05-06T12:00:00",
        "scan_time_seconds": 10.7,
        "score": 42.4,
        "risk_level": "high",
        "total_checks": 33,
        "passed": 9,
        "failed": 14,
        "warnings": 10,
        "skipped": 0,
        "store_intelligence": {
            "domain": "makfool.com",
            "email": "Not found",
            "phone": "Not found",
            "product_count": 0,
            "collection_count": 0,
            "page_count": 0,
            "theme": "Not detected",
            "language": "en",
            "scan_time": "10.7s",
            "is_shopify": False,
            "social_platforms": [],
        },
        "checks": [
            {
                "id": 14, "category": "Policy Pages",
                "name": "Shipping Policy Exists",
                "status": "FAIL", "severity": "critical",
                "description": "Shipping policy not found. This is required by GMC.",
                "fix": "1. In Shopify admin go to Settings → Policies.\n2. Add your Shipping Policy.\n3. Shopify will automatically create it at /policies/shipping.\n4. Include: delivery timeframes, shipping costs, carriers, and lost package policy.",
                "urls": [], "details": {}
            },
            {
                "id": 17, "category": "Policy Pages",
                "name": "Refund Policy Exists",
                "status": "FAIL", "severity": "critical",
                "description": "Refund/Return policy not found. This is required by GMC.",
                "fix": "1. In Shopify admin go to Settings → Policies.\n2. Add your Return Policy.\n3. Shopify creates it at /policies/refunds automatically.",
                "urls": [], "details": {}
            },
            {
                "id": 13, "category": "Contact & Business Info",
                "name": "Contact Page",
                "status": "FAIL", "severity": "critical",
                "description": "No contact page found. GMC requires a reachable contact page.",
                "fix": "1. In Shopify admin, create a new page titled 'Contact Us'.\n2. Add contact form, email address, and phone number.\n3. Link it in your main navigation.",
                "urls": [], "details": {}
            },
            {
                "id": 9, "category": "Contact & Business Info",
                "name": "Physical Address",
                "status": "FAIL", "severity": "critical",
                "description": "No physical address found on store.",
                "fix": "1. Add your business address to the contact page and footer.\n2. Virtual mailbox services are acceptable.\n3. Must match address registered in your GMC account.",
                "urls": [], "details": {}
            },
            {
                "id": 1, "category": "Trust & Domain",
                "name": "Domain Age",
                "status": "WARNING", "severity": "warning",
                "description": "Could not determine domain age. WHOIS data may be private.",
                "fix": "1. Make sure your domain registrar information is publicly visible.\n2. Avoid privacy-protected WHOIS.",
                "urls": [], "details": {}
            },
            {
                "id": 4, "category": "Trust & Domain",
                "name": "HTTPS / SSL Certificate",
                "status": "WARNING", "severity": "warning",
                "description": "SSL certificate expires in 29 days. Renew immediately.",
                "fix": "1. Renew your SSL certificate.\n2. Shopify stores use automatic SSL — check domain settings.",
                "urls": [], "details": {}
            },
            {
                "id": 77, "category": "Social & Brand",
                "name": "Social Media Presence",
                "status": "PASS", "severity": "info",
                "description": "Social media accounts found: instagram, facebook",
                "fix": "", "urls": [], "details": {}
            },
            {
                "id": 82, "category": "Shopify-Specific",
                "name": "Shopify Store Detected",
                "status": "PASS", "severity": "info",
                "description": "Shopify store confirmed.",
                "fix": "", "urls": [], "details": {}
            },
        ]
    }

    output = asyncio.run(generate_pdf(mock_result, "test-scan-001"))
    print(f"PDF generated: {output}")
