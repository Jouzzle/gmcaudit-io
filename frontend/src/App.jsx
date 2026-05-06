import { useState, useEffect, useRef, useCallback } from "react";

const API = "http://localhost:8000";

// ─── THEME ───────────────────────────────────────────────────────────────────
const css = `
  @import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800&family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;1,9..40,300&display=swap');

  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  :root {
    --bg:        #07070C;
    --bg2:       #0D0D15;
    --surface:   #111118;
    --border:    #1C1C28;
    --border2:   #252535;
    --primary:   #6366F1;
    --primary-l: #818CF8;
    --primary-d: #4338CA;
    --white:     #FFFFFF;
    --body:      #C4C4D4;
    --muted:     #5C5C78;
    --fail:      #F43F5E;
    --fail-bg:   #1A0810;
    --warn:      #F59E0B;
    --warn-bg:   #180F00;
    --pass:      #10B981;
    --pass-bg:   #061410;
    --font-head: 'Syne', sans-serif;
    --font-body: 'DM Sans', sans-serif;
  }

  html { scroll-behavior: smooth; }

  body {
    background: var(--bg);
    color: var(--body);
    font-family: var(--font-body);
    font-size: 15px;
    line-height: 1.6;
    -webkit-font-smoothing: antialiased;
    min-height: 100vh;
  }

  ::selection { background: var(--primary); color: #fff; }

  /* Scrollbar */
  ::-webkit-scrollbar { width: 4px; }
  ::-webkit-scrollbar-track { background: var(--bg); }
  ::-webkit-scrollbar-thumb { background: var(--border2); border-radius: 2px; }

  /* Animations */
  @keyframes fadeUp {
    from { opacity: 0; transform: translateY(20px); }
    to   { opacity: 1; transform: translateY(0); }
  }
  @keyframes fadeIn {
    from { opacity: 0; } to { opacity: 1; }
  }
  @keyframes pulse-ring {
    0%   { transform: scale(1); opacity: 0.4; }
    50%  { transform: scale(1.15); opacity: 0.1; }
    100% { transform: scale(1); opacity: 0.4; }
  }
  @keyframes scan-line {
    0%   { transform: translateY(-100%); opacity: 0; }
    10%  { opacity: 1; }
    90%  { opacity: 1; }
    100% { transform: translateY(400px); opacity: 0; }
  }
  @keyframes shimmer {
    0%   { background-position: -200% center; }
    100% { background-position: 200% center; }
  }
  @keyframes spin {
    to { transform: rotate(360deg); }
  }
  @keyframes float {
    0%, 100% { transform: translateY(0px); }
    50%       { transform: translateY(-8px); }
  }
  @keyframes count-up {
    from { opacity: 0; transform: scale(0.5); }
    to   { opacity: 1; transform: scale(1); }
  }

  .animate-fade-up { animation: fadeUp 0.6s ease forwards; }
  .animate-fade-in { animation: fadeIn 0.4s ease forwards; }

  /* Grain overlay */
  body::before {
    content: '';
    position: fixed;
    inset: 0;
    background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='0.03'/%3E%3C/svg%3E");
    pointer-events: none;
    z-index: 9999;
    opacity: 0.4;
  }
`;

// ─── UTILS ───────────────────────────────────────────────────────────────────
const scoreColor = (s) => s < 50 ? "var(--fail)" : s < 75 ? "var(--warn)" : "var(--pass)";
const scoreLabel = (s) => s < 50 ? "HIGH RISK" : s < 75 ? "MEDIUM RISK" : "LOW RISK";
const fmt = (url) => url.replace(/^https?:\/\/(www\.)?/, "").replace(/\/$/, "");

