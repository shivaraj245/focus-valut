import { useState, useEffect, useRef } from "react";
import { api } from "../api/client";

const COLORS = {
  bg: "#F7F8FC",
  surface: "#FFFFFF",
  surfaceAlt: "#F0F2F8",
  border: "#E2E6F0",
  accent: "#006ECC",
  accentGlow: "rgba(0,110,204,0.12)",
  accentSoft: "rgba(0,110,204,0.07)",
  green: "#00A86B",
  greenGlow: "rgba(0,168,107,0.12)",
  purple: "#7C3AED",
  purpleGlow: "rgba(124,58,237,0.12)",
  orange: "#E85D26",
  orangeGlow: "rgba(232,93,38,0.10)",
  yellow: "#B45309",
  text: "#0F172A",
  textMuted: "#64748B",
  textDim: "#CBD5E1",
};

const DEFAULT_TOPICS = [
  { label: "DSA & Algorithms", hours: 12.4, color: COLORS.accent, icon: "⬡", pct: 38 },
  { label: "Machine Learning", hours: 8.2, color: COLORS.purple, icon: "◈", pct: 25 },
  { label: "Web Development", hours: 6.1, color: COLORS.green, icon: "◉", pct: 19 },
  { label: "System Design", hours: 3.8, color: COLORS.orange, icon: "◫", pct: 12 },
  { label: "Mathematics", hours: 2.0, color: COLORS.yellow, icon: "△", pct: 6 },
];

const TOPIC_STYLE_PRESETS = [
  { color: COLORS.accent, icon: "⬡" },
  { color: COLORS.purple, icon: "◈" },
  { color: COLORS.green, icon: "◉" },
  { color: COLORS.orange, icon: "◫" },
  { color: COLORS.yellow, icon: "△" },
];

const DEFAULT_WEEK_DATA = [
  { day: "Mon", learning: 3.2, other: 1.1 },
  { day: "Tue", learning: 5.4, other: 2.3 },
  { day: "Wed", learning: 2.1, other: 3.4 },
  { day: "Thu", learning: 6.8, other: 1.2 },
  { day: "Fri", learning: 4.5, other: 2.8 },
  { day: "Sat", learning: 7.2, other: 0.9 },
  { day: "Sun", learning: 3.1, other: 1.5 },
];

const DEFAULT_FLASHCARDS = [
  { topic: "DSA", q: "What is the time complexity of QuickSort?", a: "O(n log n) average, O(n²) worst case", tag: "Algorithms" },
  { topic: "ML", q: "What does the kernel trick do in SVM?", a: "Maps data to higher dimensions implicitly without computing coordinates", tag: "Machine Learning" },
  { topic: "Web", q: "What is the Virtual DOM?", a: "A lightweight JS representation of the real DOM for efficient diffing", tag: "React" },
];

const DEFAULT_RECENT_SITES = [
  { name: "GeeksforGeeks", url: "geeksforgeeks.org", time: "2h 14m", type: "learning", topic: "DSA", icon: "G" },
  { name: "LeetCode", url: "leetcode.com", time: "1h 32m", type: "learning", topic: "DSA", icon: "L" },
  { name: "YouTube", url: "youtube.com", time: "0h 47m", type: "other", topic: "—", icon: "Y" },
  { name: "Towards Data Science", url: "towardsdatascience.com", time: "1h 05m", type: "learning", topic: "ML", icon: "T" },
  { name: "Reddit", url: "reddit.com", time: "0h 22m", type: "other", topic: "—", icon: "R" },
];

