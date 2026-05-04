import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import "./RegisterPage.css";

const BIO_MAX = 500;

export default function DistributorRegisterPage() {
  const navigate = useNavigate();
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName]   = useState("");
  const [email, setEmail]         = useState("");
  const [mobile, setMobile]       = useState("");
  const [password, setPassword]   = useState("");
  const [confirm, setConfirm]     = useState("");
  const [bio, setBio]             = useState("");

  const [error, setError]     = useState("");
  const [loading, setLoading] = useState(false);

  function validate(): string | null {
    if (!firstName.trim() || !lastName.trim()) return "Please enter your full name.";
    if (!email.trim()) return "Please enter your email address.";
    if (!mobile.trim()) return "Please enter your mobile number.";
    if (!password) return "Please choose a password.";
    if (password !== confirm) return "Passwords do not match.";
    if (bio.length > BIO_MAX) return `Bio must be ${BIO_MAX} characters or fewer.`;
    return null;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");

    const err = validate();
    if (err) { setError(err); return; }

    setLoading(true);
    const API_URL = (process.env.REACT_APP_API_URL ?? "").replace(/\/$/, "");
    try {
      const res = await fetch(`${API_URL}/api/auth/register_distributor/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: email.trim(),
          password,
          confirm_password: confirm,
          first_name: firstName.trim(),
          last_name: lastName.trim(),
          mobile: mobile.trim(),
          bio: bio.trim(),
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.error || "Submission failed. Please try again.");
        return;
      }
      localStorage.setItem("access", data.access);
      localStorage.setItem("refresh", data.refresh);
      localStorage.setItem("user", JSON.stringify(data.user));
      navigate(`/distributors/${data.user.id}`);
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
        <Link to="/distributors" className="reg-nav-back">← Back</Link>
      </nav>

      <main className="reg-main">
        <div className="reg-card">
          <div className="reg-logo">
            <img src="/subjectmatter_wordmark.svg" alt="SubjectMatter" />
          </div>

          <h1 className="reg-heading">Apply to distribute</h1>
          <p className="reg-sub">
            Tell us about yourself and why you'd be a great distributor.
            We review every application before granting access.
          </p>

          {error && (
            <div className="sm-alert sm-alert-error" style={{ marginBottom: "1.5rem" }}>
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} noValidate>

            {/* ── Section 1: Personal details ─────────── */}
            <div className="reg-section">
              <div className="reg-section-header">
                <div className="reg-section-badge">1</div>
                <h2 className="reg-section-title">Personal details</h2>
              </div>

              <div className="reg-row">
                <div className="sm-form-group">
                  <label htmlFor="d-first">First name</label>
                  <input id="d-first" type="text" className="sm-input"
                    placeholder="Jordan" value={firstName}
                    onChange={(e) => setFirstName(e.target.value)} required />
                </div>
                <div className="sm-form-group">
                  <label htmlFor="d-last">Last name</label>
                  <input id="d-last" type="text" className="sm-input"
                    placeholder="Lee" value={lastName}
                    onChange={(e) => setLastName(e.target.value)} required />
                </div>
              </div>

              <div className="sm-form-group">
                <label htmlFor="d-email">Email address</label>
                <input id="d-email" type="email" className="sm-input"
                  placeholder="you@example.com" value={email}
                  onChange={(e) => setEmail(e.target.value)} required autoComplete="email" />
              </div>

              <div className="sm-form-group">
                <label htmlFor="d-mobile">Mobile number</label>
                <input id="d-mobile" type="tel" className="sm-input"
                  placeholder="04xx xxx xxx" value={mobile}
                  onChange={(e) => setMobile(e.target.value)} required autoComplete="tel" />
              </div>

              <div className="reg-row">
                <div className="sm-form-group">
                  <label htmlFor="d-password">Password</label>
                  <input id="d-password" type="password" className="sm-input"
                    placeholder="Min. 8 characters" value={password}
                    onChange={(e) => setPassword(e.target.value)} required autoComplete="new-password" />
                </div>
                <div className="sm-form-group">
                  <label htmlFor="d-confirm">Confirm password</label>
                  <input id="d-confirm" type="password" className="sm-input"
                    placeholder="Repeat password" value={confirm}
                    onChange={(e) => setConfirm(e.target.value)} required autoComplete="new-password" />
                </div>
              </div>
            </div>

            <hr className="reg-section-divider" />

            {/* ── Section 2: Background ───────────────── */}
            <div className="reg-section">
              <div className="reg-section-header">
                <div className="reg-section-badge">2</div>
                <h2 className="reg-section-title">Your background</h2>
              </div>

              <div className="sm-form-group">
                <label htmlFor="d-bio">Your approach</label>
                <textarea
                  id="d-bio"
                  className="sm-input"
                  placeholder="Tell us about your audience, your approach to marketing, and what you'd bring to the program…"
                  rows={5}
                  maxLength={BIO_MAX + 20}
                  value={bio}
                  onChange={(e) => setBio(e.target.value)}
                  style={{ resize: "vertical", minHeight: "120px" }}
                />
                <div className={`reg-char-count${bio.length > BIO_MAX ? " over" : ""}`}>
                  {bio.length}/{BIO_MAX}
                </div>
              </div>
            </div>

            <div className="reg-submit-area">
              <button type="submit" className="sm-btn-primary reg-submit" disabled={loading}>
                {loading ? "Submitting application…" : "Submit Application"}
              </button>
              <p className="reg-terms">
                Your application will be reviewed within 1–2 business days.
                You'll receive an email once approved.
              </p>
              {error && (
                <div className="sm-alert sm-alert-error" style={{ marginTop: "1rem" }}>
                  {error}
                </div>
              )}
            </div>
          </form>

          <div className="reg-login-link">
            Already approved?{" "}
            <Link to="/login">Sign in here</Link>
          </div>
        </div>
      </main>
    </div>
  );
}
