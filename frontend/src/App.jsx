import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Phone, PhoneOff, Send, Mic, AlertTriangle, CheckCircle,
  HelpCircle, Activity, Shield, Zap, Clock, Wifi, User, Radio
} from "lucide-react";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function apiChat(sessionId, message, location, history) {
  const res = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, message, location, history }),
  });
  if (!res.ok) throw new Error("API error: " + res.status);
  return res.json();
}

async function apiEndCall(sessionId, duration, intent, confidence, decision, location) {
  const res = await fetch(`${API_BASE}/calls/end`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, duration, intent, confidence, decision, location }),
  });
  if (!res.ok) throw new Error("API error: " + res.status);
  return res.json();
}

async function apiFetchCalls() {
  const res = await fetch(`${API_BASE}/calls`);
  if (!res.ok) throw new Error("API error: " + res.status);
  return res.json();
}

async function apiFetchStats() {
  const res = await fetch(`${API_BASE}/stats`);
  if (!res.ok) throw new Error("API error: " + res.status);
  return res.json();
}

const DECISION_CFG = {
  ESCALATE: { color: "#ff4757", glow: "rgba(255,71,87,0.35)",  icon: AlertTriangle, label: "ESCALATE", sub: "Immediate dispatch required" },
  CONFIRM:  { color: "#ffa502", glow: "rgba(255,165,2,0.35)",  icon: HelpCircle,    label: "CONFIRM",  sub: "Clarification needed" },
  PROCEED:  { color: "#2ed573", glow: "rgba(46,213,115,0.35)", icon: CheckCircle,   label: "PROCEED",  sub: "Situation under control" },
};

function StatCard({ icon: Icon, value, label, color }) {
  return (
    <div className="stat-card">
      <div className="stat-icon" style={{ "--sc": color }}><Icon size={20} /></div>
      <div>
        <div className="stat-value">{value}</div>
        <div className="stat-label">{label}</div>
      </div>
    </div>
  );
}

function DecisionBadge({ decision, size = "sm" }) {
  const map = { ESCALATE: "badge--red", CONFIRM: "badge--amber", PROCEED: "badge--green" };
  return <span className={`badge ${map[decision]} badge--${size}`}>{decision}</span>;
}

