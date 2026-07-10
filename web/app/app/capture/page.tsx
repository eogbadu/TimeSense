"use client";

import { useState } from "react";
import { useApi } from "@/lib/api";
import type { TaskResponse } from "@/lib/appTypes";

const CHIPS: { label: string; color: string }[] = [
  { label: "Task", color: "var(--blue)" },
  { label: "Reminder", color: "var(--amber)" },
  { label: "Schedule", color: "var(--violet)" },
  { label: "Errand", color: "var(--cyan)" },
  { label: "Idea", color: "var(--green)" },
];

export default function CapturePage() {
  const callApi = useApi();
  const [text, setText] = useState("");
  const [hint, setHint] = useState<string | null>(null);
  const [state, setState] = useState<"idle" | "loading" | "error">("idle");
  const [captured, setCaptured] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    const raw = text.trim();
    if (!raw) return;
    setState("loading");
    setError(null);
    try {
      const task = await callApi<TaskResponse>("/api/v1/capture", {
        method: "POST",
        body: JSON.stringify({
          raw_input: raw,
          user_timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
          type_hint: hint,
        }),
      });
      setCaptured(task.title);
      setText("");
      setHint(null);
      setState("idle");
      setTimeout(() => setCaptured(null), 4000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Capture failed.");
      setState("error");
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 18, maxWidth: 560, margin: "0 auto" }}>
      <div style={{ textAlign: "center" }}>
        <h1 style={{ fontFamily: "var(--font-playfair), serif", fontSize: 32, fontWeight: 600, margin: "8px 0 6px" }}>
          What’s on your mind?
        </h1>
        <p className="muted">Type it naturally — “call the dentist tomorrow at 2pm.” TimeSense turns it into a plan.</p>
      </div>

      <textarea
        className="field"
        rows={3}
        maxLength={2000}
        placeholder="e.g. Pick up groceries after work"
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          if ((e.metaKey || e.ctrlKey) && e.key === "Enter") submit();
        }}
      />

      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        {CHIPS.map((chip) => {
          const on = hint === chip.label;
          return (
            <button
              key={chip.label}
              onClick={() => setHint(on ? null : chip.label)}
              style={{
                cursor: "pointer",
                fontSize: 14,
                fontWeight: 500,
                padding: "8px 14px",
                borderRadius: 999,
                color: on ? "#fff" : chip.color,
                background: on ? chip.color : `color-mix(in srgb, ${chip.color} 14%, transparent)`,
                border: `1px solid ${on ? "transparent" : `color-mix(in srgb, ${chip.color} 50%, transparent)`}`,
              }}
            >
              {chip.label}
            </button>
          );
        })}
      </div>

      <button className="btn btn-primary" onClick={submit} disabled={state === "loading" || !text.trim()} style={{ justifyContent: "center" }}>
        {state === "loading" ? "Capturing…" : "Capture"}
      </button>

      {captured && (
        <p style={{ color: "var(--green)", textAlign: "center" }}>✓ Captured “{captured}”</p>
      )}
      {error && <p style={{ color: "var(--amber)", textAlign: "center" }}>{error}</p>}
    </div>
  );
}
