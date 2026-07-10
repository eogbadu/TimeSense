import type { Metadata } from "next";
import Link from "next/link";
import Brand from "../Brand";

export const metadata: Metadata = {
  title: "Terms of Service · TimeSense",
  description:
    "The terms that govern your use of TimeSense — accounts, subscriptions, acceptable use, and the limits of an assistant that suggests, never decides for you.",
};

const LAST_UPDATED = "July 9, 2026";

export default function Terms() {
  return (
    <div className="site">
      <nav className="nav">
        <div className="wrap nav-inner">
          <Brand />
          <div className="nav-links">
            <Link href="/">Home</Link>
            <Link href="/app" className="btn btn-primary btn-sm">Open the app</Link>
          </div>
        </div>
      </nav>

      <main className="legal">
        <span className="eyebrow">Legal</span>
        <h1 className="display">Terms of Service</h1>
        <p className="meta">Last updated {LAST_UPDATED}</p>

        <p className="intro">
          These terms are the agreement between you and TimeSense. We’ve kept them plain. In short: TimeSense
          is an assistant that suggests your best next step — it never acts without your say-so, your data stays
          yours, and you can leave anytime. By creating an account or using the app, you agree to what’s below.
        </p>

        <h2><span className="num">1</span>The service</h2>
        <p>
          TimeSense is a personal time assistant available on iPhone, Android, and this web companion. It reads
          the context you connect — calendar, tasks, energy, location — and recommends what to do now. Its
          recommendations are <b>suggestions, not instructions or professional advice</b>. You’re always in
          control: calendar changes and replans require your explicit approval, and you decide what to act on.
        </p>

        <h2><span className="num">2</span>Your account</h2>
        <ul>
          <li>You need an account (via Firebase Authentication) to use TimeSense, and you’re responsible for keeping your sign-in secure.</li>
          <li>You must be at least 13 (or the minimum age in your country) to use the service.</li>
          <li>Provide accurate information and don’t use someone else’s account without permission.</li>
          <li>You’re responsible for activity under your account.</li>
        </ul>

        <h2><span className="num">3</span>Subscriptions &amp; billing</h2>
        <ul>
          <li><b>Free trial.</b> TimeSense Premium starts with a 14-day free trial that requires valid payment information. If you don’t cancel before it ends, it converts to a paid subscription.</li>
          <li><b>Free Basic mode.</b> After a trial or cancellation you keep a free Basic mode — you don’t lose access to the core app.</li>
          <li><b>Where you’re billed.</b> Payments are handled by Apple (StoreKit), Google Play, or Stripe depending on where you subscribe. Their terms and renewal rules apply, and <b>we never see or store your card number.</b></li>
          <li><b>Renewal &amp; cancellation.</b> Subscriptions renew automatically until cancelled. Manage or cancel anytime through your app store account (iOS/Android) or your billing portal (web); cancellation takes effect at the end of the current period.</li>
          <li><b>Refunds.</b> Refunds are handled by the store you purchased through, under their policies.</li>
          <li><b>Price changes.</b> If prices change, we’ll give notice and the new price applies to future renewals only.</li>
        </ul>

        <h2><span className="num">4</span>Acceptable use</h2>
        <p>Please don’t:</p>
        <ul>
          <li>Break the law, infringe others’ rights, or use TimeSense to harm anyone.</li>
          <li>Reverse-engineer, scrape, overload, or attempt to bypass the security of the service or our APIs.</li>
          <li>Resell or redistribute the service, or access it through automated means except as we permit.</li>
        </ul>

        <h2><span className="num">5</span>Your content</h2>
        <p>
          The tasks, notes, and captures you add are <b>yours</b>. You grant TimeSense the limited license needed
          to store, process, and display that content back to you and to operate features you enable (for example,
          sending capture text to our AI provider to turn it into a scheduled task). We don’t claim ownership of
          your content and we don’t sell it. See the{" "}
          <Link href="/privacy">Privacy Policy</Link> for exactly how your data is handled.
        </p>

        <h2><span className="num">6</span>Third-party connections</h2>
        <p>
          When you connect Apple or Google Calendar, Apple Health, location, or other integrations, your use of
          those services is governed by <b>their</b> terms, and TimeSense only accesses what you authorize. We’re
          not responsible for third-party services, and they may change or become unavailable.
        </p>

        <h2><span className="num">7</span>Disclaimers</h2>
        <div className="callout">
          <p>
            TimeSense helps you plan, but it can’t guarantee outcomes. Recommendations, schedules, travel-time
            estimates, and reminders may be incomplete or wrong, and depend on data from your device and connected
            services. <b>You remain responsible for your commitments</b> — always confirm anything that matters
            (appointments, deadlines, travel). The service is provided “as is” and “as available,” without
            warranties of any kind to the fullest extent permitted by law.
          </p>
        </div>

        <h2><span className="num">8</span>Limitation of liability</h2>
        <p>
          To the fullest extent permitted by law, TimeSense and its team won’t be liable for indirect, incidental,
          or consequential damages, or for missed events, lost time, or lost data arising from your use of the
          service. Where liability can’t be excluded, it’s limited to the amount you paid us in the 12 months
          before the claim.
        </p>

        <h2><span className="num">9</span>Termination</h2>
        <p>
          You can stop using TimeSense and delete your account at any time from Settings. We may suspend or end
          access if you materially violate these terms or to protect the service and its users. You can export or
          delete your data as described in the <Link href="/privacy">Privacy Policy</Link>.
        </p>

        <h2><span className="num">10</span>Changes</h2>
        <p>
          We may update the service and these terms. If we make material changes, we’ll update the date above and,
          where appropriate, notify you in the app. Continuing to use TimeSense after changes take effect means you
          accept the updated terms.
        </p>

        <h2><span className="num">11</span>Contact</h2>
        <p>
          Questions about these terms? Email <a href="mailto:support@timesense.app">support@timesense.app</a>.
        </p>
      </main>

      <footer className="footer">
        <div className="wrap footer-inner">
          <Brand size={17} />
          <div style={{ display: "flex", gap: 28, flexWrap: "wrap" }}>
            <Link href="/">Home</Link>
            <Link href="/privacy">Privacy</Link>
            <Link href="/app">Open the app</Link>
          </div>
          <span>© {new Date().getFullYear()} TimeSense</span>
        </div>
      </footer>
    </div>
  );
}
