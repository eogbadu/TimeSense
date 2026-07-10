"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { useApi } from "@/lib/api";
import { accentFor, priorityLabel, type NowResponse } from "@/lib/appTypes";
import WhyPanel from "./WhyPanel";

export default function NowPage() {
  const callApi = useApi();
  const [now, setNow] = useState<NowResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [agreedFor, setAgreedFor] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setNow(await callApi<NowResponse>("/api/v1/now"));
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't load.");
    } finally {
      setLoading(false);
    }
  }, [callApi]);

  useEffect(() => {
    load();
  }, [load]);

  async function markDone(id: string) {
    setBusy(true);
    try {
      await callApi(`/api/v1/tasks/${id}`, { method: "PATCH", body: JSON.stringify({ status: "done" }) });
      await load();
    } finally {
      setBusy(false);
    }
  }

  async function sendFeedback(id: string, signal: string, snoozeUntil?: string) {
    await callApi("/api/v1/recommendations/feedback", {
      method: "POST",
      body: JSON.stringify({
        task_id: id,
        signal,
        snooze_until: snoozeUntil ?? null,
        recommendation_event_id: now?.recommendation_event_id ?? null,
      }),
    });
  }

  // Agree: record it and reveal Done/Snooze in place (no reload — stay on the same recommendation).
  async function agree(id: string) {
    setAgreedFor(id);
    try {
      await sendFeedback(id, "agree");
    } catch {
      /* keep the revealed buttons; the signal is best-effort */
    }
  }

  // Disagree: record it and reload so a different (demoted, not hidden) action surfaces.
  async function disagree(id: string) {
    setBusy(true);
    try {
      await sendFeedback(id, "disagree");
      setAgreedFor(null);
      await load();
    } finally {
      setBusy(false);
    }
  }

  async function snooze(id: string) {
    setBusy(true);
    try {
      await sendFeedback(id, "snooze", new Date(Date.now() + 3 * 3600 * 1000).toISOString());
      setAgreedFor(null);
      await load();
    } finally {
      setBusy(false);
    }
  }

  if (loading) return <p className="muted">Loading your day…</p>;
  if (error) return <p style={{ color: "var(--amber)" }}>{error}</p>;
  if (!now) return null;

  const task = now.best_task;
  const c = now.context;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 22 }}>
      <div>
        <p className="label" style={{ color: "var(--blue)" }}>{now.greeting}</p>
        <h1 style={{ fontFamily: "var(--font-playfair), serif", fontSize: 34, fontWeight: 600, margin: "6px 0 0" }}>
          Your best next step
        </h1>
      </div>

      {task ? (
        (() => {
          const a = accentFor(task.title);
          return (
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <div className="hero-card">
              <div
                className="top"
                style={{
                  background: `radial-gradient(240px 200px at 100% 0%, color-mix(in srgb, ${a.color} 55%, transparent), transparent 70%), linear-gradient(150deg, #0e162a, #090d1b)`,
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span className="hpill">✦ Best next action</span>
                  {now.confidence != null && (
                    <span className="hpill">{Math.round(now.confidence * 100)}% confident</span>
                  )}
                </div>
                <h2 style={{ maxWidth: 460 }}>{task.title}</h2>
                {task.estimated_minutes != null && (
                  <p style={{ color: "rgba(255,255,255,.82)", margin: 0, fontSize: 18 }}>
                    for {task.estimated_minutes} minutes
                  </p>
                )}
                <div style={{ display: "flex", gap: 8, marginTop: 16, flexWrap: "wrap" }}>
                  <span className="hpill" style={{ background: `color-mix(in srgb, ${a.color} 30%, transparent)` }}>
                    {a.icon} {a.label}
                  </span>
                  {task.priority <= 2 && <span className="hpill">🚩 {priorityLabel(task.priority)}</span>}
                </div>
              </div>
              <div className="foot">
                {agreedFor === task.id ? (
                  <>
                    <button className="btn btn-primary btn-sm" disabled={busy} onClick={() => markDone(task.id)}>
                      {busy ? "…" : "✓ Done"}
                    </button>
                    <button className="btn btn-ghost btn-sm" disabled={busy} onClick={() => snooze(task.id)}>
                      Snooze
                    </button>
                  </>
                ) : (
                  <>
                    <button className="btn btn-primary btn-sm" disabled={busy} onClick={() => agree(task.id)}>
                      👍 Agree
                    </button>
                    <button className="btn btn-ghost btn-sm" disabled={busy} onClick={() => disagree(task.id)}>
                      👎 Disagree
                    </button>
                  </>
                )}
              </div>
            </div>
            <WhyPanel taskId={task.id} />
            </div>
          );
        })()
      ) : (
        <div className="acard">
          <p style={{ fontWeight: 600, margin: "0 0 6px" }}>You’re all caught up ✨</p>
          <p className="muted" style={{ margin: 0 }}>
            Nothing needs you right now. <Link href="/app/capture" style={{ color: "var(--blue)" }}>Capture a task</Link> and
            TimeSense will tell you what to do next.
          </p>
        </div>
      )}

      {c && (
        <div className="grid2">
          {c.next_event_title && (
            <ContextCard label="Calendar" color="var(--blue)"
              value={c.next_event_at ? new Date(c.next_event_at).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" }) : "—"}
              sub={c.next_event_title} />
          )}
          <ContextCard label="Tasks" color="var(--violet)" value={String(c.tasks_due_today)}
            sub={`due today · ${c.tasks_completed_today} done`} />
          {c.steps != null && (
            <ContextCard label="Steps" color="var(--blue)" value={c.steps.toLocaleString()} sub={`of ${c.steps_goal.toLocaleString()} goal`} />
          )}
          {c.energy_level && (
            <ContextCard label="Energy" color="var(--green)" value={cap(c.energy_level)}
              sub={c.sleep_hours ? `${c.sleep_hours}h last night` : "from your sleep"} />
          )}
        </div>
      )}
    </div>
  );
}

function ContextCard({ label, color, value, sub }: { label: string; color: string; value: string; sub: string }) {
  return (
    <div className="acard">
      <p className="label" style={{ color, marginBottom: 8 }}>{label}</p>
      <p className="val" style={{ color, margin: 0 }}>{value}</p>
      <p className="muted" style={{ fontSize: 13, margin: "4px 0 0" }}>{sub}</p>
    </div>
  );
}

function cap(s: string) {
  return s.charAt(0).toUpperCase() + s.slice(1);
}