function useCountUp(target, duration = 1200) {
  const [val, setVal] = useState(0);
  useEffect(() => {
    let start = null;
    const step = (ts) => {
      if (!start) start = ts;
      const p = Math.min((ts - start) / duration, 1);
      const ease = 1 - Math.pow(1 - p, 3);
      setVal(Math.round(ease * target));
      if (p < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }, [target]);
  return val;
}

// ─── NAV ─────────────────────────────────────────────────────────────────────
function Nav() {
  return (
    <nav style={{
      position: "fixed", top: 0, left: 0, right: 0, zIndex: 100,
      background: "rgba(7,7,12,0.85)", backdropFilter: "blur(12px)",
      borderBottom: "1px solid var(--border)",
      display: "flex", alignItems: "center", justifyContent: "space-between",
      padding: "0 32px", height: 56,
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <div style={{
          width: 28, height: 28, borderRadius: 8,
          background: "linear-gradient(135deg, var(--primary) 0%, #8B5CF6 100%)",
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: 13, fontWeight: 800, color: "#fff", fontFamily: "var(--font-head)",
        }}>G</div>
        <span style={{ fontFamily: "var(--font-head)", fontWeight: 700, fontSize: 16, color: "#fff" }}>
          GMCAudit<span style={{ color: "var(--primary)" }}>.io</span>
        </span>
      </div>
      <div style={{ display: "flex", gap: 24, alignItems: "center" }}>
        <span style={{ fontSize: 13, color: "var(--muted)", cursor: "pointer" }}>How it works</span>
        <span style={{ fontSize: 13, color: "var(--muted)", cursor: "pointer" }}>Pricing</span>
        <button style={{
          background: "var(--primary)", color: "#fff", border: "none",
          borderRadius: 8, padding: "7px 18px", fontSize: 13,
          fontFamily: "var(--font-body)", fontWeight: 500, cursor: "pointer",
        }}>Scan My Store</button>
      </div>
    </nav>
  );
}

// ─── LANDING PAGE ────────────────────────────────────────────────────────────
function LandingPage({ onScan }) {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleScan = async () => {
    const trimmed = url.trim();
    if (!trimmed) { setError("Enter your store URL"); return; }
    setError("");
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/scan/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: trimmed }),
      });
      const data = await res.json();
      onScan(data.scan_id, trimmed);
    } catch (e) {
      setError("Could not connect to scanner. Make sure backend is running.");
    } finally {
      setLoading(false);
    }
  };

  const checks = [
    { cat: "Trust & Domain", items: ["Domain age", "SSL certificate", "TLD check"] },
    { cat: "Policy Pages", items: ["Shipping policy", "Refund policy", "Privacy policy"] },
    { cat: "Misrepresentation", items: ["No urgency timers", "No fake claims", "No discount codes"] },
    { cat: "Product & Feed", items: ["Title length", "Medical claims", "Image quality"] },
    { cat: "Navigation", items: ["Required nav items", "Track Your Order", "Collections"] },
    { cat: "Technical", items: ["Broken links", "Sitemap", "Page speed"] },
  ];

  const testimonials = [
    { text: "Found the exact issue Google never told me about. Fixed it, appealed once, reinstated.", role: "Fashion Store Owner" },
    { text: "Three failed appeals. GMCAudit found policy issues I never knew about. Reinstated next try.", role: "Home & Garden Store" },
    { text: "Worth every penny. Showed me exactly what was blocking reinstatement.", role: "Beauty Products Store" },
  ];

  return (
    <div style={{ paddingTop: 56 }}>

      {/* HERO */}
      <section style={{
        minHeight: "100vh", display: "flex", flexDirection: "column",
        alignItems: "center", justifyContent: "center",
        padding: "80px 24px 60px", position: "relative", overflow: "hidden",
      }}>
        {/* BG orbs */}
        <div style={{
          position: "absolute", top: "20%", left: "10%",
          width: 500, height: 500, borderRadius: "50%",
          background: "radial-gradient(circle, rgba(99,102,241,0.08) 0%, transparent 70%)",
          pointerEvents: "none",
        }}/>
        <div style={{
          position: "absolute", bottom: "10%", right: "5%",
          width: 400, height: 400, borderRadius: "50%",
          background: "radial-gradient(circle, rgba(139,92,246,0.06) 0%, transparent 70%)",
          pointerEvents: "none",
        }}/>

        {/* Badge */}
        <div style={{
          display: "inline-flex", alignItems: "center", gap: 8,
          background: "rgba(99,102,241,0.1)", border: "1px solid rgba(99,102,241,0.3)",
          borderRadius: 100, padding: "5px 16px", marginBottom: 32,
          animation: "fadeUp 0.5s ease forwards",
        }}>
          <div style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--pass)", animation: "pulse-ring 2s infinite" }}/>
          <span style={{ fontSize: 12, color: "var(--primary-l)", fontWeight: 500 }}>
            89 checks · Shopify-specific · Step-by-step fixes
          </span>
        </div>

        {/* Headline */}
        <h1 style={{
          fontFamily: "var(--font-head)", fontWeight: 800, fontSize: "clamp(36px, 6vw, 72px)",
          lineHeight: 1.1, textAlign: "center", maxWidth: 800, color: "#fff",
          animation: "fadeUp 0.6s 0.1s ease both",
        }}>
          Is Your Store Ready for<br/>
          <span style={{
            background: "linear-gradient(135deg, var(--primary) 0%, #8B5CF6 50%, var(--primary-l) 100%)",
            WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent",
          }}>Google Merchant Center?</span>
        </h1>

        <p style={{
          marginTop: 20, fontSize: 18, color: "var(--body)", textAlign: "center",
          maxWidth: 560, lineHeight: 1.7, animation: "fadeUp 0.6s 0.2s ease both",
        }}>
          Scan your Shopify store in 60 seconds. Get your GMC compliance score,
          see exactly what's blocking approval, and fix it with step-by-step guides.
        </p>

        {/* Scan form */}
        <div style={{
          marginTop: 40, width: "100%", maxWidth: 580,
          animation: "fadeUp 0.6s 0.3s ease both",
        }}>
          <div style={{
            display: "flex", gap: 0,
            background: "var(--surface)", border: "1px solid var(--border2)",
            borderRadius: 14, padding: 6, boxShadow: "0 0 40px rgba(99,102,241,0.1)",
          }}>
            <input
              value={url}
              onChange={e => setUrl(e.target.value)}
              onKeyDown={e => e.key === "Enter" && handleScan()}
              placeholder="https://yourstore.com"
              style={{
                flex: 1, background: "transparent", border: "none", outline: "none",
                padding: "12px 16px", fontSize: 15, color: "#fff",
                fontFamily: "var(--font-body)",
              }}
            />
            <button
              onClick={handleScan}
              disabled={loading}
              style={{
                background: loading ? "var(--border2)" : "linear-gradient(135deg, var(--primary) 0%, #7C3AED 100%)",
                color: "#fff", border: "none", borderRadius: 10,
                padding: "12px 28px", fontSize: 15, fontWeight: 600,
                fontFamily: "var(--font-head)", cursor: loading ? "not-allowed" : "pointer",
                whiteSpace: "nowrap", transition: "all 0.2s",
                boxShadow: loading ? "none" : "0 4px 20px rgba(99,102,241,0.4)",
              }}
            >
              {loading ? "Starting..." : "Scan My Store →"}
            </button>
          </div>
          {error && <p style={{ color: "var(--fail)", fontSize: 13, marginTop: 8, paddingLeft: 6 }}>{error}</p>}
          <p style={{ fontSize: 12, color: "var(--muted)", textAlign: "center", marginTop: 10 }}>
            One-time scan · $29 · No subscription · 1 free re-scan included
          </p>
        </div>

        {/* Stats row */}
        <div style={{
          display: "flex", gap: 40, marginTop: 56,
          animation: "fadeUp 0.6s 0.4s ease both",
        }}>
          {[
            { n: "89", label: "Compliance Checks" },
            { n: "60s", label: "Scan Time" },
            { n: "3×", label: "More Than Competitors" },
          ].map(({ n, label }) => (
            <div key={label} style={{ textAlign: "center" }}>
              <div style={{ fontFamily: "var(--font-head)", fontWeight: 800, fontSize: 28, color: "#fff" }}>{n}</div>
              <div style={{ fontSize: 12, color: "var(--muted)", marginTop: 2 }}>{label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* WHAT WE CHECK */}
      <section style={{ padding: "80px 24px", maxWidth: 1100, margin: "0 auto" }}>
        <div style={{ textAlign: "center", marginBottom: 48 }}>
          <p style={{ fontSize: 11, fontWeight: 700, color: "var(--primary)", letterSpacing: 2, marginBottom: 12 }}>THE 89 CHECKS</p>
          <h2 style={{ fontFamily: "var(--font-head)", fontWeight: 800, fontSize: 36, color: "#fff" }}>
            Everything GMC looks at. We check it all.
          </h2>
          <p style={{ color: "var(--muted)", marginTop: 12, maxWidth: 480, margin: "12px auto 0" }}>
            Our scan covers every signal Google uses for approval decisions — most of which they never tell you about.
          </p>
        </div>
        <div style={{
          display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))",
          gap: 16,
        }}>
          {checks.map(({ cat, items }) => (
            <div key={cat} style={{
              background: "var(--surface)", border: "1px solid var(--border)",
              borderRadius: 12, padding: "20px 24px",
            }}>
              <div style={{
                fontSize: 11, fontWeight: 700, color: "var(--primary-l)",
                letterSpacing: 1, marginBottom: 12,
              }}>{cat.toUpperCase()}</div>
              {items.map(item => (
                <div key={item} style={{
                  display: "flex", alignItems: "center", gap: 8,
                  padding: "5px 0", borderBottom: "1px solid var(--border)",
                  fontSize: 13, color: "var(--body)",
                }}>
                  <span style={{ color: "var(--pass)", fontSize: 10 }}>✓</span>
                  {item}
                </div>
              ))}
            </div>
          ))}
        </div>
      </section>

      {/* VS COMPETITORS */}
      <section style={{ padding: "60px 24px", maxWidth: 900, margin: "0 auto" }}>
        <h2 style={{ fontFamily: "var(--font-head)", fontWeight: 800, fontSize: 32, color: "#fff", textAlign: "center", marginBottom: 32 }}>
          Why GMCAudit.io wins
        </h2>
        <div style={{
          background: "var(--surface)", border: "1px solid var(--border)",
          borderRadius: 16, overflow: "hidden",
        }}>
          {[
            ["", "GMCAudit.io", "GMC Scout", "GoogleClaw"],
            ["Price", "$29 one-time", "€29 one-time", "Free"],
            ["Checks", "89 meaningful", "~173 padded", "21 only"],
            ["Fix guides", "Step-by-step", "Generic", "Basic"],
            ["Shopify-specific", "✓", "Partial", "✗"],
            ["Report design", "Premium dark UI", "Plain white", "Basic PDF"],
            ["Medical claims scan", "✓", "✗", "✗"],
            ["Misrepresentation scan", "✓", "✗", "✗"],
            ["Score teaser free", "✓", "✗", "✓"],
          ].map((row, i) => (
            <div key={i} style={{
              display: "grid", gridTemplateColumns: "1.5fr 1fr 1fr 1fr",
              borderBottom: i < 8 ? "1px solid var(--border)" : "none",
              background: i === 0 ? "var(--border)" : i % 2 === 0 ? "transparent" : "rgba(255,255,255,0.01)",
            }}>
              {row.map((cell, j) => (
                <div key={j} style={{
                  padding: "12px 20px", fontSize: j === 0 ? 13 : 13,
                  color: i === 0 ? "var(--muted)" : j === 1 ? "#fff" : "var(--muted)",
                  fontWeight: i === 0 ? 600 : j === 1 ? 600 : 400,
                  fontFamily: i === 0 || j === 1 ? "var(--font-head)" : "var(--font-body)",
                  background: j === 1 && i > 0 ? "rgba(99,102,241,0.06)" : "transparent",
                  borderRight: j < 3 ? "1px solid var(--border)" : "none",
                }}>
                  {j === 1 && i === 0
                    ? <span style={{ color: "var(--primary-l)" }}>{cell}</span>
                    : cell === "✓" ? <span style={{ color: "var(--pass)" }}>✓</span>
                    : cell === "✗" ? <span style={{ color: "var(--fail)" }}>✗</span>
                    : cell}
                </div>
              ))}
            </div>
          ))}
        </div>
      </section>

      {/* TESTIMONIALS */}
      <section style={{ padding: "60px 24px", maxWidth: 1000, margin: "0 auto" }}>
        <p style={{ fontSize: 11, fontWeight: 700, color: "var(--primary)", letterSpacing: 2, textAlign: "center", marginBottom: 32 }}>
          REAL REINSTATEMENTS
        </p>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: 16 }}>
          {testimonials.map(({ text, role }) => (
            <div key={role} style={{
              background: "var(--surface)", border: "1px solid var(--border)",
              borderRadius: 12, padding: 24,
            }}>
              <div style={{ color: "var(--primary)", fontSize: 20, marginBottom: 12 }}>"</div>
              <p style={{ fontSize: 14, color: "var(--body)", lineHeight: 1.7, marginBottom: 16 }}>{text}</p>
              <p style={{ fontSize: 12, color: "var(--muted)" }}>— {role}</p>
            </div>
          ))}
        </div>
      </section>

      {/* BOTTOM CTA */}
      <section style={{ padding: "80px 24px", textAlign: "center" }}>
        <h2 style={{ fontFamily: "var(--font-head)", fontWeight: 800, fontSize: 40, color: "#fff", marginBottom: 16 }}>
          Don't appeal blind.
        </h2>
        <p style={{ color: "var(--muted)", marginBottom: 32, fontSize: 16 }}>
          Find your GMC blockers in 60 seconds. Fix them. Get approved.
        </p>
        <div style={{ display: "flex", gap: 12, justifyContent: "center", alignItems: "center" }}>
          <input
            placeholder="https://yourstore.com"
            defaultValue={url}
            onChange={e => setUrl(e.target.value)}
            style={{
              background: "var(--surface)", border: "1px solid var(--border2)",
              borderRadius: 10, padding: "12px 18px", fontSize: 15, color: "#fff",
              fontFamily: "var(--font-body)", outline: "none", width: 300,
            }}
          />
          <button
            onClick={handleScan}
            style={{
              background: "linear-gradient(135deg, var(--primary) 0%, #7C3AED 100%)",
              color: "#fff", border: "none", borderRadius: 10,
              padding: "12px 28px", fontSize: 15, fontWeight: 600,
              fontFamily: "var(--font-head)", cursor: "pointer",
              boxShadow: "0 4px 20px rgba(99,102,241,0.4)",
            }}
          >
            Scan My Store →
          </button>
        </div>
        <p style={{ fontSize: 12, color: "var(--muted)", marginTop: 12 }}>
          One-time · $29 · No subscription · 1 re-scan included
        </p>
      </section>

      {/* FOOTER */}
      <footer style={{
        borderTop: "1px solid var(--border)", padding: "24px 32px",
        display: "flex", justifyContent: "space-between", alignItems: "center",
      }}>
        <span style={{ fontFamily: "var(--font-head)", fontWeight: 700, fontSize: 14, color: "var(--muted)" }}>
          GMCAudit.io
        </span>
        <span style={{ fontSize: 12, color: "var(--muted)" }}>© 2026 GMCAudit.io · All rights reserved</span>
      </footer>
    </div>
  );
}

