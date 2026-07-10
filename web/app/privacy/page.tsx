import type { Metadata } from "next";
import Link from "next/link";
import Brand from "../Brand";

export const metadata: Metadata = {
  title: "Privacy Policy · TimeSense",
  description:
    "How TimeSense collects, uses, and protects your data — your calendar, health, location, and captures stay yours.",
};

const LAST_UPDATED = "July 9, 2026";

export default function Privacy() {
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
        <h1 className="display">Privacy Policy</h1>
        <p className="meta">Last updated {LAST_UPDATED}</p>

        <p className="intro">
          TimeSense is built on a simple promise: it should make your day calmer, never turn your life into
          data someone else profits from. This policy explains exactly what we collect, why, and the control
          you keep over all of it. We don’t sell your data, and we don’t show ads.
        </p>

        <h2><span className="num">1</span>What we collect</h2>
        <p>We collect only what’s needed to recommend your best next step and to run your account:</p>
        <ul>
          <li><b>Account.</b> Your email address and a Firebase authentication identifier when you sign in. That’s the whole account.</li>
          <li><b>What you capture.</b> The tasks, reminders, errands, notes, and ideas you add by voice or text, plus their times, priorities, and places.</li>
          <li><b>Calendar.</b> If you connect Apple or Google Calendar, we read your events and free blocks to schedule around real commitments. We only write events when you explicitly approve them.</li>
          <li><b>Health &amp; activity.</b> If you connect Apple Health (or an equivalent), we read signals like sleep, steps, and active energy to time suggestions to your energy — never diagnostic or medical records.</li>
          <li><b>Location.</b> If you allow it, we use your location to fit errands into your day and to detect commutes. You confirm commutes before anything is saved.</li>
          <li><b>Subscription.</b> Trial and subscription status. Payments are processed by Apple, Google, or Stripe — <b>we never receive or store your card number.</b></li>
          <li><b>Diagnostics.</b> Basic, aggregated usage and crash data to keep the app reliable.</li>
        </ul>

        <div className="callout">
          <p><b>Voice &amp; raw audio.</b> Voice capture is transcribed to text so TimeSense can understand it.
          We <b>never store raw audio recordings</b> unless you explicitly turn that on in Settings — it is off by
          default, opt-in only, and you can turn it off (and delete stored audio) at any time.</p>
        </div>

        <h2><span className="num">2</span>How we use it</h2>
        <ul>
          <li>To recommend the single best thing to do now, and to explain why.</li>
          <li>To schedule, reschedule, and remind — always with your approval before we change your calendar.</li>
          <li>To surface weekly insights about your focus windows, routines, and where your days slip.</li>
          <li>To operate your account, provide support, and keep the service secure.</li>
        </ul>
        <p>We do <b>not</b> use your personal content to build advertising profiles, and we do not sell it to anyone.</p>

        <h2><span className="num">3</span>AI processing</h2>
        <p>
          To turn “call the dentist tomorrow at 2pm” into a structured plan, the text you capture may be sent to
          a large-language-model provider (OpenAI by default) through our LLM gateway. This is processed under
          business terms that <b>prohibit using your data to train their models</b>. We send the minimum needed to
          parse your request, and we don’t send your health data to these providers.
        </p>

        <h2><span className="num">4</span>Who we share with</h2>
        <p>We share data only with the service providers that make TimeSense work:</p>
        <ul>
          <li><b>Firebase (Google)</b> — authentication.</li>
          <li><b>OpenAI / LLM provider</b> — parsing your captures into tasks.</li>
          <li><b>Apple, Google Play, Stripe</b> — payment processing.</li>
          <li><b>Apple / Google Calendar &amp; Health</b> — only the connections you choose to enable.</li>
        </ul>
        <p>Each provider is bound to protect your data and use it only to provide their service to us. We never sell data or share it with advertisers.</p>

        <h2><span className="num">5</span>Your controls</h2>
        <ul>
          <li><b>Approval first.</b> Calendar writes and full replans always require your explicit tap.</li>
          <li><b>Connect on your terms.</b> Health, calendar, location, and audio storage are each opt-in and can be disconnected anytime in Settings.</li>
          <li><b>Access &amp; export.</b> You can request a copy of your data.</li>
          <li><b>Delete.</b> You can delete your account and associated data from Settings or by contacting us; we remove it from active systems promptly.</li>
        </ul>

        <h2><span className="num">6</span>Retention</h2>
        <p>
          We keep your content while your account is active so TimeSense can learn your patterns. When you delete
          something — or your account — we remove it from active systems and purge it from backups on our normal
          backup cycle. Opt-in audio, if enabled, follows the retention window you choose.
        </p>

        <h2><span className="num">7</span>Security</h2>
        <p>
          Data is encrypted in transit and at rest, access is limited to what’s required to operate the service,
          and sensitive connections (health, calendar, location) are gated behind your explicit consent.
        </p>

        <h2><span className="num">8</span>Children</h2>
        <p>TimeSense is not directed to children under 13 (or the minimum age in your country), and we don’t knowingly collect their data.</p>

        <h2><span className="num">9</span>Changes</h2>
        <p>If we materially change this policy we’ll update the date above and, where appropriate, notify you in the app.</p>

        <h2><span className="num">10</span>Contact</h2>
        <p>
          Questions or requests? Email <a href="mailto:privacy@timesense.app">privacy@timesense.app</a>.
        </p>
      </main>

      <footer className="footer">
        <div className="wrap footer-inner">
          <Brand size={17} />
          <div style={{ display: "flex", gap: 28, flexWrap: "wrap" }}>
            <Link href="/">Home</Link>
            <Link href="/terms">Terms</Link>
            <Link href="/app">Open the app</Link>
          </div>
          <span>© {new Date().getFullYear()} TimeSense</span>
        </div>
      </footer>
    </div>
  );
}
