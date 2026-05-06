"""
GMCAudit.io — FastAPI Backend
Handles scan jobs, teaser API, Stripe payment, and report delivery
"""

import asyncio
import os
import uuid
import json
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, HttpUrl

# Local imports
from scanner.engine import scan_store

app = FastAPI(title="GMCAudit.io API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── In-memory store (replace with PostgreSQL in production) ───
scans_db: dict = {}
tokens_db: dict = {}  # payment_token -> scan_id

# ─── Config ───
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
SCAN_PRICE_CENTS = 2900  # $29.00
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")


# ─────────────────────────────────────────────
# REQUEST/RESPONSE MODELS
# ─────────────────────────────────────────────

class ScanRequest(BaseModel):
    url: str
    email: Optional[str] = None


class PaymentRequest(BaseModel):
    scan_id: str
    email: str


# ─────────────────────────────────────────────
# BACKGROUND SCAN JOB
# ─────────────────────────────────────────────

async def run_scan_job(scan_id: str, url: str):
    try:
        scans_db[scan_id]["status"] = "running"
        result = await scan_store(url)
        scans_db[scan_id]["status"] = "complete"
        scans_db[scan_id]["result"] = result
        scans_db[scan_id]["completed_at"] = datetime.now().isoformat()
    except Exception as e:
        scans_db[scan_id]["status"] = "error"
        scans_db[scan_id]["error"] = str(e)


# ─────────────────────────────────────────────
# ENDPOINTS
# ─────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "service": "GMCAudit.io"}


@app.post("/api/scan/start")
async def start_scan(req: ScanRequest, background_tasks: BackgroundTasks):
    """Start a scan job. Returns scan_id immediately."""
    scan_id = str(uuid.uuid4())

    scans_db[scan_id] = {
        "id": scan_id,
        "url": req.url,
        "email": req.email,
        "status": "queued",
        "created_at": datetime.now().isoformat(),
        "result": None,
        "paid": False,
    }

    background_tasks.add_task(run_scan_job, scan_id, req.url)

    return {"scan_id": scan_id, "status": "queued"}


@app.get("/api/scan/{scan_id}/status")
async def get_scan_status(scan_id: str):
    """Poll scan status."""
    scan = scans_db.get(scan_id)
    if not scan:
        raise HTTPException(404, "Scan not found")

    return {
        "scan_id": scan_id,
        "status": scan["status"],
        "url": scan["url"],
        "created_at": scan["created_at"],
    }


@app.get("/api/scan/{scan_id}/teaser")
async def get_teaser(scan_id: str):
    """
    Returns FREE teaser data:
    - Compliance score %
    - Critical issue count
    - Warning count
    - Pass count
    - Risk level
    NO check details, NO fix guides
    """
    scan = scans_db.get(scan_id)
    if not scan:
        raise HTTPException(404, "Scan not found")
    if scan["status"] != "complete":
        raise HTTPException(400, f"Scan is {scan['status']}")

    result = scan["result"]

    return {
        "scan_id": scan_id,
        "url": result["url"],
        "domain": result["domain"],
        "score": result["score"],
        "risk_level": result["risk_level"],
        "total_checks": result["total_checks"],
        "passed": result["passed"],
        "failed": result["failed"],
        "warnings": result["warnings"],
        "scan_time_seconds": result["scan_time_seconds"],
        # Teaser: only show category-level summary, no fix guides
        "category_summary": _build_category_summary(result["checks"]),
        "paid": scan["paid"],
    }


def _build_category_summary(checks: list) -> list:
    """Summarize checks by category without revealing fix details."""
    categories = {}
    for check in checks:
        cat = check["category"]
        if cat not in categories:
            categories[cat] = {"category": cat, "passed": 0, "failed": 0, "warnings": 0}
        if check["status"] == "PASS":
            categories[cat]["passed"] += 1
        elif check["status"] == "FAIL":
            categories[cat]["failed"] += 1
        elif check["status"] == "WARNING":
            categories[cat]["warnings"] += 1
    return list(categories.values())


@app.get("/api/scan/{scan_id}/full")
async def get_full_report(scan_id: str, token: Optional[str] = None):
    """
    Returns FULL report data — requires payment token.
    """
    scan = scans_db.get(scan_id)
    if not scan:
        raise HTTPException(404, "Scan not found")
    if scan["status"] != "complete":
        raise HTTPException(400, "Scan not complete")

    # Verify payment
    if not scan["paid"] and not _verify_token(scan_id, token):
        raise HTTPException(403, "Payment required to access full report")

    return scan["result"]


def _verify_token(scan_id: str, token: Optional[str]) -> bool:
    if not token:
        return False
    stored = tokens_db.get(token)
    return stored == scan_id


# ─────────────────────────────────────────────
# STRIPE PAYMENT
# ─────────────────────────────────────────────

@app.post("/api/payment/create-session")
async def create_payment_session(req: PaymentRequest):
    """Create Stripe checkout session for one-time scan payment."""
    scan = scans_db.get(req.scan_id)
    if not scan:
        raise HTTPException(404, "Scan not found")

    try:
        import stripe
        stripe.api_key = STRIPE_SECRET_KEY

        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="payment",
            customer_email=req.email,
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "unit_amount": SCAN_PRICE_CENTS,
                    "product_data": {
                        "name": "GMCAudit.io — Full Compliance Report",
                        "description": f"Complete GMC compliance audit for {scan['url']}",
                    },
                },
                "quantity": 1,
            }],
            metadata={
                "scan_id": req.scan_id,
                "email": req.email,
            },
            success_url=f"{FRONTEND_URL}/report/{req.scan_id}?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{FRONTEND_URL}/scan/{req.scan_id}",
        )

        # Store email for later
        scans_db[req.scan_id]["email"] = req.email

        return {"session_id": session.id, "url": session.url}

    except Exception as e:
        raise HTTPException(500, f"Payment session failed: {str(e)}")


