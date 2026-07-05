"use client";

import { useEffect, useState } from "react";
import { useAdminApi } from "@/lib/api";

interface AdminFeedbackSummary {
  id: string;
  user_email: string;
  task_title: string;
  signal: string;
  created_at: string;
}

interface AdminFeedbackListResponse {
  feedback: AdminFeedbackSummary[];
}

const SIGNAL_STYLES: Record<string, string> = {
  done: "text-green-600",
  snooze: "text-amber-600",
  not_now: "text-neutral-500",
};

export default function AdminFeedbackPage() {
  const callApi = useAdminApi();
  const [data, setData] = useState<AdminFeedbackListResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    callApi<AdminFeedbackListResponse>("/api/v1/admin/feedback")
      .then(setData)
      .catch((err) => setError(err.message ?? "Couldn't load feedback."))
      .finally(() => setLoading(false));
  }, [callApi]);

  if (loading) return <p className="text-sm text-neutral-500">Loading…</p>;
  if (error) return <p className="text-sm text-red-600">{error}</p>;

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-xl font-semibold">Recommendation Feedback</h1>
      {data && data.feedback.length === 0 ? (
        <p className="text-sm text-neutral-500">No feedback recorded yet.</p>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-neutral-500">
              <th className="pb-2 font-medium">User</th>
              <th className="pb-2 font-medium">Task</th>
              <th className="pb-2 font-medium">Signal</th>
              <th className="pb-2 font-medium">When</th>
            </tr>
          </thead>
          <tbody>
            {data?.feedback.map((f) => (
              <tr key={f.id} className="border-t border-neutral-200 dark:border-neutral-800">
                <td className="py-2">{f.user_email}</td>
                <td className="py-2">{f.task_title}</td>
                <td className={`py-2 font-medium ${SIGNAL_STYLES[f.signal] ?? ""}`}>
                  {f.signal}
                </td>
                <td className="py-2 text-neutral-500">
                  {new Date(f.created_at).toLocaleString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
