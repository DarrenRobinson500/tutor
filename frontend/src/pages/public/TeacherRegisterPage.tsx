import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import "./RegisterPage.css";

export default function TeacherRegisterPage() {
  const navigate = useNavigate();
  const [firstName, setFirstName]   = useState("");
  const [lastName, setLastName]     = useState("");
  const [email, setEmail]           = useState("");
  const [password, setPassword]     = useState("");
  const [confirm, setConfirm]       = useState("");
  const [schoolName, setSchoolName] = useState("");
  const [error, setError]           = useState("");
  const [loading, setLoading]       = useState(false);

  function validate(): string | null {
    if (!firstName.trim() || !lastName.trim()) return "Please enter your full name.";
    if (!email.trim()) return "Please enter your email address.";
    if (!password) return "Please choose a password.";
    if (password !== confirm) return "Passwords do not match.";
    return null;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    const validationError = validate();
    if (validationError) { setError(validationError); return; }
    setLoading(true);
    const API_URL = (process.env.REACT_APP_API_URL ?? "").replace(/\/$/, "");
    try {
      const res = await fetch(`${API_URL}/api/auth/register_teacher/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: email.trim(),
          password,
          confirm_password: confirm,
          first_name: firstName.trim(),
          last_name: lastName.trim(),
          school_name: schoolName.trim(),
        }),
      });
      const data = await res.json();
      if (!res.ok) { setError(data.error || "Registration failed. Please try again."); return; }
      localStorage.setItem("access", data.access);
      localStorage.setItem("refresh", data.refresh);
      localStorage.setItem("user", JSON.stringify(data.user));
      navigate(`/teachers/${data.user.id}`);
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
          <img src="/subjectmatter_wordmark.svg" alt="SubjectMatter" />
        </Link>
        <Link to="/teachers" className="reg-nav-back">← Back</Link>
      </nav>

      <main className="reg-main">
        <div className="reg-card">
          <div className="reg-logo">
            <img src="/subjectmatter_wordmark.svg" alt="SubjectMatter" />
          </div>

          <h1 className="reg-heading">Teacher Regististration</h1>
          <p className="reg-sub">
            Create your teacher account.
            <br /> Your first class gap report is one assessment away.
          </p>

          {error && (
            <div className="sm-alert sm-alert-error" style={{ marginBottom: "1.5rem" }}>
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} noValidate>

            {/* ── Personal details ─────────────────────── */}
            <div className="reg-section">
              <div className="reg-section-header">
                <div className="reg-section-badge">1</div>
                <h2 className="reg-section-title">Your details</h2>
              </div>

              <div className="reg-row">
                <div className="sm-form-group">
                  <label htmlFor="tc-first">First name</label>
                  <input id="tc-first" type="text" className="sm-input"
                    placeholder="Sarah" value={firstName}
                    onChange={(e) => setFirstName(e.target.value)} required />
                </div>
                <div className="sm-form-group">
                  <label htmlFor="tc-last">Last name</label>
                  <input id="tc-last" type="text" className="sm-input"
                    placeholder="Chen" value={lastName}
                    onChange={(e) => setLastName(e.target.value)} required />
                </div>
              </div>

              <div className="sm-form-group">
                <label htmlFor="tc-email">Email address</label>
                <input id="tc-email" type="email" className="sm-input"
                  placeholder="you@school.nsw.edu.au" value={email}
                  onChange={(e) => setEmail(e.target.value)} required autoComplete="email" />
              </div>

              <div className="sm-form-group">
                <label htmlFor="tc-school">School name <span className="reg-optional">(optional)</span></label>
                <input id="tc-school" type="text" className="sm-input"
                  placeholder="e.g. Sydney Grammar School" value={schoolName}
                  onChange={(e) => setSchoolName(e.target.value)} />
              </div>

              <div className="reg-row">
                <div className="sm-form-group">
                  <label htmlFor="tc-password">Password</label>
                  <input id="tc-password" type="password" className="sm-input"
                    placeholder="Choose a password" value={password}
                    onChange={(e) => setPassword(e.target.value)} required autoComplete="new-password" />
                </div>
                <div className="sm-form-group">
                  <label htmlFor="tc-confirm">Confirm password</label>
                  <input id="tc-confirm" type="password" className="sm-input"
                    placeholder="Repeat password" value={confirm}
                    onChange={(e) => setConfirm(e.target.value)} required autoComplete="new-password" />
                </div>
              </div>
            </div>

            <div className="reg-submit-area">
              <button type="submit" className="sm-btn-primary reg-submit" disabled={loading}>
                {loading ? "Creating account…" : "Create Teacher Account"}
              </button>
            </div>
          </form>

          <div className="reg-login-link">
            Already have an account?{" "}
            <Link to="/login">Sign in here</Link>
          </div>
        </div>
      </main>
    </div>
  );
}