// ─── SCANNING PAGE ────────────────────────────────────────────────────────────
const SCAN_CATEGORIES = [
  "Trust & Domain",
  "Contact & Business Info",
  "Policy Pages",
  "Navigation & Structure",
  "Footer",
  "Product & Feed",
  "Misrepresentation",
  "Homepage Trust",
  "Technical",
  "Social & Brand",
  "Shopify-Specific",
];

function ScanningPage({ scanId, storeUrl, onComplete }) {
  const [status, setStatus] = useState("queued");
  const [activeIdx, setActiveIdx] = useState(0);
  const [elapsed, setElapsed] = useState(0);
  const startRef = useRef(Date.now());

  useEffect(() => {
    const timer = setInterval(() => {
      setElapsed(Math.floor((Date.now() - startRef.current) / 1000));
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  // Animate category progress
  useEffect(() => {
    if (status !== "running" && status !== "queued") return;
    const interval = setInterval(() => {
      setActiveIdx(i => Math.min(i + 1, SCAN_CATEGORIES.length - 1));
    }, 900);
    return () => clearInterval(interval);
  }, [status]);

  // Poll scan status
  useEffect(() => {
    const poll = async () => {
      try {
        const res = await fetch(`${API}/api/scan/${scanId}/status`);
        const data = await res.json();
        setStatus(data.status);
        if (data.status === "complete") {
          setTimeout(() => onComplete(), 600);
        } else if (data.status === "error") {
          console.error("Scan error");
        }
      } catch (e) {}
    };

    const interval = setInterval(poll, 2000);
    poll();
    return () => clearInterval(interval);
  }, [scanId]);

  const progress = Math.round(((activeIdx + 1) / SCAN_CATEGORIES.length) * 100);

  return (
    <div style={{
      minHeight: "100vh", display: "flex", flexDirection: "column",
      alignItems: "center", justifyContent: "center", padding: 24,
    }}>
      {/* Scanning orb */}
      <div style={{ position: "relative", marginBottom: 48 }}>
        {[1, 2, 3].map(i => (
          <div key={i} style={{
            position: "absolute", inset: -(i * 20),
            borderRadius: "50%", border: "1px solid var(--primary)",
            opacity: 0.08 * (4 - i),
            animation: `pulse-ring ${1.5 + i * 0.3}s ease-in-out infinite`,
            animationDelay: `${i * 0.2}s`,
          }}/>
        ))}
        <div style={{
          width: 100, height: 100, borderRadius: "50%",
          background: "linear-gradient(135deg, var(--primary) 0%, #7C3AED 100%)",
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: 36, boxShadow: "0 0 60px rgba(99,102,241,0.5)",
          animation: "float 3s ease-in-out infinite",
        }}>
          🔍
        </div>
      </div>

      <h2 style={{ fontFamily: "var(--font-head)", fontWeight: 800, fontSize: 28, color: "#fff", marginBottom: 8 }}>
        Scanning {fmt(storeUrl)}
      </h2>
      <p style={{ color: "var(--muted)", marginBottom: 40, fontSize: 14 }}>
        Running {SCAN_CATEGORIES.length} check categories · {elapsed}s elapsed
      </p>

      {/* Progress bar */}
      <div style={{ width: "100%", maxWidth: 500, marginBottom: 32 }}>
        <div style={{
          height: 4, background: "var(--border)", borderRadius: 2, overflow: "hidden",
        }}>
          <div style={{
            height: "100%", borderRadius: 2,
            background: "linear-gradient(90deg, var(--primary) 0%, #8B5CF6 100%)",
            width: `${progress}%`, transition: "width 0.8s ease",
          }}/>
        </div>
        <div style={{ display: "flex", justifyContent: "space-between", marginTop: 8 }}>
          <span style={{ fontSize: 12, color: "var(--muted)" }}>{progress}% complete</span>
          <span style={{ fontSize: 12, color: "var(--muted)" }}>~60s total</span>
        </div>
      </div>

      {/* Category list */}
      <div style={{ width: "100%", maxWidth: 500 }}>
        {SCAN_CATEGORIES.map((cat, i) => {
          const done = i < activeIdx;
          const active = i === activeIdx;
          return (
            <div key={cat} style={{
              display: "flex", alignItems: "center", gap: 12,
              padding: "8px 0", borderBottom: "1px solid var(--border)",
              opacity: i > activeIdx ? 0.3 : 1, transition: "opacity 0.3s",
            }}>
              <div style={{
                width: 20, height: 20, borderRadius: "50%", flexShrink: 0,
                display: "flex", alignItems: "center", justifyContent: "center",
                background: done ? "var(--pass-bg)" : active ? "var(--surface)" : "transparent",
                border: done ? "1px solid var(--pass)" : active ? "1px solid var(--primary)" : "1px solid var(--border)",
                fontSize: 10,
              }}>
                {done ? <span style={{ color: "var(--pass)" }}>✓</span>
                  : active ? <div style={{
                    width: 8, height: 8, borderRadius: "50%",
                    border: "1.5px solid var(--primary)",
                    borderTopColor: "transparent",
                    animation: "spin 0.6s linear infinite",
                  }}/> : null}
              </div>
              <span style={{
                fontSize: 13, color: done ? "var(--pass)" : active ? "#fff" : "var(--muted)",
                fontWeight: active ? 600 : 400,
              }}>{cat}</span>
              {done && <span style={{ marginLeft: "auto", fontSize: 11, color: "var(--pass)" }}>Done</span>}
              {active && <span style={{ marginLeft: "auto", fontSize: 11, color: "var(--primary-l)" }}>Scanning...</span>}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ─── TEASER PAGE ──────────────────────────────────────────────────────────────
function TeaserPage({ scanId, storeUrl, onPay }) {
  const [data, setData] = useState(null);
  const [email, setEmail] = useState("");
  const [emailSubmitted, setEmailSubmitted] = useState(false);
  const [payLoading, setPayLoading] = useState(false);

  const animScore = useCountUp(data?.score ?? 0, 1500);
  const animFailed = useCountUp(data?.failed ?? 0, 1000);
  const animWarnings = useCountUp(data?.warnings ?? 0, 1000);
  const animPassed = useCountUp(data?.passed ?? 0, 1000);

  useEffect(() => {
    const load = async () => {
      const res = await fetch(`${API}/api/scan/${scanId}/teaser`);
      const d = await res.json();
      setData(d);
    };
    load();
  }, [scanId]);

  const handleEmailSubmit = () => {
    if (!email.includes("@")) return;
    setEmailSubmitted(true);
  };

  const handlePay = async () => {
    setPayLoading(true);
    try {
      const res = await fetch(`${API}/api/payment/create-session`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ scan_id: scanId, email }),
      });
      const d = await res.json();
      if (d.url) window.location.href = d.url;
      else onPay(scanId); // fallback for demo
    } catch {
      onPay(scanId);
    } finally {
      setPayLoading(false);
    }
  };

  if (!data) return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <div style={{ width: 32, height: 32, border: "2px solid var(--primary)", borderTopColor: "transparent", borderRadius: "50%", animation: "spin 0.8s linear infinite" }}/>
    </div>
  );

  const sc = scoreColor(data.score);
  const sl = scoreLabel(data.score);

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column", alignItems: "center", padding: "100px 24px 60px" }}>

      {/* Store URL */}
      <div style={{
        fontSize: 13, color: "var(--muted)", marginBottom: 32,
        background: "var(--surface)", border: "1px solid var(--border)",
        borderRadius: 8, padding: "6px 16px",
      }}>
        {fmt(storeUrl)}
      </div>

      {/* SCORE CARD */}
      <div style={{
        width: "100%", maxWidth: 520,
        background: "radial-gradient(ellipse at top, rgba(99,102,241,0.08) 0%, transparent 70%), var(--surface)",
        border: "1px solid var(--border2)", borderRadius: 20,
        padding: "40px 36px", textAlign: "center", marginBottom: 24,
        boxShadow: `0 0 60px ${sc}18`,
        animation: "count-up 0.6s ease forwards",
      }}>
        {/* Risk badge */}
        <div style={{
          display: "inline-flex", alignItems: "center", gap: 6,
          background: data.score < 50 ? "var(--fail-bg)" : data.score < 75 ? "var(--warn-bg)" : "var(--pass-bg)",
          border: `1px solid ${sc}44`, borderRadius: 100,
          padding: "4px 14px", marginBottom: 20, fontSize: 11, fontWeight: 700,
          color: sc, letterSpacing: 1,
        }}>
          <span>●</span> {sl} · SCAN COMPLETE
        </div>

        {/* Score */}
        <div style={{
          fontFamily: "var(--font-head)", fontWeight: 800,
          fontSize: 88, lineHeight: 1, color: sc,
          textShadow: `0 0 40px ${sc}44`,
        }}>
          {animScore}<span style={{ fontSize: 40 }}>%</span>
        </div>
        <p style={{ color: "var(--muted)", fontSize: 14, marginTop: 6 }}>
          GMC Compliance Score for <strong style={{ color: "var(--body)" }}>{fmt(storeUrl)}</strong>
        </p>

        {/* 3 stats */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8, marginTop: 28 }}>
          {[
            { n: animFailed, label: "CRITICAL\nISSUES", color: "var(--fail)", bg: "var(--fail-bg)" },
            { n: animWarnings, label: "WARNINGS\nFOUND", color: "var(--warn)", bg: "var(--warn-bg)" },
            { n: animPassed, label: "CHECKS\nPASSED", color: "var(--pass)", bg: "var(--pass-bg)" },
          ].map(({ n, label, color, bg }) => (
            <div key={label} style={{
              background: bg, borderRadius: 12, padding: "16px 8px",
              border: `1px solid ${color}22`,
            }}>
              <div style={{ fontFamily: "var(--font-head)", fontWeight: 800, fontSize: 36, color }}>{n}</div>
              <div style={{ fontSize: 10, color: "var(--muted)", marginTop: 4, whiteSpace: "pre-line", lineHeight: 1.3 }}>{label}</div>
            </div>
          ))}
        </div>

        {/* Urgency message */}
        <p style={{ marginTop: 24, fontSize: 15, color: "#fff", lineHeight: 1.5 }}>
          Your store has <strong style={{ color: "var(--fail)" }}>{data.failed} issues</strong> that can trigger a GMC suspension.
        </p>
        <p style={{ fontSize: 13, color: "var(--muted)", marginTop: 4 }}>
          Enter your email to see exactly what to fix.
        </p>
      </div>

      {/* CATEGORY PREVIEW — blurred teaser */}
      <div style={{ width: "100%", maxWidth: 520, marginBottom: 24, position: "relative" }}>
        <div style={{
          background: "var(--surface)", border: "1px solid var(--border)",
          borderRadius: 16, overflow: "hidden",
        }}>
          <div style={{ padding: "16px 20px", borderBottom: "1px solid var(--border)", display: "flex", justifyContent: "space-between" }}>
            <span style={{ fontSize: 12, fontWeight: 700, color: "var(--primary-l)", letterSpacing: 1 }}>ISSUES BY CATEGORY</span>
            <span style={{ fontSize: 12, color: "var(--muted)" }}>{data.total_checks} checks total</span>
          </div>
          {(data.category_summary || []).map((cat, i) => (
            <div key={cat.category} style={{
              display: "flex", alignItems: "center", justifyContent: "space-between",
              padding: "10px 20px", borderBottom: "1px solid var(--border)",
              filter: i > 2 ? "blur(4px)" : "none",
              pointerEvents: i > 2 ? "none" : "auto",
            }}>
              <span style={{ fontSize: 13, color: "var(--body)" }}>{cat.category}</span>
              <div style={{ display: "flex", gap: 12 }}>
                {cat.failed > 0 && <span style={{ fontSize: 12, color: "var(--fail)", fontWeight: 600 }}>{cat.failed} FAIL</span>}
                {cat.warnings > 0 && <span style={{ fontSize: 12, color: "var(--warn)", fontWeight: 600 }}>{cat.warnings} WARN</span>}
                {cat.failed === 0 && cat.warnings === 0 && <span style={{ fontSize: 12, color: "var(--pass)" }}>✓</span>}
              </div>
            </div>
          ))}
          {/* Blur overlay for lower items */}
          <div style={{
            position: "absolute", bottom: 0, left: 0, right: 0, height: 120,
            background: "linear-gradient(to top, var(--bg) 0%, transparent 100%)",
            display: "flex", alignItems: "flex-end", justifyContent: "center",
            paddingBottom: 20,
          }}>
            <span style={{ fontSize: 13, color: "var(--muted)" }}>🔒 Unlock full report to see all issues</span>
          </div>
        </div>
      </div>

      {/* EMAIL GATE / PAYMENT */}
      <div style={{
        width: "100%", maxWidth: 520,
        background: "var(--surface)", border: "1px solid var(--border2)",
        borderRadius: 16, padding: "28px 28px",
      }}>
        {!emailSubmitted ? (
          <>
            <h3 style={{ fontFamily: "var(--font-head)", fontWeight: 700, fontSize: 18, color: "#fff", marginBottom: 6 }}>
              See the Full Report →
            </h3>
            <p style={{ fontSize: 13, color: "var(--muted)", marginBottom: 20 }}>
              Enter your email to unlock all {data.failed + data.warnings} issues with step-by-step fix guides.
            </p>
            <div style={{ display: "flex", gap: 8 }}>
              <input
                value={email}
                onChange={e => setEmail(e.target.value)}
                onKeyDown={e => e.key === "Enter" && handleEmailSubmit()}
                placeholder="your@email.com"
                style={{
                  flex: 1, background: "var(--bg)", border: "1px solid var(--border2)",
                  borderRadius: 10, padding: "11px 14px", fontSize: 14,
                  color: "#fff", fontFamily: "var(--font-body)", outline: "none",
                }}
              />
              <button
                onClick={handleEmailSubmit}
                style={{
                  background: "linear-gradient(135deg, var(--primary) 0%, #7C3AED 100%)",
                  color: "#fff", border: "none", borderRadius: 10,
                  padding: "11px 20px", fontSize: 14, fontWeight: 600,
                  fontFamily: "var(--font-head)", cursor: "pointer",
                  whiteSpace: "nowrap",
                  boxShadow: "0 4px 16px rgba(99,102,241,0.4)",
                }}
              >
                See Full Report →
              </button>
            </div>
            <p style={{ fontSize: 11, color: "var(--muted)", marginTop: 10, textAlign: "center" }}>
              No spam. One email. Full report unlocked instantly.
            </p>
          </>
        ) : (
          <>
            <div style={{ display: "flex", gap: 10, marginBottom: 20 }}>
              <div style={{
                width: 40, height: 40, borderRadius: "50%", background: "var(--pass-bg)",
                border: "1px solid var(--pass)", display: "flex", alignItems: "center",
                justifyContent: "center", fontSize: 16, flexShrink: 0,
              }}>✓</div>
              <div>
                <p style={{ fontSize: 14, color: "#fff", fontWeight: 600 }}>Email confirmed</p>
                <p style={{ fontSize: 12, color: "var(--muted)" }}>{email}</p>
              </div>
            </div>

            <div style={{
              background: "var(--bg)", border: "1px solid var(--border)",
              borderRadius: 12, padding: "16px 20px", marginBottom: 20,
            }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
                <span style={{ fontSize: 14, color: "var(--body)" }}>Full GMC Compliance Report</span>
                <span style={{ fontFamily: "var(--font-head)", fontWeight: 700, fontSize: 18, color: "#fff" }}>$29</span>
              </div>
              {[
                `${data.failed} critical issues with step-by-step fixes`,
                `${data.warnings} warnings explained`,
                "Branded PDF report",
                "1 free re-scan after fixes",
              ].map(item => (
                <div key={item} style={{ display: "flex", gap: 8, fontSize: 13, color: "var(--muted)", marginTop: 4 }}>
                  <span style={{ color: "var(--pass)" }}>✓</span> {item}
                </div>
              ))}
            </div>

            <button
              onClick={handlePay}
              disabled={payLoading}
              style={{
                width: "100%", background: "linear-gradient(135deg, var(--primary) 0%, #7C3AED 100%)",
                color: "#fff", border: "none", borderRadius: 12, padding: "15px",
                fontSize: 16, fontWeight: 700, fontFamily: "var(--font-head)",
                cursor: payLoading ? "not-allowed" : "pointer",
                boxShadow: "0 4px 24px rgba(99,102,241,0.5)",
              }}
            >
              {payLoading ? "Redirecting to payment..." : "Unlock Full Report · $29 →"}
            </button>
            <p style={{ fontSize: 11, color: "var(--muted)", textAlign: "center", marginTop: 10 }}>
              Secure payment via Stripe · One-time · No subscription
            </p>
          </>
        )}
      </div>
    </div>
  );
}

// ─── FULL REPORT PAGE ─────────────────────────────────────────────────────────
function ReportPage({ scanId, token }) {
  const [data, setData] = useState(null);

  useEffect(() => {
    const load = async () => {
      const url = `${API}/api/scan/${scanId}/full${token ? `?token=${token}` : ""}`;
      const res = await fetch(url);
      if (res.ok) setData(await res.json());
    };
    load();
  }, [scanId, token]);

  if (!data) return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <div style={{ textAlign: "center" }}>
        <div style={{ width: 40, height: 40, border: "2px solid var(--primary)", borderTopColor: "transparent", borderRadius: "50%", animation: "spin 0.8s linear infinite", margin: "0 auto 16px" }}/>
        <p style={{ color: "var(--muted)" }}>Loading your report...</p>
      </div>
    </div>
  );

  const fails = data.checks.filter(c => c.status === "FAIL");
  const warnings = data.checks.filter(c => c.status === "WARNING");
  const passes = data.checks.filter(c => c.status === "PASS");
  const sc = scoreColor(data.score);

  return (
    <div style={{ maxWidth: 780, margin: "0 auto", padding: "80px 24px 80px" }}>

      {/* Header */}
      <div style={{ marginBottom: 40 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 20 }}>
          <div>
            <p style={{ fontSize: 11, color: "var(--primary-l)", fontWeight: 700, letterSpacing: 2, marginBottom: 4 }}>GMC COMPLIANCE REPORT</p>
            <h1 style={{ fontFamily: "var(--font-head)", fontWeight: 800, fontSize: 28, color: "#fff" }}>{data.domain}</h1>
          </div>
          <a
            href={`${API}/api/scan/${scanId}/pdf${token ? `?token=${token}` : ""}`}
            target="_blank"
            rel="noreferrer"
            style={{
              background: "var(--primary)", color: "#fff", border: "none",
              borderRadius: 10, padding: "10px 20px", fontSize: 13, fontWeight: 600,
              fontFamily: "var(--font-head)", cursor: "pointer", textDecoration: "none",
              display: "flex", alignItems: "center", gap: 6,
            }}
          >
            ↓ Download PDF
          </a>
        </div>

        {/* Score overview */}
        <div style={{
          display: "grid", gridTemplateColumns: "auto 1fr 1fr 1fr",
          gap: 16, background: "var(--surface)", border: "1px solid var(--border)",
          borderRadius: 16, padding: 24, alignItems: "center",
        }}>
          <div style={{ textAlign: "center", paddingRight: 24, borderRight: "1px solid var(--border)" }}>
            <div style={{ fontFamily: "var(--font-head)", fontWeight: 800, fontSize: 56, color: sc }}>{data.score}%</div>
            <div style={{ fontSize: 11, color: "var(--muted)", marginTop: 2 }}>{scoreLabel(data.score)}</div>
          </div>
          {[
            { n: data.failed, label: "Critical Issues", color: "var(--fail)" },
            { n: data.warnings, label: "Warnings", color: "var(--warn)" },
            { n: data.passed, label: "Passed", color: "var(--pass)" },
          ].map(({ n, label, color }) => (
            <div key={label} style={{ textAlign: "center" }}>
              <div style={{ fontFamily: "var(--font-head)", fontWeight: 800, fontSize: 36, color }}>{n}</div>
              <div style={{ fontSize: 12, color: "var(--muted)" }}>{label}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Issues */}
      {fails.length > 0 && (
        <div style={{ marginBottom: 40 }}>
          <h2 style={{ fontFamily: "var(--font-head)", fontWeight: 700, fontSize: 18, color: "var(--fail)", marginBottom: 16 }}>
            ● Critical Issues ({fails.length})
          </h2>
          {fails.map(check => <CheckBlock key={check.id} check={check} />)}
        </div>
      )}

      {warnings.length > 0 && (
        <div style={{ marginBottom: 40 }}>
          <h2 style={{ fontFamily: "var(--font-head)", fontWeight: 700, fontSize: 18, color: "var(--warn)", marginBottom: 16 }}>
            ▲ Warnings ({warnings.length})
          </h2>
          {warnings.map(check => <CheckBlock key={check.id} check={check} />)}
        </div>
      )}

      {passes.length > 0 && (
        <div>
          <h2 style={{ fontFamily: "var(--font-head)", fontWeight: 700, fontSize: 18, color: "var(--pass)", marginBottom: 16 }}>
            ✓ Passed ({passes.length})
          </h2>
          {passes.map(check => <CheckBlock key={check.id} check={check} collapsed />)}
        </div>
      )}
    </div>
  );
}

function CheckBlock({ check, collapsed: initCollapsed = false }) {
  const [collapsed, setCollapsed] = useState(initCollapsed);
  const sc = check.status === "FAIL" ? "var(--fail)" : check.status === "WARNING" ? "var(--warn)" : "var(--pass)";
  const sb = check.status === "FAIL" ? "var(--fail-bg)" : check.status === "WARNING" ? "var(--warn-bg)" : "var(--pass-bg)";

  return (
    <div style={{
      background: sb, border: `1px solid ${sc}22`, borderLeft: `3px solid ${sc}`,
      borderRadius: 10, marginBottom: 10, overflow: "hidden",
    }}>
      <div
        onClick={() => setCollapsed(!collapsed)}
        style={{
          display: "flex", alignItems: "center", gap: 12,
          padding: "14px 18px", cursor: "pointer",
        }}
      >
        <span style={{
          fontSize: 10, fontWeight: 700, color: sc,
          background: `${sc}22`, borderRadius: 4, padding: "2px 8px",
          letterSpacing: 0.5,
        }}>{check.status}</span>
        <div style={{ flex: 1 }}>
          <p style={{ fontSize: 11, color: "var(--muted)", marginBottom: 1 }}>{check.category}</p>
          <p style={{ fontSize: 14, color: "#fff", fontWeight: 600 }}>{check.name}</p>
        </div>
        <span style={{ color: "var(--muted)", fontSize: 12 }}>{collapsed ? "▼" : "▲"}</span>
      </div>

      {!collapsed && (
        <div style={{ padding: "0 18px 16px", borderTop: `1px solid ${sc}15` }}>
          <p style={{ fontSize: 13, color: "var(--body)", marginTop: 12, marginBottom: 12 }}>{check.description}</p>
          {check.urls?.length > 0 && (
            <div style={{ marginBottom: 12 }}>
              <p style={{ fontSize: 11, color: "var(--muted)", marginBottom: 4 }}>PAGES AFFECTED</p>
              {check.urls.map(u => (
                <a key={u} href={u} target="_blank" rel="noreferrer" style={{
                  display: "block", fontSize: 12, color: "var(--primary-l)",
                  textDecoration: "none", marginBottom: 2,
                }}>{u}</a>
              ))}
            </div>
          )}
          {check.fix && (
            <div style={{
              background: "rgba(0,0,0,0.3)", borderRadius: 8, padding: "12px 14px",
            }}>
              <p style={{ fontSize: 11, fontWeight: 700, color: sc, marginBottom: 8 }}>ACTION REQUIRED</p>
              {check.fix.split("\n").filter(Boolean).map((line, i) => (
                <p key={i} style={{ fontSize: 13, color: "var(--body)", marginBottom: 4 }}>{line}</p>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ─── APP ROUTER ───────────────────────────────────────────────────────────────
export default function App() {
  const [page, setPage] = useState("landing");
  const [scanId, setScanId] = useState(null);
  const [storeUrl, setStoreUrl] = useState("");
  const [reportToken, setReportToken] = useState(null);

  // Handle URL params for post-payment redirect
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const sid = params.get("scan_id") || window.location.pathname.split("/report/")[1]?.split("?")[0];
    const tok = params.get("token");
    const session = params.get("session_id");
    if (sid && (tok || session)) {
      setScanId(sid);
      setReportToken(tok);
      setPage("report");
    }
  }, []);

  const handleScan = (id, url) => {
    setScanId(id);
    setStoreUrl(url);
    setPage("scanning");
  };

  const handleScanComplete = () => setPage("teaser");
  const handlePay = (id, tok) => { setReportToken(tok); setPage("report"); };

  return (
    <>
      <style>{css}</style>
      <Nav />
      {page === "landing" && <LandingPage onScan={handleScan} />}
      {page === "scanning" && <ScanningPage scanId={scanId} storeUrl={storeUrl} onComplete={handleScanComplete} />}
      {page === "teaser" && <TeaserPage scanId={scanId} storeUrl={storeUrl} onPay={handlePay} />}
      {page === "report" && <ReportPage scanId={scanId} token={reportToken} />}
    </>
  );
}
