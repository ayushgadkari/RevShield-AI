from datetime import datetime
import os
import sqlite3
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from google import genai
from pydantic import BaseModel
from dotenv import load_dotenv

# Load variables from the .env file automatically
load_dotenv()

# Initialize Gemini Client (Free Tier)
AI_API_KEY = os.environ.get("GEMINI_API_KEY")
ai_client = genai.Client(api_key=AI_API_KEY)

app = FastAPI(
    title="RevShield AI - Revenue Recovery Engine",
    version="2.0",
)

# Initialize SQLite Database for audit trail
def init_db():
    conn = sqlite3.connect("revshield.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS failed_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            payment_id TEXT,
            amount INTEGER,
            currency TEXT,
            error_code TEXT,
            error_description TEXT,
            status TEXT DEFAULT 'PENDING',
            diagnosis TEXT,
            action_taken TEXT,
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

class WebhookPayload(BaseModel):
    event: str
    payload: dict

def diagnose_failure_with_ai(error_code: str, error_description: str) -> str:
    """Uses Gemini Flash to analyze payment failure and decide classification."""
    prompt = f"""
    You are an expert fintech payment gateway recovery agent. 
    Analyze the following payment failure and classify it strictly as either "RECOVERABLE" or "PERMANENT".
    
    Error Code: {error_code}
    Error Description: {error_description}
    
    Rules:
    - RECOVERABLE: Transient bank timeouts, gateway network glitches, temporary server drops. These can be retried or routed.
    - PERMANENT: Insufficient funds, incorrect UPI PIN, card blocked, fraud suspected, invalid card details. These must NOT be retried.
    
    Respond in format: [CLASSIFICATION] - [Short 1-sentence reason]
    """
    try:
        response = ai_client.models.generate_content(
            model="gemini-3.6-flash", contents=prompt
        )
        return response.text.strip()
    except Exception as e:
        return (
            f"PERMANENT - AI diagnosis failed due to error: {str(e)} (Defaulting to safe block)"
        )

@app.post("/webhook/failure")
async def receive_webhook(data: WebhookPayload):
    if data.event != "payment.failed":
        return {"status": "ignored", "message": "Event not handled"}

    # Flexible parsing: supports both standard nested webhook formats and direct flat payloads
    payment_entity = data.payload.get("payment", {}).get("entity", {})
    if not payment_entity:
        payment_entity = data.payload

    payment_id = payment_entity.get("id") or payment_entity.get("payment_id", "pay_unknown")
    amount = payment_entity.get("amount", 0)
    currency = payment_entity.get("currency", "INR")
    error_code = payment_entity.get("error_code", "UNKNOWN_ERROR")
    error_description = payment_entity.get("error_description", "No description provided")

    # --- AI DIAGNOSIS STEP ---
    ai_diagnosis = diagnose_failure_with_ai(error_code, error_description)

    # Determine action based on AI diagnosis (Guardrails)
    if "RECOVERABLE" in ai_diagnosis.upper():
        action_taken = "SCHEDULED_SMART_RETRY (Routed to backup test-mode gateway)"
        final_status = "RECOVERY_IN_PROGRESS"
    else:
        action_taken = "BLOCKED_PERMANENT_FAILURE (No retry allowed)"
        final_status = "DROPPED_SECURELY"

    # Save to SQLite Database
    conn = sqlite3.connect("revshield.db")
    cursor = conn.cursor()
    cursor.execute(
        """
            INSERT INTO failed_transactions (payment_id, amount, currency, error_code, error_description, status, diagnosis, action_taken, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            payment_id,
            amount,
            currency,
            error_code,
            error_description,
            final_status,
            ai_diagnosis,
            action_taken,
            datetime.now().isoformat(),
        ),
    )
    conn.commit()
    conn.close()

    return {
        "status": "success",
        "payment_id": payment_id,
        "ai_diagnosis": ai_diagnosis,
        "action_taken": action_taken,
    }

@app.get("/audit-trail")
async def get_audit_trail():
    conn = sqlite3.connect("revshield.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM failed_transactions ORDER BY id DESC LIMIT 20")
    rows = cursor.fetchall()
    conn.close()
    return {"audit_trail": [dict(row) for row in rows]}

# --- Interactive Web Dashboard UI Route ---
def get_dashboard_data():
    conn = sqlite3.connect("revshield.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM failed_transactions ORDER BY id DESC LIMIT 50")
    rows = [dict(row) for row in cursor.fetchall()]

    # Compute summary metrics
    cursor.execute(
        "SELECT COUNT(*), SUM(amount), SUM(CASE WHEN status='RECOVERY_IN_PROGRESS' THEN 1 ELSE 0 END), SUM(CASE WHEN status='DROPPED_SECURELY' THEN 1 ELSE 0 END) FROM failed_transactions"
    )
    metrics = cursor.fetchone()
    conn.close()

    total_tx = metrics[0] or 0
    total_volume = metrics[1] or 0
    recovered_count = metrics[2] or 0
    dropped_count = metrics[3] or 0

    success_rate = (
        round((recovered_count / total_tx * 100), 1) if total_tx > 0 else 0.0
    )

    return (
        rows,
        total_tx,
        total_volume,
        recovered_count,
        dropped_count,
        success_rate,
    )

@app.get("/", response_class=HTMLResponse)
def dashboard():
    (
        rows,
        total_tx,
        total_volume,
        recovered_count,
        dropped_count,
        success_rate,
    ) = get_dashboard_data()

    table_rows = ""
    for r in rows:
        status_color = (
            "bg-blue-900 text-blue-200 border-blue-700"
            if "RECOVERY" in r["status"]
            else "bg-rose-900 text-rose-200 border-rose-700"
        )
        table_rows += f"""
        <tr class="hover:bg-slate-700/50 transition">
            <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-white">{r['payment_id']}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-slate-300">₹{r['amount']:,.2f}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-slate-300"><span class="px-2 py-1 text-xs font-semibold rounded bg-slate-700 text-slate-200">{r['error_code']}</span></td>
            <td class="px-6 py-4 whitespace-nowrap text-sm"><span class="px-2.5 py-1 inline-flex text-xs font-semibold rounded-full border {status_color}">{r['status']}</span></td>
            <td class="px-6 py-4 text-sm text-slate-300 max-w-xs truncate" title="{r['diagnosis']}">{r['diagnosis']}</td>
            <td class="px-6 py-4 whitespace-nowrap text-xs text-slate-400">{r['created_at']}</td>
        </tr>
        """

    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>RevShield AI | Autonomous Risk Dashboard</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-slate-950 text-slate-100 min-h-screen">
        <div class="max-w-7xl mx-auto px-4 py-8">
            <!-- Header -->
            <div class="flex justify-between items-center mb-8 border-b border-slate-800 pb-4">
                <div>
                    <h1 class="text-3xl font-bold tracking-tight text-white">RevShield AI 🛡️</h1>
                    <p class="text-sm text-slate-400">Autonomous Payment Failure Recovery & Security Gateway</p>
                </div>
                <div>
                    <span class="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-emerald-950 text-emerald-400 border border-emerald-800">
                        ● System Active & Secure
                    </span>
                </div>
            </div>

            <!-- Metrics Grid -->
            <div class="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
                <div class="bg-slate-900 p-6 rounded-xl border border-slate-800 shadow-lg">
                    <p class="text-sm font-medium text-slate-400">Total Transactions</p>
                    <p class="text-3xl font-bold text-white mt-2">{total_tx}</p>
                </div>
                <div class="bg-slate-900 p-6 rounded-xl border border-slate-800 shadow-lg">
                    <p class="text-sm font-medium text-slate-400">Total Volume Analyzed</p>
                    <p class="text-3xl font-bold text-indigo-400 mt-2">₹{total_volume:,.0f}</p>
                </div>
                <div class="bg-slate-900 p-6 rounded-xl border border-slate-800 shadow-lg">
                    <p class="text-sm font-medium text-slate-400">AI Recovery Success Rate</p>
                    <p class="text-3xl font-bold text-emerald-400 mt-2">{success_rate}%</p>
                </div>
                <div class="bg-slate-900 p-6 rounded-xl border border-slate-800 shadow-lg">
                    <p class="text-sm font-medium text-slate-400">Secured & Blocked</p>
                    <p class="text-3xl font-bold text-rose-400 mt-2">{dropped_count}</p>
                </div>
            </div>

            <!-- Audit Trail Table -->
            <div class="bg-slate-900 rounded-xl border border-slate-800 shadow-xl overflow-hidden">
                <div class="px-6 py-4 bg-slate-900/50 border-b border-slate-800 flex justify-between items-center">
                    <h3 class="text-lg font-semibold text-white">Real-Time Audit Trail</h3>
                    <button onclick="location.reload()" class="px-3 py-1.5 bg-indigo-600 text-white text-xs font-semibold rounded-lg hover:bg-indigo-500 transition shadow">Refresh Data</button>
                </div>
                <div class="overflow-x-auto">
                    <table class="min-w-full divide-y divide-slate-800">
                        <thead class="bg-slate-950">
                            <tr>
                                <th class="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">Payment ID</th>
                                <th class="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">Amount</th>
                                <th class="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">Error Code</th>
                                <th class="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">Status</th>
                                <th class="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">AI Diagnosis</th>
                                <th class="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">Timestamp</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-slate-800 bg-slate-900">
                            {table_rows}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    return html_content