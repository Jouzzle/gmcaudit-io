# GMCAudit.io — Complete Deployment Guide

## Project Structure

```
gmcaudit/
├── backend/
│   ├── main.py                 # FastAPI app + all API endpoints
│   ├── requirements.txt        # Python dependencies
│   ├── scanner/
│   │   └── engine.py           # 89-check scan engine
│   ├── report/
│   │   └── generator.py        # PDF report generator
│   └── email/
│       └── sender.py           # Email delivery (Resend)
└── frontend/
    ├── package.json
    ├── vite.config.js
    ├── index.html
    └── src/
        ├── main.jsx
        └── App.jsx             # All 4 pages
```

---

## STEP 1 — Accounts to Create (free)

1. **Stripe** → stripe.com (payments)
2. **Resend** → resend.com (emails — 3,000/month free)
3. **Railway** → railway.app (hosting backend — $5/month after free tier)
4. **Vercel** → vercel.com (hosting frontend — free)
5. **Namecheap** → namecheap.com (DNS for GMCAudit.io)

---

## STEP 2 — Backend Setup

### Install dependencies
```bash
cd backend
pip install -r requirements.txt
```

### Environment variables (create .env file)
```env
# Stripe
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Resend (email)
RESEND_API_KEY=re_...
FROM_EMAIL=reports@gmcaudit.io

# App
FRONTEND_URL=https://gmcaudit.io
DATABASE_URL=postgresql://...
```

### Run locally
```bash
cd backend
uvicorn main:app --reload --port 8000
```

### Test the scan
```bash
python scanner/engine.py https://yourstore.com
```

---

## STEP 3 — Frontend Setup

### Install and run
```bash
cd frontend
npm install
npm run dev        # runs on localhost:3000
```

### Build for production
```bash
npm run build      # outputs to dist/
```

### Configure API URL
In `App.jsx`, change the API constant to your backend URL:
```js
const API = "https://your-backend.railway.app";
```

---

## STEP 4 — Stripe Setup

### Create product in Stripe Dashboard
1. Go to Products → Add Product
2. Name: "GMCAudit.io — Full Compliance Report"
3. Price: $29.00 one-time
4. Save

### Set up webhook
1. Go to Developers → Webhooks → Add endpoint
2. URL: `https://your-backend.railway.app/api/payment/webhook`
3. Events to listen: `checkout.session.completed`
4. Copy the webhook signing secret → add to env as `STRIPE_WEBHOOK_SECRET`

### Test payments
Use test card: `4242 4242 4242 4242` any future date, any CVC

---

## STEP 5 — Resend Email Setup

1. Sign up at resend.com
2. Add domain: gmcaudit.io
3. Add DNS records (Resend gives you the exact records)
4. Create API key → add to env as `RESEND_API_KEY`
5. Verify from email: reports@gmcaudit.io

### Test email
```bash
python email/sender.py
```

---

## STEP 6 — Deploy Backend to Railway

### Install Railway CLI
```bash
npm install -g @railway/cli
railway login
```

### Deploy
```bash
cd backend
railway init
railway up
```

### Add environment variables in Railway dashboard
Copy all your .env variables into Railway → Variables tab

### Add Procfile
```
web: uvicorn main:app --host 0.0.0.0 --port $PORT
```

### Railway will give you a URL like:
`https://gmcaudit-backend-production.railway.app`

---

## STEP 7 — Deploy Frontend to Vercel

### Install Vercel CLI
```bash
npm install -g vercel
```

### Deploy
```bash
cd frontend
# Update API URL in App.jsx first!
vercel --prod
```

### Connect custom domain
1. In Vercel dashboard → Domains → Add gmcaudit.io
2. In Namecheap DNS → Add CNAME pointing to Vercel
3. SSL is automatic

---

## STEP 8 — Connect Domain DNS (Namecheap)

### DNS Records to add:
```
Type    Host    Value                           TTL
CNAME   @       cname.vercel-dns.com            Auto
CNAME   www     cname.vercel-dns.com            Auto
A       api     [Railway IP]                    Auto
TXT     @       [Resend verification records]   Auto
```

---

## STEP 9 — Update Backend CORS

In `main.py`, update CORS for production:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://gmcaudit.io", "https://www.gmcaudit.io"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## STEP 10 — PostgreSQL Database (optional for launch)

The current version uses in-memory storage (fine for testing).
For production, add PostgreSQL:

### Railway PostgreSQL
1. In Railway → Add Plugin → PostgreSQL
2. Copy `DATABASE_URL` from Railway dashboard
3. Add to environment variables

### Simple schema (add to main.py)
```sql
CREATE TABLE scans (
    id VARCHAR PRIMARY KEY,
    url TEXT,
    email TEXT,
    status VARCHAR DEFAULT 'queued',
    result JSONB,
    paid BOOLEAN DEFAULT FALSE,
    access_token VARCHAR,
    pdf_path TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);
```

---

## Launch Checklist

### Before going live:
- [ ] Stripe in live mode (not test mode)
- [ ] RESEND_API_KEY set and domain verified
- [ ] FRONTEND_URL set to production URL
- [ ] CORS updated for production domain
- [ ] Stripe webhook URL pointing to production backend
- [ ] Test a full scan → payment → email flow
- [ ] Test PDF download works
- [ ] Mobile responsive check

### After launch:
- [ ] Monitor Railway logs for errors
- [ ] Watch Stripe dashboard for payments
- [ ] Check Resend dashboard for email delivery
- [ ] Add Google Analytics or Plausible

---

## API Reference

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/api/scan/start` | POST | None | Start scan, returns scan_id |
| `/api/scan/{id}/status` | GET | None | Poll scan progress |
| `/api/scan/{id}/teaser` | GET | None | Free score + summary |
| `/api/scan/{id}/full` | GET | Token | Full report (paid) |
| `/api/scan/{id}/pdf` | GET | Token | Download PDF |
| `/api/payment/create-session` | POST | None | Stripe checkout |
| `/api/payment/webhook` | POST | Stripe sig | Payment confirmation |
| `/health` | GET | None | Health check |

---

## Pricing Recommendation

Start at **$29/scan** — matches GMC Scout.

After first 50 customers:
- Consider agency plan: $99/month for unlimited scans
- Bulk: $199 for 10 scan credits

---

## Monthly Cost Estimate

| Service | Cost |
|---|---|
| Railway (backend) | ~$5/month |
| Vercel (frontend) | Free |
| Resend (email) | Free up to 3k/month |
| PostgreSQL on Railway | ~$5/month |
| Domain | ~$12/year |
| **Total** | **~$10-15/month** |

Break-even: **1 sale/month** at $29.

---

## Support

Every paid scan includes 1 free re-scan. Handle re-scans by:
1. User replies to report email
2. You trigger a new scan via the API
3. New PDF generated and emailed back

No extra infrastructure needed.
