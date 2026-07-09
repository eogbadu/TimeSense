"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, type ReactNode } from "react";
import { useAuth } from "@/lib/auth";
import { isFirebaseConfigured } from "@/lib/firebase";

const TABS = [
  { href: "/app", label: "Now" },
  { href: "/app/today", label: "Today" },
  { href: "/app/capture", label: "Capture" },
];

export default function AppLayout({ children }: { children: ReactNode }) {
  const { user, loading, signOut } = useAuth();
  const pathname = usePathname();

  if (loading) return <Centered>Loading…</Centered>;

  if (!isFirebaseConfigured) {
    return (
      <Centered>
        <h2 style={{ fontSize: 22, fontWeight: 700, marginBottom: 8 }}>Sign-in isn’t available yet</h2>
        <p className="muted" style={{ maxWidth: 380 }}>
          This environment doesn’t have a Firebase project configured. TimeSense lives on your phone —
          the web companion is here to view your day and capture quickly.
        </p>
        <Link href="/" className="btn btn-ghost btn-sm" style={{ marginTop: 18 }}>← Back to timesense</Link>
      </Centered>
    );
  }

  if (!user) return <SignIn />;

  return (
    <div className="app">
      <header className="app-bar">
        <div className="app-main app-bar-inner" style={{ padding: "0 20px" }}>
          <Link href="/" className="wordmark" style={{ fontSize: 17 }}>
            <span className="orb" aria-hidden />
            <span>Time<b>Sense</b></span>
          </Link>
          <nav className="app-tabs">
            {TABS.map((t) => (
              <Link key={t.href} href={t.href} className={pathname === t.href ? "active" : ""}>
                {t.label}
              </Link>
            ))}
          </nav>
          <button className="signout" onClick={() => signOut()}>Sign out</button>
        </div>
      </header>
      <main className="app-main">{children}</main>
    </div>
  );
}

function Centered({ children }: { children: ReactNode }) {
  return (
    <div className="app" style={{ display: "grid", placeItems: "center" }}>
      <div style={{ textAlign: "center", padding: 32 }}>{children}</div>
    </div>
  );
}

function SignIn() {
  const { signIn } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
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
      <Link href="/" className="wordmark" style={{ justifyContent: "center", marginBottom: 22 }}>
        <span className="orb" aria-hidden />
        <span>Time<b>Sense</b></span>
      </Link>
      <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 12, width: 300, textAlign: "left" }}>
        <p className="muted" style={{ textAlign: "center", marginBottom: 2 }}>Sign in to your companion</p>
        <input className="field" type="email" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        <input className="field" type="password" placeholder="Password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        {error && <p style={{ color: "var(--amber)", fontSize: 14 }}>{error}</p>}
        <button type="submit" className="btn btn-primary" disabled={submitting}>
          {submitting ? "Signing in…" : "Sign in"}
        </button>
        <p className="muted" style={{ fontSize: 13, textAlign: "center", marginTop: 4 }}>
          Use the account from your TimeSense app.
        </p>
      </form>
    </Centered>
  );
}
