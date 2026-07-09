"use client";

import { useEffect, useState } from "react";
import { useApi } from "@/lib/api";
import { accentFor, type TaskResponse } from "@/lib/appTypes";

function localDate(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function timeLine(t: TaskResponse): string {
  if (t.scheduled_start) {
    const s = new Date(t.scheduled_start).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
    return t.estimated_minutes ? `${s} · ${t.estimated_minutes} min` : s;
  }
  if (t.estimated_minutes) return `Anytime · ${t.estimated_minutes} min`;
  return "Anytime";
}

export default function TodayPage() {
  const callApi = useApi();
  const [tasks, setTasks] = useState<TaskResponse[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    callApi<TaskResponse[]>(`/api/v1/timeline/today?date=${localDate()}`)
      .then(setTasks)
      .catch((err) => setError(err instanceof Error ? err.message : "Couldn't load."));
  }, [callApi]);

  if (error) return <p style={{ color: "var(--amber)" }}>{error}</p>;
  if (!tasks) return <p className="muted">Loading your day…</p>;

  const sorted = [...tasks].sort((a, b) => {
    const av = a.scheduled_start ?? "￿";
    const bv = b.scheduled_start ?? "￿";
    return av < bv ? -1 : av > bv ? 1 : 0;
  });

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      <div style={{ marginBottom: 8 }}>
        <p className="label" style={{ color: "var(--blue)" }}>
          {new Date().toLocaleDateString([], { weekday: "long", month: "long", day: "numeric" })}
        </p>
        <h1 style={{ fontFamily: "var(--font-playfair), serif", fontSize: 34, fontWeight: 600, margin: "6px 0 0" }}>
          Today’s plan
        </h1>
      </div>

      {sorted.length === 0 ? (
        <div className="acard">
          <p style={{ margin: 0 }} className="muted">Your day is open. Capture a task and TimeSense will plan it in.</p>
        </div>
      ) : (
        <div className="acard" style={{ padding: "4px 16px" }}>
          {sorted.map((t) => {
            const a = accentFor(t.title);
            const done = t.status === "done";
            return (
              <div className="row-item" key={t.id} style={{ opacity: done ? 0.55 : 1 }}>
                <span style={{ width: 32, height: 32, borderRadius: 9, display: "grid", placeItems: "center",
                  background: `color-mix(in srgb, ${a.color} 16%, transparent)`, fontSize: 15 }}>{done ? "✓" : a.icon}</span>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <p style={{ margin: 0, fontWeight: 600, textDecoration: done ? "line-through" : "none" }}>{t.title}</p>
                  <p className="muted" style={{ margin: "2px 0 0", fontSize: 13 }}>{timeLine(t)}</p>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