@app.post("/api/payment/webhook")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook — mark scan as paid after successful payment."""
    payload = await request.body()
    try:
        import json
        event = json.loads(payload)
    except Exception as e:
        raise HTTPException(400, str(e))

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        scan_id = session["metadata"].get("scan_id")
        email = session["metadata"].get("email")

        if scan_id and scan_id in scans_db:
            scans_db[scan_id]["paid"] = True
            scans_db[scan_id]["email"] = email

            # Generate access token
            access_token = str(uuid.uuid4())
            tokens_db[access_token] = scan_id
            scans_db[scan_id]["access_token"] = access_token

            # Trigger PDF generation and email delivery
            asyncio.create_task(_deliver_report(scan_id, email, access_token))

    return {"received": True}


async def _deliver_report(scan_id: str, email: str, token: str):
    """Generate PDF and send email with report."""
    try:
        from report.generator import generate_pdf
        scan = scans_db[scan_id]
        pdf_path = await generate_pdf(scan["result"], scan_id)
        scans_db[scan_id]["pdf_path"] = pdf_path
        # Email delivery (implement with SendGrid/Resend/Mailgun)
        await _send_report_email(email, scan_id, token, pdf_path)
    except Exception as e:
        print(f"Report delivery error: {e}")


async def _send_report_email(email: str, scan_id: str, token: str, pdf_path: str):
    """Send PDF report via email. Implement with your email provider."""
    # TODO: implement with SendGrid, Resend, or Mailgun
    report_url = f"{FRONTEND_URL}/report/{scan_id}?token={token}"
    print(f"[EMAIL] Would send report to {email} — URL: {report_url}")


@app.get("/api/scan/{scan_id}/pdf")
async def download_pdf(scan_id: str, token: Optional[str] = None):
    """Download PDF report — requires payment token."""
    scan = scans_db.get(scan_id)
    if not scan:
        raise HTTPException(404, "Scan not found")
    if not scan["paid"] and not _verify_token(scan_id, token):
        raise HTTPException(403, "Payment required")

    pdf_path = scan.get("pdf_path")
    if not pdf_path or not os.path.exists(pdf_path):
        raise HTTPException(404, "PDF not yet generated")

    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=f"gmcaudit-{scan['domain']}-report.pdf"
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
