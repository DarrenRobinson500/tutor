import { Link } from "react-router-dom";
import "./TutorPage.css";

export default function TutorPage() {
  return (
    <div className="tp-root">

      {/* ── Navbar ─────────────────────────────────── */}
      <nav className="tp-nav">
        <div className="tp-nav-inner">
          <Link to="/" className="tp-nav-logo">
            <img src="/subjectmatter_wordmark.svg" alt="SubjectMatter" />
          </Link>
          <div className="tp-nav-links">
            <Link to="/login" className="tp-nav-link">Login</Link>
            <Link to="/register/tutor" className="tp-nav-cta">Apply Now</Link>
          </div>
        </div>
      </nav>

      {/* ── Hero ───────────────────────────────────── */}
      <section className="tp-hero">
        <div className="tp-hero-inner">
          <div className="tp-hero-text">
            <div className="tp-hero-eyebrow">Tutoring Positions · NSW Maths</div>
            <h1 className="tp-hero-headline">
              We find the students.<br />
              <em>You do what you do best.</em>
            </h1>
            <p className="tp-hero-sub">
              SubjectMatter matches qualified maths tutors with pre-assessed NSW
              students. You arrive knowing exactly which skills need work — and
              parents receive weekly progress reports automatically.
            </p>
            <div className="tp-hero-ctas">
              <Link to="/register/tutor" className="sm-btn-primary tp-btn-amber">
                Apply Now
              </Link>
              <a href="#how-it-works" className="sm-btn-secondary">
                See how it works ↓
              </a>
            </div>
          </div>

          {/* Mock student brief card */}
          <div className="tp-hero-card" aria-hidden="true">
            <StudentBriefCard />
          </div>
        </div>
      </section>

      {/* ── What We Offer ──────────────────────────── */}
      <section className="tp-values">
        <div className="tp-values-inner">
          <div className="tp-section-label">What we offer</div>
          <h2 className="tp-section-title">
            A platform built to make you more effective —<br />
            and keep your calendar full.
          </h2>
          <p className="tp-section-sub">
            No cold outreach. No guessing what to teach. SubjectMatter handles
            student acquisition and reporting so you can focus entirely on the session.
          </p>
          <div className="tp-values-grid">
            <ValueCard
              icon="👥"
              title="Students Matched to You"
              desc="We acquire the students and match them to you based on year level and identified skill gaps. Your calendar fills without any cold outreach or self-promotion."
            />
            <ValueCard
              icon="📋"
              title="NSW Syllabus Templates & Tools"
              desc="Every session is anchored to the 2022 NSW Mathematics K–10 Syllabus. You get structured question templates and worked examples aligned to exactly what your student needs."
            />
            <ValueCard
              icon="📈"
              title="Automated Parent Progress Reports"
              desc="After each session, the platform generates a clear progress report for parents. No write-ups. No chasing. Parents stay informed and engaged without any effort from you."
            />
          </div>
        </div>
      </section>

      {/* ── How it works ───────────────────────────── */}
      <section className="tp-how" id="how-it-works">
        <div className="tp-how-inner">
          <div className="tp-section-label">How it works</div>
          <h2 className="tp-section-title">Three steps to a full client roster.</h2>
          <div className="tp-steps">
            <div className="tp-step">
              <div className="tp-step-num">1</div>
              <h3 className="tp-step-title">Apply &amp; Get Approved</h3>
              <p className="tp-step-desc">
                Submit your application. We review your qualifications,
                year-level expertise, and communication style. Approved tutors
                are added to the matching pool.
              </p>
            </div>
            <div className="tp-step">
              <div className="tp-step-num">2</div>
              <h3 className="tp-step-title">Get Matched to Students</h3>
              <p className="tp-step-desc">
                When a student completes their diagnostic and their gaps align
                with your expertise, we send you their brief. You review it and
                confirm the match.
              </p>
            </div>
            <div className="tp-step">
              <div className="tp-step-num">3</div>
              <h3 className="tp-step-title">Teach &amp; Track Progress</h3>
              <p className="tp-step-desc">
                Run your sessions using syllabus-aligned materials. The platform
                handles reporting to parents automatically after each session.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ── Trust signals ──────────────────────────── */}
      <section className="tp-trust">
        <div className="tp-trust-inner">
          <div className="tp-section-label">Why tutors choose us</div>
          <h2 className="tp-section-title">Built for tutors who take their work seriously.</h2>
          <div className="tp-trust-grid">
            <TrustItem
              icon="📚"
              title="NSW Syllabus Aligned Materials"
              desc="Every question template and worked example is mapped to the 2022 NSW Mathematics K–10 Syllabus outcomes. You always know exactly what you're teaching and why."
            />
            <TrustItem
              icon="✅"
              title="Verified, Pre-qualified Students"
              desc="Every student arrives with a completed diagnostic. You know their year level, their gaps, and their starting point before the first session begins."
            />
            <TrustItem
              icon="📊"
              title="Structured Reporting That Parents Love"
              desc="Weekly progress reports are generated automatically from session data. Parents get clear evidence of progress — which keeps them engaged and students retained."
            />
            <TrustItem
              icon="🚫"
              title="No Cold Calling. No Admin."
              desc="We handle acquisition, matching, and reporting. You handle teaching. That's the entire arrangement."
            />
          </div>
        </div>
      </section>

      {/* ── Footer ─────────────────────────────────── */}
      <footer className="tp-footer">
        <div className="tp-footer-inner">
          <div className="tp-footer-logo">
            <img src="/subjectmatter_wordmark_orange.svg" alt="SubjectMatter" />
          </div>
          <div className="tp-footer-links">
            <Link to="/register/tutor">Apply Now</Link>
            <Link to="/login">Login</Link>
            <Link to="/register/parent">Get Started</Link>
          </div>
        </div>
        <div className="tp-footer-copy">
          © {new Date().getFullYear()} SubjectMatter. NSW maths tutoring · built for tutors.
        </div>
      </footer>
    </div>
  );
}

