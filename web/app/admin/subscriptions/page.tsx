"use client";

import { useEffect, useState } from "react";
import { useAdminApi } from "@/lib/api";

interface AdminSubscriptionSummary {
  user_id: string;
  email: string;
  platform: string;
  status: string;
  plan: string | null;
  trial_end: string | null;
  current_period_end: string | null;
  cancel_at_period_end: boolean;
}

interface AdminSubscriptionListResponse {
  subscriptions: AdminSubscriptionSummary[];
  offset: number;
  limit: number;
}

export default function AdminSubscriptionsPage() {
  const callApi = useAdminApi();
  const [data, setData] = useState<AdminSubscriptionListResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    callApi<AdminSubscriptionListResponse>("/api/v1/admin/subscriptions")
      .then(setData)
      .catch((err) => setError(err.message ?? "Couldn't load subscriptions."))
      .finally(() => setLoading(false));
  }, [callApi]);

  if (loading) return <p className="text-sm text-neutral-500">Loading…</p>;
  if (error) return <p className="text-sm text-red-600">{error}</p>;

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-xl font-semibold">Subscriptions</h1>
      {data && data.subscriptions.length === 0 ? (
        <p className="text-sm text-neutral-500">No subscriptions yet.</p>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-neutral-500">
              <th className="pb-2 font-medium">Email</th>
              <th className="pb-2 font-medium">Platform</th>
              <th className="pb-2 font-medium">Status</th>
              <th className="pb-2 font-medium">Plan</th>
              <th className="pb-2 font-medium">Trial ends</th>
              <th className="pb-2 font-medium">Cancels at period end</th>
            </tr>
          </thead>
          <tbody>
            {data?.subscriptions.map((s) => (
              <tr key={s.user_id} className="border-t border-neutral-200 dark:border-neutral-800">
                <td className="py-2">{s.email}</td>
                <td className="py-2 capitalize">{s.platform}</td>
                <td className="py-2 capitalize">{s.status}</td>
                <td className="py-2">{s.plan ?? "—"}</td>
                <td className="py-2">
                  {s.trial_end ? new Date(s.trial_end).toLocaleDateString() : "—"}
                </td>
                <td className="py-2">{s.cancel_at_period_end ? "Yes" : "No"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