function useCountUp(target, duration = 1500) {
  const [val, setVal] = useState(0);
  useEffect(() => {
    let start = null;
    let frame;
    const step = (ts) => {
      if (!start) start = ts;
      const progress = Math.min((ts - start) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setVal(parseFloat((eased * target).toFixed(1)));
      if (progress < 1) { frame = requestAnimationFrame(step); }
    };
    frame = requestAnimationFrame(step);
    return () => cancelAnimationFrame(frame);
  }, [target, duration]);
  return val;
}

function RingChart({ pct, size = 120, stroke = 8, color = COLORS.accent, sublabel }) {
  const r = (size - stroke) / 2;
  const circ = 2 * Math.PI * r;
  const [animated, setAnimated] = useState(0);
  useEffect(() => {
    const timer = setTimeout(() => setAnimated(pct || 0), 300);
    return () => clearTimeout(timer);
  }, [pct]);
  const dash = (animated / 100) * circ;
  return (
    <div style={{ position: "relative", width: size, height: size, flexShrink: 0 }}>
      <svg width={size} height={size} style={{ transform: "rotate(-90deg)" }}>
        <circle cx={size/2} cy={size/2} r={r} fill="none" stroke={COLORS.border} strokeWidth={stroke} />
        <circle cx={size/2} cy={size/2} r={r} fill="none" stroke={color} strokeWidth={stroke}
          strokeDasharray={`${dash} ${circ}`} strokeLinecap="round"
          style={{ transition: "stroke-dasharray 1.2s cubic-bezier(0.34,1.56,0.64,1)", filter: `drop-shadow(0 0 5px ${color}88)` }}
        />
      </svg>
      <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>
        <span style={{ fontSize: 20, fontWeight: 800, color: COLORS.text, fontFamily: "'Space Mono', monospace" }}>
          {Math.round(animated)}%
        </span>
        {sublabel && (
          <span style={{ fontSize: 9, color: COLORS.textMuted, letterSpacing: 1, textTransform: "uppercase", marginTop: 2 }}>
            {sublabel}
          </span>
        )}
      </div>
    </div>
  );
}

function BarChart({ data }) {
  const weekData = data && data.length > 0 ? data : DEFAULT_WEEK_DATA;
  const maxH = weekData.reduce((m, d) => Math.max(m, d.learning, d.other), 1);
  return (
    <div style={{ display: "flex", alignItems: "flex-end", gap: 8, height: 120, padding: "0 4px" }}>
      {weekData.map((d, i) => (
        <div key={d.day + i} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: 3 }}>
          <div style={{ width: "100%", display: "flex", flexDirection: "column", alignItems: "center", gap: 2, height: 100 }}>
            <div style={{ flex: 1, width: "100%", display: "flex", flexDirection: "column", justifyContent: "flex-end", gap: 2 }}>
              <div style={{
                width: "100%", background: COLORS.green, borderRadius: "3px 3px 0 0",
                height: `${(d.learning / maxH) * 80}px`,
                boxShadow: `0 2px 8px ${COLORS.greenGlow}`,
                animation: `growUp 0.8s ${i * 0.08}s both cubic-bezier(0.34,1.56,0.64,1)`,
              }} />
              <div style={{
                width: "100%", background: COLORS.border, borderRadius: "3px 3px 0 0",
                height: `${(d.other / maxH) * 80}px`,
                animation: `growUp 0.8s ${i * 0.08 + 0.1}s both cubic-bezier(0.34,1.56,0.64,1)`,
              }} />
            </div>
            <span style={{ fontSize: 10, color: COLORS.textMuted, fontFamily: "'Space Mono', monospace" }}>{d.day}</span>
          </div>
        </div>
      ))}
    </div>
  );
}

