"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { ApiError, useApi } from "@/lib/api";

interface EmailItem {
  id: string;
  subject: string;
  sender: string | null;
  detected_title: string;
  status: string;
}

export default function EmailTasksPage() {
  const callApi = useApi();
  const [hasConsent, setHasConsent] = useState<boolean | null>(null);
  const [items, setItems] = useState<EmailItem[]>([]);
  const [scanning, setScanning] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [notConnected, setNotConnected] = useState(false);

  const reloadPending = useCallback(async () => {
    try {
      setItems(await callApi<EmailItem[]>("/api/v1/email/pending"));
    } catch {
      /* leave the list as-is */
    }
  }, [callApi]);

  useEffect(() => {
    callApi<{ consents: Record<string, boolean> }>("/api/v1/consent/")
      .then((c) => setHasConsent(!!c.consents.email_content))
      .catch(() => setHasConsent(false));
    reloadPending();
  }, [callApi, reloadPending]);

  async function grantConsent() {
    setNotice(null);
    try {
      await callApi("/api/v1/consent/", {
        method: "POST",
        body: JSON.stringify({ consent_type: "email_content", granted: true }),
      });
      setHasConsent(true);
    } catch {
      setNotice("Couldn’t save your choice. Try again.");
    }
  }

  async function scan() {
    setNotice(null);
    setNotConnected(false);
    setScanning(true);
    try {
      await callApi("/api/v1/email/scan", { method: "POST", body: JSON.stringify({}) });
      await reloadPending();
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) setNotConnected(true);
      else if (err instanceof ApiError && err.status === 403) { setHasConsent(false); setNotice("Email access isn’t allowed yet."); }
      else setNotice("Couldn’t scan right now. Try again.");
    } finally {
      setScanning(false);
    }
  }

  async function decide(id: string, action: "confirm" | "reject") {
    try {
      await callApi(`/api/v1/email/actions/${id}/${action}`, { method: "POST", body: JSON.stringify({}) });
    } catch {
      setNotice("Couldn’t update that item. Try again.");
    }
    await reloadPending();
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div>
        <p className="label" style={{ color: "var(--amber)" }}>Email tasks</p>
        <h1 style={{ fontFamily: "var(--font-playfair), serif", fontSize: 34, fontWeight: 600, margin: "6px 0 0" }}>
          Tasks from your email
        </h1>
        <p className="muted" style={{ margin: "8px 0 0", maxWidth: "58ch" }}>
          TimeSense reads recent unread emails (subject and preview only) to suggest tasks. You approve
          each one — nothing is saved unless you do.
        </p>
      </div>

      {notice && (
        <div className="acard" style={{ borderColor: "var(--amber)" }}>
          <span style={{ color: "var(--amber)" }}>{notice}</span>
        </div>
      )}

      {notConnected ? (
        <div className="acard">
          <p style={{ margin: 0 }}>Connect Gmail first to scan for tasks.</p>
          <Link href="/app/connections" className="btn btn-primary btn-sm" style={{ marginTop: 12 }}>
            Go to Connections
          </Link>
        </div>
      ) : hasConsent === false ? (
        <div className="acard" style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <p style={{ margin: 0, fontWeight: 700 }}>Allow email access</p>
          <p className="muted" style={{ margin: 0, fontSize: 14 }}>
            We only read recent unread messages — the subject and a short preview, never the full
            email, and never to send anything.
          </p>
          <button className="btn btn-primary btn-sm" style={{ alignSelf: "flex-start" }} onClick={grantConsent}>
            Allow &amp; continue
          </button>
        </div>
      ) : hasConsent === null ? (
        <p className="muted">Loading…</p>
      ) : (
        <>
          <button className="btn btn-primary btn-sm" style={{ alignSelf: "flex-start" }} onClick={scan} disabled={scanning}>
            {scanning ? "Scanning…" : "Scan for tasks"}
          </button>

          {items.length === 0 ? (
            <p className="muted">No detected tasks yet — tap “Scan for tasks” to check your recent email.</p>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {items.map((it) => (
                <div key={it.id} className="acard" style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  <p style={{ margin: 0, fontWeight: 700 }}>{it.detected_title}</p>
                  <p className="muted" style={{ margin: 0, fontSize: 13 }}>
                    {it.subject} · {it.sender ?? "Unknown sender"}
                  </p>
                  <div style={{ display: "flex", gap: 10 }}>
                    <button className="btn btn-primary btn-sm" onClick={() => decide(it.id, "confirm")}>Add task</button>
                    <button className="btn btn-ghost btn-sm" onClick={() => decide(it.id, "reject")}>Dismiss</button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
