import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import "./RegisterPage.css";
import { useYears } from "../../utils/useYears";
import { dashboardPath } from "../../utils/dashboardPath";

export default function ParentRegisterPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const refCode = searchParams.get("ref") ?? "";

  // Redirect already-authenticated users to their dashboard
  useEffect(() => {
    try {
      const user = JSON.parse(localStorage.getItem("user") ?? "{}");
      if (user?.id) navigate(dashboardPath(), { replace: true });
    } catch {}
  }, []);
  const years = useYears();

  // Parent fields
  const [parentFirst, setParentFirst] = useState("");
  const [parentLast, setParentLast] = useState("");
  const [parentEmail, setParentEmail] = useState("");
  const [parentMobile, setParentMobile] = useState("");
  const [parentPassword, setParentPassword] = useState("");
  const [parentConfirm, setParentConfirm] = useState("");

  // Child fields
  const [childFirst, setChildFirst] = useState("");
  const [childLast, setChildLast] = useState("");
  const [childEmail, setChildEmail] = useState("");
  const [childYear, setChildYear] = useState("");
  const [childSchool, setChildSchool] = useState("");
  const [childMobile, setChildMobile] = useState("");
  const [childPassword, setChildPassword] = useState("");
  const [childConfirm, setChildConfirm] = useState("");

  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  function validate(): string | null {
    if (!parentFirst.trim() || !parentLast.trim()) return "Please enter your full name.";
    if (!parentEmail.trim()) return "Please enter your email address.";
    if (!parentMobile.trim()) return "Please enter your mobile number.";
    if (!parentPassword) return "Please choose a password.";
    if (parentPassword !== parentConfirm) return "Passwords do not match.";
    if (!childFirst.trim() || !childLast.trim()) return "Please enter your child's full name.";
    if (!childEmail.trim()) return "Please enter your child's email address.";
    if (!childYear) return "Please select your child's year level.";
    if (!childPassword) return "Please choose a password for your child.";
    if (childPassword !== childConfirm) return "Child's passwords do not match.";
    return null;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");

    const validationError = validate();
    if (validationError) {
      setError(validationError);
      return;
    }

    setLoading(true);
    const API_URL = (process.env.REACT_APP_API_URL ?? "").replace(/\/$/, "");
    try {
      const res = await fetch(`${API_URL}/api/auth/register_parent/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          parent_email: parentEmail.trim(),
          parent_password: parentPassword,
          parent_confirm_password: parentConfirm,
          parent_first_name: parentFirst.trim(),
          parent_last_name: parentLast.trim(),
          parent_mobile: parentMobile.trim(),
          child_first_name: childFirst.trim(),
          child_last_name: childLast.trim(),
          child_email: childEmail.trim(),
          child_year_level: childYear,
          child_school_name: childSchool.trim(),
          child_mobile: childMobile.trim(),
          child_password: childPassword,
          child_confirm_password: childConfirm,
          ...(refCode ? { referral_code: refCode } : {}),
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.error || "Registration failed. Please try again.");
        return;
      }
      localStorage.setItem("access", data.access);
      localStorage.setItem("refresh", data.refresh);
      localStorage.setItem("user", JSON.stringify(data.user));
      navigate(`/parents/${data.user.id}`);
    } catch {
      setError("Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="reg-page">
      <nav className="reg-nav">
        <Link to="/" className="reg-nav-logo">
          <img src="/subjectmatter_logo.svg" alt="SubjectMatter" />
        </Link>
        <Link to="/" className="reg-nav-back">← Back to home</Link>
      </nav>

      <main className="reg-main">
        <div className="reg-card">
          <div className="reg-logo">
            <img src="/subjectmatter_above_registration.svg" alt="SubjectMatter" />
          </div>

          <h1 className="reg-heading">Create your account</h1>
          <p className="reg-sub">
            Get your child's free NSW maths assessment in minutes.
          </p>

          {error && (
            <div className="sm-alert sm-alert-error" style={{ marginBottom: "1.5rem" }}>
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} noValidate>

            {/* ── Section 1: Parent ──────────────────── */}
            <div className="reg-section">
              <div className="reg-section-header">
                <div className="reg-section-badge">1</div>
                <h2 className="reg-section-title">Your details</h2>
              </div>

              <div className="reg-row">
                <div className="sm-form-group">
                  <label htmlFor="p-first">First name</label>
                  <input
                    id="p-first" type="text" className="sm-input"
                    placeholder="Jane"
                    value={parentFirst} onChange={(e) => setParentFirst(e.target.value)}
                    required autoComplete="given-name"
                  />
                </div>
                <div className="sm-form-group">
                  <label htmlFor="p-last">Last name</label>
                  <input
                    id="p-last" type="text" className="sm-input"
                    placeholder="Smith"
                    value={parentLast} onChange={(e) => setParentLast(e.target.value)}
                    required autoComplete="family-name"
                  />
                </div>
              </div>

              <div className="sm-form-group">
                <label htmlFor="p-email">Email address</label>
                <input
                  id="p-email" type="email" className="sm-input"
                  placeholder="you@example.com"
                  value={parentEmail} onChange={(e) => setParentEmail(e.target.value)}
                  required autoComplete="email"
                />
              </div>

              <div className="sm-form-group">
                <label htmlFor="p-mobile">Mobile number</label>
                <input
                  id="p-mobile" type="tel" className="sm-input"
                  placeholder="04xx xxx xxx"
                  value={parentMobile} onChange={(e) => setParentMobile(e.target.value)}
                  required autoComplete="tel"
                />
              </div>

              <div className="reg-row">
                <div className="sm-form-group">
                  <label htmlFor="p-password">Password</label>
                  <input
                    id="p-password" type="password" className="sm-input"
                    placeholder="Choose a password"
                    value={parentPassword} onChange={(e) => setParentPassword(e.target.value)}
                    required autoComplete="new-password"
                  />
                </div>
                <div className="sm-form-group">
                  <label htmlFor="p-confirm">Confirm password</label>
                  <input
                    id="p-confirm" type="password" className="sm-input"
                    placeholder="Repeat password"
                    value={parentConfirm} onChange={(e) => setParentConfirm(e.target.value)}
                    required autoComplete="new-password"
                  />
                </div>
              </div>
            </div>

            <hr className="reg-section-divider" />

            {/* ── Section 2: Child ───────────────────── */}
            <div className="reg-section">
              <div className="reg-section-header">
                <div className="reg-section-badge">2</div>
                <h2 className="reg-section-title">About your child</h2>
              </div>

              <div className="reg-row">
                <div className="sm-form-group">
                  <label htmlFor="c-first">Child's first name</label>
                  <input
                    id="c-first" type="text" className="sm-input"
                    placeholder="Alex"
                    value={childFirst} onChange={(e) => setChildFirst(e.target.value)}
                    required
                  />
                </div>
                <div className="sm-form-group">
                  <label htmlFor="c-last">Child's last name</label>
                  <input
                    id="c-last" type="text" className="sm-input"
                    placeholder="Smith"
                    value={childLast} onChange={(e) => setChildLast(e.target.value)}
                    required
                  />
                </div>
              </div>

              <div className="sm-form-group">
                <label htmlFor="c-email">Child's email address</label>
                <input
                  id="c-email" type="email" className="sm-input"
                  placeholder="child@example.com"
                  value={childEmail} onChange={(e) => setChildEmail(e.target.value)}
                  required autoComplete="off"
                />
              </div>

              <div className="sm-form-group">
                <label htmlFor="c-year">Year level</label>
                <select
                  id="c-year" className="sm-input"
                  value={childYear} onChange={(e) => setChildYear(e.target.value)}
                  required
                >
                  <option value="">Select year level…</option>
                  {years.map((y) => (
                    <option key={y.code} value={y.code}>{y.label}</option>
                  ))}
                </select>
              </div>

              <div className="sm-form-group">
                <label htmlFor="c-mobile">Child's mobile number</label>
                <input
                  id="c-mobile" type="tel" className="sm-input"
                  placeholder="04xx xxx xxx"
                  value={childMobile} onChange={(e) => setChildMobile(e.target.value)}
                  autoComplete="off"
                />
              </div>

              <div className="sm-form-group">
                <label htmlFor="c-school">School name <span style={{ fontWeight: 400, color: 'var(--sm-text-muted)' }}>(optional)</span></label>
                <input
                  id="c-school" type="text" className="sm-input"
                  placeholder="e.g. Pymble Ladies' College"
                  value={childSchool} onChange={(e) => setChildSchool(e.target.value)}
                />
              </div>

              <div className="reg-row">
                <div className="sm-form-group">
                  <label htmlFor="c-password">Child's password</label>
                  <input
                    id="c-password" type="password" className="sm-input"
                    placeholder="Choose a password"
                    value={childPassword} onChange={(e) => setChildPassword(e.target.value)}
                    required autoComplete="new-password"
                  />
                </div>
                <div className="sm-form-group">
                  <label htmlFor="c-confirm">Confirm child's password</label>
                  <input
                    id="c-confirm" type="password" className="sm-input"
                    placeholder="Repeat password"
                    value={childConfirm} onChange={(e) => setChildConfirm(e.target.value)}
                    required autoComplete="new-password"
                  />
                </div>
              </div>
            </div>

            <div className="reg-submit-area">
              <button type="submit" className="sm-btn-primary reg-submit" disabled={loading}>
                {loading ? "Creating account…" : "Create Account & Start Assessment →"}
              </button>
              <p className="reg-terms">
                By creating an account you agree to our Terms of Service and Privacy Policy.
              </p>
              {error && (
                <div className="sm-alert sm-alert-error" style={{ marginTop: "1rem" }}>
                  {error}
                </div>
              )}
            </div>
          </form>

          <div className="reg-login-link">
            Already have an account?{" "}
            <Link to="/login?tab=parent">Sign in</Link>
          </div>
        </div>
      </main>
    </div>
  );
}