function FlashCard({ card, active, onClick }) {
  const [flipped, setFlipped] = useState(false);
  return (
    <div onClick={() => { onClick(); setFlipped(!flipped); }}
      style={{ cursor: "pointer", perspective: 800, opacity: active ? 1 : 0.55, transform: active ? "scale(1)" : "scale(0.97)", transition: "all 0.3s ease" }}>
      <div style={{ position: "relative", height: 140, transformStyle: "preserve-3d", transform: flipped ? "rotateY(180deg)" : "rotateY(0)", transition: "transform 0.6s cubic-bezier(0.34,1.56,0.64,1)" }}>
        {/* Front */}
        <div style={{
          position: "absolute", inset: 0, backfaceVisibility: "hidden",
          background: COLORS.surface, border: `1.5px solid ${COLORS.border}`,
          borderRadius: 12, padding: 20,
          boxShadow: active ? `0 4px 24px ${COLORS.accentGlow}` : "0 1px 4px rgba(0,0,0,0.06)",
        }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
            <span style={{ fontSize: 10, color: COLORS.accent, letterSpacing: 2, textTransform: "uppercase", fontFamily: "'Space Mono', monospace" }}>{card.tag}</span>
            <span style={{ fontSize: 10, color: COLORS.textMuted }}>tap to reveal ↻</span>
          </div>
          <p style={{ fontSize: 14, color: COLORS.text, lineHeight: 1.5, margin: 0, fontFamily: "'Sora', sans-serif" }}>{card.q}</p>
        </div>
        {/* Back */}
        <div style={{
          position: "absolute", inset: 0, backfaceVisibility: "hidden", transform: "rotateY(180deg)",
          background: `linear-gradient(135deg, #EEF6FF, #F5F0FF)`,
          border: `1.5px solid ${COLORS.accent}33`, borderRadius: 12, padding: 20,
        }}>
          <div style={{ marginBottom: 8 }}>
            <span style={{ fontSize: 10, color: COLORS.green, letterSpacing: 2, textTransform: "uppercase", fontFamily: "'Space Mono', monospace" }}>Answer</span>
          </div>
          <p style={{ fontSize: 13, color: COLORS.text, lineHeight: 1.6, margin: 0, fontFamily: "'Sora', sans-serif" }}>{card.a}</p>
        </div>
      </div>
    </div>
  );
}

function NeuralBackground() {
  const canvasRef = useRef(null);
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const resize = () => { canvas.width = window.innerWidth; canvas.height = window.innerHeight; };
    resize();
    window.addEventListener("resize", resize);
    const nodes = Array.from({ length: 40 }, () => ({
      x: Math.random() * canvas.width, y: Math.random() * canvas.height,
      vx: (Math.random() - 0.5) * 0.3, vy: (Math.random() - 0.5) * 0.3,
      r: Math.random() * 2 + 1,
    }));
    let raf;
    const draw = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      nodes.forEach((n) => {
        n.x += n.vx; n.y += n.vy;
        if (n.x < 0 || n.x > canvas.width) n.vx *= -1;
        if (n.y < 0 || n.y > canvas.height) n.vy *= -1;
      });
      nodes.forEach((a, i) => {
        nodes.slice(i + 1).forEach((b) => {
          const dist = Math.hypot(a.x - b.x, a.y - b.y);
          if (dist < 180) {
            ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y);
            ctx.strokeStyle = `rgba(0,110,204,${0.06 * (1 - dist / 180)})`;
            ctx.lineWidth = 0.6; ctx.stroke();
          }
        });
        ctx.beginPath(); ctx.arc(a.x, a.y, a.r, 0, Math.PI * 2);
        ctx.fillStyle = "rgba(0,110,204,0.10)"; ctx.fill();
      });
      raf = requestAnimationFrame(draw);
    };
    draw();
    return () => { cancelAnimationFrame(raf); window.removeEventListener("resize", resize); };
  }, []);
  return <canvas ref={canvasRef} style={{ position: "fixed", inset: 0, pointerEvents: "none", zIndex: 0 }} />;
}

