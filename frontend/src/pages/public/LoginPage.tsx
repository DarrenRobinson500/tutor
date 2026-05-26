import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import "./LoginPage.css";

const DEV_USERS = [
  { label: "Admin",   email: "Darren",  password: "Darren"  },
  { label: "Parent",  email: "Amanda",  password: "Amanda"  },
  { label: "Student", email: "Michael", password: "Michael" },
  { label: "Tutor",   email: "Alex",    password: "Alex"    },
];

export default function LoginPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [forgotSent, setForgotSent] = useState(false);

  async function doLogin(loginEmail: string, loginPassword: string) {
    setError("");
    setLoading(true);
    const API_URL = (process.env.REACT_APP_API_URL ?? "").replace(/\/$/, "");
    try {
      const res = await fetch(`${API_URL}/api/auth/login/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: loginEmail, password: loginPassword }),
      });
      const data = await res.json();
      if (!res.ok) {
        if (data.error === "account_inactive") {
          setError("Your application is under review. We'll be in touch soon.");
        } else {
          setError(data.error || "Invalid email or password.");
        }
        return;
      }
      localStorage.setItem("access", data.access);
      localStorage.setItem("refresh", data.refresh);
      localStorage.setItem("user", JSON.stringify(data.user));
      const role = data.user?.role;
      if (role === "parent") navigate(`/parents/${data.user.id}`);
      else if (role === "tutor") navigate(`/tutors/${data.user.id}`);
      else if (role === "student") navigate(`/students/${data.user.id}`);
      else if (role === "admin") navigate("/admin");
      else if (role === "distributor") navigate(`/distributors/${data.user.id}`);
      else if (role === "teacher") navigate(`/teachers/${data.user.id}`);
      else navigate("/");
    } catch {
      setError("Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    await doLogin(email, password);
  }

  if (forgotSent) {
    return (
      <div className="login-page">
        <nav className="login-nav">
          <Link to="/" className="login-nav-logo">
            <img src="/subjectmatter_wordmark.svg" alt="SubjectMatter" />
          </Link>
          <Link to="/" className="login-nav-back">← Back to home</Link>
        </nav>
        <main className="login-main">
          <div className="login-card">
            <div className="login-pending">
              <div className="login-pending-icon">📬</div>
              <h3>Check your email</h3>
              <p>If an account with that email exists, you'll receive a password reset link shortly.</p>
            </div>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="login-page">
      <nav className="login-nav">
        <Link to="/" className="login-nav-logo">
          <img src="/subjectmatter_wordmark.svg" alt="SubjectMatter" />
        </Link>
        <Link to="/" className="login-nav-back">← Back to home</Link>
      </nav>

      <main className="login-main">
        <div className="login-card">
          <div className="login-card-logo">
            <img src="/subjectmatter_wordmark.svg" alt="SubjectMatter" />
          </div>
          <div className="login-card-body">
            <h2 className="login-heading">Welcome back</h2>
            <p className="login-subheading">Sign in to your account.</p>

            <form onSubmit={handleSubmit}>
              <div className="sm-form-group">
                <label htmlFor="login-email">Email address</label>
                <input
                  id="login-email"
                  type="text"
                  className="sm-input"
                  placeholder="you@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  autoComplete="email"
                />
              </div>
              <div className="sm-form-group">
                <label htmlFor="login-password">Password</label>
                <input
                  id="login-password"
                  type="password"
                  className="sm-input"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  autoComplete="current-password"
                />
              </div>

              <button
                type="button"
                className="login-forgot"
                onClick={() => setForgotSent(true)}
              >
                Forgot password?
              </button>

              {error && (
                <div className="sm-alert sm-alert-error" style={{ marginBottom: "1rem" }}>
                  {error}
                </div>
              )}

              <button type="submit" className="sm-btn-primary login-submit" disabled={loading}>
                {loading ? "Signing in…" : "Sign In"}
              </button>
            </form>

            <div className="login-divider">or</div>
            <div className="login-register-link">
              Don't have an account?{" "}
              <Link to="/register/parent">Register here</Link>
            </div>

            <div style={{ marginTop: 20, paddingTop: 16, borderTop: "1px dashed #ccc" }}>
                <div style={{ fontSize: 11, color: "#999", marginBottom: 8, textTransform: "uppercase", letterSpacing: 1 }}>
                  Dev quick-login
                </div>
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                  {DEV_USERS.map(u => (
                    <button
                      key={u.label}
                      type="button"
                      style={{
                        padding: "4px 12px",
                        fontSize: 13,
                        border: "1px solid #ccc",
                        borderRadius: 4,
                        background: "#f8f9fa",
                        cursor: "pointer",
                      }}
                      disabled={loading}
                      onClick={() => doLogin(u.email, u.password)}
                    >
                      {u.label}
                    </button>
                  ))}
                </div>
              </div>
          </div>
        </div>
      </main>
    </div>
  );
}
