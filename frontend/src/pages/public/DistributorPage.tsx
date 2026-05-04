import { Link } from "react-router-dom";
import "./DistributorPage.css";

export default function DistributorPage() {
  return (
    <div className="dp-root">

      {/* ── Navbar ─────────────────────────────────── */}
      <nav className="dp-nav">
        <div className="dp-nav-inner">
          <Link to="/" className="dp-nav-logo">
            <img src="/subjectmatter_wordmark.svg" alt="SubjectMatter" />
          </Link>
          <div className="dp-nav-links">
            <Link to="/login" className="dp-nav-link">Login</Link>
            <Link to="/register/distributor" className="dp-nav-cta">Apply Now</Link>
          </div>
        </div>
      </nav>

      {/* ── Hero ───────────────────────────────────── */}
      <section className="dp-hero">
        <div className="dp-hero-inner">
          <div className="dp-hero-text">
            <div className="dp-hero-eyebrow">Growth &amp; Earnings</div>
            <h1 className="dp-hero-headline">
              Turn your social media skills into<br />
              a revenue stream.<br />
              <em>No ceiling.</em>
            </h1>
            <p className="dp-hero-sub">
              SubjectMatter distributors earn ongoing income for every student
              they bring to the platform — and build a real acquisition portfolio
              while they're at it.
            </p>
            <div className="dp-hero-ctas">
              <Link to="/register/distributor" className="sm-btn-primary dp-btn-green">
                Apply Now
              </Link>
              <Link to="/register/tutor" className="sm-btn-secondary">
                I'm a Tutor →
              </Link>
            </div>
          </div>

          {/* Mock earnings dashboard */}
          <div className="dp-hero-card" aria-hidden="true">
            <EarningsCard />
          </div>
        </div>
      </section>

      {/* ── What We Offer ──────────────────────────── */}
      <section className="dp-values">
        <div className="dp-values-inner">
          <div className="dp-section-label">What we offer</div>
          <h2 className="dp-section-title">
            Recurring income for every student you bring —<br />
            for as long as they're on the platform.
          </h2>
          <p className="dp-section-sub">
            This isn't a one-off referral fee. Every student you acquire
            generates ongoing revenue. The more you grow, the more you earn.
          </p>
          <div className="dp-values-grid">
            <ValueCard
              icon="💸"
              title="Ongoing Revenue Per Student"
              desc="You earn a recurring cut of tuition for every student you refer, for as long as they stay active. Build your base and your income compounds."
            />
            <ValueCard
              icon="📁"
              title="A Real Campaign for Your Portfolio"
              desc="This isn't theoretical marketing. You'll run actual acquisition campaigns, hit real targets, and have the numbers to prove it."
            />
            <ValueCard
              icon="📊"
              title="Distributor Dashboard"
              desc="Track your students acquired, revenue earned, and month-on-month growth. Everything you need to measure your performance."
            />
          </div>
        </div>
      </section>

      {/* ── How It Works ───────────────────────────── */}
      <section className="dp-how">
        <div className="dp-how-inner">
          <div className="dp-section-label">How it works</div>
          <h2 className="dp-section-title">Three steps to your first commission.</h2>
          <div className="dp-steps">
            <div className="dp-step">
              <div className="dp-step-num">1</div>
              <h3 className="dp-step-title">Apply &amp; Get Your Link</h3>
              <p className="dp-step-desc">
                Submit a short application. If you're approved, you receive a
                unique referral link and access to your distributor dashboard.
              </p>
            </div>
            <div className="dp-step">
              <div className="dp-step-num">2</div>
              <h3 className="dp-step-title">Promote &amp; Acquire</h3>
              <p className="dp-step-desc">
                Run your own campaigns — social media, word of mouth, uni
                networks. Every student who signs up through your link is
                attributed to you.
              </p>
            </div>
            <div className="dp-step">
              <div className="dp-step-num">3</div>
              <h3 className="dp-step-title">Earn &amp; Grow</h3>
              <p className="dp-step-desc">
                Revenue starts the moment your students begin tuition and
                continues each month they stay active. Scale by acquiring more
                students.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ── Trust signals ──────────────────────────── */}
      <section className="dp-trust">
        <div className="dp-trust-inner">
          <div className="dp-section-label">Why distributors choose us</div>
          <h2 className="dp-section-title">
            A real performance record you can show<br />any future employer.
          </h2>
          <div className="dp-trust-grid">
            <TrustItem
              icon="📈"
              title="Transparent Earnings Dashboard"
              desc="See exactly what you've earned, how many students you've acquired, and your month-on-month growth. No black boxes."
            />
            <TrustItem
              icon="🏆"
              title="Measurable Growth Metrics"
              desc="Acquisition numbers, conversion rates, revenue growth — all tracked and exportable. Your portfolio piece is being built automatically."
            />
            <TrustItem
              icon="🎓"
              title="University Students Only"
              desc="We only work with serious applicants. That keeps the standard high and makes your involvement worth something."
            />
            <TrustItem
              icon="🔓"
              title="No Cap on Earnings"
              desc="There's no ceiling on what you can earn. The more students you acquire and retain, the more your income grows."
            />
          </div>
        </div>
      </section>

      {/* ── Footer ─────────────────────────────────── */}
      <footer className="dp-footer">
        <div className="dp-footer-inner">
          <div className="dp-footer-logo">
            <img src="/subjectmatter_wordmark_orange.svg" alt="SubjectMatter" />
          </div>
          <div className="dp-footer-links">
            <Link to="/register/distributor">Apply Now</Link>
            <Link to="/login">Login</Link>
            <Link to="/register/tutor">I'm a Tutor</Link>
          </div>
        </div>
        <div className="dp-footer-copy">
          © {new Date().getFullYear()} SubjectMatter. Earn with us · build your portfolio.
        </div>
      </footer>
    </div>
  );
}

