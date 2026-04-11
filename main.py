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
<style>*{margin:0;padding:0;box-sizing:border-box}body{font-family:system-ui,-apple-system,sans-serif;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);min-height:100vh;display:flex;align-items:center;justify-content:center;color:#fff}.container{text-align:center;padding:2rem}.logo{font-size:4rem;margin-bottom:1rem}.title{font-size:2.5rem;font-weight:700;margin-bottom:1rem}.subtitle{font-size:1.2rem;opacity:0.9;margin-bottom:2rem}.cta{display:inline-block;padding:1rem 2rem;background:#fff;color:#667eea;text-decoration:none;border-radius:8px;font-weight:600;transition:transform 0.2s}.cta:hover{transform:translateY(-2px)}</style>
</head><body>
<div class="container">
<div class="logo">🔥</div>
<h1 class="title">Beacon</h1>
<p class="subtitle">AI-powered team pulse insights</p>
<a href="/dashboard" class="cta">View Dashboard</a>
</div>
</body></html>"""
