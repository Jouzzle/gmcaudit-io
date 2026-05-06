"""
GMCAudit.io — Email Delivery
Sends branded report emails via Resend (resend.com)
Free tier: 3,000 emails/month — perfect for launch
"""

import os
import httpx
from datetime import datetime

RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
FROM_EMAIL = os.getenv("FROM_EMAIL", "reports@gmcaudit.io")
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://gmcaudit.io")


# ─────────────────────────────────────────────
# EMAIL TEMPLATES
# ─────────────────────────────────────────────

def _base_html(content: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>GMCAudit.io</title>
<style>
  body{{margin:0;padding:0;background:#07070C;font-family:'DM Sans',-apple-system,sans-serif;color:#C4C4D4}}
  .wrap{{max-width:560px;margin:0 auto;padding:40px 20px}}
  .logo{{font-weight:800;font-size:20px;color:#fff;letter-spacing:-.5px;margin-bottom:32px}}
  .logo span{{color:#6366F1}}
  .card{{background:#111118;border:1px solid #1C1C28;border-radius:16px;padding:32px}}
  .score-block{{text-align:center;padding:24px;background:#0D0D15;border-radius:12px;margin-bottom:24px}}
  .score{{font-size:64px;font-weight:800;line-height:1}}
  .badge{{display:inline-block;padding:4px 14px;border-radius:100px;font-size:11px;font-weight:700;letter-spacing:1px;margin-bottom:12px}}
  .stat-row{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-bottom:20px}}
  .stat{{text-align:center;padding:12px 4px;border-radius:8px}}
  .stat-n{{font-size:28px;font-weight:800;line-height:1}}
  .stat-l{{font-size:10px;color:#5C5C78;margin-top:3px}}
  .btn{{display:block;text-align:center;background:linear-gradient(135deg,#6366F1,#7C3AED);color:#fff;text-decoration:none;border-radius:10px;padding:14px 24px;font-size:15px;font-weight:700;margin:20px 0;box-shadow:0 4px 20px rgba(99,102,241,.4)}}
  .issue-row{{padding:10px 0;border-bottom:1px solid #1C1C28;font-size:13px}}
  .fail{{color:#F43F5E}}.warn{{color:#F59E0B}}.pass{{color:#10B981}}
  .footer{{text-align:center;padding-top:24px;font-size:11px;color:#5C5C78;line-height:1.8}}
  h2{{font-size:20px;font-weight:700;color:#fff;margin-bottom:6px}}
  p{{margin:0 0 12px;line-height:1.7}}
</style>
</head>
<body>
<div class="wrap">
  <div class="logo">GMCAudit<span>.io</span></div>
  {content}
  <div class="footer">
    GMCAudit.io · Your GMC Compliance Scanner<br>
    <a href="{FRONTEND_URL}" style="color:#6366F1;text-decoration:none">gmcaudit.io</a> ·
    Questions? Reply to this email.<br>
    © {datetime.now().year} GMCAudit.io
  </div>
</div>
</body>
</html>"""


def _score_color(score: float) -> str:
    return "#F43F5E" if score < 50 else "#F59E0B" if score < 75 else "#10B981"

def _risk_label(score: float) -> str:
    return "HIGH RISK" if score < 50 else "MEDIUM RISK" if score < 75 else "LOW RISK"

def _risk_bg(score: float) -> str:
    return "#1A0810" if score < 50 else "#180F00" if score < 75 else "#061410"


# ─────────────────────────────────────────────
# EMAIL 1: REPORT READY (after payment)
# ─────────────────────────────────────────────

def build_report_email(result: dict, report_url: str, pdf_url: str) -> dict:
    score = result["score"]
    domain = result["domain"]
    failed = result["failed"]
    warnings = result["warnings"]
    passed = result["passed"]
    sc = _score_color(score)
    rl = _risk_label(score)
    rb = _risk_bg(score)

    # Top 5 critical issues
    critical = [c for c in result["checks"] if c["status"] == "FAIL"][:5]

    issues_html = "".join([
        f'<div class="issue-row"><span class="fail">● FAIL</span> &nbsp;<strong style="color:#fff">{c["name"]}</strong><br>'
        f'<span style="font-size:12px;color:#5C5C78">{c["category"]}</span></div>'
        for c in critical
    ])

    if len([c for c in result["checks"] if c["status"] == "FAIL"]) > 5:
        remaining = len([c for c in result["checks"] if c["status"] == "FAIL"]) - 5
        issues_html += f'<div class="issue-row" style="color:#5C5C78;font-size:12px">+ {remaining} more critical issues in full report</div>'

    content = f"""
<div class="card">
  <h2>Your GMC Compliance Report is Ready</h2>
  <p style="color:#5C5C78">Scanned: <strong style="color:#C4C4D4">{domain}</strong></p>

  <div class="score-block">
    <div class="badge" style="background:{rb};color:{sc};border:1px solid {sc}44">{rl} · SCAN COMPLETE</div>
    <div class="score" style="color:{sc}">{score}<span style="font-size:32px">%</span></div>
    <p style="color:#5C5C78;font-size:13px;margin-top:4px">GMC Compliance Score</p>
    <div class="stat-row" style="margin-top:16px">
      <div class="stat" style="background:#1A0810">
        <div class="stat-n" style="color:#F43F5E">{failed}</div>
        <div class="stat-l">CRITICAL ISSUES</div>
      </div>
      <div class="stat" style="background:#180F00">
        <div class="stat-n" style="color:#F59E0B">{warnings}</div>
        <div class="stat-l">WARNINGS</div>
      </div>
      <div class="stat" style="background:#061410">
        <div class="stat-n" style="color:#10B981">{passed}</div>
        <div class="stat-l">PASSED</div>
      </div>
    </div>
  </div>

  <a href="{report_url}" class="btn">View Full Report →</a>
  <a href="{pdf_url}" style="display:block;text-align:center;color:#6366F1;text-decoration:none;font-size:13px;margin-bottom:20px">↓ Download PDF Report</a>

  <div style="border-top:1px solid #1C1C28;padding-top:16px">
    <p style="font-size:12px;font-weight:700;color:#5C5C78;letter-spacing:1px;margin-bottom:8px">CRITICAL ISSUES TO FIX</p>
    {issues_html}
  </div>

  <div style="background:#0D0D15;border-radius:10px;padding:16px;margin-top:20px">
    <p style="font-size:13px;color:#C4C4D4;margin:0">
      <strong style="color:#fff">Your re-scan is included.</strong> After fixing the issues above,
      reply to this email and we'll send you a fresh scan link — free of charge.
    </p>
  </div>
</div>"""

    return {
        "subject": f"Your GMC Compliance Report — {domain} ({score}% · {failed} Critical Issues)",
        "html": _base_html(content),
        "text": f"Your GMC Compliance Report is ready.\n\nScore: {score}%\nCritical Issues: {failed}\nWarnings: {warnings}\nPassed: {passed}\n\nView report: {report_url}\nDownload PDF: {pdf_url}\n\nGMCAudit.io",
    }


# ─────────────────────────────────────────────
# EMAIL 2: SCAN TEASER (after email capture, before payment)
# ─────────────────────────────────────────────

def build_teaser_email(domain: str, score: float, failed: int, warnings: int, payment_url: str) -> dict:
    sc = _score_color(score)
    rl = _risk_label(score)
    rb = _risk_bg(score)

    content = f"""
<div class="card">
  <h2>Your GMC Scan Results</h2>
  <p style="color:#5C5C78">We scanned <strong style="color:#C4C4D4">{domain}</strong> and found some issues.</p>

  <div class="score-block">
    <div class="badge" style="background:{rb};color:{sc};border:1px solid {sc}44">{rl}</div>
    <div class="score" style="color:{sc}">{score}<span style="font-size:32px">%</span></div>
    <p style="color:#5C5C78;font-size:13px;margin-top:4px">GMC Compliance Score</p>
    <div class="stat-row" style="margin-top:16px">
      <div class="stat" style="background:#1A0810">
        <div class="stat-n" style="color:#F43F5E">{failed}</div>
        <div class="stat-l">CRITICAL ISSUES</div>
      </div>
      <div class="stat" style="background:#180F00">
        <div class="stat-n" style="color:#F59E0B">{warnings}</div>
        <div class="stat-l">WARNINGS</div>
      </div>
    </div>
  </div>

  <p>Your store has <strong style="color:#F43F5E">{failed} critical issues</strong> that can trigger a GMC suspension or block approval.</p>
  <p style="color:#5C5C78;font-size:13px">The full report shows exactly what each issue is, which pages are affected, and step-by-step instructions to fix every single one.</p>

  <a href="{payment_url}" class="btn">Unlock Full Report · $29 →</a>

  <p style="font-size:12px;color:#5C5C78;text-align:center">One-time payment · No subscription · 1 free re-scan included</p>
</div>"""

    return {
        "subject": f"⚠️ {failed} GMC issues found on {domain} — see what to fix",
        "html": _base_html(content),
        "text": f"We found {failed} critical GMC issues on {domain}.\n\nCompliance score: {score}%\n\nUnlock the full report: {payment_url}\n\nGMCAudit.io",
    }


# ─────────────────────────────────────────────
# EMAIL 3: RE-SCAN READY
# ─────────────────────────────────────────────

def build_rescan_email(domain: str, original_score: float, new_score: float,
                       original_failed: int, new_failed: int, report_url: str) -> dict:
    improved = new_score > original_score
    diff = round(new_score - original_score, 1)

    content = f"""
<div class="card">
  <h2>Your Re-Scan is Complete</h2>
  <p style="color:#5C5C78">Re-scanned: <strong style="color:#C4C4D4">{domain}</strong></p>

  <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:20px">
    <div style="background:#0D0D15;border-radius:10px;padding:16px;text-align:center">
      <div style="font-size:11px;color:#5C5C78;margin-bottom:4px">BEFORE</div>
      <div style="font-size:40px;font-weight:800;color:{_score_color(original_score)}">{original_score}%</div>
      <div style="font-size:12px;color:#5C5C78">{original_failed} critical issues</div>
    </div>
    <div style="background:#0D0D15;border-radius:10px;padding:16px;text-align:center">
      <div style="font-size:11px;color:#5C5C78;margin-bottom:4px">NOW</div>
      <div style="font-size:40px;font-weight:800;color:{_score_color(new_score)}">{new_score}%</div>
      <div style="font-size:12px;color:#5C5C78">{new_failed} critical issues</div>
    </div>
  </div>

  {'<div style="background:#061410;border:1px solid rgba(16,185,129,.2);border-radius:10px;padding:14px;text-align:center;margin-bottom:16px"><p style="color:#10B981;font-weight:700;margin:0">🎉 Score improved by ' + str(diff) + '% — great progress!</p></div>' if improved else '<div style="background:#1A0810;border:1px solid rgba(244,63,94,.2);border-radius:10px;padding:14px;margin-bottom:16px"><p style="color:#F43F5E;font-weight:700;margin:0">Score unchanged — some issues still need attention.</p></div>'}

  <a href="{report_url}" class="btn">View Updated Report →</a>

  {'<p style="font-size:13px;color:#5C5C78;text-align:center">Your score is now strong enough to submit to Google Merchant Center. Good luck! 🚀</p>' if new_score >= 85 else '<p style="font-size:13px;color:#5C5C78;text-align:center">Keep fixing the remaining issues and your approval chances will keep improving.</p>'}
</div>"""

    return {
        "subject": f"Re-scan complete — {domain} is now at {new_score}% {'↑' if improved else '→'}",
        "html": _base_html(content),
        "text": f"Re-scan complete for {domain}.\n\nBefore: {original_score}%\nNow: {new_score}%\n\nView report: {report_url}\n\nGMCAudit.io",
    }


# ─────────────────────────────────────────────
# SEND FUNCTION
# ─────────────────────────────────────────────

async def send_email(to: str, subject: str, html: str, text: str = "") -> bool:
    if not RESEND_API_KEY:
        print(f"[EMAIL SKIPPED] No RESEND_API_KEY set. Would send to {to}: {subject}")
        return True

    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {RESEND_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "from": f"GMCAudit.io <{FROM_EMAIL}>",
                    "to": [to],
                    "subject": subject,
                    "html": html,
                    "text": text or subject,
                },
                timeout=15,
            )
            if r.status_code == 200:
                data = r.json()
                print(f"[EMAIL SENT] id={data.get('id')} to={to}")
                return True
            else:
                print(f"[EMAIL ERROR] {r.status_code}: {r.text}")
                return False
    except Exception as e:
        print(f"[EMAIL EXCEPTION] {e}")
        return False


# ─────────────────────────────────────────────
# CONVENIENCE SENDERS
# ─────────────────────────────────────────────

async def send_report_email(to: str, result: dict, scan_id: str, token: str) -> bool:
    report_url = f"{FRONTEND_URL}/report/{scan_id}?token={token}"
    pdf_url = f"{FRONTEND_URL}/api/scan/{scan_id}/pdf?token={token}"
    email = build_report_email(result, report_url, pdf_url)
    return await send_email(to, email["subject"], email["html"], email["text"])


async def send_teaser_email(to: str, domain: str, score: float, failed: int,
                             warnings: int, scan_id: str) -> bool:
    payment_url = f"{FRONTEND_URL}/scan/{scan_id}#pay"
    email = build_teaser_email(domain, score, failed, warnings, payment_url)
    return await send_email(to, email["subject"], email["html"], email["text"])


async def send_rescan_email(to: str, domain: str, original_score: float, new_score: float,
                             original_failed: int, new_failed: int, scan_id: str, token: str) -> bool:
    report_url = f"{FRONTEND_URL}/report/{scan_id}?token={token}"
    email = build_rescan_email(domain, original_score, new_score, original_failed, new_failed, report_url)
    return await send_email(to, email["subject"], email["html"], email["text"])


# ─────────────────────────────────────────────
# TEST
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import asyncio

    mock_result = {
        "domain": "makfool.com", "score": 42.4,
        "failed": 14, "warnings": 10, "passed": 9,
        "checks": [
            {"status": "FAIL", "name": "Shipping Policy Exists", "category": "Policy Pages"},
            {"status": "FAIL", "name": "Contact Page", "category": "Contact & Business Info"},
            {"status": "FAIL", "name": "Physical Address", "category": "Contact & Business Info"},
            {"status": "FAIL", "name": "Refund Policy Completeness", "category": "Policy Pages"},
            {"status": "FAIL", "name": "Store Email Domain", "category": "Social & Brand"},
            {"status": "FAIL", "name": "Privacy Policy Exists", "category": "Policy Pages"},
        ]
    }

    async def test():
        email = build_report_email(mock_result, "https://gmcaudit.io/report/test", "https://gmcaudit.io/api/scan/test/pdf")
        print("Subject:", email["subject"])
        print("HTML length:", len(email["html"]))
        with open("/tmp/test_email.html", "w") as f:
            f.write(email["html"])
        print("Preview saved to /tmp/test_email.html")

    asyncio.run(test())
