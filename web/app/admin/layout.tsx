"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";
import { useAdminApi } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { isFirebaseConfigured } from "@/lib/firebase";

interface MeResponse {
  role: string;
  email: string;
}

const NAV_ITEMS = [
  { href: "/admin", label: "Overview" },
  { href: "/admin/users", label: "Users" },
  { href: "/admin/invites", label: "Invites" },
  { href: "/admin/subscriptions", label: "Subscriptions" },
  { href: "/admin/feedback", label: "Feedback" },
];

export default function AdminLayout({ children }: { children: ReactNode }) {
  const { user, loading: authLoading, signOut } = useAuth();
  const callApi = useAdminApi();
  const pathname = usePathname();
  const [me, setMe] = useState<MeResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  // Derived rather than a separate boolean — see users/page.tsx for the same pattern.
  const roleLoading = Boolean(user) && me === null && error === null;

  useEffect(() => {
    // No user yet (or auth still resolving) — nothing to check, and no async work to kick off.
    if (authLoading || !user) return;
    callApi<MeResponse>("/api/v1/users/me")
      .then((data) => setMe(data))
      .catch((err) => setError(err.message ?? "Couldn't verify access."));
  }, [authLoading, user, callApi]);

  if (authLoading) {
    return <Centered>Loading…</Centered>;
  }

  if (!isFirebaseConfigured) {
    return (
      <Centered>
        Firebase isn&apos;t configured in this environment yet — sign-in is unavailable until a
        real Firebase project is set up (see open_questions.md).
      </Centered>
    );
  }

  if (!user) {
    return <SignInForm />;
  }

  if (roleLoading) {
    return <Centered>Loading…</Centered>;
  }

  if (error || !me || me.role !== "admin") {
    return (
      <Centered>
        <p className="font-medium">Access denied</p>
        <p className="mt-1 text-sm text-neutral-500">
          {error ?? "This account doesn't have admin access."}
        </p>
        <button
          onClick={() => signOut()}
          className="mt-4 text-sm underline underline-offset-2"
        >
          Sign out
        </button>
      </Centered>
    );
  }

  return (
    <div className="flex flex-1">
      <aside className="w-56 shrink-0 border-r border-neutral-200 p-4 dark:border-neutral-800">
        <p className="mb-4 text-sm font-semibold">TimeSense Admin</p>
        <nav className="flex flex-col gap-1">
          {NAV_ITEMS.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={`rounded px-3 py-2 text-sm ${
                pathname === item.href
                  ? "bg-neutral-900 text-white dark:bg-white dark:text-neutral-900"
                  : "hover:bg-neutral-100 dark:hover:bg-neutral-900"
              }`}
            >
              {item.label}
            </Link>
          ))}
        </nav>
        <button
          onClick={() => signOut()}
          className="mt-6 text-sm text-neutral-500 underline underline-offset-2"
        >
          Sign out
        </button>
      </aside>
      <main className="flex-1 p-6">{children}</main>
    </div>
  );
}

function Centered({ children }: { children: ReactNode }) {
  return (
    <div className="flex flex-1 items-center justify-center p-8 text-center">
      <div>{children}</div>
    </div>
  );
}

function SignInForm() {
  const { signIn } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await signIn(email, password);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign-in failed.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Centered>
      <form onSubmit={handleSubmit} className="flex w-64 flex-col gap-3 text-left">
        <p className="text-center text-sm font-medium">Admin sign in</p>
        <input
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="rounded border border-neutral-300 px-3 py-2 text-sm dark:border-neutral-700 dark:bg-neutral-900"
          required
        />
        <input
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="rounded border border-neutral-300 px-3 py-2 text-sm dark:border-neutral-700 dark:bg-neutral-900"
          required
        />
        {error && <p className="text-sm text-red-600">{error}</p>}
        <button
          type="submit"
          disabled={submitting}
          className="rounded bg-neutral-900 px-3 py-2 text-sm font-medium text-white disabled:opacity-50 dark:bg-white dark:text-neutral-900"
        >
          {submitting ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </Centered>
  );
}
