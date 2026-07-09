"use client";

import { useEffect, useState } from "react";
import { ApiError, useApi } from "@/lib/api";

interface WeeklyInsight {
  week_start: string;
  week_end: string;
  tasks_completed: number;
  tasks_total: number;
  completion_rate: number | null;
  most_skipped_meal: string | null;
  late_wake_count: number;
  commute_confirmed_count: number;
  feedback_done_count: number;
  feedback_not_now_count: number;
  summary_text: string;
}

export default function InsightsPage() {
  const callApi = useApi();
  const [insight, setInsight] = useState<WeeklyInsight | null>(null);
  const [gated, setGated] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    callApi<WeeklyInsight>("/api/v1/insights/weekly")
      .then(setInsight)
      .catch((err) => {
        if (err instanceof ApiError && err.status === 403) setGated(true);
        else setError(err instanceof Error ? err.message : "Couldn't load.");
      })
      .finally(() => setLoading(false));
  }, [callApi]);

  if (loading) return <p className="muted">Loading your insights…</p>;
  if (error) return <p style={{ color: "var(--amber)" }}>{error}</p>;
  if (gated) return <Gate />;
  if (!insight) return <p className="muted">Not enough data yet — check back after a few days.</p>;

  const rate = insight.completion_rate != null ? `${Math.round(insight.completion_rate * 100)}%` : "—";
  const stats = [
    { label: "Tasks completed", color: "var(--green)", value: `${insight.tasks_completed} of ${insight.tasks_total}` },
    { label: "Completion rate", color: "var(--blue)", value: rate },
    insight.most_skipped_meal ? { label: "Most skipped meal", color: "var(--amber)", value: cap(insight.most_skipped_meal) } : null,
    insight.late_wake_count > 0 ? { label: "Late wake-ups", color: "var(--violet)", value: String(insight.late_wake_count) } : null,
    insight.commute_confirmed_count > 0 ? { label: "Commutes tracked", color: "var(--cyan)", value: String(insight.commute_confirmed_count) } : null,
    { label: "Kept vs deferred", color: "var(--green)", value: `${insight.feedback_done_count} / ${insight.feedback_not_now_count}` },
  ].filter(Boolean) as { label: string; color: string; value: string }[];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <div>
        <p className="label" style={{ color: "var(--blue)" }}>
          {fmt(insight.week_start)} – {fmt(insight.week_end)}
        </p>
        <h1 style={{ fontFamily: "var(--font-playfair), serif", fontSize: 34, fontWeight: 600, margin: "6px 0 0" }}>Your week</h1>
      </div>

      <div className="acard">
        <p className="label" style={{ color: "var(--violet)", marginBottom: 8 }}>Summary</p>
        <p style={{ margin: 0, fontSize: 17, lineHeight: 1.55 }}>{insight.summary_text}</p>
      </div>

      <div className="grid2">
        {stats.map((s) => (
          <div className="acard" key={s.label}>
            <p className="label" style={{ color: s.color, marginBottom: 8 }}>{s.label}</p>
            <p className="val" style={{ color: s.color, margin: 0 }}>{s.value}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

function Gate() {
  const previews = [
    { title: "Best focus window", value: "9:30 AM – 11:00 AM", sub: "Usually your most productive time.", color: "var(--blue)", chart: <Line color="var(--blue)" /> },
    { title: "Pattern detected", value: "Errands often slip after 6 PM.", sub: null, color: "var(--amber)", chart: <Bars color="var(--amber)" /> },
    { title: "Schedule balance", value: "3.5 hrs open focus this week", sub: null, color: "var(--green)", chart: <Ring color="var(--green)" value={0.45} /> },
    { title: "Routine consistency", value: "Good", sub: "92% consistency this week", color: "var(--violet)", chart: <Ring color="var(--violet)" value={0.92} /> },
  ];
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
      <div style={{
        borderRadius: 20, padding: 22, color: "#fff",
        background: "linear-gradient(135deg, var(--blue), var(--violet))",
        boxShadow: "0 20px 44px -20px rgba(124,108,255,.6)",
        display: "flex", justifyContent: "space-between", alignItems: "center", gap: 16,
      }}>
        <div>
          <h1 style={{ fontSize: 24, fontWeight: 700, margin: "0 0 6px" }}>Your AI insights</h1>
          <p style={{ margin: 0, opacity: 0.92, maxWidth: 460, lineHeight: 1.5 }}>
            Unlock the patterns TimeSense finds — your best focus windows, routines, and where your days slip.
          </p>
        </div>
        <span style={{ fontSize: 22, background: "rgba(255,255,255,.18)", width: 44, height: 44, borderRadius: 999, display: "grid", placeItems: "center", flex: "none" }}>🔒</span>
      </div>

      {previews.map((p) => (
        <div className="acard" key={p.title} style={{ display: "flex", alignItems: "center", gap: 16, opacity: 0.92 }}>
          <div style={{ flex: 1, minWidth: 0 }}>
            <p className="label" style={{ color: p.color, marginBottom: 6 }}>{p.title}</p>
            <p style={{ margin: 0, fontWeight: 600, fontSize: 17 }}>{p.value}</p>
            {p.sub && <p className="muted" style={{ margin: "4px 0 0", fontSize: 13 }}>{p.sub}</p>}
          </div>
          <div style={{ flex: "none" }}>{p.chart}</div>
        </div>
      ))}

      <button className="btn btn-primary" style={{ justifyContent: "center", marginTop: 4 }}>
        Upgrade to Premium
      </button>
      <p className="muted" style={{ textAlign: "center", fontSize: 13, margin: 0 }}>
        Manage your subscription in the TimeSense mobile app.
      </p>
    </div>
  );
}

function Line({ color }: { color: string }) {
  return (
    <svg width="84" height="48" viewBox="0 0 84 48" aria-hidden>
      <polyline points="0,32 14,22 28,36 42,14 56,9 70,20 84,15" fill="none" stroke={color} strokeWidth="2.5" strokeLinejoin="round" strokeLinecap="round" />
    </svg>
  );
}
function Bars({ color }: { color: string }) {
  const hs = [0.4, 0.7, 1, 0.55, 0.85, 0.35];
  return (
    <svg width="84" height="48" viewBox="0 0 84 48" aria-hidden>
      {hs.map((h, i) => (
        <rect key={i} x={i * 14 + 3} y={48 - 46 * h} width="9" height={46 * h} rx="2" fill={color} opacity="0.85" />
      ))}
    </svg>
  );
}
function Ring({ color, value }: { color: string; value: number }) {
  const r = 20;
  const c = 2 * Math.PI * r;
  return (
    <svg width="56" height="56" viewBox="0 0 56 56" aria-hidden>
      <circle cx="28" cy="28" r={r} fill="none" stroke={color} strokeWidth="7" opacity="0.18" />
      <circle cx="28" cy="28" r={r} fill="none" stroke={color} strokeWidth="7" strokeLinecap="round"
        strokeDasharray={c} strokeDashoffset={c * (1 - value)} transform="rotate(-90 28 28)" />
    </svg>
  );
}

function cap(s: string) {
  return s.charAt(0).toUpperCase() + s.slice(1);
}
function fmt(iso: string) {
  return new Date(iso).toLocaleDateString([], { month: "short", day: "numeric" });
}
