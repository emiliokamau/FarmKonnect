/**
 * KonnectAI — Voice and Text Agricultural Assistant for FarmKonnect
 * Embeds ONLY on authenticated operational pages (dashboard.html, pos.html).
 * Self-guarding, multi-modal (Call AI + Text Chat), bilingual (Swahili & English).
 */

(async function bootstrapKonnectAI() {
  // 1. PAGE GUARD: Never render on public pages
  const PUBLIC_PAGES = new Set(["home", "register", "login", "verify-otp"]);
  const page = (document.body.dataset.page || "").toLowerCase();
  if (PUBLIC_PAGES.has(page)) {
    return;
  }

  // 2. AUTHENTICATION GUARD: Must be logged in via DRF token
  if (!window.isLoggedIn || !window.isLoggedIn()) {
    return;
  }

  const token = window.getToken ? window.getToken() : localStorage.getItem("fk_token");
  if (!token) {
    return;
  }

  // 3. STALE TOKEN GUARD: Verify token with /api/auth/me/
  try {
    const res = await fetch("/api/auth/me/", {
      headers: {
        Authorization: `Token ${token}`,
        Accept: "application/json",
      },
    });
    if (!res.ok) {
      // Stale or revoked token
      return;
    }
  } catch (err) {
    // Network error or unauthorized
    return;
  }

  // Guards passed! Mount the KonnectAI widget
  mountKonnectAI(page, token);
})();

