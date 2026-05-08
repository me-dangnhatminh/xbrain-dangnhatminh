"""
Observability Dashboard for GeekBrain AI System (Bonus A).

Runs on port 8002. Provides:
- GET /                 → Dashboard web UI
- GET /api/queries      → List all processed queries
- GET /api/query/{id}   → Get detailed events for a query
- WS  /ws               → WebSocket for real-time event streaming

Usage:
    cd w4/src
    python dashboard.py
    # Open http://localhost:8002 in browser
"""

import os
import sys
import asyncio
import json
from pathlib import Path

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from event_logger import event_logger

app = FastAPI(title="GeekBrain AI — Observability Dashboard")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── REST API Endpoints ─────────────────────────────────────────────


@app.get("/api/queries")
async def list_queries():
    """List all processed queries (most recent first)."""
    query_ids = event_logger.get_all_query_ids()
    summaries = []
    for qid in query_ids[:50]:
        summary = event_logger.get_query_summary(qid)
        if summary:
            summaries.append(summary)
    return {"queries": summaries}


@app.get("/api/query/{query_id}")
async def get_query_details(query_id: str):
    """Get all events for a specific query."""
    events = event_logger.get_events(query_id)
    return {
        "query_id": query_id,
        "events": [e.to_dict() for e in events],
    }


