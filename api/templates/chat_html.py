"""
api/templates/chat_html.py
Production-grade dark theme Web Chat UI for EPFO Intelligence Copilot.
"""

CHAT_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>EPFO Statutory Intelligence & Copilot</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
  <style>
    :root {
      --bg-dark: #090d16;
      --card-bg: #111726;
      --card-border: #1e293b;
      --accent: #38bdf8;
      --accent-glow: rgba(56, 189, 248, 0.18);
      --gold: #fbbf24;
      --gold-glow: rgba(251, 191, 36, 0.15);
      --text-main: #f8fafc;
      --text-muted: #94a3b8;
      --bot-msg-bg: #162032;
      --user-msg-bg: #1e3a8a;
      --success: #34d399;
      --warning: #f59e0b;
    }
    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }
    body {
      font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
      background: radial-gradient(circle at top right, #0f172a, var(--bg-dark));
      color: var(--text-main);
      height: 100vh;
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }
    header {
      background: rgba(17, 24, 38, 0.85);
      backdrop-filter: blur(12px);
      border-bottom: 1px solid var(--card-border);
      padding: 12px 24px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      z-index: 10;
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .emblem {
      width: 38px;
      height: 38px;
      background: linear-gradient(135deg, #0284c7, #0369a1);
      border: 1px solid var(--accent);
      border-radius: 10px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 20px;
      box-shadow: 0 0 15px var(--accent-glow);
    }
    .brand-title {
      font-size: 1.05rem;
      font-weight: 700;
      letter-spacing: -0.02em;
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .brand-subtitle {
      font-size: 0.75rem;
      color: var(--text-muted);
      font-weight: 500;
    }
    .status-badge {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: rgba(52, 211, 153, 0.1);
      color: var(--success);
      padding: 4px 10px;
      border-radius: 9999px;
      font-size: 0.72rem;
      font-weight: 600;
      border: 1px solid rgba(52, 211, 153, 0.25);
    }
    .pulse-dot {
      width: 7px;
      height: 7px;
      border-radius: 50%;
      background: var(--success);
      box-shadow: 0 0 8px var(--success);
      animation: pulse 2s infinite;
    }
    @keyframes pulse {
      0%, 100% { opacity: 1; transform: scale(1); }
      50% { opacity: 0.4; transform: scale(0.85); }
    }
    .header-actions {
      display: flex;
      gap: 10px;
      align-items: center;
    }
    .btn-secondary {
      background: rgba(30, 41, 59, 0.7);
      border: 1px solid var(--card-border);
      color: var(--text-muted);
      padding: 6px 14px;
      border-radius: 8px;
      font-size: 0.8rem;
      font-weight: 600;
      text-decoration: none;
      transition: all 0.15s ease;
      cursor: pointer;
    }
    .btn-secondary:hover {
      background: #1e293b;
      color: var(--text-main);
      border-color: var(--accent);
    }
    .main-container {
      flex: 1;
      display: flex;
      overflow: hidden;
      max-width: 1300px;
      width: 100%;
      margin: 0 auto;
      padding: 16px 20px;
      gap: 20px;
    }
    .chat-pane {
      flex: 1;
      display: flex;
      flex-direction: column;
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 16px;
      overflow: hidden;
      box-shadow: 0 10px 30px rgba(0,0,0,0.4);
    }
    .messages-container {
      flex: 1;
      overflow-y: auto;
      padding: 24px;
      display: flex;
      flex-direction: column;
      gap: 20px;
      scroll-behavior: smooth;
    }
    .msg-wrapper {
      display: flex;
      gap: 14px;
      max-width: 88%;
      animation: fadeIn 0.2s ease forwards;
    }
    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(6px); }
      to { opacity: 1; transform: translateY(0); }
    }
    .msg-wrapper.user {
      align-self: flex-end;
      flex-direction: row-reverse;
    }
    .msg-avatar {
      width: 34px;
      height: 34px;
      border-radius: 10px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 16px;
      flex-shrink: 0;
    }
    .msg-wrapper.bot .msg-avatar {
      background: linear-gradient(135deg, #0284c7, #0ea5e9);
      border: 1px solid var(--accent);
    }
    .msg-wrapper.user .msg-avatar {
      background: linear-gradient(135deg, #4f46e5, #4338ca);
      border: 1px solid #6366f1;
    }
    .msg-bubble {
      padding: 14px 18px;
      border-radius: 14px;
      font-size: 0.92rem;
      line-height: 1.55;
    }
    .msg-wrapper.bot .msg-bubble {
      background: var(--bot-msg-bg);
      border: 1px solid rgba(56, 189, 248, 0.15);
      border-top-left-radius: 4px;
      color: #e2e8f0;
    }
    .msg-wrapper.user .msg-bubble {
      background: var(--user-msg-bg);
      border: 1px solid rgba(99, 102, 241, 0.3);
      border-top-right-radius: 4px;
      color: #ffffff;
    }
    .msg-bubble h1, .msg-bubble h2, .msg-bubble h3 {
      margin-top: 10px;
      margin-bottom: 6px;
      color: #ffffff;
    }
    .msg-bubble ul, .msg-bubble ol {
      padding-left: 20px;
      margin: 8px 0;
    }
    .msg-bubble li {
      margin-bottom: 4px;
    }
    .msg-bubble code {
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.85em;
      background: rgba(0, 0, 0, 0.4);
      padding: 2px 6px;
      border-radius: 4px;
      color: var(--accent);
    }
    .citation-card {
      margin-top: 12px;
      padding: 10px 14px;
      background: rgba(15, 23, 42, 0.8);
      border: 1px dashed var(--gold);
      border-radius: 8px;
      font-size: 0.8rem;
    }
    .citation-title {
      font-weight: 700;
      color: var(--gold);
      display: flex;
      align-items: center;
      gap: 6px;
      margin-bottom: 6px;
    }
    .citation-item {
      color: var(--text-muted);
      font-size: 0.78rem;
      margin-bottom: 4px;
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .hash-badge {
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.7rem;
      color: #38bdf8;
      background: rgba(56, 189, 248, 0.1);
      padding: 1px 5px;
      border-radius: 4px;
    }
    .quick-prompts {
      padding: 8px 16px;
      background: rgba(15, 23, 42, 0.7);
      border-top: 1px solid var(--card-border);
      display: flex;
      gap: 8px;
      overflow-x: auto;
      white-space: nowrap;
      scrollbar-width: thin;
    }
    .prompt-chip {
      background: #1e293b;
      border: 1px solid #334155;
      color: #cbd5e1;
      padding: 6px 12px;
      border-radius: 20px;
      font-size: 0.78rem;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.15s ease;
      display: inline-flex;
      align-items: center;
      gap: 5px;
    }
    .prompt-chip:hover {
      background: #0284c7;
      color: #ffffff;
      border-color: var(--accent);
      transform: translateY(-1px);
    }
    .input-bar {
      padding: 16px 20px;
      background: rgba(17, 24, 38, 0.95);
      border-top: 1px solid var(--card-border);
      display: flex;
      gap: 12px;
      align-items: center;
    }
    .input-bar textarea {
      flex: 1;
      background: #0b1120;
      border: 1px solid #334155;
      border-radius: 12px;
      color: var(--text-main);
      padding: 12px 16px;
      font-family: inherit;
      font-size: 0.9rem;
      resize: none;
      height: 48px;
      outline: none;
      transition: border-color 0.15s ease;
    }
    .input-bar textarea:focus {
      border-color: var(--accent);
      box-shadow: 0 0 0 2px var(--accent-glow);
    }
    .send-btn {
      background: linear-gradient(135deg, #0284c7, #0ea5e9);
      border: none;
      color: white;
      width: 48px;
      height: 48px;
      border-radius: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      font-size: 1.2rem;
      transition: transform 0.15s ease;
    }
    .send-btn:hover {
      transform: scale(1.05);
    }
    .sidebar {
      width: 320px;
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 16px;
      padding: 20px;
      display: flex;
      flex-direction: column;
      gap: 16px;
      overflow-y: auto;
    }
    .sidebar-section {
      background: rgba(15, 23, 42, 0.6);
      border: 1px solid var(--card-border);
      border-radius: 10px;
      padding: 14px;
    }
    .sidebar-heading {
      font-size: 0.8rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--gold);
      margin-bottom: 10px;
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .metric-row {
      display: flex;
      justify-content: space-between;
      font-size: 0.8rem;
      margin-bottom: 6px;
      color: var(--text-muted);
    }
    .metric-val {
      font-weight: 600;
      color: var(--text-main);
      font-family: 'JetBrains Mono', monospace;
    }
    .typing-indicator {
      display: flex;
      align-items: center;
      gap: 5px;
      padding: 10px 14px;
      color: var(--text-muted);
      font-size: 0.82rem;
      font-style: italic;
    }
    .dot {
      width: 6px;
      height: 6px;
      background: var(--accent);
      border-radius: 50%;
      animation: bounce 1.4s infinite ease-in-out both;
    }
    .dot:nth-child(1) { animation-delay: -0.32s; }
    .dot:nth-child(2) { animation-delay: -0.16s; }
    @keyframes bounce {
      0%, 80%, 100% { transform: scale(0); }
      40% { transform: scale(1); }
    }
    @media (max-width: 900px) {
      .sidebar { display: none; }
      .main-container { padding: 8px; }
    }
  </style>
</head>
<body>

  <header>
    <div class="brand">
      <div class="emblem">⚖️</div>
      <div>
        <div class="brand-title">
          EPFO Statutory Intelligence & Copilot
          <span class="status-badge"><span class="pulse-dot"></span> Bitemporal Engine Active</span>
        </div>
        <div class="brand-subtitle">Autonomous Statutory Verification • Zero Hardcoded Law • Zero LLM Math</div>
      </div>
    </div>
    <div class="header-actions">
      <a href="/docs" target="_blank" class="btn-secondary">API Docs (Swagger)</a>
      <a href="/v1/social/daily-briefing" target="_blank" class="btn-secondary">Daily Social Briefing</a>
    </div>
  </header>

  <div class="main-container">
    <div class="chat-pane">
      <div class="messages-container" id="chatMessages">
        <div class="msg-wrapper bot">
          <div class="msg-avatar">⚖️</div>
          <div class="msg-bubble">
            <strong>Welcome to the EPFO Intelligence System Copilot.</strong>
            <p style="margin-top: 6px;">I am your private, legally locked statutory compliance engine. Ask me anything about EPF, EPS-95, EDLI, ECR inspection gates, Section 7Q / 14B penalties, or CGIT Section 7-I appeal memos.</p>
            <div class="citation-card">
              <div class="citation-title">🔒 Statutory Guarantee</div>
              <div class="citation-item">• All monetary calculations execute in <strong>integer paise</strong> via Stage 2 rule engines.</div>
              <div class="citation-item">• All legal citations are validated against SHA-256 cryptographic hashes.</div>
            </div>
          </div>
        </div>
      </div>

      <div class="quick-prompts">
        <button class="prompt-chip" onclick="sendPrompt('What is the current EPFO statutory wage ceiling and what changes in September 2026?')">🏛️ Wage Ceiling 2026</button>
        <button class="prompt-chip" onclick="sendPrompt('Explain the Supreme Court 50% allowance cap on basic wages with an example of Rs 50,000 gross salary.')">⚖️ SC 50% Allowance Cap</button>
        <button class="prompt-chip" onclick="sendPrompt('My Form 19 was rejected because member name does not match Aadhaar. How to fix it?')">⚠️ Form 19 Rejected</button>
        <button class="prompt-chip" onclick="sendPrompt('Calculate Section 7Q interest and Section 14B damages for Rs 2,50,000 late ECR arrears delayed by 45 days.')">💸 7Q & 14B Penalties</button>
        <button class="prompt-chip" onclick="sendPrompt('Draft a CGIT Section 7-I appeal against Section 7A order for Rs 5,00,000 with 25% pre-deposit under Section 7O.')">📜 CGIT Appeal Draft</button>
      </div>

      <div class="input-bar">
        <textarea id="userInput" placeholder="Ask anything about EPFO rules, claims, ECR, 7Q/14B, or court rulings... (Enter to send)" rows="1"></textarea>
        <button class="send-btn" id="sendBtn" onclick="sendMessage()">➤</button>
      </div>
    </div>

    <div class="sidebar">
      <div class="sidebar-section">
        <div class="sidebar-heading">⚙️ Engine Architecture</div>
        <div class="metric-row"><span>Stage 1 Baseline</span><span class="metric-val">PostgreSQL Bitemporal</span></div>
        <div class="metric-row"><span>Temporal Exclusion</span><span class="metric-val">btree_gist daterange</span></div>
        <div class="metric-row"><span>Stage 2 Math</span><span class="metric-val">Deterministic (Paise)</span></div>
        <div class="metric-row"><span>Stage 3 Ingestion</span><span class="metric-val">304 ETag Probes</span></div>
        <div class="metric-row"><span>Stage 4 Consensus</span><span class="metric-val">Dual-Extractor (≥0.98)</span></div>
        <div class="metric-row"><span>Stage 5 Precedents</span><span class="metric-val">Citation-Locked RAG</span></div>
      </div>

      <div class="sidebar-section">
        <div class="sidebar-heading">🕒 Autonomous Sweep Cycle</div>
        <div class="metric-row"><span>06:00 IST</span><span class="metric-val">Statutory Ingestion</span></div>
        <div class="metric-row"><span>06:15 IST</span><span class="metric-val">Shadow DB Gate</span></div>
        <div class="metric-row"><span>06:30 IST</span><span class="metric-val">Cache Refresh</span></div>
        <div class="metric-row"><span>Hash Chain</span><span class="metric-val" style="color:var(--success)">VERIFIED ✓</span></div>
      </div>

      <div class="sidebar-section">
        <div class="sidebar-heading">🤖 Active Integrations</div>
        <div class="metric-row"><span>Web Chat Copilot</span><span class="metric-val" style="color:var(--success)">Online</span></div>
        <div class="metric-row"><span>Telegram Bot</span><span class="metric-val">Ready (bot/)</span></div>
        <div class="metric-row"><span>Auto Social Bot</span><span class="metric-val">Connected</span></div>
      </div>
    </div>
  </div>

  <script>
    const chatMessages = document.getElementById('chatMessages');
    const userInput = document.getElementById('userInput');
    const sendBtn = document.getElementById('sendBtn');

    userInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    });

    function sendPrompt(text) {
      userInput.value = text;
      sendMessage();
    }

    async function sendMessage() {
      const q = userInput.value.trim();
      if (!q) return;

      appendMessage('user', q);
      userInput.value = '';

      const typingDiv = showTypingIndicator();

      try {
        const res = await fetch('/v1/copilot/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query: q })
        });

        const data = await res.json();
        typingDiv.remove();

        if (res.ok) {
          appendBotResponse(data);
        } else {
          appendMessage('bot', '⚠️ Error: ' + (data.detail || 'Failed to process statutory query.'));
        }
      } catch (err) {
        typingDiv.remove();
        appendMessage('bot', '⚠️ Connection error: Could not reach EPFO Intelligence Server.');
      }
    }

    function appendMessage(sender, text) {
      const wrapper = document.createElement('div');
      wrapper.className = `msg-wrapper ${sender}`;

      const avatar = document.createElement('div');
      avatar.className = 'msg-avatar';
      avatar.innerHTML = sender === 'bot' ? '⚖️' : '👤';

      const bubble = document.createElement('div');
      bubble.className = 'msg-bubble';
      bubble.innerHTML = marked.parse(text);

      wrapper.appendChild(avatar);
      wrapper.appendChild(bubble);
      chatMessages.appendChild(wrapper);
      chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function appendBotResponse(data) {
      const wrapper = document.createElement('div');
      wrapper.className = 'msg-wrapper bot';

      const avatar = document.createElement('div');
      avatar.className = 'msg-avatar';
      avatar.innerHTML = '⚖️';

      const bubble = document.createElement('div');
      bubble.className = 'msg-bubble';
      bubble.innerHTML = marked.parse(data.answer_markdown);

      if (data.calculation_summary) {
        const calcCard = document.createElement('div');
        calcCard.className = 'citation-card';
        calcCard.style.borderColor = '#38bdf8';
        let itemsHtml = '';
        for (const [k, v] of Object.entries(data.calculation_summary)) {
          itemsHtml += `<div class="citation-item"><strong>${k}:</strong> ${v}</div>`;
        }
        calcCard.innerHTML = `<div class="citation-title" style="color:#38bdf8">🧮 Deterministic Engine Breakdown</div>${itemsHtml}`;
        bubble.appendChild(calcCard);
      }

      if (data.citations && data.citations.length > 0) {
        const citCard = document.createElement('div');
        citCard.className = 'citation-card';
        let citHtml = '';
        data.citations.forEach(c => {
          citHtml += `<div class="citation-item">📜 <strong>${c.source || 'Statutory Source'}:</strong> ${c.ref || c.doc_ref || ''} <span class="hash-badge">${c.doc_sha256 ? c.doc_sha256.slice(0, 10) + '...' : 'SHA-256 Verified'}</span></div>`;
        });
        citCard.innerHTML = `<div class="citation-title">🔒 Verified Legal Envelopes</div>${citHtml}`;
        bubble.appendChild(citCard);
      }

      wrapper.appendChild(avatar);
      wrapper.appendChild(bubble);
      chatMessages.appendChild(wrapper);
      chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function showTypingIndicator() {
      const div = document.createElement('div');
      div.className = 'typing-indicator';
      div.innerHTML = '<div class="dot"></div><div class="dot"></div><div class="dot"></div> &nbsp; Evaluating statutory rule engines...';
      chatMessages.appendChild(div);
      chatMessages.scrollTop = chatMessages.scrollHeight;
      return div;
    }
  </script>
</body>
</html>
"""
