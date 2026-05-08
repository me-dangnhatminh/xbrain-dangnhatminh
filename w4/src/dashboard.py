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
    
    <!-- Markdown & Syntax Highlighting -->
    <script src="https://cdn.jsdelivr.net/npm/marked@11.1.1/marked.min.js"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/atom-one-dark.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
    
    <style>
        /* ── CSS Variables ─────────────────────────────── */
        /* ── CSS Variables ─────────────────────────────── */
        :root {
            --bg: #0f1117;
            --surface: #1a1d27;
            --surface2: #22262f;
            --surface3: #2a2e38;
            --border: #2d3240;
            --text: #e4e6eb;
            --muted: #8b8fa3;
            --accent: #6c63ff;
            --accent-hover: #5b54e0;
            --green: #22c55e;
            --orange: #f59e0b;
            --purple: #a855f7;
            --red: #ef4444;
            --blue: #3b82f6;
            --cyan: #06b6d4;
            --yellow: #eab308;
            --transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        html, body {
            height: 100%;
            overflow: hidden;
        }
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
            max-height: calc(100vh - 69px);
            position: relative;
            overflow: hidden;
        }

        /* ── Chat Panel ────────────────────────────── */
        .chat-panel {
            background: var(--surface);
            border-right: 1px solid var(--border);
            display: flex;
            flex-direction: column;
            position: relative;
            height: 100%;
            overflow: hidden;
        }
        .chat-header {
            padding: 16px;
            border-bottom: 1px solid var(--border);
            flex-shrink: 0;
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
            transition: var(--transition);
            position: relative;
        }
        .level-btn:hover:not(.active) { 
            border-color: var(--accent); 
            background: var(--surface3);
            transform: translateY(-1px);
        }
        .level-btn.active { 
            border-color: var(--accent); 
            background: rgba(108, 99, 255, 0.15);
            box-shadow: 0 0 0 3px rgba(108, 99, 255, 0.1);
        }
        .level-btn:focus {
            outline: 2px solid var(--accent);
            outline-offset: 2px;
        }
        .session-info {
            font-size: 0.75em;
            color: var(--muted);
            padding: 8px;
            background: var(--bg);
            border-radius: 6px;
        }

        .chat-messages {
            flex: 1;
            min-height: 0;
            overflow-y: auto;
            overflow-x: hidden;
            padding: 16px;
            scroll-behavior: smooth;
            position: relative;
        }
        .message {
            margin-bottom: 16px;
            animation: fadeIn 0.3s ease-out;
            opacity: 0;
            animation-fill-mode: forwards;
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
            position: relative;
            word-wrap: break-word;
            overflow-wrap: break-word;
        }
        .message.user .msg-bubble {
            background: var(--accent);
            color: white;
            text-align: left;
            border-bottom-right-radius: 4px;
        }
        .message.assistant .msg-bubble {
            background: var(--surface2);
            border: 1px solid var(--border);
            border-bottom-left-radius: 4px;
        }
        .message.assistant.error .msg-bubble {
            background: rgba(239, 68, 68, 0.1);
            border-color: var(--red);
        }
        .message.assistant.loading .msg-bubble {
            background: var(--surface2);
            border: 1px solid var(--border);
            padding: 16px 20px;
        }
        .typing-indicator {
            display: inline-flex;
            gap: 4px;
            align-items: center;
        }
        .typing-indicator span {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: var(--muted);
            animation: typing 1.4s infinite;
        }
        .typing-indicator span:nth-child(2) { animation-delay: 0.2s; }
        .typing-indicator span:nth-child(3) { animation-delay: 0.4s; }
        @keyframes typing {
            0%, 60%, 100% { transform: translateY(0); opacity: 0.7; }
            30% { transform: translateY(-10px); opacity: 1; }
        }
        
        /* ── Markdown Styles ─────────────────────────── */
        .markdown-content {
            line-height: 1.7;
        }
        .markdown-content h1,
        .markdown-content h2,
        .markdown-content h3,
        .markdown-content h4,
        .markdown-content h5,
        .markdown-content h6 {
            margin: 16px 0 8px 0;
            font-weight: 600;
            line-height: 1.3;
        }
        .markdown-content h1 { font-size: 1.6em; border-bottom: 2px solid var(--border); padding-bottom: 8px; }
        .markdown-content h2 { font-size: 1.4em; border-bottom: 1px solid var(--border); padding-bottom: 6px; }
        .markdown-content h3 { font-size: 1.2em; }
        .markdown-content h4 { font-size: 1.1em; }
        .markdown-content h5 { font-size: 1.0em; }
        .markdown-content h6 { font-size: 0.95em; color: var(--muted); }
        
        .markdown-content p {
            margin: 8px 0;
        }
        
        .markdown-content ul,
        .markdown-content ol {
            margin: 8px 0;
            padding-left: 24px;
        }
        .markdown-content li {
            margin: 4px 0;
        }
        .markdown-content li > ul,
        .markdown-content li > ol {
            margin: 4px 0;
        }
        
        .markdown-content code {
            background: var(--bg);
            padding: 2px 6px;
            border-radius: 4px;
            font-family: 'Fira Code', 'Consolas', monospace;
            font-size: 0.9em;
            color: var(--cyan);
        }
        
        .markdown-content pre {
            background: var(--bg);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 16px;
            overflow-x: auto;
            margin: 12px 0;
        }
        .markdown-content pre code {
            background: transparent;
            padding: 0;
            color: inherit;
            font-size: 0.85em;
            line-height: 1.5;
        }
        
        .markdown-content blockquote {
            border-left: 4px solid var(--accent);
            padding-left: 16px;
            margin: 12px 0;
            color: var(--muted);
            font-style: italic;
        }
        
        .markdown-content table {
            border-collapse: collapse;
            width: 100%;
            margin: 12px 0;
            font-size: 0.9em;
        }
        .markdown-content table th,
        .markdown-content table td {
            border: 1px solid var(--border);
            padding: 8px 12px;
            text-align: left;
        }
        .markdown-content table th {
            background: var(--surface2);
            font-weight: 600;
        }
        .markdown-content table tr:hover {
            background: rgba(108, 99, 255, 0.05);
        }
        
        .markdown-content a {
            color: var(--accent);
            text-decoration: none;
            border-bottom: 1px solid transparent;
            transition: border-color 0.2s;
        }
        .markdown-content a:hover {
            border-bottom-color: var(--accent);
        }
        
        .markdown-content hr {
            border: none;
            border-top: 1px solid var(--border);
            margin: 16px 0;
        }
        
        .markdown-content img {
            max-width: 100%;
            border-radius: 8px;
            margin: 12px 0;
        }
        
        .markdown-content strong {
            font-weight: 600;
            color: var(--text);
        }
        
        .markdown-content em {
            font-style: italic;
            color: var(--muted);
        }
        
        /* Code block with language label */
        .code-block-wrapper {
            position: relative;
            margin: 12px 0;
        }
        .code-block-wrapper .language-label {
            position: absolute;
            top: 8px;
            right: 8px;
            background: rgba(108, 99, 255, 0.2);
            color: var(--accent);
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.7em;
            font-weight: 600;
            text-transform: uppercase;
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
        
        /* Adjust markdown in message bubbles */
        .message .msg-bubble .markdown-content h1,
        .message .msg-bubble .markdown-content h2,
        .message .msg-bubble .markdown-content h3 {
            margin-top: 12px;
            margin-bottom: 8px;
        }
        .message .msg-bubble .markdown-content h1:first-child,
        .message .msg-bubble .markdown-content h2:first-child,
        .message .msg-bubble .markdown-content h3:first-child {
            margin-top: 0;
        }
        .message .msg-bubble .markdown-content p:first-child {
            margin-top: 0;
        }
        .message .msg-bubble .markdown-content p:last-child {
            margin-bottom: 0;
        }
        .message .msg-bubble .markdown-content pre {
            margin: 10px 0;
        }
        .message .msg-bubble .markdown-content ul,
        .message .msg-bubble .markdown-content ol {
            margin: 8px 0;
        }

        .chat-input-area {
            padding: 16px;
            border-top: 1px solid var(--border);
            flex-shrink: 0;
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
            transition: var(--transition);
            position: relative;
            overflow: hidden;
        }
        .send-btn:hover:not(:disabled) { 
            background: var(--accent-hover);
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(108, 99, 255, 0.3);
        }
        .send-btn:active:not(:disabled) {
            transform: translateY(0);
        }
        .send-btn:disabled {
            background: var(--surface2);
            color: var(--muted);
            cursor: not-allowed;
            transform: none;
        }
        .send-btn.loading::after {
            content: '';
            position: absolute;
            width: 16px;
            height: 16px;
            top: 50%;
            left: 50%;
            margin-left: -8px;
            margin-top: -8px;
            border: 2px solid transparent;
            border-top-color: white;
            border-radius: 50%;
            animation: spin 0.6s linear infinite;
        }
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        .send-btn.loading span {
            opacity: 0;
        }

        /* ── Observability Panel ─────────────────────────── */
        .obs-panel {
            overflow-y: auto;
            overflow-x: hidden;
            padding: 24px 32px;
            scroll-behavior: smooth;
            position: relative;
            height: 100%;
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
        .event .ev-body pre code {
            background: transparent;
            padding: 0;
        }
        
        /* Markdown in event body */
        .event .ev-body .markdown-content {
            margin-top: 8px;
            font-size: 1em;
        }
        .event .ev-body .markdown-content h1,
        .event .ev-body .markdown-content h2,
        .event .ev-body .markdown-content h3 {
            margin: 12px 0 6px 0;
            font-size: 1.1em;
        }
        .event .ev-body .markdown-content p {
            margin: 6px 0;
        }
        .event .ev-body .markdown-content pre {
            margin: 8px 0;
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
            transition: var(--transition);
        }
        .new-session-btn:hover {
            border-color: var(--accent);
            background: rgba(108, 99, 255, 0.1);
            transform: translateY(-1px);
        }
        .new-session-btn:active {
            transform: translateY(0);
        }
        .new-session-btn:focus {
            outline: 2px solid var(--accent);
            outline-offset: 2px;
        }
        
        /* ── Scrollbar Styling ─────────────────────────── */
        .chat-messages::-webkit-scrollbar,
        .obs-panel::-webkit-scrollbar,
        .history-list::-webkit-scrollbar {
            width: 8px;
        }
        .chat-messages::-webkit-scrollbar-track,
        .obs-panel::-webkit-scrollbar-track,
        .history-list::-webkit-scrollbar-track {
            background: var(--surface);
            border-radius: 4px;
        }
        .chat-messages::-webkit-scrollbar-thumb,
        .obs-panel::-webkit-scrollbar-thumb,
        .history-list::-webkit-scrollbar-thumb {
            background: var(--border);
            border-radius: 4px;
            transition: background 0.2s;
        }
        .chat-messages::-webkit-scrollbar-thumb:hover,
        .obs-panel::-webkit-scrollbar-thumb:hover,
        .history-list::-webkit-scrollbar-thumb:hover {
            background: var(--muted);
        }
        
        /* Firefox scrollbar */
        .chat-messages,
        .obs-panel,
        .history-list {
            scrollbar-width: thin;
            scrollbar-color: var(--border) var(--surface);
        }
        
        /* ── Scroll to Bottom Button ─────────────────────────── */
        .scroll-to-bottom {
            position: fixed;
            background: var(--accent);
            color: white;
            border: none;
            width: 40px;
            height: 40px;
            border-radius: 50%;
            cursor: pointer;
            font-size: 1.2em;
            box-shadow: 0 4px 12px rgba(108, 99, 255, 0.4);
            transition: var(--transition);
            z-index: 50;
            opacity: 0;
            visibility: hidden;
            transform: scale(0.8);
            pointer-events: none;
        }
        .scroll-to-bottom.visible {
            opacity: 1;
            visibility: visible;
            transform: scale(1);
            pointer-events: all;
        }
        .scroll-to-bottom:hover {
            transform: scale(1.1);
            box-shadow: 0 6px 16px rgba(108, 99, 255, 0.5);
        }
        .scroll-to-bottom:active {
            transform: scale(0.95);
        }
        
        /* Position for chat panel scroll button */
        #scroll-to-bottom-chat {
            left: 420px;
            bottom: 90px;
        }
        
        /* Position for observability panel scroll button */
        #scroll-to-bottom-obs {
            right: 40px;
            bottom: 40px;
        }
        
        @media (max-width: 1200px) {
            #scroll-to-bottom-chat {
                left: 340px;
            }
        }
        
        @media (max-width: 900px) {
            #scroll-to-bottom-chat {
                left: auto;
                right: 40px;
                bottom: calc(50vh + 90px);
            }
            #scroll-to-bottom-obs {
                bottom: 40px;
            }
        }
        
        /* ── Copy Button for Code Blocks ─────────────────────────── */
        .code-block-wrapper {
            position: relative;
        }
        .copy-code-btn {
            position: absolute;
            top: 8px;
            right: 8px;
            background: var(--surface2);
            border: 1px solid var(--border);
            color: var(--text);
            padding: 4px 8px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.7em;
            opacity: 0;
            transition: opacity 0.2s, background 0.2s;
        }
        .code-block-wrapper:hover .copy-code-btn {
            opacity: 1;
        }
        .copy-code-btn:hover {
            background: var(--accent);
            border-color: var(--accent);
        }
        .copy-code-btn.copied {
            background: var(--green);
            border-color: var(--green);
        }
        
        /* ── Responsive Design ─────────────────────────── */
        @media (max-width: 1200px) {
            .container {
                grid-template-columns: 400px 1fr;
                max-height: calc(100vh - 69px);
            }
        }
        @media (max-width: 900px) {
            .container {
                grid-template-columns: 1fr;
                grid-template-rows: 50vh 50vh;
                max-height: calc(100vh - 69px);
            }
            .chat-panel {
                border-right: none;
                border-bottom: 1px solid var(--border);
                max-height: 50vh;
            }
            .obs-panel {
                max-height: 50vh;
            }
        }
        
        /* ── Tooltip System ─────────────────────────── */
        .tooltip {
            position: relative;
            display: inline-block;
        }
        .tooltip .tooltiptext {
            visibility: hidden;
            background-color: var(--surface3);
            color: var(--text);
            text-align: center;
            border-radius: 6px;
            padding: 6px 10px;
            position: absolute;
            z-index: 1000;
            bottom: 125%;
            left: 50%;
            transform: translateX(-50%);
            opacity: 0;
            transition: opacity 0.3s;
            font-size: 0.75em;
            white-space: nowrap;
            border: 1px solid var(--border);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        }
        .tooltip .tooltiptext::after {
            content: "";
            position: absolute;
            top: 100%;
            left: 50%;
            margin-left: -5px;
            border-width: 5px;
            border-style: solid;
            border-color: var(--surface3) transparent transparent transparent;
        }
        .tooltip:hover .tooltiptext {
            visibility: visible;
            opacity: 1;
        }
        
        /* ── Toast Notification System ─────────────────────────── */
        .toast-container {
            position: fixed;
            top: 80px;
            right: 20px;
            z-index: 10000;
            display: flex;
            flex-direction: column;
            gap: 10px;
            pointer-events: none;
        }
        .toast {
            background: var(--surface2);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 12px 16px;
            min-width: 250px;
            max-width: 400px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
            display: flex;
            align-items: center;
            gap: 12px;
            animation: slideIn 0.3s ease-out;
            pointer-events: all;
        }
        .toast.success { border-left: 3px solid var(--green); }
        .toast.error { border-left: 3px solid var(--red); }
        .toast.info { border-left: 3px solid var(--blue); }
        .toast.warning { border-left: 3px solid var(--yellow); }
        @keyframes slideIn {
            from { transform: translateX(400px); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        .toast.hiding {
            animation: slideOut 0.3s ease-out forwards;
        }
        @keyframes slideOut {
            to { transform: translateX(400px); opacity: 0; }
        }
        .toast-icon {
            font-size: 1.2em;
            flex-shrink: 0;
        }
        .toast-content {
            flex: 1;
            font-size: 0.85em;
        }
        .toast-close {
            background: none;
            border: none;
            color: var(--muted);
            cursor: pointer;
            font-size: 1.2em;
            padding: 0;
            width: 20px;
            height: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 4px;
            transition: var(--transition);
        }
        .toast-close:hover {
            background: var(--surface);
            color: var(--text);
        }
        
        /* ── Query History Sidebar ─────────────────────────── */
        .history-toggle {
            position: fixed;
            right: 20px;
            bottom: 20px;
            background: var(--accent);
            color: white;
            border: none;
            width: 56px;
            height: 56px;
            border-radius: 50%;
            cursor: pointer;
            font-size: 1.5em;
            box-shadow: 0 4px 12px rgba(108, 99, 255, 0.4);
            transition: var(--transition);
            z-index: 100;
        }
        .history-toggle:hover {
            transform: scale(1.1);
            box-shadow: 0 6px 16px rgba(108, 99, 255, 0.5);
        }
        .history-sidebar {
            position: fixed;
            right: -350px;
            top: 69px;
            bottom: 0;
            width: 350px;
            background: var(--surface);
            border-left: 1px solid var(--border);
            transition: right 0.3s ease-out;
            z-index: 99;
            display: flex;
            flex-direction: column;
        }
        .history-sidebar.open {
            right: 0;
        }
        .history-header {
            padding: 16px;
            border-bottom: 1px solid var(--border);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .history-header h3 {
            font-size: 1em;
            font-weight: 600;
        }
        .history-close {
            background: none;
            border: none;
            color: var(--muted);
            cursor: pointer;
            font-size: 1.2em;
            padding: 4px;
            border-radius: 4px;
            transition: var(--transition);
        }
        .history-close:hover {
            background: var(--surface2);
            color: var(--text);
        }
        .history-list {
            flex: 1;
            overflow-y: auto;
            padding: 8px;
            scroll-behavior: smooth;
        }
        .history-item {
            background: var(--surface2);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 12px;
            margin-bottom: 8px;
            cursor: pointer;
            transition: var(--transition);
        }
        .history-item:hover {
            border-color: var(--accent);
            background: var(--surface3);
            transform: translateX(-4px);
        }
        .history-item-query {
            font-size: 0.85em;
            margin-bottom: 6px;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }
        .history-item-meta {
            font-size: 0.7em;
            color: var(--muted);
            display: flex;
            gap: 8px;
        }
    </style>
</head>
<body>
    <!-- Toast Container -->
    <div class="toast-container" id="toast-container"></div>
    
    <!-- Query History Sidebar -->
    <div class="history-sidebar" id="history-sidebar">
        <div class="history-header">
            <h3>📜 Query History</h3>
            <button class="history-close" onclick="toggleHistory()" aria-label="Close history">×</button>
        </div>
        <div class="history-list" id="history-list">
            <div class="empty-state" style="padding: 40px 20px;">
                <div class="icon" style="font-size: 2em;">📭</div>
                <p style="font-size: 0.85em;">No queries yet</p>
            </div>
        </div>
    </div>
    
    <!-- History Toggle Button -->
    <button class="history-toggle" onclick="toggleHistory()" aria-label="Toggle query history" title="Query History">
        📜
    </button>
    
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
                    <div class="icon">💬</div>
                    <p>Start a conversation by typing a question below.</p>
                </div>
            </div>
            <button class="scroll-to-bottom" id="scroll-to-bottom-chat" onclick="scrollToBottom('chat-messages')" aria-label="Scroll to bottom" title="Scroll to bottom">
                ↓
            </button>
            <div class="chat-input-area">
                <div class="input-wrapper">
                    <textarea 
                        id="chat-input" 
                        class="chat-input" 
                        placeholder="Ask a question about GeekBrain..."
                        rows="2"
                        onkeydown="handleKeyDown(event)"
                    ></textarea>
                    <button class="send-btn" id="send-btn" onclick="sendMessage()" aria-label="Send message">
                        <span>Send</span>
                    </button>
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
        <button class="scroll-to-bottom" id="scroll-to-bottom-obs" onclick="scrollToBottom('obs-panel')" aria-label="Scroll to bottom" title="Scroll to bottom">
            ↓
        </button>
    </div>

    <script>
        const MAIN_API = 'http://localhost:8001';
        const DASHBOARD_API = window.location.origin;
        
        let currentLevel = 'L1';
        let sessionId = generateSessionId();
        let messages = [];
        let queryHistory = [];
        let isProcessing = false;
        let currentQueryId = null;
        let pollInterval = null;

        // ── Toast Notification System ──────────────
        function showToast(message, type = 'info') {
            const container = document.getElementById('toast-container');
            const toast = document.createElement('div');
            toast.className = `toast ${type}`;
            
            const icons = {
                success: '✅',
                error: '❌',
                info: 'ℹ️',
                warning: '⚠️'
            };
            
            toast.innerHTML = `
                <span class="toast-icon">${icons[type] || icons.info}</span>
                <div class="toast-content">${message}</div>
                <button class="toast-close" onclick="this.parentElement.remove()">×</button>
            `;
            
            container.appendChild(toast);
            
            // Auto remove after 5 seconds
            setTimeout(() => {
                toast.classList.add('hiding');
                setTimeout(() => toast.remove(), 300);
            }, 5000);
        }
        
        // ── Query History Management ──────────────
        function toggleHistory() {
            const sidebar = document.getElementById('history-sidebar');
            sidebar.classList.toggle('open');
            if (sidebar.classList.contains('open')) {
                loadQueryHistory();
            }
        }
        
        async function loadQueryHistory() {
            try {
                const res = await fetch(`${DASHBOARD_API}/api/queries`);
                const data = await res.json();
                queryHistory = data.queries || [];
                renderQueryHistory();
            } catch (e) {
                console.error('Failed to load history:', e);
                showToast('Failed to load query history', 'error');
            }
        }
        
        function renderQueryHistory() {
            const list = document.getElementById('history-list');
            
            if (queryHistory.length === 0) {
                list.innerHTML = `
                    <div class="empty-state" style="padding: 40px 20px;">
                        <div class="icon" style="font-size: 2em;">📭</div>
                        <p style="font-size: 0.85em;">No queries yet</p>
                    </div>
                `;
                return;
            }
            
            list.innerHTML = queryHistory.map(q => `
                <div class="history-item" onclick="loadHistoryQuery('${q.query_id}')">
                    <div class="history-item-query">${escapeHtml(q.query || 'Unknown query')}</div>
                    <div class="history-item-meta">
                        <span>${new Date(q.timestamp).toLocaleString()}</span>
                        <span class="level-badge ${q.level}">${q.level}</span>
                    </div>
                </div>
            `).join('');
        }
        
        async function loadHistoryQuery(queryId) {
            try {
                const res = await fetch(`${DASHBOARD_API}/api/query/${queryId}`);
                const data = await res.json();
                
                if (data.events && data.events.length > 0) {
                    currentQueryId = queryId;
                    renderObservability(queryId, data.events);
                    toggleHistory();
                    showToast('Query loaded from history', 'success');
                }
            } catch (e) {
                console.error('Failed to load query:', e);
                showToast('Failed to load query', 'error');
            }
        }

        // ── Markdown Configuration ──────────────
        marked.setOptions({
            highlight: function(code, lang) {
                if (lang && hljs.getLanguage(lang)) {
                    try {
                        return hljs.highlight(code, { language: lang }).value;
                    } catch (e) {
                        console.error('Highlight error:', e);
                    }
                }
                return hljs.highlightAuto(code).value;
            },
            breaks: true,
            gfm: true
        });

        // ── Render Markdown ─────────────────────
        function renderMarkdown(text) {
            if (!text) return '';
            try {
                const html = marked.parse(text);
                return `<div class="markdown-content">${html}</div>`;
            } catch (e) {
                console.error('Markdown parse error:', e);
                return escapeHtml(text);
            }
        }
        
        // ── Add Copy Buttons to Code Blocks ────
        function addCopyButtons(container) {
            container.querySelectorAll('pre code').forEach((codeBlock) => {
                const pre = codeBlock.parentElement;
                if (pre.querySelector('.copy-code-btn')) return; // Already has button
                
                const wrapper = document.createElement('div');
                wrapper.className = 'code-block-wrapper';
                pre.parentNode.insertBefore(wrapper, pre);
                wrapper.appendChild(pre);
                
                const button = document.createElement('button');
                button.className = 'copy-code-btn';
                button.textContent = 'Copy';
                button.setAttribute('aria-label', 'Copy code to clipboard');
                button.onclick = () => {
                    navigator.clipboard.writeText(codeBlock.textContent).then(() => {
                        button.textContent = 'Copied!';
                        button.classList.add('copied');
                        showToast('Code copied to clipboard', 'success');
                        setTimeout(() => {
                            button.textContent = 'Copy';
                            button.classList.remove('copied');
                        }, 2000);
                    }).catch(err => {
                        console.error('Copy failed:', err);
                        showToast('Failed to copy code', 'error');
                    });
                };
                wrapper.appendChild(button);
            });
        }

        // ── Initialize ──────────────────────────
        function init() {
            document.getElementById('session-id').textContent = sessionId;
            document.getElementById('chat-input').focus();
            
            // Load initial query history
            loadQueryHistory();
            
            // Setup scroll listeners
            setupScrollListeners();
            
            // Add keyboard shortcuts
            document.addEventListener('keydown', (e) => {
                // Ctrl/Cmd + K to focus input
                if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                    e.preventDefault();
                    document.getElementById('chat-input').focus();
                }
                // Ctrl/Cmd + H to toggle history
                if ((e.ctrlKey || e.metaKey) && e.key === 'h') {
                    e.preventDefault();
                    toggleHistory();
                }
                // Escape to close history
                if (e.key === 'Escape') {
                    const sidebar = document.getElementById('history-sidebar');
                    if (sidebar.classList.contains('open')) {
                        toggleHistory();
                    }
                }
            });
        }
        
        // ── Scroll Management ──────────────────────────
        function setupScrollListeners() {
            const chatMessages = document.getElementById('chat-messages');
            const obsPanel = document.getElementById('obs-panel');
            
            // Remove old listeners if any
            chatMessages.removeEventListener('scroll', handleChatScroll);
            obsPanel.removeEventListener('scroll', handleObsScroll);
            
            // Add new listeners
            chatMessages.addEventListener('scroll', handleChatScroll);
            obsPanel.addEventListener('scroll', handleObsScroll);
        }
        
        function handleChatScroll() {
            updateScrollButtonVisibility('chat-messages', 'scroll-to-bottom-chat');
        }
        
        function handleObsScroll() {
            updateScrollButtonVisibility('obs-panel', 'scroll-to-bottom-obs');
        }
        
        function updateScrollButtonVisibility(containerId, buttonId) {
            const container = document.getElementById(containerId);
            const button = document.getElementById(buttonId);
            
            if (!container || !button) return;
            
            const isNearBottom = container.scrollHeight - container.scrollTop - container.clientHeight < 100;
            const hasScroll = container.scrollHeight > container.clientHeight;
            
            if (hasScroll && !isNearBottom) {
                button.classList.add('visible');
            } else {
                button.classList.remove('visible');
            }
        }
        
        function scrollToBottom(elementId, smooth = true) {
            const element = document.getElementById(elementId);
            if (element) {
                if (smooth) {
                    element.scrollTo({
                        top: element.scrollHeight,
                        behavior: 'smooth'
                    });
                } else {
                    element.scrollTop = element.scrollHeight;
                }
            }
        }
        
        function isScrolledToBottom(element) {
            if (!element) return true;
            return element.scrollHeight - element.scrollTop - element.clientHeight < 50;
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
            if (messages.length > 0 && !confirm('Start a new session? Current conversation will be cleared.')) {
                return;
            }
            sessionId = generateSessionId();
            document.getElementById('session-id').textContent = sessionId;
            messages = [];
            renderMessages();
            clearObservability();
            showToast('New session started', 'info');
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
            const sendBtn = document.getElementById('send-btn');
            const query = input.value.trim();
            
            if (!query || isProcessing) return;
            
            // Add user message
            messages.push({ role: 'user', content: query, timestamp: Date.now() });
            input.value = '';
            renderMessages();
            
            // Disable input and show loading state
            isProcessing = true;
            sendBtn.disabled = true;
            sendBtn.classList.add('loading');
            input.disabled = true;
            
            // Add loading message
            const loadingMsgIndex = messages.length;
            messages.push({ 
                role: 'assistant', 
                content: '', 
                loading: true,
                timestamp: Date.now()
            });
            renderMessages();
            
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
                    throw new Error(`API error: ${response.status} ${response.statusText}`);
                }
                
                const data = await response.json();
                
                // Remove loading message and add real response
                messages.splice(loadingMsgIndex, 1);
                messages.push({
                    role: 'assistant',
                    content: data.answer,
                    sources: data.sources,
                    tools_used: data.tools_used,
                    processing_time: data.processing_time,
                    timestamp: Date.now()
                });
                
                renderMessages();
                
                // Load observability for this query
                await loadLatestQueryObservability();
                
                // Reload history
                loadQueryHistory();
                
                showToast('Response received successfully', 'success');
                
            } catch (error) {
                console.error('Error sending message:', error);
                
                // Remove loading message and add error
                messages.splice(loadingMsgIndex, 1);
                messages.push({
                    role: 'assistant',
                    content: `Failed to get response: ${error.message}`,
                    error: true,
                    timestamp: Date.now()
                });
                renderMessages();
                
                showToast(`Error: ${error.message}`, 'error');
            } finally {
                isProcessing = false;
                sendBtn.disabled = false;
                sendBtn.classList.remove('loading');
                input.disabled = false;
                input.focus();
            }
        }

        function renderMessages() {
            const container = document.getElementById('chat-messages');
            const wasAtBottom = isScrolledToBottom(container);
            
            if (messages.length === 0) {
                container.innerHTML = `
                    <div class="empty-state" style="padding:60px 20px;">
                        <div class="icon">💬</div>
                        <p>Start a conversation by typing a question below.</p>
                        <p style="font-size: 0.8em; margin-top: 8px; color: var(--muted);">
                            Tip: Press <kbd style="background: var(--surface2); padding: 2px 6px; border-radius: 4px;">Ctrl+K</kbd> to focus input
                        </p>
                    </div>
                `;
                return;
            }
            
            container.innerHTML = messages.map((msg, index) => {
                if (msg.role === 'user') {
                    return `
                        <div class="message user" style="animation-delay: ${index * 0.05}s">
                            <div class="msg-bubble">${escapeHtml(msg.content)}</div>
                        </div>
                    `;
                } else if (msg.loading) {
                    return `
                        <div class="message assistant loading" style="animation-delay: ${index * 0.05}s">
                            <div class="msg-bubble">
                                <div class="typing-indicator">
                                    <span></span>
                                    <span></span>
                                    <span></span>
                                </div>
                            </div>
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
                    
                    const errorClass = msg.error ? ' error' : '';
                    
                    return `
                        <div class="message assistant${errorClass}" style="animation-delay: ${index * 0.05}s">
                            <div class="msg-bubble">
                                ${msg.error ? escapeHtml(msg.content) : renderMarkdown(msg.content)}
                                ${msg.error || meta.length === 0 ? '' : `
                                    <div class="msg-meta">
                                        ${meta.join(' • ')}
                                    </div>
                                `}
                            </div>
                        </div>
                    `;
                }
            }).join('');
            
            // Apply syntax highlighting to code blocks
            container.querySelectorAll('pre code').forEach((block) => {
                hljs.highlightElement(block);
            });
            
            // Add copy buttons to code blocks
            addCopyButtons(container);
            
            // Scroll to bottom only if user was already at bottom or if it's a new message
            if (wasAtBottom || messages[messages.length - 1]?.role === 'assistant') {
                requestAnimationFrame(() => {
                    scrollToBottom('chat-messages', true);
                });
            }
            
            // Update scroll button visibility
            updateScrollButtonVisibility('chat-messages', 'scroll-to-bottom-chat');
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
            const wasAtBottom = isScrolledToBottom(panel);
            
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
            
            // Apply syntax highlighting to code blocks in observability panel
            panel.querySelectorAll('pre code').forEach((block) => {
                hljs.highlightElement(block);
            });
            
            // Add copy buttons to code blocks
            addCopyButtons(panel);
            
            // Auto-scroll to bottom only if user was already at bottom
            if (wasAtBottom) {
                requestAnimationFrame(() => {
                    scrollToBottom('obs-panel', true);
                });
            }
            
            // Update scroll button visibility
            updateScrollButtonVisibility('obs-panel', 'scroll-to-bottom-obs');
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
                            <pre><code class="language-json">${escapeHtml(JSON.stringify(d.parameters, null, 2))}</code></pre>
                            <strong>${d.success ? '✅' : '❌'} Result:</strong>
                            <div style="margin-top: 8px;">${renderMarkdown(d.result)}</div>`;

                case 'llm_invoked':
                    return `<strong>Model:</strong> ${escapeHtml(d.model_id || 'Claude')}<br>
                            <strong>Prompt length:</strong> ${d.prompt_length} chars<br>
                            ${d.response_preview ? '<strong>Preview:</strong><div style="margin-top: 8px;">' + renderMarkdown(d.response_preview) + '</div>' : ''}`;

                case 'memory_loaded':
                    return `<strong>Session:</strong> ${escapeHtml(d.session_id)}<br>
                            <strong>History turns loaded:</strong> ${d.num_turns}`;

                case 'response_generated':
                    return `<strong>Final Answer:</strong><div style="margin-top: 8px;">${renderMarkdown(d.response)}</div><br>
                            <span class="proc-time">⏱ ${d.processing_time_ms.toFixed(0)}ms</span>
                            ${d.tools_used.length > 0 ? '<br><strong>Tools:</strong> ' + d.tools_used.map(t => '<span class="tool-badge">' + t + '</span>').join(' ') : ''}`;

                default:
                    return `<pre><code class="language-json">${escapeHtml(JSON.stringify(d, null, 2))}</code></pre>`;
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