function mountKonnectAI(page, token) {
  // Prevent duplicate mounts
  if (document.getElementById("kaiWidgetContainer")) return;

  // State
  let sessionId = sessionStorage.getItem("kai_session_id") || null;
  let currentLang = "auto";
  let isChatOpen = false;
  let isCallActive = false;
  let ws = null;
  let mediaStream = null;
  let audioContext = null;
  let mediaRecorder = null;
  let currentAudio = null;
  let isMuted = false;
  let animationFrameId = null;
  let speechRecognition = null;
  let browserSpeechMode = false;

  // Inject Floating Buttons Container
  const container = document.createElement("div");
  container.id = "kaiWidgetContainer";
  container.className = "kai-widget-container";
  container.innerHTML = `
    <!-- Voice Call Trigger -->
    <button class="kai-floating-btn kai-call-btn" id="kaiCallBtn" title="Call KonnectAI">
      <span class="kai-btn-icon">🎙</span>
      <span class="kai-btn-label">Call AI</span>
    </button>

    <!-- Text Chat Trigger -->
    <button class="kai-floating-btn kai-chat-btn" id="kaiChatBtn" title="Chat with KonnectAI">
      <span class="kai-btn-icon">💬</span>
      <span class="kai-btn-label">Chat</span>
      <span class="kai-badge-dot"></span>
    </button>

    <!-- Chat Panel -->
    <div class="kai-chat-panel" id="kaiChatPanel">
      <div class="kai-panel-header">
        <div class="kai-header-title">
          <span class="kai-logo-icon">🌾</span>
          <div>
            <strong>KonnectAI</strong>
            <span class="kai-status-sub">Online · ${page === "pos" ? "POS Mode" : "Farm Advisor"}</span>
          </div>
        </div>
        <div class="kai-header-actions">
          <select id="kaiLangSelect" class="kai-lang-select" title="Language">
            <option value="auto">🌐 Auto (Swahili/English)</option>
            <option value="sw">🇰🇪 Kiswahili</option>
            <option value="en">🇬🇧 English</option>
          </select>
          <button class="kai-close-btn" id="kaiCloseChat" title="Close">✕</button>
        </div>
      </div>

      <div class="kai-messages-box" id="kaiMessagesBox">
        <div class="kai-msg kai-msg-ai">
          <div class="kai-bubble">
            Habari! I am KonnectAI, your farm and store assistant. You can speak or type in Kiswahili or English.
          </div>
          <span class="kai-meta">Just now</span>
        </div>
      </div>

      <form class="kai-input-bar" id="kaiChatForm">
        <input type="text" id="kaiTextInput" placeholder="Type a message (e.g. Nimeuza gunia 5 za mahindi)..." autocomplete="off" required />
        <button type="submit" class="kai-send-btn" id="kaiSendBtn" title="Send">➤</button>
      </form>
    </div>

    <!-- Voice Call Overlay -->
    <div class="kai-overlay" id="kaiVoiceOverlay">
      <div class="kai-call-card">
        <div class="kai-call-header">
          <div class="kai-avatar-pulse">
            <span class="kai-pulse-ring"></span>
            <span class="kai-pulse-ring delay"></span>
            <div class="kai-avatar-inner">🌾</div>
          </div>
          <h2>KonnectAI Voice Assistant</h2>
          <p id="kaiCallStatus" class="kai-call-status">Connecting call…</p>
          <div id="kaiIntentBadge" class="kai-intent-badge">FMS / POS</div>
        </div>

        <!-- Waveform Visualizer -->
        <div class="kai-visualizer-wrap">
          <canvas id="kaiWaveCanvas" width="340" height="90"></canvas>
        </div>

        <!-- Live Subtitles & Transcript -->
        <div class="kai-transcript-box" id="kaiTranscriptBox">
          <p class="kai-hint-sub">Listening... Say something like: "Nimeuza gunia tano za mahindi"</p>
        </div>

        <!-- Toast Notifications (SMS, Tools) -->
        <div id="kaiCallToast" class="kai-call-toast"></div>

        <!-- Call Actions -->
        <div class="kai-call-controls">
          <button class="kai-ctrl-btn" id="kaiMuteBtn" title="Mute / Unmute">
            <span id="kaiMuteIcon">🎤</span>
            <span id="kaiMuteLabel">Mute</span>
          </button>
          <button class="kai-ctrl-btn kai-hangup-btn" id="kaiHangupBtn" title="End Call">
            <span>🔴</span>
            <span>End Call</span>
          </button>
          <button class="kai-ctrl-btn" id="kaiInterruptBtn" title="Barge-in / Interrupt AI">
            <span>✋</span>
            <span>Interrupt</span>
          </button>
        </div>
      </div>
    </div>
  `;

  document.body.appendChild(container);

  // DOM Elements
  const chatBtn = document.getElementById("kaiChatBtn");
  const callBtn = document.getElementById("kaiCallBtn");
  const chatPanel = document.getElementById("kaiChatPanel");
  const closeChat = document.getElementById("kaiCloseChat");
  const chatForm = document.getElementById("kaiChatForm");
  const textInput = document.getElementById("kaiTextInput");
  const messagesBox = document.getElementById("kaiMessagesBox");
  const langSelect = document.getElementById("kaiLangSelect");

  const voiceOverlay = document.getElementById("kaiVoiceOverlay");
  const callStatus = document.getElementById("kaiCallStatus");
  const intentBadge = document.getElementById("kaiIntentBadge");
  const transcriptBox = document.getElementById("kaiTranscriptBox");
  const callToast = document.getElementById("kaiCallToast");
  const hangupBtn = document.getElementById("kaiHangupBtn");
  const muteBtn = document.getElementById("kaiMuteBtn");
  const interruptBtn = document.getElementById("kaiInterruptBtn");
  const muteIcon = document.getElementById("kaiMuteIcon");
  const muteLabel = document.getElementById("kaiMuteLabel");
  const canvas = document.getElementById("kaiWaveCanvas");
  const canvasCtx = canvas.getContext("2d");

  // ===================================================================
  // TEXT CHAT MODE
  // ===================================================================

  chatBtn.addEventListener("click", () => {
    isChatOpen = !isChatOpen;
    chatPanel.classList.toggle("open", isChatOpen);
    if (isChatOpen) {
      textInput.focus();
      loadHistoryFromStorage();
    }
  });

  closeChat.addEventListener("click", () => {
    isChatOpen = false;
    chatPanel.classList.remove("open");
  });

  langSelect.addEventListener("change", (e) => {
    currentLang = e.target.value;
  });

  chatForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const query = textInput.value.trim();
    if (!query) return;

    // Render user message
    appendMessage("user", query);
    textInput.value = "";

    // Show typing loader
    const typingId = appendTypingIndicator();

    try {
      const resp = await fetch("/api/konnect-ai/turn/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Token ${token}`,
        },
        body: JSON.stringify({
          session_id: sessionId ? parseInt(sessionId, 10) : null,
          text: query,
          language: currentLang,
          page: page,
        }),
      });

      removeTypingIndicator(typingId);

      if (!resp.ok) {
        appendMessage("ai", "Samahani, kumetokea hitilafu. Tafadhali jaribu tena.");
        return;
      }

      const data = await resp.json();
      if (data.session_id) {
        sessionId = data.session_id;
        sessionStorage.setItem("kai_session_id", sessionId);
      }

      // Render AI reply with tool chips and intent badge
      appendMessage("ai", data.reply, {
        intent: data.intent,
        toolCalls: data.tool_calls,
        smsSent: data.sms_sent,
      });

    } catch (err) {
      removeTypingIndicator(typingId);
      appendMessage("ai", "Network error. Please check your connection.");
    }
  });

  function appendMessage(role, text, meta = {}) {
    const msgEl = document.createElement("div");
    msgEl.className = `kai-msg kai-msg-${role}`;

    const visibleToolCalls = (meta.toolCalls || []).filter((tc) =>
      tc.summary && !String(text || "").includes(tc.summary)
    );
    const toolBadges = visibleToolCalls
      .map((tc) => `
        <div class="kai-tool-chip ${tc.ok ? 'success' : 'pending'}">
          <span>${tc.ok ? '✓' : '⚠️'}</span>
          <span>${escapeHtml(tc.ok && tc.wrote ? "Saved" : tc.summary || tc.name)}</span>
        </div>`)
      .join("");

    let smsBadge = "";
    if (meta.smsSent) {
      smsBadge = `<div class="kai-sms-badge">📩 SMS confirmation dispatched</div>`;
    }

    let intentTag = "";
    if (meta.intent && meta.intent !== "GENERAL") {
      intentTag = `<span class="kai-bubble-intent">${meta.intent}</span>`;
    }

    msgEl.innerHTML = `
      <div class="kai-bubble">
        ${intentTag}
        <div class="kai-bubble-text">${escapeHtml(text)}</div>
        ${toolBadges}
        ${smsBadge}
      </div>
      <span class="kai-meta">Just now</span>
    `;

    messagesBox.appendChild(msgEl);
    messagesBox.scrollTop = messagesBox.scrollHeight;
    saveHistoryToStorage();
  }

  function appendTypingIndicator() {
    const id = "kaiTyping_" + Date.now();
    const el = document.createElement("div");
    el.id = id;
    el.className = "kai-msg kai-msg-ai kai-typing";
    el.innerHTML = `
      <div class="kai-bubble">
        <span class="kai-dot"></span>
        <span class="kai-dot"></span>
        <span class="kai-dot"></span>
      </div>
    `;
    messagesBox.appendChild(el);
    messagesBox.scrollTop = messagesBox.scrollHeight;
    return id;
  }

  function removeTypingIndicator(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
  }

  function saveHistoryToStorage() {
    try {
      sessionStorage.setItem("kai_history", messagesBox.innerHTML);
    } catch {}
  }

  function loadHistoryFromStorage() {
    try {
      const saved = sessionStorage.getItem("kai_history");
      if (saved && messagesBox.children.length <= 1) {
        messagesBox.innerHTML = saved;
        messagesBox.scrollTop = messagesBox.scrollHeight;
      }
    } catch {}
  }

  // ===================================================================
  // VOICE CALL MODE (WebSocket + Web Audio API)
  // ===================================================================

  callBtn.addEventListener("click", () => {
    startVoiceCall();
  });

  hangupBtn.addEventListener("click", () => {
    endVoiceCall();
  });

  interruptBtn.addEventListener("click", () => {
    triggerInterrupt();
  });

  muteBtn.addEventListener("click", () => {
    isMuted = !isMuted;
    if (mediaStream) {
      mediaStream.getAudioTracks().forEach((track) => {
        track.enabled = !isMuted;
      });
    }
    if (speechRecognition) {
      if (isMuted) speechRecognition.stop();
      else {
        try { speechRecognition.start(); } catch {}
      }
    }
    muteIcon.textContent = isMuted ? "🔇" : "🎤";
    muteLabel.textContent = isMuted ? "Unmute" : "Mute";
  });

  async function startVoiceCall() {
    isCallActive = true;
    voiceOverlay.classList.add("active");
    callStatus.textContent = "Requesting microphone…";
    intentBadge.style.display = "none";
    transcriptBox.innerHTML = `<p class="kai-hint-sub">Connecting to KonnectAI voice service…</p>`;
    startWaveformVisualizer();

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    browserSpeechMode = Boolean(SpeechRecognition);

    if (!browserSpeechMode) {
      if (!navigator.mediaDevices?.getUserMedia) {
        callStatus.textContent = "Voice recognition unavailable.";
        transcriptBox.innerHTML = `<p class="kai-error-sub">Use a recent Chrome or Edge browser for voice chat.</p>`;
        isCallActive = false;
        return;
      }
      try {
        mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      } catch (err) {
        callStatus.textContent = "Microphone access denied.";
        transcriptBox.innerHTML = `<p class="kai-error-sub">Allow microphone access, then start the call again.</p>`;
        isCallActive = false;
        return;
      }
    }

    // Connect WebSocket
    const WS_BASE = (location.protocol === "https:" ? "wss://" : "ws://") + location.host;
    const wsUrl = `${WS_BASE}/ws/konnect-ai/?token=${encodeURIComponent(token)}`;

    try {
      ws = new WebSocket(wsUrl);
    } catch (err) {
      callStatus.textContent = "Connection failed.";
      isCallActive = false;
      return;
    }

    ws.onopen = () => {
      callStatus.textContent = "Connected · Listening…";
      ws.send(JSON.stringify({ type: "start", language: currentLang }));
      if (browserSpeechMode) initBrowserSpeechRecognition(SpeechRecognition);
      else initAudioCapture();
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        handleServerWebSocketMessage(msg);
      } catch (e) {
        console.warn("[KonnectAI WS] parse error:", e);
      }
    };

    ws.onerror = (e) => {
      callStatus.textContent = "Call disconnected.";
    };

    ws.onclose = () => {
      if (isCallActive) {
        callStatus.textContent = "Call Ended.";
      }
    };
  }

  function initBrowserSpeechRecognition(SpeechRecognition) {
    speechRecognition = new SpeechRecognition();
    speechRecognition.continuous = true;
    speechRecognition.interimResults = false;
    speechRecognition.lang = currentLang === "sw" ? "sw-KE" : "en-US";

    speechRecognition.onresult = (event) => {
      for (let index = event.resultIndex; index < event.results.length; index++) {
        const result = event.results[index];
        if (!result.isFinal) continue;
        const text = result[0]?.transcript?.trim();
        if (text && ws?.readyState === WebSocket.OPEN) {
          callStatus.textContent = "Processing…";
          ws.send(JSON.stringify({ type: "text_turn", text, page }));
        }
      }
    };

    speechRecognition.onerror = (event) => {
      callStatus.textContent = event.error === "not-allowed"
        ? "Microphone access denied."
        : "Speech recognition error.";
      if (event.error === "not-allowed") {
        transcriptBox.innerHTML = `<p class="kai-error-sub">Allow microphone access in your browser settings, then restart the call.</p>`;
        endVoiceCall();
      }
    };

    speechRecognition.onend = () => {
      if (isCallActive && !isMuted && ws?.readyState === WebSocket.OPEN) {
        try { speechRecognition.start(); } catch {}
      }
    };

    try {
      speechRecognition.start();
      callStatus.textContent = "Active Call · Speak freely";
      transcriptBox.innerHTML = `<p class="kai-hint-sub">Listening… Speak clearly, then pause for a response.</p>`;
    } catch (err) {
      callStatus.textContent = "Could not start speech recognition.";
    }
  }

  function initAudioCapture() {
    if (!mediaStream) return;

    try {
      // Use MediaRecorder to produce audio slices
      mediaRecorder = new MediaRecorder(mediaStream);
      mediaRecorder.ondataavailable = async (e) => {
        if (e.data && e.data.size > 0 && ws && ws.readyState === WebSocket.OPEN) {
          const reader = new FileReader();
          reader.onloadend = () => {
            const b64 = reader.result.split(",")[1];
            if (b64) {
              ws.send(JSON.stringify({ type: "audio", data: b64 }));
            }
          };
          reader.readAsDataURL(e.data);
        }
      };

      // Record in 800ms slices for responsive voice latency
      mediaRecorder.start(800);

      // Periodically signal utterance end for processing
      let speechTimer = setInterval(() => {
        if (isCallActive && ws && ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: "end_utterance", page: page }));
        } else {
          clearInterval(speechTimer);
        }
      }, 3500);

    } catch (err) {
      console.warn("MediaRecorder error:", err);
    }
  }

  function handleServerWebSocketMessage(msg) {
    if (msg.type === "ready" || msg.type === "session_ready") {
      callStatus.textContent = "Active Call · Speak freely";
    } else if (msg.type === "intent") {
      intentBadge.textContent = `${msg.intent} MODE`;
      intentBadge.style.display = "inline-block";
    } else if (msg.type === "final_transcript") {
      transcriptBox.innerHTML = `
        <div class="kai-user-transcript">
          <span class="kai-speaker-tag">You:</span> "${escapeHtml(msg.text)}"
        </div>
      `;
    } else if (msg.type === "ai_text_local") {
      const prev = transcriptBox.innerHTML;
      transcriptBox.innerHTML = `
        ${prev}
        <div class="kai-ai-transcript">
          <span class="kai-speaker-tag">KonnectAI:</span> ${escapeHtml(msg.text)}
        </div>
      `;
      transcriptBox.scrollTop = transcriptBox.scrollHeight;
      if (browserSpeechMode && window.speechSynthesis) {
        if (speechRecognition) speechRecognition.stop();
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(msg.text);
        utterance.lang = currentLang === "sw" ? "sw-KE" : "en-US";
        utterance.onend = () => {
          if (isCallActive && !isMuted && speechRecognition) {
            try { speechRecognition.start(); } catch {}
          }
        };
        window.speechSynthesis.speak(utterance);
      }
    } else if (msg.type === "tool_result") {
      if (!msg.ok) showCallToast("The requested change was not saved.");
    } else if (msg.type === "sms_sent") {
      showCallToast(`📩 Confirmation SMS sent to ${msg.to || 'your phone'}`);
    } else if (msg.type === "audio_out") {
      if (!browserSpeechMode) playAudioResponse(msg.data);
    } else if (msg.type === "error") {
      showCallToast(msg.detail || "Voice service error.");
    }
  }

  function playAudioResponse(b64Audio) {
    if (!b64Audio) return;

    // Barge-in: stop any currently playing voice
    if (currentAudio) {
      currentAudio.pause();
      currentAudio = null;
    }

    try {
      const audio = new Audio("data:audio/mp3;base64," + b64Audio);
      currentAudio = audio;
      callStatus.textContent = "KonnectAI is speaking…";
      audio.play().catch(() => {});
      audio.onended = () => {
        callStatus.textContent = "Listening…";
        currentAudio = null;
      };
    } catch (err) {
      console.warn("Audio play error:", err);
    }
  }

  function triggerInterrupt() {
    if (currentAudio) {
      currentAudio.pause();
      currentAudio = null;
    }
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: "interrupt" }));
    }
    callStatus.textContent = "Listening… (Interrupted)";
  }

  function endVoiceCall() {
    isCallActive = false;
    if (speechRecognition) {
      speechRecognition.onend = null;
      try { speechRecognition.stop(); } catch {}
      speechRecognition = null;
    }
    if (window.speechSynthesis) window.speechSynthesis.cancel();
    if (currentAudio) {
      currentAudio.pause();
      currentAudio = null;
    }
    if (mediaRecorder && mediaRecorder.state !== "inactive") {
      try { mediaRecorder.stop(); } catch {}
    }
    if (mediaStream) {
      mediaStream.getTracks().forEach((track) => track.stop());
      mediaStream = null;
    }
    if (ws) {
      try {
        ws.send(JSON.stringify({ type: "end" }));
        ws.close();
      } catch {}
      ws = null;
    }
    if (animationFrameId) {
      cancelAnimationFrame(animationFrameId);
      animationFrameId = null;
    }
    voiceOverlay.classList.remove("active");
  }

  function showCallToast(text) {
    callToast.textContent = text;
    callToast.classList.add("visible");
    setTimeout(() => {
      callToast.classList.remove("visible");
    }, 4500);
  }

  // Waveform visualization on canvas
  function startWaveformVisualizer() {
    let phase = 0;
    function renderWave() {
      if (!isCallActive) return;
      canvasCtx.clearRect(0, 0, canvas.width, canvas.height);
      canvasCtx.beginPath();
      canvasCtx.lineWidth = 2.5;
      canvasCtx.strokeStyle = "#2e7d32";

      const sliceWidth = canvas.width / 50;
      let x = 0;
      for (let i = 0; i <= 50; i++) {
        const amplitude = isMuted ? 2 : 18 * Math.sin(phase + i * 0.25);
        const y = canvas.height / 2 + amplitude * Math.sin(i * 0.3);
        if (i === 0) canvasCtx.moveTo(x, y);
        else canvasCtx.lineTo(x, y);
        x += sliceWidth;
      }
      canvasCtx.stroke();
      phase += 0.08;
      animationFrameId = requestAnimationFrame(renderWave);
    }
    renderWave();
  }

  function escapeHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }
}
