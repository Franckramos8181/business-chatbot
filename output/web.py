import logging
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from ai.assistant import chat
from db.connection import get_session
from db.models import AnalysisSnapshot

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Business Chatbot", version="0.1.0")


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


@app.post("/chat")
async def chat_endpoint(req: ChatRequest):
    session_id = uuid.UUID(req.session_id) if req.session_id else None
    result = chat(req.message, session_id=session_id)
    return JSONResponse(result)


@app.get("/api/snapshot")
async def get_snapshot():
    with get_session() as session:
        snapshot = session.query(AnalysisSnapshot).order_by(
            AnalysisSnapshot.snapshot_date.desc()
        ).first()

        if not snapshot:
            return JSONResponse({"message": "No data available. Run a sync first."})

        return JSONResponse({
            "date": str(snapshot.snapshot_date),
            "total_revenue": float(snapshot.total_revenue or 0),
            "total_expenses": float(snapshot.total_expenses or 0),
            "net_profit": float(snapshot.net_profit or 0),
            "total_liabilities": float(snapshot.total_liabilities or 0),
            "products": snapshot.product_breakdown or [],
            "opportunities": snapshot.insights or [],
        })


@app.get("/", response_class=HTMLResponse)
async def index():
    return DASHBOARD_HTML


DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Business Chatbot</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f5f5f5; color: #333; }
        .container { max-width: 900px; margin: 0 auto; padding: 20px; }
        h1 { margin-bottom: 20px; color: #1a1a2e; }

        .metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 30px; }
        .metric-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        .metric-card .label { font-size: 0.85em; color: #666; margin-bottom: 5px; }
        .metric-card .value { font-size: 1.5em; font-weight: 600; }
        .metric-card .positive { color: #2d6a4f; }
        .metric-card .negative { color: #d32f2f; }

        .chat-container { background: white; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); overflow: hidden; }
        .chat-header { padding: 15px 20px; background: #1a1a2e; color: white; font-weight: 600; }
        .chat-messages { height: 400px; overflow-y: auto; padding: 20px; }
        .message { margin-bottom: 15px; padding: 10px 15px; border-radius: 8px; max-width: 80%; line-height: 1.5; }
        .message.user { background: #e3f2fd; margin-left: auto; }
        .message.assistant { background: #f5f5f5; }
        .chat-input { display: flex; border-top: 1px solid #eee; }
        .chat-input input { flex: 1; padding: 15px 20px; border: none; outline: none; font-size: 1em; }
        .chat-input button { padding: 15px 25px; background: #1a1a2e; color: white; border: none; cursor: pointer; font-size: 1em; }
        .chat-input button:hover { background: #16213e; }
        .chat-input button:disabled { opacity: 0.5; cursor: not-allowed; }

        .examples { margin-top: 20px; padding: 15px; background: white; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        .examples h3 { margin-bottom: 10px; font-size: 0.9em; color: #666; }
        .example-btn { display: inline-block; margin: 3px; padding: 8px 12px; background: #e8eaf6; border: none; border-radius: 20px; cursor: pointer; font-size: 0.85em; }
        .example-btn:hover { background: #c5cae9; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Business Chatbot</h1>

        <div class="metrics" id="metrics"></div>

        <div class="chat-container">
            <div class="chat-header">Ask a business question</div>
            <div class="chat-messages" id="messages">
                <div class="message assistant">Hello! I can help you analyze your business finances. Ask me anything about revenue, expenses, pricing, or forecasts.</div>
            </div>
            <div class="chat-input">
                <input type="text" id="input" placeholder="e.g. What's my net profit this year?" onkeydown="if(event.key==='Enter')sendMessage()">
                <button id="sendBtn" onclick="sendMessage()">Send</button>
            </div>
        </div>

        <div class="examples">
            <h3>Try asking:</h3>
            <button class="example-btn" onclick="askExample(this)">What's my net profit this year?</button>
            <button class="example-btn" onclick="askExample(this)">If I raise tax returns by $5, how much more profit?</button>
            <button class="example-btn" onclick="askExample(this)">Which products can I raise prices on safely?</button>
            <button class="example-btn" onclick="askExample(this)">Show me my top 5 customers by revenue</button>
            <button class="example-btn" onclick="askExample(this)">What does my revenue forecast look like?</button>
            <button class="example-btn" onclick="askExample(this)">How long to pay off my credit card debt at $500/month?</button>
        </div>
    </div>

    <script>
        let sessionId = null;

        async function loadMetrics() {
            try {
                const res = await fetch('/api/snapshot');
                const data = await res.json();
                if (data.message) return;

                document.getElementById('metrics').innerHTML = `
                    <div class="metric-card">
                        <div class="label">Revenue (YTD)</div>
                        <div class="value">$${data.total_revenue.toLocaleString(undefined, {minimumFractionDigits: 2})}</div>
                    </div>
                    <div class="metric-card">
                        <div class="label">Expenses (YTD)</div>
                        <div class="value">$${data.total_expenses.toLocaleString(undefined, {minimumFractionDigits: 2})}</div>
                    </div>
                    <div class="metric-card">
                        <div class="label">Net Profit</div>
                        <div class="value ${data.net_profit >= 0 ? 'positive' : 'negative'}">$${data.net_profit.toLocaleString(undefined, {minimumFractionDigits: 2})}</div>
                    </div>
                    <div class="metric-card">
                        <div class="label">Liabilities</div>
                        <div class="value negative">$${data.total_liabilities.toLocaleString(undefined, {minimumFractionDigits: 2})}</div>
                    </div>
                `;
            } catch (e) {}
        }

        function addMessage(text, role) {
            const div = document.createElement('div');
            div.className = `message ${role}`;
            div.textContent = text;
            const container = document.getElementById('messages');
            container.appendChild(div);
            container.scrollTop = container.scrollHeight;
        }

        async function sendMessage() {
            const input = document.getElementById('input');
            const btn = document.getElementById('sendBtn');
            const msg = input.value.trim();
            if (!msg) return;

            addMessage(msg, 'user');
            input.value = '';
            btn.disabled = true;

            try {
                const res = await fetch('/chat', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ message: msg, session_id: sessionId })
                });
                const data = await res.json();
                sessionId = data.session_id;
                addMessage(data.response, 'assistant');
            } catch (e) {
                addMessage('Error connecting to the server. Please try again.', 'assistant');
            }

            btn.disabled = false;
            input.focus();
        }

        function askExample(btn) {
            document.getElementById('input').value = btn.textContent;
            sendMessage();
        }

        loadMetrics();
    </script>
</body>
</html>"""


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
