import { Link } from "react-router-dom";
import "./CompetitionPage.css";

export default function CompetitionPage() {
  return (
    <div className="cp-root">

      {/* ── Navbar ─────────────────────────────────── */}
      <nav className="cp-nav">
        <div className="cp-nav-inner">
          <Link to="/" className="cp-nav-logo">
            <img src="/subjectmatter_wordmark.svg" alt="SubjectMatter" />
          </Link>
          <div className="cp-nav-links">
            <Link to="/login" className="cp-nav-link">Login</Link>
            <Link to="/register/parent" className="cp-nav-cta">Get Started</Link>
          </div>
        </div>
      </nav>

      {/* ── Hero ───────────────────────────────────── */}
      <section className="cp-hero">
        <div className="cp-hero-inner">
          <div className="cp-hero-text">
            <div className="cp-hero-eyebrow">Competition Preparation · NSW Maths</div>
            <h1 className="cp-hero-headline">
              Train for the podium.<br />
              <em>One skill at a time.</em>
            </h1>
            <p className="cp-hero-sub">
              SubjectMatter prepares students for the AMC, IMAS, UNSW ICAS and other
              NSW mathematics competitions. Structured skill work, weekly homework
              loops and live tutoring — purpose-built for students who want to compete.
            </p>
            <div className="cp-hero-ctas">
              <Link to="/register/parent" className="sm-btn-primary cp-btn-purple">
                Get Started
              </Link>
              <a href="#how-it-works" className="sm-btn-secondary">
                See how it works ↓
              </a>
            </div>
          </div>

          {/* Decorative score card */}
          <div className="cp-hero-card" aria-hidden="true">
            <ScoreCard />
          </div>
        </div>
      </section>

      {/* ── What We Offer ──────────────────────────── */}
      <section className="cp-values">
        <div className="cp-values-inner">
          <div className="cp-section-label">What we offer</div>
          <h2 className="cp-section-title">
            Structured preparation for students who want<br />
            to go beyond the classroom.
          </h2>
          <p className="cp-section-sub">
            Competition maths requires precision, speed and deep fluency with core
            skills. SubjectMatter builds that foundation through weekly homework
            loops, targeted tutoring and a live competency tracker.
          </p>
          <div className="cp-values-grid">
            <ValueCard
              icon="🎯"
              title="Skill-by-Skill Mastery Tracking"
              desc="Every skill in the NSW K–10 maths syllabus is tracked individually. Students earn stars as they progress from foundational to advanced — so you can see exactly where they stand."
            />
            <ValueCard
              icon="🔁"
              title="Weekly Learning Loops"
              desc="Each focus skill gets a structured homework session each week. Students work through adaptive question sets, earn competency, and get a new set the following week."
            />
            <ValueCard
              icon="🧑‍🏫"
              title="Live Tutoring Sessions"
              desc="Weekly one-on-one sessions with a qualified maths tutor who works through competition-style problems and reinforces the skills students need under exam conditions."
            />
          </div>
        </div>
      </section>

      {/* ── How it works ───────────────────────────── */}
      <section className="cp-how" id="how-it-works">
        <div className="cp-how-inner">
          <div className="cp-section-label">How it works</div>
          <h2 className="cp-section-title">From enrolment to the competition floor.</h2>
          <div className="cp-steps">
            <div className="cp-step">
              <div className="cp-step-num">1</div>
              <h3 className="cp-step-title">Diagnostic Assessment</h3>
              <p className="cp-step-desc">
                Your student completes a diagnostic covering all NSW syllabus skills.
                We identify strengths, gaps and the starting point for their
                competition preparation program.
              </p>
            </div>
            <div className="cp-step">
              <div className="cp-step-num">2</div>
              <h3 className="cp-step-title">Weekly Homework &amp; Tutoring</h3>
              <p className="cp-step-desc">
                Each week your student works through a set of focus-area questions
                and attends a tutoring session. Progress is tracked automatically
                and shared with parents after every session.
              </p>
            </div>
            <div className="cp-step">
              <div className="cp-step-num">3</div>
              <h3 className="cp-step-title">Compete with Confidence</h3>
              <p className="cp-step-desc">
                With strong foundational skills and consistent weekly practice,
                students approach competition day with the depth and speed that
                top results require.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ── Competitions supported ─────────────────── */}
      <section className="cp-comps">
        <div className="cp-comps-inner">
          <div className="cp-section-label">Competitions we prepare for</div>
          <h2 className="cp-section-title">NSW & national mathematics competitions.</h2>
          <div className="cp-comp-grid">
            <CompItem name="AMC" full="Australian Mathematics Competition" level="All year levels" />
            <CompItem name="IMAS" full="International Mathematics Assessment for Schools" level="Years 3–10" />
            <CompItem name="ICAS" full="UNSW ICAS Mathematics" level="Years 3–10" />
            <CompItem name="AMT" full="Australian Mathematics Trust Events" level="Years 7–12" />
          </div>
        </div>
      </section>

      {/* ── Trust signals ──────────────────────────── */}
      <section className="cp-trust">
        <div className="cp-trust-inner">
          <div className="cp-section-label">Why SubjectMatter</div>
          <h2 className="cp-section-title">Serious preparation for serious students.</h2>
          <div className="cp-trust-grid">
            <TrustItem
              icon="📐"
              title="NSW Syllabus Aligned"
              desc="All question templates are mapped to the 2022 NSW Mathematics K–10 Syllabus. Competition preparation starts with mastery of every core skill."
            />
            <TrustItem
              icon="⭐"
              title="Star-Based Competency System"
              desc="Students earn stars as they demonstrate mastery across easy, medium and hard questions. Progress is visible, measurable and motivating."
            />
            <TrustItem
              icon="📊"
              title="Weekly Progress Reports"
              desc="Parents receive a progress report after every session — so they can track skill growth, star improvements and weekly homework completion."
            />
            <TrustItem
              icon="🏆"
              title="Competition-Tested Methods"
              desc="Our tutors understand what competition questions demand: speed, precision and the ability to apply skills in unfamiliar contexts."
            />
          </div>
        </div>
      </section>

      {/* ── Footer ─────────────────────────────────── */}
      <footer className="cp-footer">
        <div className="cp-footer-inner">
          <div className="cp-footer-logo">
            <img src="/subjectmatter_wordmark.svg" alt="SubjectMatter" />
          </div>
          <div className="cp-footer-links">
            <Link to="/register/parent">Get Started</Link>
            <Link to="/login">Login</Link>
            <Link to="/tutors">For Tutors</Link>
          </div>
        </div>
        <div className="cp-footer-copy">
          © {new Date().getFullYear()} SubjectMatter. NSW maths competition preparation.
        </div>
      </footer>
    </div>
  );
}