# ── WebSocket for real-time streaming ──────────────────────────────


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Stream events for a query_id in real-time."""
    await websocket.accept()
    try:
        data = await websocket.receive_text()
        msg = json.loads(data)
        query_id = msg.get("query_id", "")

        if not query_id:
            await websocket.send_json({"error": "query_id required"})
            await websocket.close()
            return

        # Poll and stream events until response_generated
        last_count = 0
        max_polls = 60  # max 30 seconds
        for _ in range(max_polls):
            events = event_logger.get_events(query_id)
            if len(events) > last_count:
                await websocket.send_json({
                    "query_id": query_id,
                    "events": [e.to_dict() for e in events],
                })
                last_count = len(events)

                # Check if done
                if events[-1].event_type == "response_generated":
                    break

            await asyncio.sleep(0.5)

    except WebSocketDisconnect:
        pass
    except Exception:
        pass


# ── Dashboard HTML ─────────────────────────────────────────────────


DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GeekBrain AI — Chat & Observability</title>
    <style>
        :root {
            --bg: #0f1117;
            --surface: #1a1d27;
            --surface2: #22262f;
            --border: #2d3240;
            --text: #e4e6eb;
            --muted: #8b8fa3;
            --accent: #6c63ff;
            --green: #22c55e;
            --orange: #f59e0b;
            --purple: #a855f7;
            --red: #ef4444;
            --blue: #3b82f6;
            --cyan: #06b6d4;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.6;
        }

        /* ── Header ─────────────────────────────── */
        header {
            background: linear-gradient(135deg, #1a1d27 0%, #0f1117 100%);
            border-bottom: 1px solid var(--border);
            padding: 20px 32px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        header .left {
            display: flex;
            align-items: center;
            gap: 16px;
        }
        header h1 {
            font-size: 1.3em;
            font-weight: 600;
            background: linear-gradient(135deg, var(--accent), var(--cyan));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        header .badge {
            background: var(--surface2);
            border: 1px solid var(--border);
            padding: 4px 12px;
            border-radius: 999px;
            font-size: 0.75em;
            color: var(--muted);
        }
        .status-dot {
            display: inline-block;
            width: 8px; height: 8px;
            border-radius: 50%;
            background: var(--green);
            margin-right: 6px;
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.4; }
        }

        /* ── Layout ─────────────────────────────── */
        .container {
            display: grid;
            grid-template-columns: 480px 1fr;
            height: calc(100vh - 69px);
        }

        /* ── Chat Panel ────────────────────────────── */
        .chat-panel {
            background: var(--surface);
            border-right: 1px solid var(--border);
            display: flex;
            flex-direction: column;
        }
        .chat-header {
            padding: 16px;
            border-bottom: 1px solid var(--border);
        }
        .chat-header h2 {
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: var(--muted);
            margin-bottom: 12px;
        }
        .level-selector {
            display: flex;
            gap: 8px;
            margin-bottom: 12px;
        }
        .level-btn {
            flex: 1;
            padding: 8px;
            border: 1px solid var(--border);
            background: var(--surface2);
            color: var(--text);
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.8em;
            font-weight: 600;
            transition: all 0.2s;
        }
        .level-btn:hover { border-color: var(--accent); }
        .level-btn.active { border-color: var(--accent); background: rgba(108, 99, 255, 0.15); }
        .session-info {
            font-size: 0.75em;
            color: var(--muted);
            padding: 8px;
            background: var(--bg);
            border-radius: 6px;
        }

        .chat-messages {
            flex: 1;
            overflow-y: auto;
            padding: 16px;
        }
        .message {
            margin-bottom: 16px;
            animation: fadeIn 0.3s ease-out;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(8px); }
            to   { opacity: 1; transform: translateY(0); }
        }
        .message.user {
            text-align: right;
        }
        .message .msg-bubble {
            display: inline-block;
            max-width: 85%;
            padding: 12px 16px;
            border-radius: 12px;
            font-size: 0.9em;
        }
        .message.user .msg-bubble {
            background: var(--accent);
            color: white;
            text-align: left;
        }
        .message.assistant .msg-bubble {
            background: var(--surface2);
            border: 1px solid var(--border);
        }
        .message .msg-meta {
            font-size: 0.7em;
            color: var(--muted);
            margin-top: 4px;
        }
        .message.assistant .msg-meta {
            display: flex;
            gap: 8px;
            align-items: center;
        }

        .chat-input-area {
            padding: 16px;
            border-top: 1px solid var(--border);
        }
        .input-wrapper {
            display: flex;
            gap: 8px;
        }
        .chat-input {
            flex: 1;
            background: var(--surface2);
            border: 1px solid var(--border);
            color: var(--text);
            padding: 12px;
            border-radius: 8px;
            font-size: 0.9em;
            font-family: inherit;
            resize: none;
        }
        .chat-input:focus {
            outline: none;
            border-color: var(--accent);
        }
        .send-btn {
            background: var(--accent);
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 600;
            transition: background 0.2s;
        }
        .send-btn:hover { background: #5b54e0; }
        .send-btn:disabled {
            background: var(--surface2);
            color: var(--muted);
            cursor: not-allowed;
        }

        /* ── Observability Panel ─────────────────────────── */
        .obs-panel {
            overflow-y: auto;
            padding: 24px 32px;
        }
        .obs-panel h2 { font-size: 1.1em; margin-bottom: 20px; }
        .empty-state {
            text-align: center;
            padding: 80px 20px;
            color: var(--muted);
        }
        .empty-state .icon { font-size: 3em; margin-bottom: 12px; }

        /* ── Event Timeline ─────────────────────── */
        .timeline { position: relative; padding-left: 32px; }
        .timeline::before {
            content: '';
            position: absolute;
            left: 11px;
            top: 0;
            bottom: 0;
            width: 2px;
            background: var(--border);
        }
        .event {
            position: relative;
            margin-bottom: 16px;
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 16px;
            transition: all 0.3s;
            animation: fadeIn 0.4s ease-out;
        }
        .event::before {
            content: '';
            position: absolute;
            left: -27px;
            top: 20px;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            border: 2px solid var(--border);
            background: var(--bg);
        }

        /* Event type colors */
        .event.query_received    { border-left: 3px solid var(--blue); }
        .event.query_received::before    { border-color: var(--blue); background: var(--blue); }
        .event.retrieval_completed { border-left: 3px solid var(--green); }
        .event.retrieval_completed::before { border-color: var(--green); background: var(--green); }
        .event.tool_executed     { border-left: 3px solid var(--orange); }
        .event.tool_executed::before     { border-color: var(--orange); background: var(--orange); }
        .event.llm_invoked       { border-left: 3px solid var(--purple); }
        .event.llm_invoked::before       { border-color: var(--purple); background: var(--purple); }
        .event.memory_loaded     { border-left: 3px solid var(--cyan); }
        .event.memory_loaded::before     { border-color: var(--cyan); background: var(--cyan); }
        .event.response_generated { border-left: 3px solid var(--red); }
        .event.response_generated::before { border-color: var(--red); background: var(--red); }

        .event .ev-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }
        .event .ev-type {
            font-weight: 600;
            font-size: 0.85em;
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }
        .event .ev-time { font-size: 0.7em; color: var(--muted); }
        .event .ev-body { font-size: 0.85em; }
        .event .ev-body pre {
            background: var(--bg);
            padding: 10px;
            border-radius: 6px;
            overflow-x: auto;
            font-size: 0.9em;
            margin-top: 6px;
            color: var(--cyan);
        }

        .chunk-card {
            background: var(--bg);
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 10px;
            margin: 6px 0;
            font-size: 0.82em;
        }
        .chunk-card .source { color: var(--green); font-weight: 600; }
        .chunk-card .score { color: var(--muted); float: right; }

        .tool-badge {
            display: inline-block;
            background: rgba(245,158,11,0.15);
            color: var(--orange);
            padding: 2px 8px;
            border-radius: 4px;
            font-weight: 600;
            font-size: 0.85em;
        }
        .level-badge {
            padding: 2px 6px;
            border-radius: 4px;
            font-weight: 600;
            font-size: 0.85em;
        }
        .level-badge.L1 { background: rgba(34,197,94,0.15); color: var(--green); }
        .level-badge.L2 { background: rgba(59,130,246,0.15); color: var(--blue); }
        .level-badge.L3 { background: rgba(245,158,11,0.15); color: var(--orange); }
        .level-badge.L4 { background: rgba(168,85,247,0.15); color: var(--purple); }
        .proc-time {
            display: inline-block;
            background: rgba(239,68,68,0.12);
            color: var(--red);
            padding: 4px 12px;
            border-radius: 6px;
            font-weight: 700;
            font-size: 1.1em;
        }

        .new-session-btn {
            background: var(--surface2);
            border: 1px solid var(--border);
            color: var(--text);
            padding: 6px 12px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.75em;
            transition: all 0.2s;
        }
        .new-session-btn:hover {
            border-color: var(--accent);
            background: rgba(108, 99, 255, 0.1);
        }
    </style>
</head>
<body>
    <header>
        <div class="left">
            <h1>🧠 GeekBrain AI — Chat & Observability</h1>
            <span class="badge"><span class="status-dot"></span>Live</span>
        </div>
    </header>

    <div class="container">
        <!-- Chat Panel -->
        <div class="chat-panel">
            <div class="chat-header">
                <h2>💬 Chat Interface</h2>
                <div class="level-selector">
                    <button class="level-btn active" data-level="L1" onclick="selectLevel('L1')">L1</button>
                    <button class="level-btn" data-level="L2" onclick="selectLevel('L2')">L2</button>
                    <button class="level-btn" data-level="L3" onclick="selectLevel('L3')">L3</button>
                    <button class="level-btn" data-level="L4" onclick="selectLevel('L4')">L4</button>
                </div>
                <div class="session-info">
                    <span id="session-display">Session: <strong id="session-id">-</strong></span>
                    <button class="new-session-btn" onclick="newSession()">🔄 New Session</button>
                </div>
            </div>
            <div class="chat-messages" id="chat-messages">
                <div class="empty-state" style="padding:60px 20px;">
                    <div class="icon">�</div>
                    <p>Start a conversation by typing a question below.</p>
                </div>
            </div>
            <div class="chat-input-area">
                <div class="input-wrapper">
                    <textarea 
                        id="chat-input" 
                        class="chat-input" 
                        placeholder="Ask a question about GeekBrain..."
                        rows="2"
                        onkeydown="handleKeyDown(event)"
                    ></textarea>
                    <button class="send-btn" id="send-btn" onclick="sendMessage()">Send</button>
                </div>
            </div>
        </div>

        <!-- Observability Panel -->
        <div class="obs-panel" id="obs-panel">
            <div class="empty-state">
                <div class="icon">🔍</div>
                <p>Send a query to see the processing pipeline in real-time.</p>
            </div>
        </div>
    </div>

    <script>
        const MAIN_API = 'http://localhost:8001';
        const DASHBOARD_API = window.location.origin;
        
        let currentLevel = 'L1';
        let sessionId = generateSessionId();
        let messages = [];
        let isProcessing = false;
        let currentQueryId = null;
        let pollInterval = null;

        // ── Initialize ──────────────────────────
        function init() {
            document.getElementById('session-id').textContent = sessionId;
            document.getElementById('chat-input').focus();
        }

        // ── Level Selection ─────────────────────
        function selectLevel(level) {
            currentLevel = level;
            document.querySelectorAll('.level-btn').forEach(btn => {
                btn.classList.toggle('active', btn.dataset.level === level);
            });
            
            // Show/hide session info based on L4
            const sessionInfo = document.querySelector('.session-info');
            sessionInfo.style.display = level === 'L4' ? 'block' : 'none';
        }

        // ── Session Management ──────────────────
        function generateSessionId() {
            return 'session-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
        }

        function newSession() {
            sessionId = generateSessionId();
            document.getElementById('session-id').textContent = sessionId;
            messages = [];
            renderMessages();
            clearObservability();
        }

        // ── Message Handling ────────────────────
        function handleKeyDown(event) {
            if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                sendMessage();
            }
        }

        async function sendMessage() {
            const input = document.getElementById('chat-input');
            const query = input.value.trim();
            
            if (!query || isProcessing) return;
            
            // Add user message
            messages.push({ role: 'user', content: query });
            input.value = '';
            renderMessages();
            
            // Disable input
            isProcessing = true;
            document.getElementById('send-btn').disabled = true;
            document.getElementById('chat-input').disabled = true;
            
            // Show loading in observability
            showLoadingObservability();
            
            try {
                // Send to API
                const payload = {
                    query: query,
                    level: currentLevel
                };
                
                if (currentLevel === 'L4') {
                    payload.session_id = sessionId;
                }
                
                const response = await fetch(`${MAIN_API}/query`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                
                if (!response.ok) {
                    throw new Error(`API error: ${response.status}`);
                }
                
                const data = await response.json();
                
                // Add assistant message
                messages.push({
                    role: 'assistant',
                    content: data.answer,
                    sources: data.sources,
                    tools_used: data.tools_used,
                    processing_time: data.processing_time
                });
                
                renderMessages();
                
                // Load observability for this query
                await loadLatestQueryObservability();
                
            } catch (error) {
                console.error('Error sending message:', error);
                messages.push({
                    role: 'assistant',
                    content: '❌ Error: ' + error.message,
                    error: true
                });
                renderMessages();
            } finally {
                isProcessing = false;
                document.getElementById('send-btn').disabled = false;
                document.getElementById('chat-input').disabled = false;
                document.getElementById('chat-input').focus();
            }
        }

        function renderMessages() {
            const container = document.getElementById('chat-messages');
            
            if (messages.length === 0) {
                container.innerHTML = `
                    <div class="empty-state" style="padding:60px 20px;">
                        <div class="icon">💬</div>
                        <p>Start a conversation by typing a question below.</p>
                    </div>
                `;
                return;
            }
            
            container.innerHTML = messages.map(msg => {
                if (msg.role === 'user') {
                    return `
                        <div class="message user">
                            <div class="msg-bubble">${escapeHtml(msg.content)}</div>
                        </div>
                    `;
                } else {
                    const meta = [];
                    if (msg.processing_time) {
                        meta.push(`⏱ ${(msg.processing_time * 1000).toFixed(0)}ms`);
                    }
                    if (msg.tools_used && msg.tools_used.length > 0) {
                        meta.push(`🔧 ${msg.tools_used.join(', ')}`);
                    }
                    if (msg.sources && msg.sources.length > 0) {
                        meta.push(`📄 ${msg.sources.length} sources`);
                    }
                    
                    return `
                        <div class="message assistant">
                            <div class="msg-bubble">
                                ${escapeHtml(msg.content)}
                                ${msg.error ? '' : `
                                    <div class="msg-meta">
                                        ${meta.join(' • ')}
                                    </div>
                                `}
                            </div>
                        </div>
                    `;
                }
            }).join('');
            
            // Scroll to bottom
            container.scrollTop = container.scrollHeight;
        }

        // ── Observability ───────────────────────
        function showLoadingObservability() {
            const panel = document.getElementById('obs-panel');
            panel.innerHTML = `
                <h2>🔄 Processing Query...</h2>
                <div class="empty-state">
                    <div class="icon">⏳</div>
                    <p>Waiting for events...</p>
                </div>
            `;
        }

        function clearObservability() {
            const panel = document.getElementById('obs-panel');
            panel.innerHTML = `
                <div class="empty-state">
                    <div class="icon">🔍</div>
                    <p>Send a query to see the processing pipeline in real-time.</p>
                </div>
            `;
        }

        async function loadLatestQueryObservability() {
            try {
                // Get latest query
                const res = await fetch(`${DASHBOARD_API}/api/queries`);
                const data = await res.json();
                
                if (data.queries && data.queries.length > 0) {
                    const latestQuery = data.queries[0];
                    currentQueryId = latestQuery.query_id;
                    
                    // Start polling for events
                    await pollQueryEvents(currentQueryId);
                }
            } catch (e) {
                console.error('Failed to load observability:', e);
            }
        }

        async function pollQueryEvents(queryId) {
            let attempts = 0;
            const maxAttempts = 20;
            
            const poll = async () => {
                try {
                    const res = await fetch(`${DASHBOARD_API}/api/query/${queryId}`);
                    const data = await res.json();
                    
                    renderObservability(data.query_id, data.events);
                    
                    // Check if done
                    const lastEvent = data.events[data.events.length - 1];
                    if (lastEvent && lastEvent.event_type === 'response_generated') {
                        if (pollInterval) {
                            clearInterval(pollInterval);
                            pollInterval = null;
                        }
                        return;
                    }
                    
                    attempts++;
                    if (attempts >= maxAttempts) {
                        if (pollInterval) {
                            clearInterval(pollInterval);
                            pollInterval = null;
                        }
                    }
                } catch (e) {
                    console.error('Polling error:', e);
                }
            };
            
            // Initial load
            await poll();
            
            // Poll every 500ms
            if (pollInterval) clearInterval(pollInterval);
            pollInterval = setInterval(poll, 500);
        }

        function renderObservability(queryId, events) {
            const panel = document.getElementById('obs-panel');
            
            if (!events || events.length === 0) {
                panel.innerHTML = `
                    <h2>Pipeline: ${queryId}</h2>
                    <div class="empty-state">
                        <div class="icon">⏳</div>
                        <p>No events yet...</p>
                    </div>
                `;
                return;
            }
            
            let html = `<h2>🔍 Pipeline: ${queryId}</h2>`;
            html += '<div class="timeline">';
            
            events.forEach(e => {
                html += `<div class="event ${e.event_type}">`;
                html += `<div class="ev-header">
                    <span class="ev-type">${formatType(e.event_type)}</span>
                    <span class="ev-time">${new Date(e.timestamp).toLocaleTimeString()}</span>
                </div>`;
                html += `<div class="ev-body">${renderEventBody(e)}</div>`;
                html += '</div>';
            });
            
            html += '</div>';
            panel.innerHTML = html;
            
            // Auto-scroll to bottom
            panel.scrollTop = panel.scrollHeight;
        }

        function renderEventBody(e) {
            const d = e.data;
            switch (e.event_type) {
                case 'query_received':
                    return `<strong>Query:</strong> "${escapeHtml(d.query)}"<br>
                            <strong>Level:</strong> <span class="level-badge ${d.level}">${d.level}</span>
                            ${d.session_id ? '<br><strong>Session:</strong> ' + d.session_id : ''}`;

                case 'retrieval_completed':
                    let chunks = `<strong>Retrieved ${d.num_chunks} chunks:</strong>`;
                    (d.chunks || []).forEach(c => {
                        chunks += `<div class="chunk-card">
                            <span class="source">📄 ${escapeHtml(c.source)}</span>
                            <span class="score">score: ${c.score}</span>
                            <br>${escapeHtml(c.text)}
                        </div>`;
                    });
                    return chunks;

                case 'tool_executed':
                    return `<span class="tool-badge">🔧 ${escapeHtml(d.tool_name)}</span>
                            <pre>${escapeHtml(JSON.stringify(d.parameters, null, 2))}</pre>
                            <strong>${d.success ? '✅' : '❌'} Result:</strong>
                            <pre>${escapeHtml(d.result)}</pre>`;

                case 'llm_invoked':
                    return `<strong>Model:</strong> ${escapeHtml(d.model_id || 'Claude')}<br>
                            <strong>Prompt length:</strong> ${d.prompt_length} chars<br>
                            ${d.response_preview ? '<strong>Preview:</strong> ' + escapeHtml(d.response_preview) : ''}`;

                case 'memory_loaded':
                    return `<strong>Session:</strong> ${escapeHtml(d.session_id)}<br>
                            <strong>History turns loaded:</strong> ${d.num_turns}`;

                case 'response_generated':
                    return `<strong>Final Answer:</strong><br>${escapeHtml(d.response)}<br><br>
                            <span class="proc-time">⏱ ${d.processing_time_ms.toFixed(0)}ms</span>
                            ${d.tools_used.length > 0 ? '<br><strong>Tools:</strong> ' + d.tools_used.map(t => '<span class="tool-badge">' + t + '</span>').join(' ') : ''}`;

                default:
                    return `<pre>${escapeHtml(JSON.stringify(d, null, 2))}</pre>`;
            }
        }

        function formatType(t) {
            const icons = {
                query_received: '📥 Query Received',
                retrieval_completed: '📚 Retrieval Completed',
                tool_executed: '🔧 Tool Executed',
                llm_invoked: '🧠 LLM Invoked',
                memory_loaded: '💾 Memory Loaded',
                response_generated: '✅ Response Generated'
            };
            return icons[t] || t;
        }

        function escapeHtml(str) {
            if (!str) return '';
            return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
        }

        // ── Start ───────────────────────────────
        init();
    </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    """Serve the observability dashboard UI."""
    return DASHBOARD_HTML


if __name__ == "__main__":
    port = int(os.getenv("DASHBOARD_PORT", "8002"))
    print(f"🔍 Observability Dashboard starting on http://localhost:{port}")
    print(f"   Main API events source: event_logger singleton")
    uvicorn.run(app, host="0.0.0.0", port=port)
