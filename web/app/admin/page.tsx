"use client";

import { useEffect, useState } from "react";
import { useAdminApi } from "@/lib/api";

interface MetricsResponse {
  total_users: number;
  active_subscriptions: number;
  trialing_subscriptions: number;
  waitlist_count: number;
  active_invite_codes: number;
  calendar_integrations_connected: number;
}

interface IntegrationProviderStatus {
  provider: string;
  active_count: number;
  inactive_count: number;
}

interface IntegrationStatusResponse {
  providers: IntegrationProviderStatus[];
}

export default function AdminOverviewPage() {
  const callApi = useAdminApi();
  const [metrics, setMetrics] = useState<MetricsResponse | null>(null);
  const [integrations, setIntegrations] = useState<IntegrationStatusResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      callApi<MetricsResponse>("/api/v1/admin/metrics"),
      callApi<IntegrationStatusResponse>("/api/v1/admin/integrations"),
    ])
      .then(([m, i]) => {
        setMetrics(m);
        setIntegrations(i);
      })
      .catch((err) => setError(err.message ?? "Couldn't load metrics."))
      .finally(() => setLoading(false));
  }, [callApi]);

  if (loading) return <p className="text-sm text-neutral-500">Loading…</p>;
  if (error) return <p className="text-sm text-red-600">{error}</p>;
  if (!metrics) return null;

  const cards = [
    { label: "Total users", value: metrics.total_users },
    { label: "Active subscriptions", value: metrics.active_subscriptions },
    { label: "Trialing", value: metrics.trialing_subscriptions },
    { label: "Waitlist", value: metrics.waitlist_count },
    { label: "Active invite codes", value: metrics.active_invite_codes },
    { label: "Calendars connected", value: metrics.calendar_integrations_connected },
  ];

  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="mb-4 text-xl font-semibold">Overview</h1>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
          {cards.map((card) => (
            <div
              key={card.label}
              className="rounded-lg border border-neutral-200 p-4 dark:border-neutral-800"
            >
              <p className="text-2xl font-semibold">{card.value}</p>
              <p className="text-sm text-neutral-500">{card.label}</p>
            </div>
          ))}
        </div>
      </div>

      {integrations && (
        <div>
          <h2 className="mb-3 text-sm font-semibold uppercase text-neutral-500">
            Integration status
          </h2>
          {integrations.providers.length === 0 ? (
            <p className="text-sm text-neutral-500">No calendar integrations connected yet.</p>
          ) : (
            <table className="w-full max-w-md text-sm">
              <thead>
                <tr className="text-left text-neutral-500">
                  <th className="pb-2 font-medium">Provider</th>
                  <th className="pb-2 font-medium">Active</th>
                  <th className="pb-2 font-medium">Inactive</th>
                </tr>
              </thead>
              <tbody>
                {integrations.providers.map((p) => (
                  <tr key={p.provider} className="border-t border-neutral-200 dark:border-neutral-800">
                    <td className="py-2 capitalize">{p.provider}</td>
                    <td className="py-2">{p.active_count}</td>
                    <td className="py-2">{p.inactive_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}