/* ── Sub-components ──────────────────────────────────────────── */

function StudentBriefCard() {
  return (
    <div className="tp-brief-card">
      <div className="tp-card-header">
        <div className="tp-card-avatar">A</div>
        <div>
          <div className="tp-card-title">Alex's Student Brief</div>
          <div className="tp-card-subtitle">Year 8 · Pre-session diagnostic</div>
        </div>
      </div>

      <div className="tp-gap-summary">
        <div className="tp-gap-item tp-gap-critical">
          <span className="tp-gap-dot" />
          Geometry: 3 skills below year level
        </div>
        <div className="tp-gap-item tp-gap-warn">
          <span className="tp-gap-dot" />
          Ratios &amp; Rates: approaching year level
        </div>
      </div>

      <SkillBar label="Algebra" pct={78} status="good" />
      <SkillBar label="Geometry" pct={41} status="gap" />
      <SkillBar label="Statistics" pct={86} status="good" />
      <SkillBar label="Ratios & Rates" pct={62} status="warn" />

      <div className="tp-card-flag">
        <span className="tp-card-flag-icon">✓</span>
        Ready to match — student assessed 2 days ago
      </div>
    </div>
  );
}

function SkillBar({
  label,
  pct,
  status,
}: {
  label: string;
  pct: number;
  status: "good" | "warn" | "gap";
}) {
  return (
    <div className="tp-skill-row">
      <div className="tp-skill-label">
        <span className="tp-skill-name">{label}</span>
        <span className={`tp-skill-pct ${status}`}>{pct}%</span>
      </div>
      <div className="tp-bar-track">
        <div className={`tp-bar-fill ${status}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

function ValueCard({
  icon,
  title,
  desc,
}: {
  icon: string;
  title: string;
  desc: string;
}) {
  return (
    <div className="tp-value-card">
      <div className="tp-value-icon">{icon}</div>
      <h3 className="tp-value-title">{title}</h3>
      <p className="tp-value-desc">{desc}</p>
    </div>
  );
}

function TrustItem({
  icon,
  title,
  desc,
}: {
  icon: string;
  title: string;
  desc: string;
}) {
  return (
    <div className="tp-trust-item">
      <div className="tp-trust-icon">{icon}</div>
      <div className="tp-trust-content">
        <h4>{title}</h4>
        <p>{desc}</p>
      </div>
    </div>
  );
}
