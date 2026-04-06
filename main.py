"""Beacon — AI-powered team pulse checker."""
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import datetime

app = FastAPI(title="Beacon", version="0.1.0")

@app.get("/health")
def health():
    return {"status": "healthy", "service": "beacon",
            "timestamp": datetime.datetime.utcnow().isoformat()}

@app.get("/", response_class=HTMLResponse)
def home():
    return """<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Beacon</title>
<style>*{margin:0;padding:0;box-sizing:border-box}body{font-family:-apple-system,sans-serif;
background:#0F172A;color:#E2E8F0;min-height:100vh;display:flex;align-items:center;
justify-content:center}.c{text-align:center;max-width:600px;padding:40px}
h1{font-size:3rem;font-weight:800;margin-bottom:16px;background:linear-gradient(135deg,#38BDF8,#818CF8);
-webkit-background-clip:text;-webkit-text-fill-color:transparent}
p{font-size:1.1rem;color:#94A3B8;line-height:1.7;margin-bottom:24px}
.s{display:inline-flex;align-items:center;gap:8px;background:#1E293B;border-radius:24px;
padding:8px 20px;font-size:.9rem;color:#38BDF8}
.d{width:8px;height:8px;border-radius:50%;background:#22C55E;animation:p 2s infinite}
@keyframes p{0%,100%{opacity:1}50%{opacity:.5}}
.g{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:32px;text-align:left}
.f{background:#1E293B;border-radius:12px;padding:20px}
.f h3{font-size:.95rem;margin-bottom:6px}.f p{font-size:.85rem;color:#64748B;margin:0}
</style></head><body><div class="c"><h1>Beacon</h1>
<p>AI-powered team pulse checker. Know how your team is doing before the standup.</p>
<div class="s"><span class="d"></span>Deployed by ForgeScaler</div>
<div class="g"><div class="f"><h3>Pulse Checks</h3><p>Quick daily sentiment.</p></div>
<div class="f"><h3>Trend Analysis</h3><p>AI spots patterns early.</p></div>
<div class="f"><h3>Smart Alerts</h3><p>Know when energy shifts.</p></div>
<div class="f"><h3>Retros</h3><p>AI-generated summaries.</p></div></div></div></body></html>"""

@app.get("/api/pulse")
def get_pulse():
    return {"status": "stub", "message": "Pulse check — not yet implemented"}

@app.get("/api/team")
def get_team():
    return {"status": "stub", "message": "Team endpoint — not yet implemented"}