/* ── Sub-components ──────────────────────────────────────────── */

function ScoreCard() {
  return (
    <div className="cp-score-card">
      <div className="cp-score-header">
        <div className="cp-score-avatar">J</div>
        <div>
          <div className="cp-score-title">Jamie's Competition Prep</div>
          <div className="cp-score-subtitle">Year 7 · AMC preparation</div>
        </div>
      </div>

      <div className="cp-score-stats">
        <div className="cp-stat">
          <div className="cp-stat-value">18</div>
          <div className="cp-stat-label">Skills mastered</div>
        </div>
        <div className="cp-stat">
          <div className="cp-stat-value">★★★☆</div>
          <div className="cp-stat-label">Algebra</div>
        </div>
        <div className="cp-stat">
          <div className="cp-stat-value">★★☆☆</div>
          <div className="cp-stat-label">Geometry</div>
        </div>
      </div>

      <div className="cp-score-week">
        <div className="cp-week-item cp-week-done">✓ Homework completed this week</div>
        <div className="cp-week-item cp-week-done">✓ Tutoring session done</div>
        <div className="cp-week-item cp-week-next">↑ Algebra: level up in 1 session</div>
      </div>
    </div>
  );
}

function ValueCard({ icon, title, desc }: { icon: string; title: string; desc: string }) {
  return (
    <div className="cp-value-card">
      <div className="cp-value-icon">{icon}</div>
      <h3 className="cp-value-title">{title}</h3>
      <p className="cp-value-desc">{desc}</p>
    </div>
  );
}

function TrustItem({ icon, title, desc }: { icon: string; title: string; desc: string }) {
  return (
    <div className="cp-trust-item">
      <div className="cp-trust-icon">{icon}</div>
      <div className="cp-trust-content">
        <h4>{title}</h4>
        <p>{desc}</p>
      </div>
    </div>
  );
}

function CompItem({ name, full, level }: { name: string; full: string; level: string }) {
  return (
    <div className="cp-comp-item">
      <div className="cp-comp-acronym">{name}</div>
      <div className="cp-comp-full">{full}</div>
      <div className="cp-comp-level">{level}</div>
    </div>
  );
}
