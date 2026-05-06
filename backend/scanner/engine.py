"""
GMCAudit.io — Scan Engine v2
Full GMC compliance scanner with all missing checks added
"""

import asyncio
import re
import time
import ssl
import socket
from datetime import datetime
from urllib.parse import urljoin, urlparse
from dataclasses import dataclass, field
from typing import Optional
import httpx
from bs4 import BeautifulSoup


@dataclass
class CheckResult:
    id: int
    category: str
    name: str
    status: str
    severity: str
    description: str
    fix: str
    urls: list = field(default_factory=list)
    details: dict = field(default_factory=dict)


@dataclass
class ScanResult:
    url: str
    scanned_at: str
    scan_time_seconds: float
    domain: str
    store_intelligence: dict
    checks: list
    score: float
    total_checks: int
    passed: int
    failed: int
    warnings: int
    skipped: int


class GMCScanner:

    FREE_EMAIL_DOMAINS = {"gmail.com","yahoo.com","hotmail.com","outlook.com","aol.com","icloud.com","mail.com","protonmail.com"}
    MEDICAL_KEYWORDS = ["orthopedic","orthopaedic","anti-anxiety","calming","joint pain","cure","treat","heal","therapy","therapeutic","medical grade","clinical","pain relief","arthritis","inflammation","diagnose","prevent disease","fda approved","fda cleared"]
    URGENCY_KEYWORDS = ["countdown","timer","hurry","limited time","expires in","offer ends","only today","flash sale","last chance","selling fast","almost gone"]
    SCARCITY_KEYWORDS = [r"only [0-9]+ left","low stock","almost sold out","limited stock","selling out","high demand"]
    FAKE_CLAIM_KEYWORDS = ["guaranteed to cure","100% proven","#1 in the world","world's best","scientifically proven","clinically proven","doctor recommended","as seen on tv","miracle","magic"]
    AI_TEMPLATE_SIGNALS = ["we are passionate about","founded with a passion","our journey began","we believe in quality","committed to excellence","dedicated to providing","our mission is to","we strive to","lorem ipsum"]

    def __init__(self, url: str):
        self.raw_url = url.strip()
        self.base_url = self._normalize_url(self.raw_url)
        self.domain = urlparse(self.base_url).netloc.replace("www.", "")
        self.results = []
        self._page_cache = {}
        self._html_cache = {}
        self._status_cache = {}
        self.client = None
        self.store_intelligence = {}
        self.start_time = time.time()
        self._product_urls = []
        self._collection_urls = []
        self._page_urls_sitemap = []
        self._sitemap_html = ""

    def _normalize_url(self, url):
        if not url.startswith("http"):
            url = "https://" + url
        p = urlparse(url)
        return f"{p.scheme}://{p.netloc}"

    async def _get(self, path, timeout=15):
        url = urljoin(self.base_url, path) if not path.startswith("http") else path
        if url in self._html_cache:
            return self._status_cache.get(url, 200), self._html_cache[url]
        try:
            r = await self.client.get(url, timeout=timeout, follow_redirects=True)
            self._status_cache[url] = r.status_code
            html = r.text if r.status_code == 200 else ""
            self._html_cache[url] = html
            return r.status_code, html
        except Exception:
            self._status_cache[url] = 0
            self._html_cache[url] = ""
            return 0, ""

    async def _soup(self, path):
        if path in self._page_cache:
            return self._page_cache[path]
        status, html = await self._get(path)
        if status == 200 and html:
            soup = BeautifulSoup(html, "html.parser")
            self._page_cache[path] = soup
            return soup
        self._page_cache[path] = None
        return None

    def _text(self, soup):
        if not soup:
            return ""
        return soup.get_text(" ", strip=True).lower()

    def _add(self, result):
        self.results.append(result)

    async def run(self):
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; GMCAudit/2.0; +https://gmcaudit.io)",
            "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        async with httpx.AsyncClient(headers=headers, verify=False, timeout=20) as client:
            self.client = client
            await self._prefetch_sitemap()
            await asyncio.gather(
                self._check_trust_domain(),
                self._check_contact_info(),
                self._check_policy_pages(),
                self._check_policy_completeness_deep(),
                self._check_navigation_structure(),
                self._check_footer(),
                self._check_product_feed(),
                self._check_misrepresentation(),
                self._check_homepage_trust(),
                self._check_technical(),
                self._check_social_brand(),
                self._check_shopify_specific(),
            )
            await self._build_store_intelligence()
        return self._build_result()

    async def _prefetch_sitemap(self):
        _, sitemap = await self._get("/sitemap.xml")
        self._sitemap_html = sitemap
        self._product_urls = re.findall(r'<loc>(https?://[^<]+/products/[^<]+)</loc>', sitemap)
        self._collection_urls = re.findall(r'<loc>(https?://[^<]+/collections/[^<]+)</loc>', sitemap)
        self._page_urls_sitemap = re.findall(r'<loc>(https?://[^<]+/pages/[^<]+)</loc>', sitemap)

    # ── TRUST & DOMAIN ──────────────────────────────────────────────────────

    async def _check_trust_domain(self):
        age_days, reg_date = await self._get_domain_age_rdap()
        if age_days is not None:
            self.store_intelligence["domain_age_days"] = age_days
            self.store_intelligence["domain_registered"] = reg_date
            if age_days < 30:
                s, sev = "FAIL", "critical"
                d = f"Domain is only {age_days} days old (registered {reg_date}). GMC flags new domains as high-risk."
            elif age_days < 90:
                s, sev = "WARNING", "warning"
                d = f"Domain is {age_days} days old. Under 90 days = lower GMC trust score."
            else:
                s, sev = "PASS", "info"
                d = f"Domain is {age_days} days old. Good domain age."
            self._add(CheckResult(id=1, category="Trust & Domain", name="Domain Age",
                status=s, severity=sev, description=d,
                fix="" if s=="PASS" else
                "1. Wait at least 30 days before applying to GMC.\n"
                "2. Build social media (15+ posts per platform).\n"
                "3. Get some traffic before applying.\n"
                "4. Consider an aged domain (60+ days).",
                details={"age_days": age_days, "registered": reg_date}))
        else:
            self._add(CheckResult(id=1, category="Trust & Domain", name="Domain Age",
                status="WARNING", severity="warning",
                description="Could not determine domain age via RDAP. May indicate WHOIS privacy.",
                fix="1. Make registrar info publicly visible.\n2. Avoid WHOIS privacy on new domains."))

        try:
            ctx = ssl.create_default_context()
            with socket.create_connection((self.domain, 443), timeout=10) as sock:
                with ctx.wrap_socket(sock, server_hostname=self.domain) as ssock:
                    cert = ssock.getpeercert()
                    expire = datetime.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y %Z')
                    days_left = (expire - datetime.now()).days
                    self._add(CheckResult(id=4, category="Trust & Domain", name="HTTPS / SSL Certificate",
                        status="WARNING" if days_left < 30 else "PASS",
                        severity="warning" if days_left < 30 else "info",
                        description=f"SSL expires in {days_left} days." + (" Renew immediately." if days_left < 30 else ""),
                        fix="1. Renew SSL certificate.\n2. Check Shopify domain settings." if days_left < 30 else "",
                        details={"days_left": days_left}))
        except Exception:
            self._add(CheckResult(id=4, category="Trust & Domain", name="HTTPS / SSL Certificate",
                status="FAIL", severity="critical",
                description="SSL certificate invalid or HTTPS not configured.",
                fix="1. Shopify admin: Online Store → Domains → Enable SSL.\n2. Contact Shopify support."))

        tld = "." + self.domain.split(".")[-1]
        bad_tlds = {".xyz",".tk",".ml",".ga",".cf",".gq",".top",".click",".loan"}
        if tld in bad_tlds:
            self._add(CheckResult(id=5, category="Trust & Domain", name="Domain Extension",
                status="FAIL", severity="critical",
                description=f"Domain uses '{tld}' — flagged by GMC as high-risk TLD.",
                fix="1. Register a .com domain.\n2. Set 301 redirects.\n3. Update GMC account."))
        elif tld not in {".com",".co",".io",".net",".org",".store",".shop"}:
            self._add(CheckResult(id=5, category="Trust & Domain", name="Domain Extension",
                status="WARNING", severity="warning",
                description=f"Domain uses '{tld}'. .com preferred by GMC.",
                fix="Consider registering .com version."))
        else:
            self._add(CheckResult(id=5, category="Trust & Domain", name="Domain Extension",
                status="PASS", severity="info",
                description=f"Domain uses '{tld}' — acceptable.", fix=""))

    async def _get_domain_age_rdap(self):
        try:
            rdap_url = f"https://rdap.org/domain/{self.domain}"
            async with httpx.AsyncClient(timeout=10, verify=False) as client:
                r = await client.get(rdap_url)
                if r.status_code == 200:
                    data = r.json()
                    for event in data.get("events", []):
                        if event.get("eventAction") == "registration":
                            reg_str = event.get("eventDate", "")
                            if reg_str:
                                reg_date = datetime.fromisoformat(reg_str.replace("Z", "+00:00"))
                                age_days = (datetime.now(reg_date.tzinfo) - reg_date).days
                                return age_days, reg_date.strftime("%B %d, %Y")
        except Exception:
            pass
        try:
            import whois
            w = whois.whois(self.domain)
            created = w.creation_date
            if isinstance(created, list): created = created[0]
            if created:
                return (datetime.now() - created).days, created.strftime("%B %d, %Y")
        except Exception:
            pass
        return None, None

    # ── CONTACT & BUSINESS INFO ─────────────────────────────────────────────

    async def _check_contact_info(self):
        contact_soup = None
        contact_url = None
        for path in ["/pages/contact", "/pages/contact-us", "/pages/get-in-touch", "/contact"]:
            s = await self._soup(path)
            if s:
                contact_soup = s
                contact_url = urljoin(self.base_url, path)
                break

        home_soup = await self._soup("/")
        footer_text = ""
        if home_soup:
            footer = home_soup.find("footer")
            if footer: footer_text = self._text(footer)

        full_text = self._text(contact_soup) + " " + footer_text
        email_pat = r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}'

        self._add(CheckResult(id=13, category="Contact & Business Info", name="Contact Page",
            status="PASS" if contact_soup else "FAIL", severity="critical",
            description=f"Contact page found at {contact_url}" if contact_soup else "No contact page found.",
            fix="" if contact_soup else
            "1. Create 'Contact Us' page in Shopify.\n2. Add form, email, phone.\n"
            "3. Link in navigation.\n4. URL: /pages/contact.",
            urls=[contact_url] if contact_url else []))

        emails = re.findall(email_pat, full_text)
        if emails:
            self.store_intelligence["email"] = emails[0]
        self._add(CheckResult(id=7, category="Contact & Business Info", name="Email Address",
            status="PASS" if emails else "FAIL", severity="critical",
            description=f"Email found: {emails[0]}" if emails else "No email found on contact page or footer.",
            fix="" if emails else
            "1. Add domain email to contact page and footer.\n2. Use support@yourdomain.com not Gmail.",
            details={"email": emails[0]} if emails else {}))

        phone_pat = r'[\+]?[(]?[0-9]{1,4}[)]?[-\s\.]?[(]?[0-9]{1,3}[)]?[-\s\.]?[0-9]{3,4}[-\s\.]?[0-9]{3,4}'
        phones = [p for p in re.findall(phone_pat, full_text) if len(re.sub(r'\D','',p)) >= 7]
        if phones:
            self.store_intelligence["phone"] = phones[0]
        self._add(CheckResult(id=8, category="Contact & Business Info", name="Phone Number",
            status="PASS" if phones else "WARNING", severity="warning",
            description=f"Phone found: {phones[0]}" if phones else "No phone number found.",
            fix="" if phones else
            "1. Add business phone to contact page.\n2. Use virtual phone (Zadarma, Google Voice)."))

        addr_kws = ["street","st.","ave","avenue","road","rd.","blvd","lane","drive","suite","floor",
                    "london","new york","los angeles","united kingdom","uk","usa","united states",
                    "france","netherlands","australia","germany","spain","italy"]
        has_addr = any(kw in full_text for kw in addr_kws)
        if has_addr:
            m = re.search(r'\d+[^,\n]{5,50},\s*[^,\n]{3,30}', full_text, re.IGNORECASE)
            if m: self.store_intelligence["address"] = m.group(0)[:100]
        self._add(CheckResult(id=9, category="Contact & Business Info", name="Physical Address",
            status="PASS" if has_addr else "FAIL", severity="critical",
            description="Physical address detected." if has_addr else "No physical address found.",
            fix="" if has_addr else
            "1. Add business address to contact page and footer.\n"
            "2. Virtual mailbox services are acceptable.\n"
            "3. Must match GMC account address."))

        hours_kws = ["monday","tuesday","friday","9am","9:00","am -","am–","business hours","mon-fri","open hours"]
        has_hours = any(kw in full_text for kw in hours_kws)
        if has_hours: self.store_intelligence["support_hours"] = "Detected"
        self._add(CheckResult(id=10, category="Contact & Business Info", name="Customer Service Hours",
            status="PASS" if has_hours else "WARNING", severity="warning",
            description="Support hours detected." if has_hours else "No support hours found.",
            fix="" if has_hours else
            "1. Add hours to contact page: 'Monday–Friday: 9:00 AM – 5:00 PM GMT'\n2. Add to footer."))

        all_emails = re.findall(email_pat, self._text(home_soup) + " " + full_text)
        mismatched = [e for e in set(all_emails)
                      if e.split("@")[-1].lower() in self.FREE_EMAIL_DOMAINS
                      or (e.split("@")[-1].lower() != self.domain
                          and f"www.{e.split('@')[-1].lower()}" != self.domain)]
        self._add(CheckResult(id=11, category="Contact & Business Info", name="Email Domain Mismatch",
            status="FAIL" if mismatched else "PASS", severity="critical",
            description=f"Free/mismatched emails: {', '.join(mismatched[:3])}" if mismatched else "All emails match store domain.",
            fix="" if not mismatched else
            "1. Replace free emails with domain email.\n"
            "2. Set up via Google Workspace or Zoho Mail.\n"
            "3. Update in all pages and policies."))

        if home_soup:
            dn = self.domain.split(".")[0].lower()
            title_t = home_soup.find("title")
            title_t = title_t.get_text("").lower() if title_t else ""
            header = home_soup.find("header")
            header_t = self._text(header) if header else ""
            footer_tag = home_soup.find("footer")
            footer_t = self._text(footer_tag) if footer_tag else ""
            score = sum([dn in title_t, dn in header_t, dn in footer_t])
            self._add(CheckResult(id=12, category="Contact & Business Info", name="Brand Name Consistency",
                status="PASS" if score >= 2 else "WARNING", severity="warning",
                description=f"Brand name in {score}/3 locations (title, header, footer).",
                fix="" if score >= 2 else
                "1. Ensure brand name in page title, header, footer.\n"
                "2. GMC account name must match exactly."))

    # ── POLICY PAGES ────────────────────────────────────────────────────────

    async def _check_policy_pages(self):
        checks = [
            ("/policies/shipping", "/pages/shipping-policy", "Shipping Policy", 14, 15, 16),
            ("/policies/refunds", "/pages/return-policy", "Refund/Return Policy", 17, 18, 19),
            ("/policies/privacy", "/pages/privacy-policy", "Privacy Policy", 22, 23, None),
            ("/policies/terms-of-service", "/pages/terms", "Terms of Service", 24, None, None),
        ]
        for correct, wrong, name, id_exist, id_url, id_complete in checks:
            c_status, c_html = await self._get(correct)
            w_status, _ = await self._get(wrong)
            has_c = c_status == 200 and len(c_html) > 200
            has_w = w_status == 200

            if name == "Shipping Policy":
                self._add(CheckResult(id=id_exist, category="Policy Pages", name=f"{name} Exists",
                    status="PASS" if has_c else "FAIL", severity="critical",
                    description=f"{name} found." if has_c else f"{name} not found. Required by GMC.",
                    fix="" if has_c else
                    "1. Shopify admin: Settings → Policies.\n2. Add Shipping Policy.\n"
                    "3. Shopify creates it at /policies/shipping.",
                    urls=[urljoin(self.base_url, correct)] if has_c else []))
                if id_url:
                    if has_w and not has_c:
                        self._add(CheckResult(id=id_url, category="Policy Pages", name=f"{name} URL",
                            status="FAIL", severity="critical",
                            description=f"Shipping policy at WRONG location: {wrong}",
                            fix="1. Delete /pages/shipping-policy.\n2. Create in Shopify Settings → Policies.\n3. Set 301 redirect.",
                            urls=[urljoin(self.base_url, wrong)]))
                    elif has_c:
                        self._add(CheckResult(id=id_url, category="Policy Pages", name=f"{name} URL",
                            status="PASS", severity="info", description="Correct Shopify URL.", fix=""))
                if id_complete and has_c:
                    text = c_html.lower()
                    has_time = any(k in text for k in ["business day","days","week","delivery time"])
                    has_cost = any(k in text for k in ["free shipping","shipping cost","$","€","£","free"])
                    missing = []
                    if not has_time: missing.append("delivery timeframe")
                    if not has_cost: missing.append("shipping cost")
                    self._add(CheckResult(id=id_complete, category="Policy Pages", name=f"{name} Completeness",
                        status="FAIL" if missing else "PASS", severity="critical",
                        description=f"Missing: {', '.join(missing)}" if missing else "Shipping policy complete.",
                        fix="1. Add delivery timeframes.\n2. Add shipping costs.\n3. Add order cutoff time." if missing else ""))

            elif name == "Refund/Return Policy":
                self._add(CheckResult(id=id_exist, category="Policy Pages", name=f"{name} Exists",
                    status="PASS" if has_c else "FAIL", severity="critical",
                    description=f"{name} found." if has_c else f"{name} not found. Required by GMC.",
                    fix="" if has_c else
                    "1. Shopify admin: Settings → Policies.\n2. Add Return Policy.\n"
                    "3. Shopify creates it at /policies/refunds.",
                    urls=[urljoin(self.base_url, correct)] if has_c else []))
                if id_url:
                    if has_w and not has_c:
                        self._add(CheckResult(id=id_url, category="Policy Pages", name=f"{name} URL",
                            status="FAIL", severity="critical",
                            description=f"Refund policy at WRONG location: {wrong}",
                            fix="1. Delete /pages/return-policy.\n2. Create in Settings → Policies.\n3. Set 301 redirect.",
                            urls=[urljoin(self.base_url, wrong)]))
                    elif has_c:
                        self._add(CheckResult(id=id_url, category="Policy Pages", name=f"{name} URL",
                            status="PASS", severity="info", description="Correct Shopify URL.", fix=""))
                if id_complete and has_c:
                    text = c_html.lower()
                    required = {
                        "cancellation_period": ["cancel","cancellation","24 hours","36 hours"],
                        "refund_method": ["refund method","original payment","store credit"],
                        "damaged_goods": ["damaged","defective","broken","wrong item"],
                        "return_procedure": ["return process","how to return","initiate a return"],
                        "shipping_costs": ["return shipping","customer pays","free return","who pays"],
                    }
                    missing = [s for s, kws in required.items() if not any(k in text for k in kws)]
                    self._add(CheckResult(id=id_complete, category="Policy Pages", name=f"{name} Completeness",
                        status="FAIL" if missing else "PASS", severity="critical",
                        description=f"Missing {len(missing)}/5 sections: {', '.join(missing)}" if missing else "All 5 required sections present.",
                        fix="Add missing sections:\n1. Cancellation period\n2. Refund method\n3. Damaged goods\n4. Return procedure\n5. Return shipping responsibility" if missing else ""))
                    has_window = bool(re.search(r'\d+\s*days?', text))
                    self._add(CheckResult(id=20, category="Policy Pages", name="Return Window Stated",
                        status="PASS" if has_window else "FAIL", severity="critical",
                        description="Return window stated." if has_window else "Return window not found.",
                        fix="" if has_window else "Add: 'Returns accepted within 30 days of delivery.'"))
                    pays_kws = ["customer pays","buyer pays","you pay","free return","we cover","we pay"]
                    self._add(CheckResult(id=21, category="Policy Pages", name="Return Shipping Responsibility",
                        status="PASS" if any(k in text for k in pays_kws) else "WARNING", severity="warning",
                        description="Return shipping responsibility stated." if any(k in text for k in pays_kws) else "Who pays return shipping not stated.",
                        fix="" if any(k in text for k in pays_kws) else "Add: 'Customer is responsible for return shipping costs.'"))

            elif name == "Privacy Policy":
                self._add(CheckResult(id=id_exist, category="Policy Pages", name=f"{name} Exists",
                    status="PASS" if has_c else "FAIL", severity="critical",
                    description=f"{name} found." if has_c else f"{name} not found. Required by law and GMC.",
                    fix="" if has_c else "1. Shopify admin: Settings → Policies.\n2. Add Privacy Policy.",
                    urls=[urljoin(self.base_url, correct)] if has_c else []))
                if id_url and has_c:
                    text = c_html.lower()
                    gdpr_kws = ["personal data","data protection","data controller","gdpr","cookies","right to erasure"]
                    has_gdpr = sum(1 for k in gdpr_kws if k in text) >= 2
                    self._add(CheckResult(id=id_url, category="Policy Pages", name="Privacy Policy GDPR Content",
                        status="PASS" if has_gdpr else "WARNING", severity="warning",
                        description="GDPR language found in privacy policy." if has_gdpr else "Privacy policy may lack GDPR compliance language.",
                        fix="" if has_gdpr else
                        "1. Add: personal data, data controller, data protection.\n2. Add cookie consent notice.\n3. Include right to erasure for EU customers."))

            elif name == "Terms of Service":
                self._add(CheckResult(id=id_exist, category="Policy Pages", name=f"{name} Exists",
                    status="PASS" if (has_c and len(c_html) > 500) else "FAIL", severity="critical",
                    description=f"{name} exists with content." if has_c else f"{name} missing or insufficient.",
                    fix="" if has_c else "1. Shopify admin: Settings → Policies.\n2. Add Terms of Service.",
                    urls=[urljoin(self.base_url, correct)] if has_c else []))

        # About Us
        about_soup = None
        for path in ["/pages/about-us", "/pages/about", "/pages/our-story"]:
            s = await self._soup(path)
            if s:
                about_soup = s
                break
        if about_soup:
            text = self._text(about_soup)
            wc = len(text.split())
            self._add(CheckResult(id=25, category="Policy Pages", name="About Us Page Exists",
                status="PASS", severity="info", description=f"About Us found ({wc} words).", fix=""))
            ai_sigs = [s for s in self.AI_TEMPLATE_SIGNALS if s in text]
            self._add(CheckResult(id=26, category="Policy Pages", name="About Us Content Quality",
                status="FAIL" if wc < 150 else "WARNING" if len(ai_sigs) >= 2 else "PASS",
                severity="critical" if wc < 150 else "warning",
                description=f"Too short ({wc} words)." if wc < 150
                    else f"AI template language detected ({len(ai_sigs)} signals)." if len(ai_sigs) >= 2
                    else f"Good content ({wc} words).",
                fix="1. Write real brand story (150+ words).\n2. Include who/why/mission.\n3. Avoid AI template phrases.\n4. Use humanizer tool." if wc < 150 or len(ai_sigs) >= 2 else ""))
        else:
            self._add(CheckResult(id=25, category="Policy Pages", name="About Us Page Exists",
                status="FAIL", severity="critical", description="No About Us page found.",
                fix="1. Create /pages/about-us.\n2. Write 150+ words of real brand story.\n3. Link in navigation."))

        # FAQ
        has_faq = False
        for _p in ["/pages/faq","/pages/faqs","/pages/frequently-asked-questions"]:
            if await self._soup(_p):
                has_faq = True
                break
        self._add(CheckResult(id=27, category="Policy Pages", name="FAQ Page",
            status="PASS" if has_faq else "WARNING", severity="warning",
            description="FAQ page found." if has_faq else "No FAQ page found.",
            fix="" if has_faq else
            "1. Create /pages/faq.\n2. Add 8-10 questions.\n3. Cover: shipping, returns, payment.\n4. Link from footer."))

    # ── DEEP POLICY COMPLETENESS (new checks) ───────────────────────────────

    async def _check_policy_completeness_deep(self):
        _, shipping_html = await self._get("/policies/shipping")
        _, refund_html = await self._get("/policies/refunds")
        s_text = shipping_html.lower() if shipping_html else ""
        r_text = refund_html.lower() if refund_html else ""

        # Order cutoff time (NEW)
        cutoff_kws = ["cutoff","cut-off","cut off","order by","place order before",
                      "orders placed before","pm (gmt","pm (aest","pm (cet","5:00 pm","17:00","same day"]
        has_cutoff = any(k in s_text for k in cutoff_kws)
        self._add(CheckResult(id=90, category="Policy Pages", name="Order Cutoff Time",
            status="PASS" if has_cutoff else "WARNING", severity="warning",
            description="Order cutoff time stated in shipping policy." if has_cutoff else "Order cutoff time not stated. GMC Scout flags this.",
            fix="" if has_cutoff else
            "1. Add to shipping policy: 'Order cutoff time: 5:00 PM (GMT)'\n"
            "2. Or: 'Orders placed before 3pm ship same day.'\n"
            "3. Tells customers when to order for specific delivery dates."))

        # Restocking fee (NEW)
        restock_kws = ["restocking fee","restocking fees","no restocking","no restock",
                       "restock fee","no fee","restocking: no","restocking fee: none"]
        has_restock = any(k in r_text for k in restock_kws)
        self._add(CheckResult(id=91, category="Policy Pages", name="Restocking Fee Policy",
            status="PASS" if has_restock else "WARNING", severity="warning",
            description="Restocking fee policy stated." if has_restock else "Restocking fee not stated. GMC Scout flags this.",
            fix="" if has_restock else
            "1. Add to refund policy: 'Restocking Fees: No restocking fee charged.'\n"
            "2. Or if you charge: 'A 15% restocking fee applies.'\n"
            "3. Required for full policy transparency."))

        # Accepts exchanges (NEW)
        exchange_kws = ["exchange","exchanges","swap","replacement","we accept exchange","exchange for","exchange policy"]
        has_exchanges = any(k in r_text for k in exchange_kws)
        self._add(CheckResult(id=92, category="Policy Pages", name="Exchange Policy Stated",
            status="PASS" if has_exchanges else "WARNING", severity="warning",
            description="Exchange policy stated in refund policy." if has_exchanges else "Exchange policy not stated.",
            fix="" if has_exchanges else
            "1. Add: 'We accept exchanges within 30 days of delivery.'\n"
            "2. Or: 'We do not accept exchanges — please return for a refund.'\n"
            "3. Either answer is acceptable — just state it clearly."))

        # Refund processing time (NEW)
        proc_kws = ["business days","working days","5-7 days","7 days","refund within",
                    "processed within","refund processing","3-5 business","5 working","7 business"]
        has_proc = any(k in r_text for k in proc_kws)
        self._add(CheckResult(id=93, category="Policy Pages", name="Refund Processing Time",
            status="PASS" if has_proc else "WARNING", severity="warning",
            description="Refund processing timeframe stated." if has_proc else "Refund processing time not stated.",
            fix="" if has_proc else
            "1. Add: 'Refunds processed within 5-7 business days.'\n"
            "2. Include when it appears in customer's account.\n"
            "3. Standard: 5-10 business days."))

    # ── NAVIGATION & STRUCTURE ──────────────────────────────────────────────

    async def _check_navigation_structure(self):
        home_soup = await self._soup("/")
        if not home_soup: return

        nav = home_soup.find("nav") or home_soup.find("header")
        nav_text = self._text(nav) if nav else ""
        nav_links = [a.get("href","").lower() for a in (nav.find_all("a") if nav else [])]

        has_home = "home" in nav_text or any("home" in l for l in nav_links) or "/" in nav_links
        self._add(CheckResult(id=28, category="Navigation & Structure", name="Home in Navigation",
            status="PASS" if has_home else "WARNING", severity="warning",
            description="Home link in navigation." if has_home else "Home link not in main navigation.",
            fix="" if has_home else "1. Add 'Home' to main navigation.\n2. Shopify: Online Store → Navigation → Main menu."))

        has_collections = any("collection" in l for l in nav_links) or "collections" in nav_text
        self._add(CheckResult(id=29, category="Navigation & Structure", name="Collections in Navigation",
            status="PASS" if has_collections else "FAIL", severity="critical",
            description="Collections in navigation." if has_collections else "Collections not in main navigation.",
            fix="" if has_collections else "1. Add collections to navigation.\n2. GMC requires easy access to product categories."))

        track_paths = ["/pages/track-your-order","/pages/order-tracking","/pages/track-order","/pages/tracking"]
        has_track = False
        for path in track_paths:
            s, _ = await self._get(path)
            if s == 200:
                has_track = True
                break
        has_track_nav = any("track" in l for l in nav_links)
        self._add(CheckResult(id=30, category="Navigation & Structure", name="Track Your Order",
            status="PASS" if (has_track or has_track_nav) else "FAIL", severity="critical",
            description="Track Your Order page found." if (has_track or has_track_nav) else "Track Your Order missing.",
            fix="" if (has_track or has_track_nav) else
            "1. Install ParcelPanel or Track123.\n2. Create /pages/track-your-order.\n"
            "3. Add to main navigation. Required for GMC approval."))

        has_about_nav = any("about" in l for l in nav_links) or "about" in nav_text[:200]
        self._add(CheckResult(id=31, category="Navigation & Structure", name="About Us in Navigation",
            status="PASS" if has_about_nav else "WARNING", severity="warning",
            description="About Us in navigation." if has_about_nav else "About Us not in navigation.",
            fix="" if has_about_nav else "Add About Us to main navigation."))

        policy_in_nav = any(kw in l for l in nav_links for kw in ["privacy","terms","refund","shipping-policy"])
        self._add(CheckResult(id=32, category="Navigation & Structure", name="No Policy Pages in Main Nav",
            status="FAIL" if policy_in_nav else "PASS", severity="warning",
            description="Policy pages in main navigation. Looks unprofessional to GMC." if policy_in_nav else "No policy pages in main nav. Good.",
            fix="Remove policies from main nav. They belong in footer only." if policy_in_nav else ""))

        await self._check_collections_product_count()

    async def _check_collections_product_count(self):
        if not self._collection_urls:
            self._add(CheckResult(id=33, category="Navigation & Structure", name="Collections Have Min 5 Products",
                status="WARNING", severity="warning",
                description="Could not detect collections.",
                fix="1. Create at least 5 collections.\n2. Each needs minimum 5 products."))
            return

        under_threshold = []
        empty_collections = []
        for col_url in self._collection_urls[:10]:
            path = col_url.replace(self.base_url, "")
            if path in ["/collections/all", "/collections/frontpage"]: continue
            soup = await self._soup(path)
            if not soup: continue
            product_links = set(a.get("href","") for a in soup.find_all("a", href=True) if "/products/" in a.get("href",""))
            count = len(product_links)
            col_name = path.split("/collections/")[-1].replace("-"," ").title()
            if count == 0:
                empty_collections.append({"name": col_name, "url": col_url, "count": 0})
            elif count < 5:
                under_threshold.append({"name": col_name, "url": col_url, "count": count})

        all_issues = empty_collections + under_threshold
        if all_issues:
            details_text = "\n".join([f"• {c['name']} — {c['count']} products (needs 5+)\n  URL: {c['url']}" for c in all_issues[:5]])
            self._add(CheckResult(id=33, category="Navigation & Structure", name="Collections Have Min 5 Products",
                status="FAIL", severity="critical",
                description=f"Found {len(all_issues)} collection(s) with fewer than 5 products:\n{details_text}",
                fix="1. Add 5+ products to every collection.\n2. Remove or hide empty collections.\n3. GMC flags thin/empty collections.\n4. Merge small collections if needed.",
                urls=[c["url"] for c in all_issues[:5]], details={"issues": all_issues}))
        else:
            self._add(CheckResult(id=33, category="Navigation & Structure", name="Collections Have Min 5 Products",
                status="PASS", severity="info", description="All checked collections have 5+ products.", fix=""))

    # ── FOOTER ──────────────────────────────────────────────────────────────

    async def _check_footer(self):
        home_soup = await self._soup("/")
        if not home_soup: return
        footer = home_soup.find("footer")
        if not footer:
            self._add(CheckResult(id=35, category="Footer", name="Footer Present",
                status="FAIL", severity="critical", description="No footer detected.",
                fix="1. Add footer to Shopify theme.\n2. Must contain: policies, social, payment icons, contact."))
            return

        footer_text = self._text(footer)
        footer_links = [a.get("href","").lower() for a in footer.find_all("a", href=True)]

        self._add(CheckResult(id=35, category="Footer", name="Refund Policy in Footer",
            status="PASS" if any("refund" in l or "return" in l for l in footer_links) else "FAIL",
            severity="critical",
            description="Refund/return policy linked in footer." if any("refund" in l or "return" in l for l in footer_links) else "Refund policy NOT linked in footer. GMC requires this.",
            fix="" if any("refund" in l or "return" in l for l in footer_links) else "1. Add Refund Policy link to footer.\n2. Shopify: Online Store → Navigation → Footer menu."))

        self._add(CheckResult(id=36, category="Footer", name="Privacy Policy in Footer",
            status="PASS" if any("privacy" in l for l in footer_links) else "FAIL",
            severity="critical",
            description="Privacy policy in footer." if any("privacy" in l for l in footer_links) else "Privacy policy NOT in footer.",
            fix="" if any("privacy" in l for l in footer_links) else "Add Privacy Policy link to footer."))

        social_domains = ["instagram.com","facebook.com","tiktok.com","twitter.com","x.com","youtube.com"]
        has_social = any(any(s in l for s in social_domains) for l in footer_links)
        self._add(CheckResult(id=37, category="Footer", name="Social Media in Footer",
            status="PASS" if has_social else "WARNING", severity="warning",
            description="Social media linked in footer." if has_social else "No social media links in footer.",
            fix="" if has_social else "1. Add social links to footer.\n2. Instagram + Facebook minimum.\n3. Accounts need 15+ posts."))

        payment_kws = ["visa","mastercard","paypal","amex","apple pay","google pay","payment"]
        imgs = footer.find_all("img", alt=True)
        has_payment = any(k in footer_text for k in payment_kws) or \
                      any(any(k in img.get("alt","").lower() for k in payment_kws) for img in imgs)
        self._add(CheckResult(id=38, category="Footer", name="Payment Icons in Footer",
            status="PASS" if has_payment else "WARNING", severity="warning",
            description="Payment icons in footer." if has_payment else "No payment icons in footer.",
            fix="" if has_payment else "1. Add payment icons to footer.\n2. Shopify theme editor: Footer → Show payment icons."))

        addr_kws = ["street","ave","road","london","new york","united kingdom","usa","france","netherlands","australia"]
        has_addr = any(k in footer_text for k in addr_kws)
        self._add(CheckResult(id=39, category="Footer", name="Address/Company Info in Footer",
            status="PASS" if has_addr else "WARNING", severity="warning",
            description="Company address in footer." if has_addr else "No company address in footer.",
            fix="" if has_addr else "1. Add company address to footer.\n2. Major trust signal for GMC reviewers."))

        email_pat = r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}'
        has_contact = bool(re.search(email_pat, footer_text)) or any("contact" in l for l in footer_links)
        self._add(CheckResult(id=40, category="Footer", name="Contact Email/Link in Footer",
            status="PASS" if has_contact else "WARNING", severity="warning",
            description="Contact info in footer." if has_contact else "No contact info in footer.",
            fix="" if has_contact else "1. Add email address to footer.\n2. Or add 'Contact Us' link."))

    # ── PRODUCT & FEED ──────────────────────────────────────────────────────

    async def _check_product_feed(self):
        product_urls = self._product_urls[:10]
        if not product_urls:
            _, col_html = await self._get("/collections/all")
            if col_html:
                links = re.findall(r'href="(/products/[^"?]+)"', col_html)
                product_urls = [urljoin(self.base_url, u) for u in set(links)][:10]

        product_count = len(self._product_urls)
        self.store_intelligence["product_count"] = product_count

        if product_count >= 10:
            self._add(CheckResult(id=41, category="Product & Feed", name="Minimum Products",
                status="PASS", severity="info", description=f"{product_count} products found. Good.", fix=""))
        elif product_count >= 5:
            self._add(CheckResult(id=41, category="Product & Feed", name="Minimum Products",
                status="WARNING", severity="warning",
                description=f"Only {product_count} products. Aim for 30-50 minimum for GMC.",
                fix="1. Upload 30-50 products.\n2. Upload gradually: 3/day → 9/day → 15/day (max 50/day)."))
        else:
            self._add(CheckResult(id=41, category="Product & Feed", name="Minimum Products",
                status="FAIL", severity="critical",
                description=f"Only {product_count} products. GMC requires minimum 5-10.",
                fix="1. Upload 5-10 products minimum before applying.\n2. Ideally 30-50 across 5+ collections."))

        # NEW: Per-product 404 check (matches GMC Scout behavior)
        broken_products = []
        for prod_url in self._product_urls[:20]:
            try:
                r = await self.client.head(prod_url, timeout=8, follow_redirects=True)
                if r.status_code == 404:
                    broken_products.append(prod_url)
            except Exception:
                pass
        self._add(CheckResult(id=94, category="Product & Feed", name="Broken Product URLs",
            status="FAIL" if broken_products else "PASS", severity="critical",
            description=f"Found {len(broken_products)} product URL(s) returning 404. These products are in your sitemap but not accessible." if broken_products else "All checked product URLs are accessible.",
            fix="1. Fix or delete broken products in Shopify admin.\n2. Set 301 redirects from broken URLs to active products.\n3. Broken product URLs directly cause GMC product disapprovals." if broken_products else "",
            urls=broken_products[:5]))

        if not product_urls: return

        title_issues, med_title, med_desc = [], [], []
        has_images = has_ship = has_refund = has_payment = False
        empty_desc = 0

        for prod_url in product_urls[:5]:
            path = prod_url.replace(self.base_url,"") if prod_url.startswith(self.base_url) else prod_url
            soup = await self._soup(path)
            if not soup: continue
            t = soup.find("h1")
            if t:
                tt = t.get_text(strip=True)
                if len(tt) > 120: title_issues.append(f"{tt[:60]}... ({len(tt)} chars)")
                if any(k in tt.lower() for k in self.MEDICAL_KEYWORDS): med_title.append(tt[:80])
            pt = self._text(soup)
            if any(k in pt for k in self.MEDICAL_KEYWORDS): med_desc.append(prod_url)
            imgs = soup.find_all("img", src=True)
            if any("cdn.shopify" in i.get("src","") or "product" in i.get("src","").lower() for i in imgs): has_images = True
            desc = soup.find(class_=lambda c: c and "description" in str(c).lower())
            if desc and len(desc.get_text(strip=True)) < 50: empty_desc += 1
            if any(k in pt for k in ["shipping information","delivery information","shipping & delivery"]): has_ship = True
            if any(k in pt for k in ["return policy","refund policy","returns & refunds"]): has_refund = True
            if any(k in pt for k in ["visa","mastercard","paypal","amex","apple pay"]): has_payment = True

        self._add(CheckResult(id=42, category="Product & Feed", name="Product Title Length",
            status="FAIL" if title_issues else "PASS", severity="warning",
            description=f"{len(title_issues)} title(s) over 120 chars." if title_issues else "All titles under 120 chars.",
            fix="1. Keep titles under 120 chars.\n2. Most important keywords in first 9 words.\n3. Use Shopify bulk editor to fix multiple." if title_issues else "",
            details={"offending": title_issues[:3]}))
        self._add(CheckResult(id=43, category="Product & Feed", name="Medical Claims in Titles",
            status="FAIL" if med_title else "PASS", severity="critical",
            description=f"Medical claims in {len(med_title)} title(s)." if med_title else "No medical claims in titles.",
            fix="1. Remove: orthopedic, anti-anxiety, joint pain, etc.\n2. Use: Ergonomic, Memory Foam, Supportive.\n3. These keywords WILL get your GMC suspended." if med_title else "",
            details={"offending": med_title[:3]}))
        self._add(CheckResult(id=44, category="Product & Feed", name="Medical Claims in Descriptions",
            status="FAIL" if med_desc else "PASS", severity="critical",
            description=f"Medical claims in {len(med_desc)} description(s)." if med_desc else "No medical claims in descriptions.",
            fix="1. Remove all health/medical claims.\n2. Focus on: materials, features, dimensions.\n3. Run site-wide search for these keywords." if med_desc else "",
            urls=med_desc[:3]))
        self._add(CheckResult(id=45, category="Product & Feed", name="Product Images Present",
            status="PASS" if has_images else "FAIL", severity="critical",
            description="Product images found." if has_images else "Could not detect product images.",
            fix="" if has_images else "1. Add images to every product.\n2. Use clean backgrounds.\n3. Minimum 800x800px. No text overlays."))
        self._add(CheckResult(id=47, category="Product & Feed", name="Shipping Info on Product Page",
            status="PASS" if has_ship else "WARNING", severity="warning",
            description="Shipping info section on product pages." if has_ship else "No shipping section on product pages.",
            fix="" if has_ship else "1. Add shipping dropdown on product pages.\n2. Include timeframe, cost, countries.\n3. Link to full shipping policy."))
        self._add(CheckResult(id=48, category="Product & Feed", name="Refund Info on Product Page",
            status="PASS" if has_refund else "WARNING", severity="warning",
            description="Refund info on product pages." if has_refund else "No refund section on product pages.",
            fix="" if has_refund else "1. Add returns dropdown on product pages.\n2. Summary: window, responsibility, method."))
        self._add(CheckResult(id=49, category="Product & Feed", name="Payment Icons on Product Page",
            status="PASS" if has_payment else "WARNING", severity="warning",
            description="Payment icons near Add to Cart." if has_payment else "No payment icons near Add to Cart.",
            fix="" if has_payment else "1. Add payment icons below Add to Cart.\n2. Shopify theme editor: Product page → Show payment icons."))
        self._add(CheckResult(id=50, category="Product & Feed", name="Product Descriptions",
            status="FAIL" if empty_desc >= 2 else "PASS", severity="warning",
            description=f"{empty_desc} products with empty/short descriptions." if empty_desc else "Products have descriptions.",
            fix="1. Write unique descriptions (100+ words) per product.\n2. Write for Google (SEO keywords).\n3. Bold important keywords." if empty_desc >= 2 else ""))

    # ── MISREPRESENTATION ────────────────────────────────────────────────────

    async def _check_misrepresentation(self):
        home_soup = await self._soup("/")
        home_text = self._text(home_soup) if home_soup else ""
        product_texts = []
        for url in self._product_urls[:3]:
            path = url.replace(self.base_url,"") if url.startswith(self.base_url) else url
            s = await self._soup(path)
            if s: product_texts.append(self._text(s))
        all_text = home_text + " ".join(product_texts)

        has_timer = any(k in all_text for k in self.URGENCY_KEYWORDS)
        has_js_timer = False
        if home_soup:
            for script in home_soup.find_all("script", src=False):
                if script.string and any(k in script.string.lower() for k in ["countdown","timer","setinterval"]):
                    has_js_timer = True
                    break
        self._add(CheckResult(id=51, category="Misrepresentation", name="No Urgency Timers",
            status="FAIL" if (has_timer or has_js_timer) else "PASS", severity="critical",
            description="Urgency timers/text detected." if (has_timer or has_js_timer) else "No urgency timers detected.",
            fix="1. Remove ALL countdown timers.\n2. Remove urgency text ('offer ends', 'only today').\n3. #1 cause of GMC misrepresentation suspensions.\n4. Re-add only after 4+ weeks of GMC approval." if (has_timer or has_js_timer) else ""))

        scarcity_found = [p for p in self.SCARCITY_KEYWORDS if re.search(p, all_text, re.IGNORECASE)]
        self._add(CheckResult(id=52, category="Misrepresentation", name="No False Scarcity",
            status="FAIL" if scarcity_found else "PASS", severity="critical",
            description=f"Scarcity language: {', '.join(scarcity_found[:3])}" if scarcity_found else "No false scarcity detected.",
            fix="1. Remove 'Only X left' unless real inventory.\n2. Remove 'Selling fast', 'Almost sold out'.\n3. Fake scarcity = GMC misrepresentation." if scarcity_found else ""))

        fake_found = [k for k in self.FAKE_CLAIM_KEYWORDS if k in all_text]
        self._add(CheckResult(id=53, category="Misrepresentation", name="No Fake Claims",
            status="FAIL" if fake_found else "PASS", severity="critical",
            description=f"Misleading claims: {', '.join(fake_found[:3])}" if fake_found else "No fake claims detected.",
            fix="1. Remove unverifiable claims.\n2. Avoid: 'Guaranteed', '#1 in world', 'Miracle'.\n3. Use feature-based language." if fake_found else ""))

        discount_kws = ["promo code","coupon code","discount code","use code","enter code","% off with code"]
        has_discount = any(k in home_text for k in discount_kws)
        self._add(CheckResult(id=54, category="Misrepresentation", name="No Visible Discount Codes",
            status="FAIL" if has_discount else "PASS", severity="critical",
            description="Discount codes visible pre-purchase." if has_discount else "No discount codes visible.",
            fix="1. Remove all discount banners.\n2. No discount codes until 4+ weeks after GMC approval.\n3. Max 40% after approval." if has_discount else ""))

        material_claims = re.findall(r'100%\s+(leather|cashmere|silk|cotton|wool|linen)', all_text, re.IGNORECASE)
        self._add(CheckResult(id=55, category="Misrepresentation", name="No False Material Claims",
            status="WARNING" if material_claims else "PASS", severity="warning",
            description=f"100% material claims: {', '.join(material_claims[:3])}. Verify accuracy." if material_claims else "No suspicious material claims.",
            fix="1. Only claim 100% if verified.\n2. If a blend, state exact percentage.\n3. Use 'premium leather' if unverified." if material_claims else ""))

        health_kws = ["before and after","lose weight","burns fat","slims","detox"]
        has_health = any(k in all_text for k in health_kws)
        self._add(CheckResult(id=57, category="Misrepresentation", name="No Health/Weight Claims",
            status="FAIL" if has_health else "PASS", severity="critical",
            description="Health/weight claims detected." if has_health else "No health claims detected.",
            fix="1. Remove all before/after transformation claims.\n2. Remove weight loss language.\n3. These cause permanent GMC suspension." if has_health else ""))

    # ── HOMEPAGE TRUST ───────────────────────────────────────────────────────

    async def _check_homepage_trust(self):
        home_soup = await self._soup("/")
        if not home_soup: return
        ht = self._text(home_soup)

        logo = home_soup.find("img", class_=lambda c: c and "logo" in str(c).lower()) or \
               home_soup.find(class_=lambda c: c and "logo" in str(c).lower())
        self._add(CheckResult(id=61, category="Homepage Trust", name="Store Logo",
            status="PASS" if logo else "WARNING", severity="warning",
            description="Logo detected." if logo else "No logo detected.",
            fix="" if logo else "1. Upload logo to Shopify.\n2. Theme editor: Header → Logo."))

        vp_kws = ["free shipping","money back","satisfaction guaranteed","quality","fast delivery","easy return"]
        self._add(CheckResult(id=62, category="Homepage Trust", name="Value Proposition",
            status="PASS" if any(k in ht for k in vp_kws) else "WARNING", severity="warning",
            description="Value proposition on homepage." if any(k in ht for k in vp_kws) else "No value proposition found.",
            fix="" if any(k in ht for k in vp_kws) else "1. Add USPs: Free Shipping, 30-Day Returns, Secure Payment."))

        badge_kws = ["trust","secure","guarantee","verified","certified"]
        self._add(CheckResult(id=63, category="Homepage Trust", name="Trust Badges",
            status="PASS" if any(k in ht for k in badge_kws) else "WARNING", severity="warning",
            description="Trust badges found." if any(k in ht for k in badge_kws) else "No trust badges.",
            fix="" if any(k in ht for k in badge_kws) else "1. Add: Secure Checkout, Money-Back, SSL Secured badges."))

        review_kws = ["review","rating","star","customer","verified buyer","testimonial"]
        self._add(CheckResult(id=64, category="Homepage Trust", name="Social Proof on Homepage",
            status="PASS" if any(k in ht for k in review_kws) else "WARNING", severity="warning",
            description="Social proof on homepage." if any(k in ht for k in review_kws) else "No social proof on homepage.",
            fix="" if any(k in ht for k in review_kws) else "1. Add customer reviews section.\n2. Use Loox, Judge.me, or Yotpo.\n3. Minimum 5 visible reviews."))

        contact_kws = ["contact","chat","support","help","email us"]
        self._add(CheckResult(id=65, category="Homepage Trust", name="Contact Option Visible",
            status="PASS" if any(k in ht for k in contact_kws) else "WARNING", severity="warning",
            description="Contact option visible." if any(k in ht for k in contact_kws) else "No contact option on homepage.",
            fix="" if any(k in ht for k in contact_kws) else "1. Add live chat or email in header/announcement bar."))

        hero = home_soup.find(class_=lambda c: c and any(k in str(c).lower() for k in ["hero","banner","slideshow","featured"]))
        self._add(CheckResult(id=66, category="Homepage Trust", name="Professional Hero Section",
            status="PASS" if hero else "WARNING", severity="warning",
            description="Hero banner detected." if hero else "No hero banner detected.",
            fix="" if hero else "1. Add hero image/banner.\n2. Include headline and CTA."))

    # ── TECHNICAL ────────────────────────────────────────────────────────────

    async def _check_technical(self):
        home_soup = await self._soup("/")
        home_status, _ = await self._get("/")

        self._add(CheckResult(id=70, category="Technical", name="Store is Live",
            status="PASS" if home_status == 200 else "FAIL", severity="critical",
            description=f"Store live (HTTP {home_status})." if home_status == 200 else f"Store returned HTTP {home_status}.",
            fix="" if home_status == 200 else "1. Check Shopify plan.\n2. Remove password protection.\n3. Check domain DNS."))

        if home_soup:
            pw = "enter password" in self._text(home_soup) or "password protected" in self._text(home_soup)
            lf = home_soup.find("form", action=lambda a: a and "password" in str(a).lower())
            self._add(CheckResult(id=73, category="Technical", name="No Password Protection",
                status="FAIL" if (pw or lf) else "PASS", severity="critical",
                description="Store is password protected. GMC cannot access it." if (pw or lf) else "Store publicly accessible.",
                fix="1. Shopify: Online Store → Preferences → Password → Uncheck 'Restrict access'." if (pw or lf) else ""))

            viewport = home_soup.find("meta", attrs={"name": "viewport"})
            self._add(CheckResult(id=74, category="Technical", name="Mobile Viewport Meta Tag",
                status="PASS" if viewport else "FAIL", severity="warning",
                description="Mobile viewport meta tag present." if viewport else "Mobile viewport missing.",
                fix="" if viewport else "Add: <meta name='viewport' content='width=device-width,initial-scale=1'>"))

        # Broken links + contact variants
        if home_soup:
            all_links = [a["href"] for a in home_soup.find_all("a", href=True) if a["href"].startswith("http")][:20]
            broken, wrong_domain = [], []
            for link in all_links:
                ld = urlparse(link).netloc.replace("www.","")
                if ld and ld != self.domain:
                    wrong_domain.append(link)
                    continue
                try:
                    r = await self.client.head(link, timeout=8, follow_redirects=True)
                    if r.status_code == 404: broken.append(link)
                except Exception:
                    pass

            # Also check common contact URLs (GMC Scout does this explicitly)
            for path in ["/contact","/pages/contact","/pages/contact-us","/pages/get-in-touch"]:
                s, _ = await self._get(path)
                url = urljoin(self.base_url, path)
                if s == 404 and url not in broken:
                    broken.append(url)

            self._add(CheckResult(id=67, category="Technical", name="No Broken Links",
                status="FAIL" if broken else "PASS", severity="warning",
                description=f"Found {len(broken)} broken link(s) (404)." if broken else "No broken links detected.",
                fix="1. Fix broken links.\n2. Use Deadlinkchecker.com.\n3. Set 301 redirects for changed URLs." if broken else "",
                urls=broken[:5]))

            # Wrong domain links in policy pages (NEW — matches GMC Scout)
            policy_wrong = []
            for path in ["/policies/privacy","/policies/shipping","/policies/refunds"]:
                _, html = await self._get(path)
                if html:
                    for a in BeautifulSoup(html, "html.parser").find_all("a", href=True):
                        href = a["href"]
                        if href.startswith("http"):
                            ld = urlparse(href).netloc.replace("www.","")
                            if ld and ld != self.domain and ld not in ["ico.org.uk","gdpr.eu","shopify.com","stripe.com","paypal.com"]:
                                policy_wrong.append({"url": href, "found_on": urljoin(self.base_url, path)})
            self._add(CheckResult(id=68, category="Technical", name="Wrong Domain Links in Policies",
                status="WARNING" if policy_wrong else "PASS", severity="warning",
                description=f"Found {len(policy_wrong)} link(s) to different domains in policy pages." if policy_wrong else "No unexpected cross-domain links in policy pages.",
                fix="1. Review external links in policy pages.\n2. Remove unexpected external links.\n3. Keep only: regulatory links (ico.org.uk) and essential payment links." if policy_wrong else "",
                urls=[d["url"] for d in policy_wrong[:3]]))

        sitemap_status, _ = await self._get("/sitemap.xml")
        self._add(CheckResult(id=71, category="Technical", name="Sitemap Accessible",
            status="PASS" if sitemap_status == 200 else "WARNING", severity="warning",
            description="sitemap.xml accessible." if sitemap_status == 200 else "sitemap.xml not accessible.",
            fix="" if sitemap_status == 200 else "1. Shopify auto-generates sitemap.xml.\n2. Submit to Google Search Console."))

        robots_status, _ = await self._get("/robots.txt")
        self._add(CheckResult(id=72, category="Technical", name="robots.txt Accessible",
            status="PASS" if robots_status == 200 else "WARNING", severity="info",
            description="robots.txt accessible." if robots_status == 200 else "robots.txt not found.",
            fix="" if robots_status == 200 else "Shopify auto-generates robots.txt. Check domain settings."))

    # ── SOCIAL & BRAND ───────────────────────────────────────────────────────

    async def _check_social_brand(self):
        home_soup = await self._soup("/")
        if not home_soup: return
        all_links = [a.get("href","").lower() for a in home_soup.find_all("a", href=True)]

        social_platforms = {
            "Instagram": ["instagram.com"], "Facebook": ["facebook.com","fb.com"],
            "TikTok": ["tiktok.com"], "Twitter/X": ["twitter.com","x.com"], "YouTube": ["youtube.com"],
        }
        found = [p for p, domains in social_platforms.items() if any(any(d in l for d in domains) for l in all_links)]
        self.store_intelligence["social_platforms"] = found

        self._add(CheckResult(id=77, category="Social & Brand", name="Social Media Presence",
            status="PASS" if found else "FAIL", severity="critical",
            description=f"Social media found: {', '.join(found)}" if found else "No social media accounts linked.",
            fix="" if found else "1. Create Instagram + Facebook accounts.\n2. Post 15+ times each.\n3. Include brand name in handles and tags.\n4. Link from footer."))

        social_urls = [a.get("href","") for a in home_soup.find_all("a", href=True)
                       if any(s in a.get("href","").lower() for s in ["instagram.com","facebook.com","tiktok.com"])]
        broken_social = []
        for url in social_urls[:3]:
            try:
                r = await self.client.head(url, timeout=8, follow_redirects=True)
                if r.status_code in [404, 410]: broken_social.append(url)
            except Exception: pass

        self._add(CheckResult(id=78, category="Social & Brand", name="Social Links Working",
            status="FAIL" if broken_social else "PASS", severity="warning",
            description=f"{len(broken_social)} broken social link(s)." if broken_social else "All social links working.",
            fix="1. Update broken social links.\n2. Make accounts public." if broken_social else "",
            urls=broken_social))

        dn = self.domain.split(".")[0].lower()
        title_t = home_soup.find("title")
        title_t = title_t.get_text("").lower() if title_t else ""
        header = home_soup.find("header")
        header_t = self._text(header) if header else ""
        footer_tag = home_soup.find("footer")
        footer_t = self._text(footer_tag) if footer_tag else ""
        score = sum([dn in title_t, dn in header_t, dn in footer_t])
        self._add(CheckResult(id=79, category="Social & Brand", name="Brand Name Consistency",
            status="PASS" if score >= 2 else "WARNING", severity="warning",
            description=f"Brand name in {score}/3 locations (title, header, footer).",
            fix="" if score >= 2 else "1. Brand name in page title, header, and footer.\n2. GMC name must match exactly."))

        about_soup = await self._soup("/pages/about-us") or await self._soup("/pages/about")
        if about_soup:
            at = self._text(about_soup)
            ai_sigs = [s for s in self.AI_TEMPLATE_SIGNALS if s in at]
            self._add(CheckResult(id=80, category="Social & Brand", name="About Us Authenticity",
                status="WARNING" if len(ai_sigs) >= 2 else "PASS", severity="warning",
                description=f"AI template language detected ({len(ai_sigs)} signals)." if len(ai_sigs) >= 2 else "About Us appears authentic.",
                fix="" if len(ai_sigs) < 2 else "1. Rewrite in your own words.\n2. Add specific brand story.\n3. Use humanizer tool."))

        email_pat = r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}'
        free_emails = [e for e in re.findall(email_pat, self._text(home_soup))
                       if e.split("@")[-1].lower() in self.FREE_EMAIL_DOMAINS]
        self._add(CheckResult(id=81, category="Social & Brand", name="Store Email Domain",
            status="FAIL" if free_emails else "PASS", severity="critical",
            description=f"Free email domains: {', '.join(free_emails[:3])}." if free_emails else "Professional domain email. Good.",
            fix="" if not free_emails else "1. Replace free emails with domain email.\n2. Google Workspace or Zoho Mail.\n3. Update in all pages and policies."))

    # ── SHOPIFY-SPECIFIC ─────────────────────────────────────────────────────

    async def _check_shopify_specific(self):
        home_html = self._html_cache.get(urljoin(self.base_url, "/"), "")
        is_shopify = any(k in home_html for k in ["cdn.shopify.com","Shopify.theme","myshopify.com","shopify-section"])
        self.store_intelligence["is_shopify"] = is_shopify

        theme_match = re.search(r'"name"\s*:\s*"([^"]+)"', home_html)
        theme_name = theme_match.group(1) if theme_match else "Not detected"
        self.store_intelligence["theme"] = theme_name

        self._add(CheckResult(id=82, category="Shopify-Specific", name="Shopify Store Detected",
            status="PASS" if is_shopify else "WARNING", severity="info",
            description=f"Shopify confirmed. Theme: {theme_name}" if is_shopify else "Could not confirm Shopify.",
            fix=""))

        for cid, path, name in [
            (83, "/policies/shipping", "Shipping Policy URL"),
            (84, "/policies/refunds", "Refund Policy URL"),
            (85, "/policies/privacy", "Privacy Policy URL"),
            (86, "/policies/terms-of-service", "Terms of Service URL"),
        ]:
            st, html = await self._get(path)
            self._add(CheckResult(id=cid, category="Shopify-Specific", name=name,
                status="PASS" if (st == 200 and len(html) > 200) else "FAIL", severity="critical",
                description=f"{name} at correct path ({path})." if st == 200 else f"{name} NOT at {path}.",
                fix=f"1. Shopify: Settings → Policies.\n2. Add {name}.\n3. Shopify auto-creates at {path}.\n4. Do NOT create in Pages section." if st != 200 else "",
                urls=[urljoin(self.base_url, path)] if st == 200 else []))

        _, col_html = await self._get("/collections/all")
        self._add(CheckResult(id=87, category="Shopify-Specific", name="Collections URL Structure",
            status="PASS" if "/collections/" in (col_html or "") else "WARNING", severity="info",
            description="Standard /collections/ URL structure confirmed." if "/collections/" in (col_html or "") else "Could not confirm collection URL structure.",
            fix=""))

        has_shopify_sitemap = any(k in self._sitemap_html for k in ["sitemap_products_1.xml","sitemap_collections_1.xml"])
        self._add(CheckResult(id=89, category="Shopify-Specific", name="Shopify Sitemap Format",
            status="PASS" if has_shopify_sitemap else "WARNING", severity="info",
            description="Shopify sitemap format confirmed." if has_shopify_sitemap else "Sitemap doesn't match Shopify format.",
            fix="" if has_shopify_sitemap else "Shopify auto-generates sitemap. Submit to Google Search Console."))

    # ── STORE INTELLIGENCE BUILDER ───────────────────────────────────────────

    async def _build_store_intelligence(self):
        home_soup = await self._soup("/")
        home_html = self._html_cache.get(urljoin(self.base_url, "/"), "")

        lang = "en"
        if home_soup:
            html_tag = home_soup.find("html")
            if html_tag and html_tag.get("lang"): lang = html_tag.get("lang")

        # Currency (NEW)
        currency = "Unknown"
        for pat in [r'"priceCurrency"\s*:\s*"([A-Z]{3})"',
                    r'Shopify\.currency[^{]*"active"\s*:\s*"([A-Z]{3})"',
                    r'"currency"\s*:\s*"([A-Z]{3})"']:
            m = re.search(pat, home_html)
            if m:
                currency = m.group(1)
                break

        # Jurisdiction (NEW)
        jurisdiction = "Unknown"
        for pat in [r'"country_code"\s*:\s*"([A-Z]{2})"', r'"country"\s*:\s*"([A-Za-z ]{2,30})"']:
            m = re.search(pat, home_html)
            if m and len(m.group(1)) <= 25:
                jurisdiction = m.group(1)
                break

        # Timezone (NEW)
        tz = "Unknown"
        for t in ["GMT","UTC","EST","PST","CET","AEST","JST","IST","AEDT","NZST"]:
            if t in home_html.upper():
                tz = t
                break

        # Payment methods
        payment_methods = []
        if home_soup:
            footer = home_soup.find("footer")
            footer_text = self._text(footer) if footer else ""
            for kw, name in [("visa","Visa"),("mastercard","Mastercard"),("paypal","PayPal"),
                              ("amex","American Express"),("american express","American Express"),
                              ("apple pay","Apple Pay"),("google pay","Google Pay"),
                              ("klarna","Klarna"),("shop pay","Shop Pay"),("maestro","Maestro"),
                              ("union pay","Union Pay")]:
                if kw in footer_text and name not in payment_methods:
                    payment_methods.append(name)

        # Shipping info from policy
        _, shipping_html = await self._get("/policies/shipping")
        _, refund_html = await self._get("/policies/refunds")
        shipping_info = self._extract_shipping_info(shipping_html or "")
        refund_info = self._extract_refund_info(refund_html or "")

        self.store_intelligence.update({
            "domain": self.domain,
            "url": self.base_url,
            "product_count": len(self._product_urls),
            "collection_count": len(self._collection_urls),
            "page_count": len(self._page_urls_sitemap),
            "theme": self.store_intelligence.get("theme","Not detected"),
            "language": lang,
            "currency": currency,
            "jurisdiction": jurisdiction,
            "timezone": tz,
            "is_shopify": self.store_intelligence.get("is_shopify", False),
            "payment_methods": payment_methods,
            "scan_time": f"{time.time() - self.start_time:.1f}s",
            **shipping_info,
            **refund_info,
        })

    def _extract_shipping_info(self, html):
        if not html: return {}
        text = html.lower()
        info = {}
        if "free shipping" in text or "free delivery" in text:
            info["shipping_cost"] = "Free"
        tm = re.search(r'(\d+[-–]\d+|\d+)\s*(business\s+days?|working\s+days?|days?)', text)
        if tm: info["shipping_time"] = tm.group(0).strip()
        cm = re.search(r'cut.?off\s*(?:time)?\s*:?\s*(\d{1,2}:\d{2}\s*(?:am|pm)?)', text)
        if not cm: cm = re.search(r'(\d{1,2}:\d{2}\s*(?:am|pm)?)\s*(?:\([a-z]+\))?\s*cut.?off', text)
        if cm: info["order_cutoff_time"] = cm.group(1).strip().upper()
        countries = []
        for c in ["australia","united kingdom","united states","canada","germany","france","netherlands","sweden"]:
            if c in text: countries.append(c.title())
        if countries: info["shipping_countries"] = countries
        return info

    def _extract_refund_info(self, html):
        if not html: return {}
        text = html.lower()
        info = {}
        wm = re.search(r'(\d+)\s*days?', text)
        if wm: info["return_window"] = f"{wm.group(1)} days"
        if any(k in text for k in ["customer pays","buyer pays","you pay for"]):
            info["return_shipping"] = "Customer pays"
        elif any(k in text for k in ["free return","we pay","prepaid"]):
            info["return_shipping"] = "We pay"
        pm = re.search(r'(\d+[-–]?\d*)\s*(business\s+days?|working\s+days?)', text)
        if pm: info["refund_processing"] = pm.group(0).strip()
        if any(k in text for k in ["we accept exchange","exchanges accepted","yes"]) and "exchange" in text:
            info["accepts_exchanges"] = "Yes"
        elif any(k in text for k in ["no exchange","we do not accept exchange"]):
            info["accepts_exchanges"] = "No"
        if any(k in text for k in ["no restocking fee","no restock","restocking fee: none"]):
            info["restocking_fee"] = "No fee"
        elif "restocking fee" in text:
            fm = re.search(r'(\d+)%?\s*restocking', text)
            info["restocking_fee"] = f"{fm.group(1)}%" if fm else "Yes (amount unclear)"
        return info

    # ── SCORE CALCULATOR ─────────────────────────────────────────────────────

    def _build_result(self):
        passed = sum(1 for r in self.results if r.status == "PASS")
        failed = sum(1 for r in self.results if r.status == "FAIL")
        warnings = sum(1 for r in self.results if r.status == "WARNING")
        skipped = sum(1 for r in self.results if r.status == "SKIP")
        total = len(self.results)
        scoreable = total - skipped
        score = round((passed + warnings * 0.5) / scoreable * 100, 1) if scoreable > 0 else 0
        return ScanResult(
            url=self.base_url, scanned_at=datetime.now().isoformat(),
            scan_time_seconds=round(time.time() - self.start_time, 1),
            domain=self.domain, store_intelligence=self.store_intelligence,
            checks=self.results, score=score, total_checks=total,
            passed=passed, failed=failed, warnings=warnings, skipped=skipped,
        )


async def scan_store(url: str) -> dict:
    scanner = GMCScanner(url)
    result = await scanner.run()
    return {
        "url": result.url, "domain": result.domain,
        "scanned_at": result.scanned_at, "scan_time_seconds": result.scan_time_seconds,
        "score": result.score, "total_checks": result.total_checks,
        "passed": result.passed, "failed": result.failed,
        "warnings": result.warnings, "skipped": result.skipped,
        "risk_level": "high" if result.score < 50 else "medium" if result.score < 75 else "low",
        "store_intelligence": result.store_intelligence,
        "checks": [
            {"id": c.id, "category": c.category, "name": c.name,
             "status": c.status, "severity": c.severity,
             "description": c.description, "fix": c.fix,
             "urls": c.urls, "details": c.details}
            for c in sorted(result.checks, key=lambda x: (
                0 if x.status=="FAIL" else 1 if x.status=="WARNING" else 2))
        ],
    }


if __name__ == "__main__":
    import json, sys
    url = sys.argv[1] if len(sys.argv) > 1 else "https://makfool.com"
    result = asyncio.run(scan_store(url))
    print(json.dumps(result, indent=2, default=str))
