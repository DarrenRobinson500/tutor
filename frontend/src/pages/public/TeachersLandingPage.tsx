import { Link } from "react-router-dom";
import "./TeachersLandingPage.css";

export default function TeachersLandingPage() {
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
            <Link to="/register/teacher" className="tp-nav-cta">Register</Link>
          </div>
        </div>
      </nav>

      {/* ── Hero ───────────────────────────────────── */}
      <section className="tp-hero">
        <div className="tp-hero-inner">
          <div className="tp-hero-text">
            <div className="tp-hero-eyebrow">Free forever for teachers · NSW K–10 Mathematics</div>
            <h1 className="tp-hero-headline">
              Your students have knowledge gaps.<br />
              <em>Find and fix them.</em>
            </h1>
            <p className="tp-hero-sub">
              SubjectMatter gives NSW maths teachers a free whole-class diagnostic tool — built on an open question bank, mapped to the NSW syllabus, and designed to reduce your marking load.
            </p>
            <div className="tp-hero-ctas">
              <Link to="/register/teacher" className="sm-btn-primary">
                Register
              </Link>
              <a href="#how-it-works" className="sm-btn-secondary">
                See How It Works →
              </a>
            </div>
          </div>

          {/* Mock class roster card */}
          <div className="tp-hero-card" aria-hidden="true">
            <div className="tp-card-header">
              <div className="tp-card-avatar">7M</div>
              <div>
                <div className="tp-card-title">Year 7 Maths — Gap Report</div>
                <div className="tp-card-subtitle">28 students · Week 11</div>
              </div>
            </div>

            <ClassRow name="Aisha K."  topic="Fractions"   status="gap" />
            <ClassRow name="Ben T."    topic="Algebra"     status="warn" />
            <ClassRow name="Chloe M."  topic="On track"    status="good" />
            <ClassRow name="David R."  topic="Percentages" status="gap" />
            <ClassRow name="Emma S."   topic="On track"    status="good" />

            <div className="tp-card-flag">
              <span className="tp-card-flag-icon">⚠</span>
              11 students below stage level in Number &amp; Algebra
            </div>
          </div>
        </div>
      </section>

      {/* ── Value propositions ─────────────────────── */}
      <section className="tp-values">
        <div className="tp-values-inner">
          <div className="tp-section-label">What we offer</div>
          <h2 className="tp-section-title">
            A whole-class assessment tool.<br />Built by teachers, for teachers.
          </h2>
          <p className="tp-section-sub">
            No marking. No generic EdTech. A complete question bank covering
            the NSW K–10 syllabus — open, contributable, and free.
          </p>
          <div className="tp-values-grid tp-values-grid--2col">
            <ValueCard
              icon="🏫"
              title="Whole-Class Diagnostic Tool"
              desc="Run a diagnostic across your entire class in one go. Get an instant gap report broken down by student, by topic, and by stage outcome — not one student at a time."
            />
            <ValueCard
              icon="📖"
              title="Open Question Bank — Full K–10 Coverage"
              desc="The full question set covering the NSW K–10 Maths Syllabus is open and free. Browse, assign, and use any question. No paywalls, no locked tiers."
            />
            <ValueCard
              icon="✏️"
              title="Add Your Own Questions. Share with Others."
              desc="Write your own questions and contribute them to the bank. When other teachers use and rate your questions, the whole platform gets better. Built on the same principle as open-source software."
            />
            <ValueCard
              icon="📨"
              title="Parent-Facing Reports That Reinforce Your Work"
              desc="Automated weekly progress updates go directly to parents — in plain English, aligned to what you're teaching. Fewer 'how is my child going?' emails. More informed families."
            />
          </div>
        </div>
      </section>

      {/* ── How it works ───────────────────────────── */}
      <section className="tp-how" id="how-it-works">
        <div className="tp-how-inner">
          <div className="tp-section-label">How it works</div>
          <h2 className="tp-section-title">Three steps to knowing your class.</h2>
          <div className="tp-steps">
            <div className="tp-step">
              <div className="tp-step-num">1</div>
              <h3 className="tp-step-title">Register &amp; Set Up Your Class</h3>
              <p className="tp-step-desc">
                Create your teacher account, add your class, and select the
                syllabus topics you're currently covering. Takes under 10 minutes.
              </p>
            </div>
            <div className="tp-step">
              <div className="tp-step-num">2</div>
              <h3 className="tp-step-title">Run Diagnostics &amp; Review Gap Reports</h3>
              <p className="tp-step-desc">
                Assign a diagnostic to your students. Results come back as an
                instant, syllabus-referenced gap report — no marking, no data
                entry on your end.
              </p>
            </div>
            <div className="tp-step">
              <div className="tp-step-num">3</div>
              <h3 className="tp-step-title">Track Progress &amp; Share with Parents</h3>
              <p className="tp-step-desc">
                Weekly competency updates go to parents automatically. You see
                the same data in your teacher dashboard — progress by student,
                by topic, over time.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ── Trust signals ──────────────────────────── */}
      <section className="tp-trust">
        <div className="tp-trust-inner">
          <div className="tp-section-label">Why teachers trust us</div>
          <h2 className="tp-section-title">
            Built for teachers who know the curriculum —<br />
            and want the data to back it up.
          </h2>
          <div className="tp-trust-grid">
            <TrustItem
              icon="🧑‍🏫"
              title="Designed by Teachers, for Teachers"
              desc="SubjectMatter was built with practising NSW maths teachers — not around them. The question bank, the gap reports, and the parent communications are all designed around how teachers actually work."
            />
            <TrustItem
              icon="🔓"
              title="Free Forever for Teachers"
              desc="No trial. No freemium tier. No 'upgrade to unlock'. The full diagnostic and reporting tool is permanently free for classroom teachers. Always."
            />
            <TrustItem
              icon="📊"
              title="Objective, Syllabus-Referenced Gap Data"
              desc="Not 'needs improvement' — specific outcomes, specific gaps, referenced by stage. The kind of data that holds up in a parent conversation or a faculty review meeting."
            />
            <TrustItem
              icon="🔧"
              title="No Marking. No Extra Admin."
              desc="The platform handles question delivery, automated marking, and report generation. You get the output — by student, by topic, by week — without the workload."
            />
          </div>
        </div>
      </section>

      {/* ── CTA Banner ─────────────────────────────── */}
      <section className="tp-cta">
        <div className="tp-cta-inner">
          <h2 className="tp-section-title">
            Start with one class.<br />Free today. Free forever.
          </h2>
          <p className="tp-section-sub">
            No credit card. No trial period. No catch. Register your class
            in under 10 minutes and run your first diagnostic today.
          </p>
          <div className="tp-hero-ctas">
            <Link to="/register/teacher" className="sm-btn-primary">
              Register — It's Free
            </Link>
            <Link to="/contact" className="sm-btn-secondary">
              Have questions? Contact us →
            </Link>
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
            <Link to="/register/teacher">Register Your Class</Link>
            <Link to="/login">Login</Link>
            <Link to="/register/parent">For Parents</Link>
          </div>
        </div>
        <div className="tp-footer-copy">
          © {new Date().getFullYear()} SubjectMatter. NSW maths tutoring · built for teachers.
        </div>
      </footer>
    </div>
  );
}

/* ── Sub-components ──────────────────────────────────────────── */

function ClassRow({
  name,
  topic,
  status,
}: {
  name: string;
  topic: string;
  status: "good" | "warn" | "gap";
}) {
  const dot: Record<string, string> = {
    good: "#43a047",
    warn: "var(--sm-orange)",
    gap: "#e53935",
  };
  return (
    <div className="tp-class-row">
      <span className="tp-class-name">{name}</span>
      <span className="tp-class-topic">{topic}</span>
      <span
        className="tp-class-dot"
        style={{ background: dot[status] }}
        aria-label={status}
      />
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
