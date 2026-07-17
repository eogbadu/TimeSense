"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ApiError, useApi } from "@/lib/api";

type ProviderId = "google" | "microsoft" | "gmail" | "slack";

interface Provider {
  id: ProviderId;
  name: string;
  color: string;
  blurb: string;
}

const PROVIDERS: Provider[] = [
  { id: "google", name: "Google Calendar", color: "var(--blue)", blurb: "Schedule around your Google events." },
  { id: "microsoft", name: "Outlook Calendar", color: "var(--cyan)", blurb: "Schedule around your Outlook / Microsoft events." },
  { id: "gmail", name: "Gmail", color: "var(--amber)", blurb: "Find tasks in recent emails — read-only, you approve each one." },
  { id: "slack", name: "Slack", color: "var(--violet)", blurb: "Turn Slack messages into tasks you can approve." },
];

export default function ConnectionsPage() {
  const callApi = useApi();
  const [connected, setConnected] = useState<Set<ProviderId>>(new Set());
  const [connecting, setConnecting] = useState<ProviderId | null>(null);
  const [banner, setBanner] = useState<{ kind: "ok" | "err"; text: string } | null>(null);

  // The OAuth callback returns here with ?status=connected&provider=… (or ?status=failed).
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const status = params.get("status");
    const provider = params.get("provider") as ProviderId | null;
    if (status === "connected" && provider) {
      setConnected((prev) => new Set(prev).add(provider));
      setBanner({ kind: "ok", text: `${label(provider)} connected.` });
    } else if (status === "failed") {
      setBanner({ kind: "err", text: "Couldn't connect. Please try again." });
    }
    if (status) window.history.replaceState({}, "", "/app/connections");
  }, []);

  async function connect(id: ProviderId) {
    setConnecting(id);
    setBanner(null);
    try {
      const { authorize_url } = await callApi<{ authorize_url: string }>(
        `/api/v1/integrations/${id}/authorize?platform=web`
      );
      window.location.href = authorize_url; // hand off to the provider consent screen
    } catch (err) {
      setConnecting(null);
      if (err instanceof ApiError && err.status === 403) {
        setBanner({ kind: "err", text: "Connecting apps is a Premium feature." });
      } else if (err instanceof ApiError && err.status === 503) {
        setBanner({ kind: "err", text: `${label(id)} isn’t configured on the server yet.` });
      } else {
        setBanner({ kind: "err", text: "Couldn’t start sign-in. Try again." });
      }
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div>
        <p className="label" style={{ color: "var(--blue)" }}>Connections</p>
        <h1 style={{ fontFamily: "var(--font-playfair), serif", fontSize: 34, fontWeight: 600, margin: "6px 0 0" }}>
          Connect your tools
        </h1>
        <p className="muted" style={{ margin: "8px 0 0", maxWidth: "58ch" }}>
          TimeSense only reads what it needs, and calendar changes always ask first.
        </p>
      </div>

      {banner && (
        <div className="acard" style={{ borderColor: banner.kind === "ok" ? "var(--green)" : "var(--amber)" }}>
          <span style={{ color: banner.kind === "ok" ? "var(--green)" : "var(--amber)" }}>{banner.text}</span>
        </div>
      )}

      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {PROVIDERS.map((p) => (
          <div key={p.id} className="acard" style={{ display: "flex", alignItems: "center", gap: 14 }}>
            <span aria-hidden style={{ width: 10, height: 10, borderRadius: 999, background: p.color, boxShadow: `0 0 10px ${p.color}`, flex: "none" }} />
            <div style={{ flex: 1, minWidth: 0 }}>
              <p style={{ margin: 0, fontWeight: 700 }}>{p.name}</p>
              <p className="muted" style={{ margin: "2px 0 0", fontSize: 13 }}>{p.blurb}</p>
              {p.id === "gmail" && connected.has("gmail") && (
                <Link href="/app/email" style={{ color: "var(--amber)", fontSize: 13, fontWeight: 600 }}>
                  Review email tasks →
                </Link>
              )}
            </div>
            {connected.has(p.id) ? (
              <span style={{ color: "var(--green)", fontWeight: 600, fontSize: 14, flex: "none" }}>✓ Connected</span>
            ) : (
              <button
                className="btn btn-primary btn-sm"
                style={{ flex: "none" }}
                onClick={() => connect(p.id)}
                disabled={connecting === p.id}
              >
                {connecting === p.id ? "Opening…" : "Connect"}
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function label(id: ProviderId): string {
  return PROVIDERS.find((p) => p.id === id)?.name ?? id;
}
