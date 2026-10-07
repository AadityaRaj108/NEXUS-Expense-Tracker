from pathlib import Path
import re

ROOT = Path.cwd()
ROUTES = ROOT / 'app' / 'routes.py'
JS = ROOT / 'app' / 'static' / 'js' / 'app.js'
if not ROUTES.exists() or not JS.exists():
    raise SystemExit('Run this script from NEXUS_Expense_Tracker_Major_Project_v1 project root.')

routes = ROUTES.read_text(encoding='utf-8')
js = JS.read_text(encoding='utf-8')

marker = '# NEXUS INTEGRATION UPGRADE'
if marker not in routes:
    routes += r'''

# NEXUS INTEGRATION UPGRADE
# Voice capture, report export, email/WhatsApp/SMS launchers, and payment gateway hooks.
from datetime import datetime as _nexus_datetime
from flask import Response as _NexusResponse
import csv as _nexus_csv
import io as _nexus_io
import os as _nexus_os
import urllib.parse as _nexus_urlparse


def _nexus_current_user_id():
    return session.get("user_id")


def _nexus_user_transactions():
    uid = _nexus_current_user_id()
    if not uid:
        return []
    db = get_db()
    return db.execute(
        "SELECT id, type, amount, category, payment_method, transaction_date, note, created_at "
        "FROM transactions WHERE user_id = ? ORDER BY transaction_date DESC, id DESC",
        (uid,),
    ).fetchall()


@main.route("/api/report/csv")
@login_required
def nexus_report_csv():
    rows = _nexus_user_transactions()
    out = _nexus_io.StringIO()
    writer = _nexus_csv.writer(out)
    writer.writerow(["ID", "Type", "Amount", "Category", "Payment Method", "Date", "Note", "Created At"])
    for r in rows:
        writer.writerow([r["id"], r["type"], r["amount"], r["category"], r["payment_method"], r["transaction_date"], r["note"] or "", r["created_at"] or ""])
    return _NexusResponse(
        out.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=nexus-expense-report.csv"},
    )


@main.route("/api/integration/config")
@login_required
def nexus_integration_config():
    return jsonify({
        "email": bool(_nexus_os.getenv("NEXUS_SMTP_HOST")),
        "whatsapp": bool(_nexus_os.getenv("NEXUS_WHATSAPP_URL")),
        "sms": bool(_nexus_os.getenv("NEXUS_SMS_URL")),
        "payment": bool(_nexus_os.getenv("NEXUS_PAYMENT_URL")),
        "csv_export": True,
    })


@main.route("/api/integration/links")
@login_required
def nexus_integration_links():
    """Return safe provider links configured through environment variables."""
    return jsonify({
        "email": _nexus_os.getenv("NEXUS_EMAIL_COMPOSE_URL", ""),
        "whatsapp": _nexus_os.getenv("NEXUS_WHATSAPP_URL", ""),
        "sms": _nexus_os.getenv("NEXUS_SMS_URL", ""),
        "payment": _nexus_os.getenv("NEXUS_PAYMENT_URL", ""),
    })
'''
    ROUTES.write_text(routes, encoding='utf-8')