export default function FocusVaultDashboard() {
  const [activeCard, setActiveCard] = useState(0);
  const [activeTab, setActiveTab] = useState("overview");
  const [userId] = useState(1);

  const [summary, setSummary] = useState(null);
  const [daily, setDaily] = useState(null);
  const [weekly, setWeekly] = useState(null);
  const [topicsData, setTopicsData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [mlTestResult, setMlTestResult] = useState(null);
  const [mlError, setMlError] = useState(null);

  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true);
        const [summaryRes, dailyRes, weeklyRes, topicRes] = await Promise.all([
          api.getUserSummary(userId),
          api.getDailyAnalytics(userId),
          api.getWeeklyAnalytics(userId),
          api.getTopicAnalytics(userId),
        ]);
        setSummary(summaryRes.data);
        setDaily(dailyRes.data);
        setWeekly(weeklyRes.data);
        setTopicsData(topicRes.data);
      } catch (e) {
        console.error("Error loading dashboard data", e);
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, [userId]);

  const totalLearningHours = summary?.learning_time_hours || 0;
  const totalOtherHours = Math.max((summary?.total_time_hours || 0) - totalLearningHours, 0);
  const totalLearning = useCountUp(totalLearningHours);
  const totalOther = useCountUp(totalOtherHours);
  const streak = useCountUp(14, 1000);

  const learningPct = summary?.learning_percentage || 0;
  const todayFocusPct = daily?.learning_percentage ?? learningPct;

  const weeklyChartData =
    weekly && weekly.daily_stats
      ? Object.entries(weekly.daily_stats).map(([date, stats]) => {
          const d = new Date(date);
          const day = d.toLocaleDateString("en-US", { weekday: "short" });
          const learningH = +(stats.learning_time / 3600).toFixed(1);
          const otherH = +((stats.total_time - stats.learning_time) / 3600).toFixed(1);
          return { day, learning: learningH, other: otherH };
        })
      : DEFAULT_WEEK_DATA;

  const topics =
    topicsData && topicsData.topics && topicsData.topics.length > 0
      ? (() => {
          const totalSeconds = topicsData.topics.reduce((s, t) => s + (t.total_time || 0), 0) || 1;
          return topicsData.topics.slice(0, 5).map((t, idx) => {
            const style = TOPIC_STYLE_PRESETS[idx % TOPIC_STYLE_PRESETS.length];
            return { label: t.name, hours: +(t.total_time / 3600).toFixed(1), pct: Math.round((t.total_time / totalSeconds) * 100), color: style.color, icon: style.icon };
          });
        })()
      : DEFAULT_TOPICS;

  const flashcards = DEFAULT_FLASHCARDS;
  const recentSites = DEFAULT_RECENT_SITES;

  const runMlTest = async () => {
    try {
      setMlError(null); setMlTestResult(null);
      const res = await api.mlFullPredict({ title: "Binary Search Tree implementation in C++", domain: "geeksforgeeks.org", duration_seconds: 300, hour_of_day: 18 });
      setMlTestResult(res.data);
    } catch (e) {
      console.error("ML test failed", e);
      setMlError(e?.message || "Request failed");
    }
  };

  if (loading && !summary && !daily && !weekly) {
    return (
      <div style={{ minHeight: "100vh", background: COLORS.bg, color: COLORS.text, display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "'Sora', sans-serif" }}>
        Loading FocusVault dashboard...
      </div>
    );
  }

  return (
    <div style={{ minHeight: "100vh", background: COLORS.bg, color: COLORS.text, fontFamily: "'Sora', sans-serif", position: "relative", overflowX: "hidden" }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Sora:wght@300;400;500;600;700;800&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; }
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-track { background: ${COLORS.bg}; }
        ::-webkit-scrollbar-thumb { background: ${COLORS.border}; border-radius: 4px; }
        @keyframes growUp { from { transform: scaleY(0); transform-origin: bottom; } to { transform: scaleY(1); transform-origin: bottom; } }
        @keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.35; } }
        @keyframes slideIn { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes fadeGlow { 0%,100% { box-shadow: 0 2px 16px rgba(0,110,204,0.07); } 50% { box-shadow: 0 4px 32px rgba(0,110,204,0.16); } }
        .stat-card { animation: slideIn 0.6s both; }
        .stat-card:hover { transform: translateY(-3px) !important; transition: transform 0.2s ease !important; box-shadow: 0 8px 32px rgba(0,0,0,0.10) !important; }
        .site-row:hover { background: ${COLORS.surfaceAlt} !important; }
        .nav-tab { transition: all 0.2s ease; }
        .nav-tab:hover { color: ${COLORS.accent} !important; }
      `}</style>

      <NeuralBackground />

      <div style={{ position: "relative", zIndex: 1, maxWidth: 1280, margin: "0 auto", padding: "0 24px 48px" }}>

        {/* ── Header ── */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "28px 0 32px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
            <div style={{
              width: 42, height: 42, borderRadius: 12,
              background: `linear-gradient(135deg, ${COLORS.accent}, ${COLORS.purple})`,
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: 20, boxShadow: `0 4px 16px ${COLORS.accentGlow}`,
            }}>🧠</div>
            <div>
              <div style={{ fontSize: 22, fontWeight: 800, letterSpacing: -0.5, color: COLORS.text }}>
                Focus<span style={{ color: COLORS.accent }}>Vault</span>
              </div>
              <div style={{ fontSize: 11, color: COLORS.textMuted, letterSpacing: 1, textTransform: "uppercase", fontFamily: "'Space Mono', monospace" }}>
                Knowledge Tracker
              </div>
            </div>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <div
              style={{
                width: 38, height: 38, borderRadius: "50%",
                background: `linear-gradient(135deg, ${COLORS.purple}, ${COLORS.accent})`,
                display: "flex", alignItems: "center", justifyContent: "center",
                fontSize: 15, fontWeight: 700, border: `2px solid ${COLORS.border}`,
                color: "#fff",
              }}
            >F</div>
          </div>
        </div>

        {/* ── Stat Cards ── */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16, marginBottom: 16 }}>
          {[
            { label: "Learning Hours", value: `${totalLearning.toFixed(1)}h`, sub: "Total focused learning", color: COLORS.green, icon: "📚", glow: COLORS.greenGlow, delay: "0s" },
            { label: "Other Activity", value: `${totalOther.toFixed(1)}h`, sub: "Non-learning usage", color: COLORS.orange, icon: "🌐", glow: COLORS.orangeGlow, delay: "0.1s" },
            { label: "Focus Streak", value: `${Math.round(streak)} days`, sub: "Active learning days", color: COLORS.accent, icon: "🔥", glow: COLORS.accentGlow, delay: "0.2s" },
            { label: "Flashcards Due", value: "24", sub: "Ready for review", color: COLORS.purple, icon: "⚡", glow: COLORS.purpleGlow, delay: "0.3s" },
          ].map((s, i) => (
            <div key={i} className="stat-card" style={{
              background: COLORS.surface, border: `1.5px solid ${COLORS.border}`,
              borderRadius: 16, padding: "20px 22px", animationDelay: s.delay,
              position: "relative", overflow: "hidden",
              boxShadow: "0 2px 12px rgba(0,0,0,0.05)",
            }}>
              <div style={{ position: "absolute", top: -20, right: -20, width: 80, height: 80, borderRadius: "50%", background: s.glow, pointerEvents: "none" }} />
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                <div>
                  <div style={{ fontSize: 11, color: COLORS.textMuted, letterSpacing: 1, textTransform: "uppercase", marginBottom: 10, fontFamily: "'Space Mono', monospace" }}>{s.label}</div>
                  <div style={{ fontSize: 30, fontWeight: 800, color: s.color, letterSpacing: -1, fontFamily: "'Space Mono', monospace", lineHeight: 1 }}>{s.value}</div>
                  <div style={{ fontSize: 11, color: COLORS.textMuted, marginTop: 6 }}>{s.sub}</div>
                </div>
                <span style={{ fontSize: 24 }}>{s.icon}</span>
              </div>
            </div>
          ))}
        </div>

        {/* ── Main Grid ── */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 340px", gap: 16 }}>

          {/* LEFT */}
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>

            {/* Weekly Chart */}
            <div style={{ background: COLORS.surface, border: `1.5px solid ${COLORS.border}`, borderRadius: 16, padding: 24, boxShadow: "0 2px 12px rgba(0,0,0,0.04)" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
                <div>
                  <div style={{ fontSize: 15, fontWeight: 700, color: COLORS.text }}>Weekly Activity</div>
                  <div style={{ fontSize: 11, color: COLORS.textMuted, marginTop: 2 }}>Learning vs Other browsing</div>
                </div>
                <div style={{ display: "flex", gap: 16 }}>
                  {[{ c: COLORS.green, l: "Learning" }, { c: COLORS.border, l: "Other" }].map((x) => (
                    <div key={x.l} style={{ display: "flex", alignItems: "center", gap: 6 }}>
                      <div style={{ width: 8, height: 8, borderRadius: 2, background: x.c }} />
                      <span style={{ fontSize: 11, color: COLORS.textMuted }}>{x.l}</span>
                    </div>
                  ))}
                </div>
              </div>
              <BarChart data={weeklyChartData} />
            </div>

            {/* Topic Breakdown */}
            <div style={{ background: COLORS.surface, border: `1.5px solid ${COLORS.border}`, borderRadius: 16, padding: 24, boxShadow: "0 2px 12px rgba(0,0,0,0.04)" }}>
              <div style={{ fontSize: 15, fontWeight: 700, marginBottom: 6, color: COLORS.text }}>Topic Breakdown</div>
              <div style={{ fontSize: 11, color: COLORS.textMuted, marginBottom: 20 }}>AI-classified learning categories</div>
              <div style={{ display: "flex", gap: 24, alignItems: "center" }}>
                <RingChart pct={learningPct} size={130} color={COLORS.accent} sublabel="Learning" />
                <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 10 }}>
                  {topics.map((t, i) => (
                    <div key={i} style={{ display: "flex", alignItems: "center", gap: 10 }}>
                      <span style={{ fontSize: 14, width: 20, textAlign: "center" }}>{t.icon}</span>
                      <div style={{ flex: 1 }}>
                        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                          <span style={{ fontSize: 12, color: COLORS.text, fontWeight: 500 }}>{t.label}</span>
                          <span style={{ fontSize: 11, color: COLORS.textMuted, fontFamily: "'Space Mono', monospace" }}>{t.hours}h</span>
                        </div>
                        <div style={{ height: 4, background: COLORS.surfaceAlt, borderRadius: 2, overflow: "hidden", border: `1px solid ${COLORS.border}` }}>
                          <div style={{ height: "100%", width: `${t.pct}%`, background: t.color, borderRadius: 2, transition: "width 1.2s cubic-bezier(0.34,1.56,0.64,1)" }} />
                        </div>
                      </div>
                      <span style={{ fontSize: 11, color: t.color, fontFamily: "'Space Mono', monospace", width: 30, textAlign: "right", fontWeight: 700 }}>{t.pct}%</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Recent Sites */}
            <div style={{ background: COLORS.surface, border: `1.5px solid ${COLORS.border}`, borderRadius: 16, padding: 24, boxShadow: "0 2px 12px rgba(0,0,0,0.04)" }}>
              <div style={{ fontSize: 15, fontWeight: 700, marginBottom: 6, color: COLORS.text }}>Recent Activity</div>
              <div style={{ fontSize: 11, color: COLORS.textMuted, marginBottom: 16 }}>Today's browsing, ML-classified</div>
              <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                {recentSites.map((s, i) => (
                  <div key={i} className="site-row" style={{
                    display: "flex", alignItems: "center", gap: 12,
                    padding: "10px 12px", borderRadius: 10, cursor: "pointer",
                    transition: "background 0.2s ease",
                  }}>
                    <div style={{
                      width: 32, height: 32, borderRadius: 8, flexShrink: 0,
                      background: s.type === "learning" ? `${COLORS.green}18` : COLORS.surfaceAlt,
                      border: `1.5px solid ${s.type === "learning" ? COLORS.green + "55" : COLORS.border}`,
                      display: "flex", alignItems: "center", justifyContent: "center",
                      fontSize: 13, fontWeight: 700,
                      color: s.type === "learning" ? COLORS.green : COLORS.textMuted,
                      fontFamily: "'Space Mono', monospace",
                    }}>{s.icon}</div>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: 13, fontWeight: 500, color: COLORS.text }}>{s.name}</div>
                      <div style={{ fontSize: 11, color: COLORS.textMuted }}>{s.url}</div>
                    </div>
                    <div style={{ textAlign: "right" }}>
                      <div style={{ fontSize: 12, fontFamily: "'Space Mono', monospace", color: COLORS.text }}>{s.time}</div>
                      <div style={{ fontSize: 10, color: s.type === "learning" ? COLORS.green : COLORS.textMuted, marginTop: 2 }}>
                        {s.type === "learning" ? `✓ ${s.topic}` : "○ Other"}
                      </div>
                    </div>
                    <div style={{
                      width: 6, height: 6, borderRadius: "50%",
                      background: s.type === "learning" ? COLORS.green : COLORS.textDim,
                      boxShadow: s.type === "learning" ? `0 0 5px ${COLORS.green}88` : "none",
                      animation: s.type === "learning" ? "pulse 2s infinite" : "none",
                    }} />
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* RIGHT */}
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>

            {/* Focus Score */}
            <div style={{
              background: COLORS.surface, border: `1.5px solid ${COLORS.border}`,
              borderRadius: 16, padding: 24, textAlign: "center",
              boxShadow: "0 2px 12px rgba(0,0,0,0.04)",
              animation: "fadeGlow 3s infinite",
            }}>
              <div style={{ fontSize: 11, color: COLORS.textMuted, letterSpacing: 2, textTransform: "uppercase", marginBottom: 16, fontFamily: "'Space Mono', monospace" }}>
                Today's Focus Score
              </div>
              <div style={{ display: "flex", justifyContent: "center" }}>
                <RingChart pct={todayFocusPct} size={150} stroke={10} color={COLORS.accent} sublabel="Focus" />
              </div>
              <div style={{ marginTop: 16, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                {[
                  { l: "Productive", v: "4h 12m", c: COLORS.green },
                  { l: "Distracted", v: "1h 8m", c: COLORS.orange },
                ].map((x) => (
                  <div key={x.l} style={{ background: COLORS.surfaceAlt, borderRadius: 8, padding: "10px 12px", border: `1px solid ${COLORS.border}` }}>
                    <div style={{ fontSize: 10, color: COLORS.textMuted, letterSpacing: 1, textTransform: "uppercase", marginBottom: 4 }}>{x.l}</div>
                    <div style={{ fontSize: 16, fontWeight: 700, color: x.c, fontFamily: "'Space Mono', monospace" }}>{x.v}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* Flashcards */}
            <div style={{ background: COLORS.surface, border: `1.5px solid ${COLORS.border}`, borderRadius: 16, padding: 24, boxShadow: "0 2px 12px rgba(0,0,0,0.04)" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
                <div>
                  <div style={{ fontSize: 15, fontWeight: 700, color: COLORS.text }}>Flashcards</div>
                  <div style={{ fontSize: 11, color: COLORS.textMuted, marginTop: 2 }}>Tap to flip</div>
                </div>
                <div style={{
                  background: `${COLORS.purple}15`, border: `1.5px solid ${COLORS.purple}44`,
                  color: COLORS.purple, fontSize: 11, padding: "4px 10px", borderRadius: 6,
                  fontFamily: "'Space Mono', monospace", fontWeight: 700,
                }}>24 due</div>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {flashcards.map((c, i) => (
                  <FlashCard key={i} card={c} active={activeCard === i} onClick={() => setActiveCard(i)} />
                ))}
              </div>
              <button style={{
                width: "100%", marginTop: 14, padding: "11px",
                background: `linear-gradient(135deg, ${COLORS.accent}15, ${COLORS.purple}15)`,
                border: `1.5px solid ${COLORS.accent}55`, borderRadius: 10, cursor: "pointer",
                color: COLORS.accent, fontSize: 12, fontWeight: 600, letterSpacing: 0.5,
                fontFamily: "'Sora', sans-serif",
              }}>Start Review Session →</button>
            </div>

            {/* AI Insight */}
            <div style={{
              background: `linear-gradient(135deg, #EEF6FF, #F5F0FF)`,
              border: `1.5px solid ${COLORS.accent}33`,
              borderRadius: 16, padding: 20,
              boxShadow: "0 2px 12px rgba(0,110,204,0.06)",
            }}>
              <div style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
                <div style={{
                  width: 32, height: 32, borderRadius: 8, flexShrink: 0,
                  background: `${COLORS.accent}18`, border: `1.5px solid ${COLORS.accent}44`,
                  display: "flex", alignItems: "center", justifyContent: "center", fontSize: 16,
                }}>✦</div>
                <div>
                  <div style={{ fontSize: 12, fontWeight: 600, color: COLORS.accent, marginBottom: 6, letterSpacing: 0.5 }}>AI Insight</div>
                  <p style={{ fontSize: 12, color: COLORS.textMuted, lineHeight: 1.6, margin: 0 }}>
                    You spent{" "}
                    <span style={{ color: COLORS.green, fontWeight: 600 }}>more time</span>{" "}
                    on your top topic this week. Your peak focus window looks like{" "}
                    <span style={{ color: COLORS.accent, fontWeight: 600 }}>mornings</span>
                    . Consider scheduling your hardest topics then.
                  </p>
                </div>
              </div>
            </div>

          </div>
        </div>
      </div>
    </div>
  );
}