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
<style>*{margin:0;padding:0;box-sizing:border-box}body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);min-height:100vh;display:flex;align-items:center;justify-content:center;color:#fff}.container{text-align:center;padding:2rem;max-width:800px}.logo{font-size:4rem;margin-bottom:1rem}.title{font-size:3rem;font-weight:700;margin-bottom:1rem;text-shadow:2px 2px 4px rgba(0,0,0,0.2)}.subtitle{font-size:1.5rem;margin-bottom:2rem;opacity:0.9}.features{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:2rem;margin-top:3rem}.feature{background:rgba(255,255,255,0.1);backdrop-filter:blur(10px);padding:2rem;border-radius:1rem;transition:transform 0.3s ease}.feature:hover{transform:translateY(-5px)}.feature-icon{font-size:3rem;margin-bottom:1rem}.feature-title{font-size:1.3rem;font-weight:600;margin-bottom:0.5rem}.feature-desc{opacity:0.8;line-height:1.6}.cta{margin-top:3rem}.btn{display:inline-block;padding:1rem 2.5rem;font-size:1.2rem;font-weight:600;color:#fff;background:#ff0000;border:none;border-radius:50px;text-decoration:none;cursor:pointer;transition:all 0.3s ease;box-shadow:0 4px 15px rgba(255,0,0,0.3)}.btn:hover{transform:scale(1.05);box-shadow:0 6px 20px rgba(255,0,0,0.4)}</style>
</head><body>
<div class="container">
<div class="logo">🔴</div>
<h1 class="title">Beacon</h1>
<p class="subtitle">AI-powered team pulse checker</p>
<div class="features">
<div class="feature">
<div class="feature-icon">📊</div>
<h3 class="feature-title">Real-time Insights</h3>
<p class="feature-desc">Track team performance with intelligent pulse checks</p>
</div>
<div class="feature">
<div class="feature-icon">🤖</div>
<h3 class="feature-title">AI Analysis</h3>
<p class="feature-desc">Get actionable insights powered by advanced AI</p>
</div>
<div class="feature">
<div class="feature-icon">🚨</div>
<h3 class="feature-title">Smart Alerts</h3>
<p class="feature-desc">Stay informed with trend detection and notifications</p>
</div>
</div>
<div class="cta">
<a href="/dashboard" class="btn">Get Started</a>
</div>
</div>
</body></html>"""