/* ── Sub-components ──────────────────────────────────────────── */

const MONTH_LABELS = ["Nov", "Dec", "Jan", "Feb", "Mar", "Apr"];
const MONTH_VALUES = [3, 5, 6, 8, 11, 14];
const MAX_VALUE = Math.max(...MONTH_VALUES);

function EarningsCard() {
  return (
    <div className="dp-earnings-card">
      <div className="dp-card-header">
        <div className="dp-card-avatar">J</div>
        <div>
          <div className="dp-card-title">Jordan's Dashboard</div>
          <div className="dp-card-subtitle">Distributor · Active</div>
        </div>
      </div>

      <div className="dp-card-stats">
        <div className="dp-card-stat">
          <div className="dp-stat-value">14</div>
          <div className="dp-stat-label">Students acquired</div>
        </div>
        <div className="dp-card-stat">
          <div className="dp-stat-value dp-stat-green">$280<span className="dp-stat-unit">/mo</span></div>
          <div className="dp-stat-label">Monthly revenue</div>
        </div>
      </div>

      <div className="dp-chart-label">Students acquired (6 months)</div>
      <div className="dp-chart">
        {MONTH_VALUES.map((val, i) => (
          <MonthBar key={i} label={MONTH_LABELS[i]} value={val} max={MAX_VALUE} />
        ))}
      </div>

      <div className="dp-card-callout">
        <span className="dp-callout-arrow">↑</span>
        3 new students this week
      </div>
    </div>
  );
}

function MonthBar({
  label,
  value,
  max,
}: {
  label: string;
  value: number;
  max: number;
}) {
  const pct = Math.round((value / max) * 100);
  return (
    <div className="dp-month-col">
      <div className="dp-month-track">
        <div className="dp-month-fill" style={{ height: `${pct}%` }} />
      </div>
      <div className="dp-month-label">{label}</div>
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
    <div className="dp-value-card">
      <div className="dp-value-icon">{icon}</div>
      <h3 className="dp-value-title">{title}</h3>
      <p className="dp-value-desc">{desc}</p>
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
    <div className="dp-trust-item">
      <div className="dp-trust-icon">{icon}</div>
      <div className="dp-trust-content">
        <h4>{title}</h4>
        <p>{desc}</p>
      </div>
    </div>
  );
}