# Append a self-contained UI layer. It injects controls on every logged-in page without touching existing templates/CSS.
if '// NEXUS INTEGRATION UI' not in js:
    js += r'''

// NEXUS INTEGRATION UI
(() => {
  "use strict";
  if (window.__NEXUS_INTEGRATIONS__) return;
  window.__NEXUS_INTEGRATIONS__ = true;

  const esc = (s) => String(s ?? "").replace(/[&<>\"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
  const toast = (msg, type="") => {
    if (typeof window.showToast === "function") return window.showToast(msg, type);
    const old = document.querySelector(".toast");
    if (old) old.remove();
    const t = document.createElement("div");
    t.className = "toast";
    t.textContent = msg;
    document.body.appendChild(t);
    setTimeout(() => t.remove(), 3500);
  };

  const style = document.createElement("style");
  style.textContent = `
    .nexus-tools{position:fixed;right:22px;bottom:22px;z-index:9999;font-family:inherit}
    .nexus-tools-main{border:0;border-radius:999px;padding:13px 17px;cursor:pointer;font-weight:700;background:#111;color:#fff;box-shadow:0 10px 30px rgba(0,0,0,.2)}
    .nexus-tools-panel{display:none;position:absolute;right:0;bottom:56px;width:290px;padding:14px;border-radius:18px;background:#fff;border:1px solid rgba(0,0,0,.09);box-shadow:0 18px 50px rgba(0,0,0,.18)}
    .nexus-tools-panel.open{display:block}.nexus-tools-title{font-weight:800;margin-bottom:10px}.nexus-tool{width:100%;text-align:left;border:1px solid #ddd;background:#fff;border-radius:10px;padding:10px 12px;margin:5px 0;cursor:pointer}.nexus-tool:hover{background:#f5f5f5}
    .nexus-voice-box{display:none;margin-top:10px;padding:10px;border-radius:12px;background:#f7f7f7;font-size:13px}.nexus-voice-box.show{display:block}.nexus-voice-actions{display:flex;gap:7px;margin-top:8px}.nexus-voice-actions button{border:0;border-radius:8px;padding:7px 10px;cursor:pointer}
  `;
  document.head.appendChild(style);

  const root = document.createElement("div");
  root.className = "nexus-tools";
  root.innerHTML = `
    <div class="nexus-tools-panel" id="nexusToolsPanel">
      <div class="nexus-tools-title">NEXUS Connected Tools</div>
      <button class="nexus-tool" data-action="voice">🎙️ Voice Expense Capture</button>
      <button class="nexus-tool" data-action="csv">📊 Export Complete Data (CSV)</button>
      <button class="nexus-tool" data-action="email">📧 Email Report</button>
      <button class="nexus-tool" data-action="whatsapp">💬 WhatsApp</button>
      <button class="nexus-tool" data-action="sms">📱 SMS</button>
      <button class="nexus-tool" data-action="payment">💳 Open Payment Gateway</button>
      <div class="nexus-voice-box" id="nexusVoiceBox">
        <div id="nexusVoiceStatus">Listening…</div>
        <div id="nexusVoiceText"></div>
        <div class="nexus-voice-actions"><button id="nexusVoiceStop">Stop</button><button id="nexusVoiceConfirm">Use</button></div>
      </div>
    </div>
    <button class="nexus-tools-main" id="nexusToolsMain">NEXUS Tools</button>`;
  document.body.appendChild(root);

  const panel = root.querySelector("#nexusToolsPanel");
  root.querySelector("#nexusToolsMain").onclick = () => panel.classList.toggle("open");

  async function config() {
    try { return await (await fetch("/api/integration/config")).json(); } catch { return {}; }
  }

  function startVoice() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const box = root.querySelector("#nexusVoiceBox"), status = root.querySelector("#nexusVoiceStatus"), text = root.querySelector("#nexusVoiceText");
    box.classList.add("show");
    if (!SpeechRecognition) { status.textContent = "Voice recognition is not supported. Use Google Chrome."; return; }
    const r = new SpeechRecognition();
    r.lang = "en-IN"; r.interimResults = true; r.continuous = false;
    let finalText = "";
    r.onstart = () => { status.textContent = "Listening… speak your expense."; };
    r.onresult = e => {
      let t = ""; for (let i=e.resultIndex;i<e.results.length;i++) t += e.results[i][0].transcript + " ";
      text.textContent = t.trim(); if (e.results[e.results.length-1].isFinal) finalText = t.trim();
    };
    r.onerror = e => status.textContent = "Voice error: " + e.error;
    r.onend = () => { if (finalText) { status.textContent = "Captured. Click Use to send it to NEXUS."; box.dataset.text = finalText; } };
    root.querySelector("#nexusVoiceStop").onclick = () => { try { r.stop(); } catch {} };
    root.querySelector("#nexusVoiceConfirm").onclick = async () => {
      const spoken = box.dataset.text || text.textContent;
      if (!spoken) return;
      const resp = await fetch("/api/voice/parse", {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({text:spoken})});
      const data = await resp.json();
      if (!resp.ok) return toast(data.error || "Voice parsing failed.", "error");
      const parsed = data.parsed || data;
      const ok = confirm(`Create transaction?\n\n${(parsed.kind||parsed.type||"expense").toUpperCase()} ₹${parsed.amount||"?"}\n${parsed.category||"Other"} • ${parsed.payment_method||"Other"}`);
      if (!ok) return;
      const c = await fetch("/api/voice/confirm", {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({voice_command_id:data.voice_command_id,parsed})});
      const cd = await c.json();
      if (!c.ok) return toast(cd.error || "Could not save transaction.", "error");
      toast("Voice transaction added successfully.");
      setTimeout(() => location.reload(), 700);
    };
    try { r.start(); } catch(e) { status.textContent = "Microphone could not start."; }
  }

  root.querySelectorAll(".nexus-tool").forEach(btn => btn.onclick = async () => {
    const action = btn.dataset.action;
    if (action === "voice") return startVoice();
    if (action === "csv") { location.href = "/api/report/csv"; return; }
    const links = await (async()=>{try{return await (await fetch("/api/integration/links")).json()}catch{return {}}})();
    if (action === "email") {
      if (links.email) location.href = links.email;
      else { location.href = `mailto:?subject=${encodeURIComponent("NEXUS Expense Report")}&body=${encodeURIComponent("My NEXUS expense report is attached/exported from the dashboard.\n\nUse the Export Complete Data option to download the CSV.")}`; }
    } else if (action === "whatsapp") {
      const url = links.whatsapp || `https://wa.me/?text=${encodeURIComponent("NEXUS Expense Report: Please see the exported CSV from my Expense Tracker.")}`; window.open(url,"_blank","noopener");
    } else if (action === "sms") {
      const url = links.sms || `sms:?body=${encodeURIComponent("NEXUS Expense Report: Please see the exported CSV from my Expense Tracker.")}`; location.href = url;
    } else if (action === "payment") {
      if (links.payment) window.open(links.payment,"_blank","noopener"); else toast("Payment gateway is ready for provider configuration. Set NEXUS_PAYMENT_URL.");
    }
  });
})();
'''
    JS.write_text(js, encoding='utf-8')

print('NEXUS integration upgrade applied.')
print('Files updated:', ROUTES, JS)
print('Run: python run.py')