function IncomingCallOverlay({ onAccept, onDecline }) {
  return (
    <motion.div className="call-overlay" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
      {[0,1,2,3].map(i => <div key={i} className="pulse-ring" style={{ animationDelay: `${i * 0.45}s` }} />)}
      <motion.div className="call-card" initial={{ scale: 0.75, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} transition={{ type: "spring", stiffness: 220, damping: 20 }}>
        <div className="caller-icon-bg"><Phone size={36} className="caller-icon-svg" /></div>
        <p className="call-tag">INCOMING EMERGENCY CALL</p>
        <h2 className="caller-number">1092 — 4471</h2>
        <p className="caller-location">📍 Sector 14, New Delhi</p>
        <p className="call-status-text">Connecting to SPASHT AI…</p>
        <div className="call-buttons">
          <button className="btn-decline" onClick={onDecline}><PhoneOff size={20} /><span>Decline</span></button>
          <button className="btn-accept"  onClick={onAccept}><Phone size={20} /><span>Accept</span></button>
        </div>
      </motion.div>
    </motion.div>
  );
}

function ActiveCallPanel({ onEnd, onCallLogged }) {
  const SESSION_ID = useRef(`call-${Date.now()}`).current;
  const LOCATION   = "Sector 14, New Delhi";

  const [inputText, setInputText]   = useState("");
  const [transcript, setTranscript] = useState([
    { id: Date.now(), label: "SYSTEM", text: "Call accepted. SPASHT AI monitoring active.", time: "00:00" }
  ]);
  const [result, setResult]   = useState(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [callTime, setCallTime]   = useState(0);
  const [apiError, setApiError]   = useState(null);

  const historyRef    = useRef([]);
  const timerRef      = useRef(null);
  const transcriptRef = useRef(null);
  const startRef      = useRef(Date.now());

  useEffect(() => {
    timerRef.current = setInterval(() => setCallTime(t => t + 1), 1000);
    return () => clearInterval(timerRef.current);
  }, []);

  useEffect(() => {
    if (transcriptRef.current) transcriptRef.current.scrollTop = transcriptRef.current.scrollHeight;
  }, [transcript]);

  const fmt = s => `${String(Math.floor(s/60)).padStart(2,"0")}:${String(s%60).padStart(2,"0")}`;

  const handleSend = async () => {
    const text = inputText.trim(); if (!text || analyzing) return;
    const time = fmt(callTime);
    setApiError(null);
    setTranscript(t => [...t, { id: Date.now(), label: "CALLER", text, time }]);
    setInputText("");
    setAnalyzing(true);
    historyRef.current.push({ role: "caller", content: text });

    try {
      const data = await apiChat(SESSION_ID, text, LOCATION, historyRef.current);
      if (data.intent) setResult(data.intent);
      const aiText = data.ai_message;
      setTranscript(t => [
        ...t,
        { id: Date.now()+1, label: "AI", text: aiText, time: fmt(callTime) },
        ...(data.intent ? [{
          id: Date.now()+2, label: "SYSTEM",
          text: `Intent: ${data.intent.intent} · ${Math.round(data.intent.confidence*100)}% · ${data.intent.decision}`,
          time: fmt(callTime)
        }] : [])
      ]);
      historyRef.current.push({ role: "ai", content: aiText });
    } catch (err) {
      setApiError("Backend unreachable — is the FastAPI server running on port 8000?");
      setTranscript(t => [...t, {
        id: Date.now()+1, label: "SYSTEM",
        text: "⚠️ Cannot reach SPASHT API. Start the backend with: uvicorn main:app --reload",
        time: fmt(callTime)
      }]);
    } finally {
      setAnalyzing(false);
    }
  };

  const handleEnd = async () => {
    const elapsed = Math.round((Date.now() - startRef.current) / 1000);
    const m = Math.floor(elapsed/60), s = elapsed%60;
    const dur = `${m}m ${String(s).padStart(2,"0")}s`;
    if (result) {
      try {
        await apiEndCall(SESSION_ID, dur, result.intent, result.confidence, result.decision, LOCATION);
        onCallLogged();
      } catch (_) {}
    }
    onEnd();
  };

  const SCENARIOS = [
    { label: "🚨 Emergency", text: "Someone is following me, I'm scared!" },
    { label: "⚠️ Unclear",   text: "Something feels wrong, I'm not sure what" },
    { label: "✅ Calm",      text: "There's an argument nearby, no one is hurt" },
  ];

  const cfg = result ? DECISION_CFG[result.decision] : null;

  return (
    <motion.div className="active-call-panel" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}>
      <div className="acall-header">
        <div className="acall-header-left">
          <span className="live-dot" />
          <span className="acall-title">ACTIVE CALL — 1092-4471</span>
          <span className="acall-loc">📍 {LOCATION}</span>
        </div>
        <div className="acall-header-right">
          <span className="acall-timer">{fmt(callTime)}</span>
          <button className="btn-end-call" onClick={handleEnd}><PhoneOff size={14} /> End Call</button>
        </div>
      </div>

      {apiError && <div className="api-error-banner">⚠️ {apiError}</div>}

      <div className="acall-body">
        <div className="acall-transcript-col">
          <div className="acall-section-label">
            <Mic size={13} /> Live Transcript {analyzing && <span className="analyzing-pill">AI thinking…</span>}
          </div>
          <div className="transcript-scroll" ref={transcriptRef}>
            {transcript.map(e => (
              <motion.div key={e.id} initial={{ opacity:0, x:-12 }} animate={{ opacity:1, x:0 }} className="te">
                <span className="te-time">{e.time}</span>
                <span className={`te-label te-label--${e.label.toLowerCase()}`}>{e.label}</span>
                <span className="te-text">{e.text}</span>
              </motion.div>
            ))}
            {analyzing && <div className="thinking-dots"><span/><span/><span/></div>}
          </div>
          <div className="scenario-row">
            {SCENARIOS.map(s => <button key={s.label} className="scenario-btn" onClick={() => setInputText(s.text)}>{s.label}</button>)}
          </div>
          <div className="input-row">
            <textarea className="call-input" value={inputText} onChange={e => setInputText(e.target.value)}
              onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); }}}
              placeholder="Simulate caller speech… (Enter to send)" rows={2} />
            <button className="btn-send" onClick={handleSend} disabled={!inputText.trim() || analyzing}><Send size={17} /></button>
          </div>
        </div>

        <div className="acall-decision-col">
          <div className="acall-section-label"><Activity size={13} /> AI Decision Engine</div>
          <AnimatePresence mode="wait">
            {result && cfg ? (
              <motion.div key={result.decision+result.intent} initial={{ opacity:0, y:16 }} animate={{ opacity:1, y:0 }} className="decision-pane">
                <div className="decision-hero" style={{ "--dc": cfg.color, "--dg": cfg.glow }}>
                  <cfg.icon size={28} />
                  <div>
                    <div className="dh-label">{cfg.label}</div>
                    <div className="dh-sub">{cfg.sub}</div>
                  </div>
                </div>
                <div className="dmetric">
                  <div className="dmetric-label"><Zap size={11}/> INTENT</div>
                  <div className="dmetric-val">{result.intent}</div>
                </div>
                {result.reasoning && (
                  <div className="dmetric">
                    <div className="dmetric-label"><Radio size={11}/> REASONING</div>
                    <div className="dmetric-val" style={{fontSize:"0.72rem",opacity:0.8,lineHeight:1.4}}>{result.reasoning}</div>
                  </div>
                )}
                <div className="dmetric">
                  <div className="dmetric-label"><Activity size={11}/> CONFIDENCE</div>
                  <div className="dmetric-val conf-big">{Math.round(result.confidence*100)}%</div>
                  <div className="conf-track">
                    <motion.div className="conf-fill" initial={{width:0}} animate={{width:`${result.confidence*100}%`}}
                      transition={{duration:0.8,ease:"easeOut"}} style={{background:`linear-gradient(90deg,${cfg.color}66,${cfg.color})`}} />
                  </div>
                </div>
                <div className="dmetric">
                  <div className="dmetric-label"><Shield size={11}/> URGENCY</div>
                  <div className={`urgency-chip urgency--${result.urgency.toLowerCase()}`}>{result.urgency}</div>
                </div>
              </motion.div>
            ) : (
              <motion.div key="waiting" initial={{opacity:0}} animate={{opacity:1}} exit={{opacity:0}} className="decision-waiting">
                <Shield size={36} className="dw-icon" />
                <p>Awaiting input…</p>
                <p className="dw-sub">Type a message to trigger the AI agent</p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </motion.div>
  );
}

