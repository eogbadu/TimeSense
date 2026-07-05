"use client";

import { useEffect, useState } from "react";
import { useAdminApi } from "@/lib/api";

interface AdminUserSummary {
  id: string;
  email: string;
  role: string;
  is_active: boolean;
  onboarding_complete: boolean;
  created_at: string;
}

interface AdminUserListResponse {
  users: AdminUserSummary[];
  total: number;
  offset: number;
  limit: number;
}

const PAGE_SIZE = 25;

export default function AdminUsersPage() {
  const callApi = useAdminApi();
  const [search, setSearch] = useState("");
  const [offset, setOffset] = useState(0);
  const [data, setData] = useState<AdminUserListResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  // Derived rather than a separate boolean: no data yet and no error means still loading.
  // Subsequent searches/pages just replace `data` once ready, without a re-loading flash.
  const loading = data === null && error === null;

  useEffect(() => {
    const params = new URLSearchParams({
      offset: String(offset),
      limit: String(PAGE_SIZE),
    });
    if (search) params.set("search", search);

    callApi<AdminUserListResponse>(`/api/v1/admin/users?${params.toString()}`)
      .then((result) => {
        setError(null);
        setData(result);
      })
      .catch((err) => setError(err.message ?? "Couldn't load users."));
  }, [callApi, search, offset]);

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-xl font-semibold">Users</h1>
      <input
        type="search"
        placeholder="Search by email…"
        value={search}
        onChange={(e) => {
          setOffset(0);
          setSearch(e.target.value);
        }}
        className="w-72 rounded border border-neutral-300 px-3 py-2 text-sm dark:border-neutral-700 dark:bg-neutral-900"
      />

      {loading && <p className="text-sm text-neutral-500">Loading…</p>}
      {error && <p className="text-sm text-red-600">{error}</p>}

      {!loading && !error && data && (
        <>
          {data.users.length === 0 ? (
            <p className="text-sm text-neutral-500">No users match this search.</p>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-neutral-500">
                  <th className="pb-2 font-medium">Email</th>
                  <th className="pb-2 font-medium">Role</th>
                  <th className="pb-2 font-medium">Active</th>
                  <th className="pb-2 font-medium">Onboarded</th>
                  <th className="pb-2 font-medium">Joined</th>
                </tr>
              </thead>
              <tbody>
                {data.users.map((u) => (
                  <tr key={u.id} className="border-t border-neutral-200 dark:border-neutral-800">
                    <td className="py-2">{u.email}</td>
                    <td className="py-2">{u.role}</td>
                    <td className="py-2">{u.is_active ? "Yes" : "No"}</td>
                    <td className="py-2">{u.onboarding_complete ? "Yes" : "No"}</td>
                    <td className="py-2">{new Date(u.created_at).toLocaleDateString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <div className="flex items-center gap-3 text-sm text-neutral-500">
            <button
              onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
              disabled={offset === 0}
              className="underline underline-offset-2 disabled:opacity-40"
            >
              Previous
            </button>
            <span>
              {offset + 1}–{Math.min(offset + PAGE_SIZE, data.total)} of {data.total}
            </span>
            <button
              onClick={() => setOffset(offset + PAGE_SIZE)}
              disabled={offset + PAGE_SIZE >= data.total}
              className="underline underline-offset-2 disabled:opacity-40"
            >
              Next
            </button>
          </div>
        </>
      )}
    </div>
  );
}
