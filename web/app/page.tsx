/* eslint-disable @next/next/no-img-element */
import Link from "next/link";

const features = [
  {
    tag: "Best next action",
    color: "var(--blue)",
    title: "The one thing to do now — decided for you",
    body: "TimeSense weighs your schedule, priorities, energy, and where you are, then recommends the single best thing to do right now. No staring at a to-do list wondering what matters.",
    img: "/screens/now_focus.png",
    reverse: false,
  },
  {
    tag: "Capture",
    color: "var(--violet)",
    title: "Just say it",
    body: "Add anything by voice or text. “Call the dentist tomorrow at 2pm” becomes a scheduled plan — with the time, priority, and place understood. Tag it a reminder, errand, or idea and it’s handled accordingly.",
    img: "/screens/capture.png",
    reverse: true,
  },
  {
    tag: "Health & energy",
    color: "var(--green)",
    title: "Work with your energy, not against it",
    body: "Connect Apple Health and TimeSense factors your sleep, steps, and how long you’ve been sitting into what it suggests — a focus block when you’re sharp, a short walk when you’ve been still too long.",
    img: "/screens/now_health.png",
    reverse: false,
  },
  {
    tag: "Explainable",
    color: "var(--cyan)",
    title: "Understand every call",
    body: "Tap “Why this recommendation” to see exactly what it weighed — calendar, time of day, energy, and place — with a confidence score. It’s an assistant you can trust, not a black box.",
    img: "/screens/why.png",
    reverse: true,
  },
  {
    tag: "Insights",
    color: "var(--amber)",
    title: "Learns your patterns, quietly",
    body: "Over time TimeSense notices your best focus windows, your routines, and where your days slip — and turns them into better suggestions. It gets more useful the more you use it.",
    img: "/screens/insights.png",
    reverse: false,
  },
];

const grid = [
  { c: "var(--blue)", i: "📅", t: "Calendar-aware", d: "Reads your events and free blocks (Apple, Google) to time everything around real commitments — and reminds you to leave on time." },
  { c: "var(--violet)", i: "🎙️", t: "Voice & text capture", d: "Speak or type naturally; on-device transcription turns it into a structured, scheduled task." },
  { c: "var(--green)", i: "⚡", t: "Health & activity", d: "Sleep, steps, active energy, and inactivity shape recommendations that respect how you actually feel." },
  { c: "var(--cyan)", i: "📍", t: "Location & errands", d: "Attach a place to an errand and TimeSense routes it into your day when it genuinely fits your travel." },
  { c: "var(--amber)", i: "🔔", t: "Timely nudges", d: "A gentle push at the right moment — not a firehose of notifications you learn to ignore." },
  { c: "var(--blue)", i: "🧭", t: "Calm by design", d: "One clear next step, native on iPhone and Android. The point is relief, not another dashboard to manage." },
];

function Orb() {
  return <span className="orb" aria-hidden />;
}

export default function Home() {
  return (
    <div className="site">
      {/* Nav */}
      <nav className="nav">
        <div className="wrap nav-inner">
          <Link href="/" className="wordmark">
            <Orb />
            <span>Time<b>Sense</b></span>
          </Link>
          <div className="nav-links">
            <a href="#features">Features</a>
            <a href="#how">How it works</a>
            <Link href="/admin">Admin</Link>
            <a href="#get" className="btn btn-primary btn-sm">Get the app</a>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <header className="hero">
        <div className="wrap hero-grid">
          <div>
            <span className="eyebrow">Personal time assistant · AI</span>
            <h1 className="display">
              Know the <span className="grad">best next step</span>.
            </h1>
            <p className="lede">
              TimeSense reads your calendar, tasks, energy, and location to tell you the single best
              thing to do now — so planning your day never becomes another job.
            </p>
            <div className="hero-cta" id="get">
              <a href="#get" className="btn btn-primary">Download for iPhone</a>
              <a href="#features" className="btn btn-ghost">See how it works</a>
            </div>
            <p className="hero-note">14-day free trial · Free Basic mode after · iPhone &amp; Android</p>
          </div>
          <div className="hero-media">
            <div className="phone phone-lg">
              <img src="/screens/now_focus.png" alt="TimeSense recommending the best next action" />
            </div>
          </div>
        </div>
      </header>

      {/* Feature rows */}
      <main id="features" className="section">
        <div className="wrap">
          <div className="head">
            <span className="eyebrow">What it does</span>
            <h2>An assistant for your time, not another to-do list</h2>
            <p className="lede">
              Five signals — schedule, tasks, energy, location, and time of day — become one calm
              recommendation you can act on.
            </p>
          </div>

          {features.map((f) => (
            <section key={f.tag} className={`feature${f.reverse ? " reverse" : ""}`}>
              <div>
                <span className="pill" style={{ color: f.color, background: `color-mix(in srgb, ${f.color} 16%, transparent)` }}>
                  {f.tag}
                </span>
                <h2>{f.title}</h2>
                <p>{f.body}</p>
              </div>
              <div className="feature-media">
                <div className="phone">
                  <img src={f.img} alt={f.title} loading="lazy" />
                </div>
              </div>
            </section>
          ))}
        </div>
      </main>

      {/* Grid */}
      <section id="how" className="section">
        <div className="wrap">
          <div className="head">
            <span className="eyebrow">Everything, considered</span>
            <h2>Context in, clarity out</h2>
          </div>
          <div className="grid-cards">
            {grid.map((g) => (
              <div key={g.t} className="card">
                <div className="ic" style={{ color: g.c, background: `color-mix(in srgb, ${g.c} 16%, transparent)` }}>
                  <span>{g.i}</span>
                </div>
                <h3>{g.t}</h3>
                <p>{g.d}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="cta-band">
        <div className="wrap">
          <span className="eyebrow">Don’t make managing your day another job</span>
          <h2 className="display" style={{ margin: "18px 0 26px" }}>
            Let TimeSense hold the plan.
          </h2>
          <div className="hero-cta" style={{ justifyContent: "center" }}>
            <a href="#get" className="btn btn-primary">Download for iPhone</a>
            <a href="#get" className="btn btn-ghost">Get it on Android</a>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="footer">
        <div className="wrap footer-inner">
          <Link href="/" className="wordmark" style={{ fontSize: 17 }}>
            <Orb />
            <span>Time<b>Sense</b></span>
          </Link>
          <div style={{ display: "flex", gap: 28, flexWrap: "wrap" }}>
            <a href="#features">Features</a>
            <a href="#get">Download</a>
            <Link href="/admin">Admin</Link>
          </div>
          <span>© {new Date().getFullYear()} TimeSense</span>
        </div>
      </footer>
    </div>
  );
}
