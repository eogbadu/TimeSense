"use client";

import { useCallback, useEffect, useState } from "react";
import { useAdminApi } from "@/lib/api";

interface InviteCode {
  id: string;
  code: string;
  max_uses: number;
  uses: number;
  is_active: boolean;
  expires_at: string | null;
  note: string | null;
}

interface WaitlistEntry {
  id: string;
  email: string;
  status: string;
  position: number;
  created_at: string;
}

export default function AdminInvitesPage() {
  const callApi = useAdminApi();
  const [codes, setCodes] = useState<InviteCode[] | null>(null);
  const [waitlist, setWaitlist] = useState<WaitlistEntry[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState("");
  const [maxUses, setMaxUses] = useState(1);
  const [creating, setCreating] = useState(false);
  // Derived rather than a separate boolean — see users/page.tsx for the same pattern.
  const loading = codes === null && error === null;

  const refresh = useCallback(() => {
    Promise.all([
      callApi<InviteCode[]>("/api/v1/invites/codes"),
      callApi<WaitlistEntry[]>("/api/v1/admin/waitlist"),
    ])
      .then(([c, w]) => {
        setError(null);
        setCodes(c);
        setWaitlist(w);
      })
      .catch((err) => setError(err.message ?? "Couldn't load invites."));
  }, [callApi]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function handleCreate(event: React.FormEvent) {
    event.preventDefault();
    setCreating(true);
    try {
      await callApi("/api/v1/invites/codes", {
        method: "POST",
        body: JSON.stringify({ max_uses: maxUses, note: note || null }),
      });
      setNote("");
      setMaxUses(1);
      refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't create invite code.");
    } finally {
      setCreating(false);
    }
  }

  async function handleDisable(code: string) {
    await callApi(`/api/v1/invites/codes/${code}`, { method: "DELETE" });
    refresh();
  }

  if (loading) return <p className="text-sm text-neutral-500">Loading…</p>;
  if (error) return <p className="text-sm text-red-600">{error}</p>;

  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="mb-4 text-xl font-semibold">Invite Codes</h1>
        <form onSubmit={handleCreate} className="mb-4 flex items-end gap-3">
          <label className="flex flex-col text-sm">
            Max uses
            <input
              type="number"
              min={0}
              value={maxUses}
              onChange={(e) => setMaxUses(Number(e.target.value))}
              className="w-24 rounded border border-neutral-300 px-2 py-1 dark:border-neutral-700 dark:bg-neutral-900"
            />
          </label>
          <label className="flex flex-col text-sm">
            Note (optional)
            <input
              type="text"
              value={note}
              onChange={(e) => setNote(e.target.value)}
              className="w-56 rounded border border-neutral-300 px-2 py-1 dark:border-neutral-700 dark:bg-neutral-900"
            />
          </label>
          <button
            type="submit"
            disabled={creating}
            className="rounded bg-neutral-900 px-3 py-2 text-sm font-medium text-white disabled:opacity-50 dark:bg-white dark:text-neutral-900"
          >
            {creating ? "Creating…" : "Create code"}
          </button>
        </form>

        {codes && codes.length === 0 ? (
          <p className="text-sm text-neutral-500">No active invite codes.</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-neutral-500">
                <th className="pb-2 font-medium">Code</th>
                <th className="pb-2 font-medium">Uses</th>
                <th className="pb-2 font-medium">Note</th>
                <th className="pb-2 font-medium"></th>
              </tr>
            </thead>
            <tbody>
              {codes?.map((c) => (
                <tr key={c.id} className="border-t border-neutral-200 dark:border-neutral-800">
                  <td className="py-2 font-mono">{c.code}</td>
                  <td className="py-2">
                    {c.uses} / {c.max_uses === 0 ? "∞" : c.max_uses}
                  </td>
                  <td className="py-2 text-neutral-500">{c.note ?? "—"}</td>
                  <td className="py-2">
                    <button
                      onClick={() => handleDisable(c.code)}
                      className="text-red-600 underline underline-offset-2"
                    >
                      Disable
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div>
        <h2 className="mb-3 text-sm font-semibold uppercase text-neutral-500">Waitlist</h2>
        {waitlist && waitlist.length === 0 ? (
          <p className="text-sm text-neutral-500">Nobody is waiting.</p>
        ) : (
          <table className="w-full max-w-lg text-sm">
            <thead>
              <tr className="text-left text-neutral-500">
                <th className="pb-2 font-medium">#</th>
                <th className="pb-2 font-medium">Email</th>
                <th className="pb-2 font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {waitlist?.map((entry) => (
                <tr key={entry.id} className="border-t border-neutral-200 dark:border-neutral-800">
                  <td className="py-2">{entry.position}</td>
                  <td className="py-2">{entry.email}</td>
                  <td className="py-2">{entry.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
