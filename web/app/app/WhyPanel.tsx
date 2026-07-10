"use client";

import { useState } from "react";
import { useApi } from "@/lib/api";
import { signalColor, type WhyResponse } from "@/lib/appTypes";

/** Lazily-loaded "Why this recommendation?" disclosure for the web Now hero. */
export default function WhyPanel({ taskId }: { taskId: string }) {
  const callApi = useApi();
  const [open, setOpen] = useState(false);
  const [why, setWhy] = useState<WhyResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function toggle() {
    const next = !open;
    setOpen(next);
    if (next && !why && !loading) {
      setLoading(true);
      setError(null);
      try {
        setWhy(await callApi<WhyResponse>(`/api/v1/now/why?task_id=${taskId}`));
      } catch (err) {
        setError(err instanceof Error ? err.message : "Couldn't load the explanation.");
      } finally {
        setLoading(false);
      }
    }
  }

  return (
    <div>
      <button
        onClick={toggle}
        aria-expanded={open}
        className="btn btn-ghost btn-sm"
        style={{ width: "100%", justifyContent: "space-between" }}
      >
        <span>✦ Why this recommendation?</span>
        <span style={{ transition: "transform .15s", transform: open ? "rotate(90deg)" : "none", opacity: 0.7 }}>›</span>
      </button>

      {open && (
        <div className="acard" style={{ marginTop: 10, display: "flex", flexDirection: "column", gap: 16 }}>
          {loading && <p className="muted" style={{ margin: 0 }}>Thinking it through…</p>}
          {error && <p style={{ color: "var(--amber)", margin: 0 }}>{error}</p>}
          {why && <WhyBody why={why} />}
        </div>
      )}
    </div>
  );
}

/** Presentational body — rendered inside the disclosure once the explanation loads. */
export function WhyBody({ why }: { why: WhyResponse }) {
  return (
    <>
      <p style={{ margin: 0, fontSize: 16, lineHeight: 1.6 }}>{why.summary}</p>

              {why.signals.length > 0 && (
                <Section label="Signals analysed">
                  <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                    {why.signals.map((s) => {
                      const color = s.available ? signalColor(s.name) : "var(--muted)";
                      return (
                        <div key={s.name} style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
                          <span
                            aria-hidden
                            style={{
                              flex: "none", marginTop: 2, width: 18, height: 18, borderRadius: 999,
                              display: "grid", placeItems: "center", fontSize: 11, color: "#fff",
                              background: s.available ? color : "transparent",
                              border: s.available ? "none" : "1px solid color-mix(in srgb, var(--muted) 60%, transparent)",
                            }}
                          >
                            {s.available ? "✓" : ""}
                          </span>
                          <div style={{ minWidth: 0 }}>
                            <span style={{ fontWeight: 600, color: s.available ? "var(--ink)" : "var(--muted)" }}>{s.name}</span>
                            <span className="muted"> — {s.detail}</span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </Section>
              )}

              {why.decision_factors.length > 0 && (
                <Section label="What tipped it">
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                    {why.decision_factors.map((f) => (
                      <span
                        key={f.name}
                        style={{
                          fontSize: 13, padding: "6px 12px", borderRadius: 999,
                          border: "1px solid var(--line)", color: "var(--ink)",
                        }}
                      >
                        {f.name}: <span className="muted">{f.rating}</span>
                      </span>
                    ))}
                  </div>
                </Section>
              )}

              {why.alternatives_considered.length > 0 && (
                <Section label="Also considered">
                  <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                    {why.alternatives_considered.map((a) => (
                      <div key={a.task_id} style={{ fontSize: 14 }}>
                        <span style={{ fontWeight: 600 }}>{a.title}</span>
                        <span className="muted"> — {a.reason_not_selected}</span>
                      </div>
                    ))}
                  </div>
                </Section>
              )}
    </>
  );
}

function Section({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="label" style={{ color: "var(--muted)", marginBottom: 10 }}>{label}</p>
      {children}
    </div>
  );
}