export default function App() {
  const [phase, setPhase]   = useState("idle");
  const [callLog, setCallLog] = useState([]);
  const [stats, setStats]   = useState({ total:0, escalated:0, confirmed:0, proceeded:0 });
  const [clock, setClock]   = useState("");
  const audioCtxRef = useRef(null);

  useEffect(() => {
    const tick = () => {
      const n = new Date();
      setClock(`${String(n.getHours()).padStart(2,"0")}:${String(n.getMinutes()).padStart(2,"0")}:${String(n.getSeconds()).padStart(2,"0")}`);
    };
    tick(); const id = setInterval(tick, 1000); return () => clearInterval(id);
  }, []);

  const refreshData = async () => {
    try {
      const [logData, statsData] = await Promise.all([apiFetchCalls(), apiFetchStats()]);
      setCallLog(logData.entries || []);
      setStats(statsData);
    } catch (_) {}
  };

  useEffect(() => { refreshData(); }, []);

  useEffect(() => {
    if (phase !== "incoming") {
      if (audioCtxRef.current) { audioCtxRef.current.close(); audioCtxRef.current = null; }
      return;
    }
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    audioCtxRef.current = ctx;
    let stopped = false;
    const ring = () => {
      if (stopped || ctx.state === "closed") return;
      const osc = ctx.createOscillator(); const gain = ctx.createGain();
      osc.connect(gain); gain.connect(ctx.destination);
      osc.frequency.value = 880; osc.type = "sine";
      gain.gain.setValueAtTime(0, ctx.currentTime);
      gain.gain.linearRampToValueAtTime(0.1, ctx.currentTime + 0.05);
      gain.gain.linearRampToValueAtTime(0, ctx.currentTime + 0.35);
      osc.start(ctx.currentTime); osc.stop(ctx.currentTime + 0.4);
      setTimeout(ring, 1500);
    };
    ring();
    return () => { stopped = true; };
  }, [phase]);

  const todayStr = new Date().toLocaleDateString("en-GB", { day:"2-digit", month:"short", year:"numeric" });

  return (
    <div className="app">
      <div className="bg-grid" />
      <AnimatePresence>
        {phase === "incoming" && (
          <IncomingCallOverlay
            onAccept={() => setPhase("active")}
            onDecline={() => setPhase("idle")}
          />
        )}
      </AnimatePresence>

      <div className="shell">
        <nav className="topnav">
          <div className="topnav-brand">
            <div className="brand-icon"><Shield size={16} /></div>
            <div>
              <div className="brand-name">SPASHT AI</div>
              <div className="brand-sub">1092 EMERGENCY DISPATCH SYSTEM</div>
            </div>
          </div>
          <div className="topnav-clock">
            <div className="clock-time">{clock}</div>
            <div className="clock-date">{todayStr}</div>
          </div>
          <div className="topnav-status">
            <span className="status-pill status-online"><span className="s-dot" />ONLINE</span>
            <span className="status-divider">|</span>
            <span className="status-item"><User size={13} /> OPR-4721</span>
            <span className="status-divider">|</span>
            <span className="status-item"><Wifi size={13} /> LIVE</span>
          </div>
        </nav>

        <div className="stats-row">
          <StatCard icon={Phone}         value={stats.total}     label="TOTAL CALLS" color="#38bdf8" />
          <StatCard icon={AlertTriangle} value={stats.escalated} label="ESCALATED"   color="#ff4757" />
          <StatCard icon={HelpCircle}    value={stats.confirmed} label="CONFIRMED"   color="#ffa502" />
          <StatCard icon={CheckCircle}   value={stats.proceeded} label="PROCEEDED"   color="#2ed573" />
        </div>

        <div className="main-content">
          <AnimatePresence mode="wait">
            {phase === "active" ? (
              <ActiveCallPanel
                key="active"
                onCallLogged={refreshData}
                onEnd={() => { setPhase("idle"); refreshData(); }}
              />
            ) : (
              <motion.div key="idle" className="system-ready-panel" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                <div className="sr-icon-wrap">
                  {[0,1,2].map(i => <div key={i} className="sr-ring" style={{ animationDelay: `${i*0.7}s` }} />)}
                  <div className="sr-icon"><Shield size={32} /></div>
                </div>
                <h2 className="sr-title">SYSTEM READY</h2>
                <p className="sr-sub">Awaiting Emergency Dispatch Signal...</p>
                <button className="btn-simulate" onClick={() => setPhase("incoming")}>
                  <Phone size={16} /> SIMULATE INCOMING CALL
                </button>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        <div className="calllog-section">
          <div className="calllog-header">
            <span className="calllog-title"><Clock size={14} /> CALL LOG</span>
            <span className="calllog-count">{callLog.length} records</span>
          </div>
          <table className="calllog-table">
            <thead>
              <tr><th>TIME</th><th>DURATION</th><th>INTENT</th><th>CONFIDENCE</th><th>DECISION</th></tr>
            </thead>
            <tbody>
              {callLog.map(row => (
                <motion.tr key={row.id} initial={{ opacity:0, y:-8 }} animate={{ opacity:1, y:0 }}>
                  <td className="td-time">{row.time}</td>
                  <td className="td-dur">{row.duration}</td>
                  <td className="td-intent">{row.intent.toUpperCase()}</td>
                  <td className="td-conf" style={{ color: row.confidence >= 0.7 ? "#38bdf8" : row.confidence >= 0.5 ? "#ffa502" : "#ff4757" }}>
                    {Math.round(row.confidence * 100)}%
                  </td>
                  <td><DecisionBadge decision={row.decision} /></td>
                </motion.tr>
              ))}
            </tbody>
          </table>
          {callLog.length === 0 && (
            <div style={{textAlign:"center",padding:"1.5rem",color:"rgba(255,255,255,0.3)",fontSize:"0.8rem"}}>
              No calls logged yet — simulate a call above
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
