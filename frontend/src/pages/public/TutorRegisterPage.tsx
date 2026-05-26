import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import "./RegisterPage.css";
import { useYears } from "../../utils/useYears";
const BIO_MAX = 300;

export default function TutorRegisterPage() {
  const navigate = useNavigate();
  const years = useYears();
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName]   = useState("");
  const [email, setEmail]         = useState("");
  const [mobile, setMobile]       = useState("");
  const [password, setPassword]   = useState("");
  const [confirm, setConfirm]     = useState("");
  const [qualification, setQualification] = useState("");
  const [university, setUniversity]       = useState("");
  const [yearLevels, setYearLevels] = useState<string[]>([]);
  const [bio, setBio]             = useState("");

  const [error, setError]     = useState("");
  const [loading, setLoading] = useState(false);

  function toggleYear(y: string) {
    setYearLevels((prev) =>
      prev.includes(y) ? prev.filter((x) => x !== y) : [...prev, y]
    );
  }

  function validate(): string | null {
    if (!firstName.trim() || !lastName.trim()) return "Please enter your full name.";
    if (!email.trim()) return "Please enter your email address.";
    if (!mobile.trim()) return "Please enter your mobile number.";
    if (!password) return "Please choose a password.";
    if (password !== confirm) return "Passwords do not match.";
    if (!qualification.trim()) return "Please enter what you are currently studying.";
    if (!university.trim()) return "Please enter your university.";
    if (yearLevels.length === 0) return "Please select at least one year level you can tutor.";
    if (bio.length > BIO_MAX) return `Bio must be ${BIO_MAX} characters or fewer.`;
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
      const res = await fetch(`${API_URL}/api/auth/register_tutor/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: email.trim(),
          password,
          confirm_password: confirm,
          first_name: firstName.trim(),
          last_name: lastName.trim(),
          mobile: mobile.trim(),
          qualification: qualification.trim(),
          university: university.trim(),
          year_levels: yearLevels,
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
      navigate(`/tutors/${data.user.id}`);
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
        <Link to="/" className="reg-nav-back">← Back to home</Link>
      </nav>

      <main className="reg-main">
        <div className="reg-card">
          <div className="reg-logo">
            <img src="/subjectmatter_wordmark.svg" alt="SubjectMatter" />
          </div>

          <h1 className="reg-heading">Apply to be a tutor</h1>
          <p className="reg-sub">
            Tell us about yourself. We review every application before
            approving tutors on the platform.
          </p>

          {error && (
            <div className="sm-alert sm-alert-error" style={{ marginBottom: "1.5rem" }}>
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} noValidate>

            {/* ── Personal details ───────────────────── */}
            <div className="reg-section">
              <div className="reg-section-header">
                <div className="reg-section-badge">1</div>
                <h2 className="reg-section-title">Personal details</h2>
              </div>

              <div className="reg-row">
                <div className="sm-form-group">
                  <label htmlFor="t-first">First name</label>
                  <input id="t-first" type="text" className="sm-input"
                    placeholder="Sarah" value={firstName}
                    onChange={(e) => setFirstName(e.target.value)} required />
                </div>
                <div className="sm-form-group">
                  <label htmlFor="t-last">Last name</label>
                  <input id="t-last" type="text" className="sm-input"
                    placeholder="Chen" value={lastName}
                    onChange={(e) => setLastName(e.target.value)} required />
                </div>
              </div>

              <div className="sm-form-group">
                <label htmlFor="t-email">Email address</label>
                <input id="t-email" type="email" className="sm-input"
                  placeholder="you@example.com" value={email}
                  onChange={(e) => setEmail(e.target.value)} required autoComplete="email" />
              </div>

              <div className="sm-form-group">
                <label htmlFor="t-mobile">Mobile number</label>
                <input id="t-mobile" type="tel" className="sm-input"
                  placeholder="04xx xxx xxx" value={mobile}
                  onChange={(e) => setMobile(e.target.value)} required autoComplete="tel" />
              </div>

              <div className="reg-row">
                <div className="sm-form-group">
                  <label htmlFor="t-password">Password</label>
                  <input id="t-password" type="password" className="sm-input"
                    placeholder="Min. 8 characters" value={password}
                    onChange={(e) => setPassword(e.target.value)} required autoComplete="new-password" />
                </div>
                <div className="sm-form-group">
                  <label htmlFor="t-confirm">Confirm password</label>
                  <input id="t-confirm" type="password" className="sm-input"
                    placeholder="Repeat password" value={confirm}
                    onChange={(e) => setConfirm(e.target.value)} required autoComplete="new-password" />
                </div>
              </div>
            </div>

            <hr className="reg-section-divider" />

            {/* ── Tutor details ───────────────────── */}
            <div className="reg-section">
              <div className="reg-section-header">
                <div className="reg-section-badge">2</div>
                <h2 className="reg-section-title">Tutor details</h2>
              </div>

              <div className="sm-form-group">
                <label htmlFor="t-qual">What are you currently studying?</label>
                <input id="t-qual" type="text" className="sm-input"
                  placeholder="e.g. B.Sc. Mathematics"
                  value={qualification} onChange={(e) => setQualification(e.target.value)} required />
              </div>

              <div className="sm-form-group">
                <label htmlFor="t-university">University</label>
                <input id="t-university" type="text" className="sm-input"
                  placeholder="e.g. University of Sydney"
                  value={university} onChange={(e) => setUniversity(e.target.value)} required />
              </div>

              <div className="sm-form-group">
                <label>Year levels you can tutor</label>
                <div className="reg-checkboxes">
                  <button
                    type="button"
                    className="reg-checkbox-item"
                    style={{ background: "none", border: "1px dashed var(--sm-border)", cursor: "pointer", fontWeight: 600 }}
                    onClick={() => setYearLevels(years.map((y) => y.code))}
                  >
                    All years
                  </button>
                  {years.map((y) => (
                    <label key={y.code} className="reg-checkbox-item">
                      <input
                        type="checkbox"
                        checked={yearLevels.includes(y.code)}
                        onChange={() => toggleYear(y.code)}
                      />
                      {y.label}
                    </label>
                  ))}
                </div>
              </div>

              <div className="sm-form-group">
                <label htmlFor="t-bio">
                  Brief bio{" "}
                </label>
                <textarea
                  id="t-bio"
                  className="sm-input"
                  placeholder="Tell us about yourself, your tutoring style and any relevant experience…"
                  rows={4}
                  maxLength={BIO_MAX + 20}
                  value={bio}
                  onChange={(e) => setBio(e.target.value)}
                  style={{ resize: "vertical", minHeight: "100px" }}
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
            <Link to="/login?tab=tutor">Sign in here</Link>
          </div>
        </div>
      </main>
    </div>
  );
}
