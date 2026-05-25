import { Link } from "react-router-dom";
import "./LandingPage.css";

export default function LandingPage({ refCode }: { refCode?: string } = {}) {
  const registerHref = refCode ? `/register/parent?ref=${refCode}` : "/register/parent";
  return (
    <div className="lp-root">

      {/* ── Navbar ─────────────────────────────────── */}
      <nav className="lp-nav">
        <div className="lp-nav-inner">
          <Link to="/" className="lp-nav-logo">
            <img src="/subjectmatter_wordmark.svg" alt="SubjectMatter" />
          </Link>
          <div className="lp-nav-links">
            <Link to="/login" className="lp-nav-link">Login</Link>
            <Link to={registerHref} className="lp-nav-cta">Get Started</Link>
          </div>
        </div>
      </nav>

      {/* ── Hero ───────────────────────────────────── */}
      <section className="lp-hero">
        <div className="lp-hero-inner">
          <div className="lp-hero-text">
            <div className="lp-hero-eyebrow">NSW K–10 Mathematics</div>
            <h1 className="lp-hero-headline">
              Know exactly where your child<br />
              stands in maths, <br />
              <em>and what to do about it.</em>
            </h1>
            <p className="lp-hero-sub">
              SubjectMatter gives your child a free diagnostic assessment
              mapped to the NSW syllabus, then connects them with a qualified
              tutor. You get a clear progress report every week.
            </p>
            <div className="lp-hero-ctas">
              <Link to={registerHref} className="sm-btn-primary">
                Get a Free Assessment
              </Link>
              <Link to={registerHref} className="sm-btn-primary">
                Get a Tutor
              </Link>
              <Link to="/register/tutor" className="sm-btn-secondary">
                I'm a Tutor →
              </Link>
            </div>
          </div>

          {/* Mock report card */}
          <div className="lp-hero-card" aria-hidden="true">
            <div className="lp-card-header">
              <div className="lp-card-avatar">A</div>
              <div>
                <div className="lp-card-title">Alex's Assessment Report</div>
                <div className="lp-card-subtitle">Year 8 · March 2026</div>
              </div>
            </div>

            <SkillBar label="Algebra" pct={78} status="good" />
            <SkillBar label="Geometry" pct={41} status="gap" />
            <SkillBar label="Statistics" pct={86} status="good" />
            <SkillBar label="Ratios & Rates" pct={62} status="warn" />

            <div className="lp-card-flag">
              <span className="lp-card-flag-icon">⚠</span>
              Geometry gap identified — 3 skills below year level
            </div>
          </div>
        </div>
      </section>

      {/* ── Value propositions ─────────────────────── */}
      <section className="lp-values">
        <div className="lp-values-inner">
          <div className="lp-section-label">What we offer</div>
          <h2 className="lp-section-title">The assessment every NSW parent<br />wished they had sooner.</h2>
          <p className="lp-section-sub">
            No guesswork. No tutor impressions. Just objective, syllabus-aligned
            evidence of exactly where your child is and where they need to go.
          </p>
          <div className="lp-values-grid">
            <ValueCard
              icon="📋"
              title="Free NSW Syllabus Diagnostic"
              desc="Every question maps directly to the 2022 NSW Mathematics K–10 syllabus outcomes. You get a precise picture of your child's strengths and gaps — not a vague estimate."
            />
            <ValueCard
              icon="🎯"
              title="Matched to a Qualified Tutor"
              desc="We connect you with a tutor who knows exactly which skills need attention. No more guessing at what to work on — your child's tutor has the evidence in hand."
            />
            <ValueCard
              icon="📈"
              title="Weekly Progress Reports"
              desc="Every week you receive a clear, authoritative report showing what your child practised, what improved, and what's still in progress. You stay informed without any effort."
            />
          </div>
        </div>
      </section>

      {/* ── How it works ───────────────────────────── */}
      <section className="lp-how">
        <div className="lp-how-inner">
          <div className="lp-section-label">How it works</div>
          <h2 className="lp-section-title">Three steps to confidence.</h2>
          <div className="lp-steps">
            <div className="lp-step">
              <div className="lp-step-num">1</div>
              <h3 className="lp-step-title">Assess</h3>
              <p className="lp-step-desc">
                Your child completes a free adaptive diagnostic. It's mapped to
                the NSW syllabus and takes around 20 minutes. No pressure — it's
                designed to find gaps, not create anxiety.
              </p>
            </div>
            <div className="lp-step">
              <div className="lp-step-num">2</div>
              <h3 className="lp-step-title">Match</h3>
              <p className="lp-step-desc">
                We pair your child with a qualified, vetted tutor suited to their
                year level and specific gaps. Every tutor is reviewed and approved
                before they can accept students.
              </p>
            </div>
            <div className="lp-step">
              <div className="lp-step-num">3</div>
              <h3 className="lp-step-title">Track</h3>
              <p className="lp-step-desc">
                Each week you receive a progress report. Not a tutor's impression —
                actual performance data. Watch the gaps close over time with
                evidence you can rely on.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ── Trust signals ──────────────────────────── */}
      <section className="lp-trust">
        <div className="lp-trust-inner">
          <div className="lp-section-label">Why parents trust us</div>
          <h2 className="lp-section-title">Built for families who want answers,<br />not just reassurance.</h2>
          <div className="lp-trust-grid">
            <TrustItem
              icon="📚"
              title="NSW Syllabus Aligned"
              desc="Every assessment item is mapped to the 2022 NSW Mathematics K–10 Syllabus outcomes. Your child's results are directly meaningful to their school curriculum."
            />
            <TrustItem
              icon="📊"
              title="Objective Progress Tracking"
              desc="Results are based on your child's actual performance data, not a tutor's impressions. You see real numbers and real improvement — or the lack of it."
            />
            <TrustItem
              icon="✅"
              title="Vetted, Approved Tutors"
              desc="Every tutor on SubjectMatter is reviewed and manually approved before they work with students. Qualifications, year-level expertise and communication are all assessed."
            />
            <TrustItem
              icon="🔓"
              title="No Lock-In"
              desc="Start with the free assessment. Continue only if it's working for your family. There's no subscription, no hidden fees, and no pressure to commit before you see results."
            />
          </div>
        </div>
      </section>

      {/* ── Footer ─────────────────────────────────── */}
      <footer className="lp-footer">
        <div className="lp-footer-inner">
          <div className="lp-footer-logo">
            <img src="/subjectmatter_wordmark_orange.svg" alt="SubjectMatter" />
          </div>
          <div className="lp-footer-links">
            <Link to={registerHref}>Get Started</Link>
            <Link to="/login">Login</Link>
            <Link to="/register/tutor">Become a Tutor</Link>
          </div>
        </div>
        <div className="lp-footer-copy">
          © {new Date().getFullYear()} SubjectMatter. NSW maths tutoring · built for families.
        </div>
      </footer>
    </div>
  );
}

/* ── Sub-components ──────────────────────────────────────────── */

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
    <div className="lp-skill-row">
      <div className="lp-skill-label">
        <span className="lp-skill-name">{label}</span>
        <span className={`lp-skill-pct ${status}`}>{pct}%</span>
      </div>
      <div className="lp-bar-track">
        <div
          className={`lp-bar-fill ${status}`}
          style={{ width: `${pct}%` }}
        />
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
    <div className="lp-value-card">
      <div className="lp-value-icon">{icon}</div>
      <h3 className="lp-value-title">{title}</h3>
      <p className="lp-value-desc">{desc}</p>
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
    <div className="lp-trust-item">
      <div className="lp-trust-icon">{icon}</div>
      <div className="lp-trust-content">
        <h4>{title}</h4>
        <p>{desc}</p>
      </div>
    </div>
  );
}
