import { Link } from "react-router-dom";
import { useEffect, useState, useRef } from "react";
import { apiFetch } from "../../utils/apiFetch";
import { dashboardPath } from "../../utils/dashboardPath";
import { IncomingCallBanner } from "./IncomingCallBanner";

const NAV_STYLES = `
  .sm-page {
    min-height: 100vh;
    background: #FFFBF5;
    font-family: Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
  }
  .sm-layout-nav {
    background: rgba(255,251,245,0.95);
    backdrop-filter: blur(8px);
    border-bottom: 1px solid #F0EAE0;
    padding: 0 2rem;
    height: 64px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    position: sticky;
    top: 0;
    z-index: 100;
  }
  .sm-nav-left {
    display: flex;
    align-items: center;
    gap: 1.5rem;
  }
  .sm-nav-logo img { height: 32px; width: auto; }
  .sm-nav-links {
    display: flex;
    align-items: center;
    gap: 0.25rem;
  }
  .sm-nav-right {
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }
  .sm-nav-user {
    font-size: 0.8125rem;
    color: #8C8179;
  }
  .sm-nav-link {
    font-size: 0.875rem;
    font-family: Inter, -apple-system, sans-serif;
    color: #5C5249;
    background: none;
    border: none;
    cursor: pointer;
    padding: 0.4rem 0.75rem;
    border-radius: 6px;
    transition: color 0.15s, background 0.15s;
    text-decoration: none;
    display: inline-block;
    line-height: 1.4;
  }
  .sm-nav-link:hover { color: #2D2D2D; background: #FFF5E8; }
  .sm-dev-btn {
    font-size: 0.7rem;
    padding: 0.2rem 0.55rem;
    border-radius: 4px;
    border: 1px solid rgba(232,119,34,0.3);
    background: rgba(232,119,34,0.08);
    color: #b85c14;
    cursor: pointer;
    font-family: Inter, sans-serif;
    transition: background 0.15s;
  }
  .sm-dev-btn:hover {
    background: rgba(232,119,34,0.18);
    color: #8a3f08;
  }
  .sm-nav-dropdown { position: relative; }
  .sm-nav-dropdown-menu {
    position: absolute;
    top: calc(100% + 4px);
    left: 0;
    background: #fff;
    border: 1px solid #F0EAE0;
    border-radius: 8px;
    box-shadow: 0 4px 16px rgba(0,0,0,0.1);
    z-index: 200;
    min-width: 140px;
    padding: 4px 0;
  }
  .sm-nav-dropdown-item {
    display: block;
    width: 100%;
    padding: 0.4rem 0.9rem;
    font-size: 0.875rem;
    color: #5C5249;
    background: none;
    border: none;
    text-align: left;
    text-decoration: none;
    cursor: pointer;
    transition: background 0.12s, color 0.12s;
  }
  .sm-nav-dropdown-item:hover { background: #FFF5E8; color: #2D2D2D; }
`;

const DEFAULT_DEV_USERS = [
  { label: "Admin",   email: "Darren",  password: "Darren"  },
  { label: "Parent",  email: "Amanda",  password: "Amanda"  },
  { label: "Student", email: "Michael", password: "Michael" },
  { label: "Tutor",   email: "Alex",    password: "Alex"    },
];

const HEADER_STYLE: React.CSSProperties = {
  background: "linear-gradient(145deg, #FFFBF5 0%, #FFF5E8 100%)",
  padding: "2.5rem 2rem 2rem",
  borderBottom: "1px solid #F0EAE0",
};
const HEADER_TITLE_STYLE: React.CSSProperties = {
  fontFamily: "Lora, Georgia, serif",
  fontSize: "1.875rem",
  fontWeight: 700,
  color: "#2D2D2D",
  margin: "0 0 0.4rem",
};
const HEADER_SUB_STYLE: React.CSSProperties = {
  fontSize: "1rem",
  color: "#5C5249",
  margin: 0,
};

function NavDropdown({ label, children }: { label: string; children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", handleOutside);
    return () => document.removeEventListener("mousedown", handleOutside);
  }, []);

  return (
    <div ref={ref} className="sm-nav-dropdown">
      <button className="sm-nav-link" onClick={() => setOpen((v) => !v)}>
        {label} <span style={{ fontSize: "0.7em", verticalAlign: "middle" }}>▾</span>
      </button>
      {open && (
        <div className="sm-nav-dropdown-menu" onClick={() => setOpen(false)}>
          {children}
        </div>
      )}
    </div>
  );
}

export function PageHeader({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div style={HEADER_STYLE}>
      <div className="container">
        <h1 style={HEADER_TITLE_STYLE}>{title}</h1>
        {subtitle && <p style={HEADER_SUB_STYLE}>{subtitle}</p>}
      </div>
    </div>
  );
}

export function Layout({ children, hideNav, header }: { children: React.ReactNode; hideNav?: boolean; header?: React.ReactNode }) {
  const storedUser = localStorage.getItem("user");
  const user = storedUser ? JSON.parse(storedUser) : null;
  const access = localStorage.getItem("access");
  const [devUsers, setDevUsers] = useState(DEFAULT_DEV_USERS);

  useEffect(() => {
    fetch(`${(process.env.REACT_APP_API_URL ?? "").replace(/\/$/, "")}/api/settings/`)
      .then(r => r.json())
      .then((d: { dev_users?: typeof DEFAULT_DEV_USERS }) => {
        if (Array.isArray(d.dev_users) && d.dev_users.length) setDevUsers(d.dev_users);
      })
      .catch(() => {});
  }, []);

  async function devLoginAs(email: string, password: string) {
    const API_URL = (process.env.REACT_APP_API_URL ?? "").replace(/\/$/, "");
    try {
      const res = await fetch(`${API_URL}/api/auth/login/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      const data = await res.json();
      if (!res.ok) return;
      localStorage.setItem("access", data.access);
      localStorage.setItem("refresh", data.refresh);
      localStorage.setItem("user", JSON.stringify(data.user));
      const role = data.user?.role;
      if (role === "parent") window.location.href = `/parents/${data.user.id}`;
      else if (role === "tutor") window.location.href = `/tutors/${data.user.id}`;
      else if (role === "student") window.location.href = `/students/${data.user.id}`;
      else if (role === "admin") window.location.href = "/admin";
      else window.location.href = "/";
    } catch { /* ignore */ }
  }

  async function switchToParent() {
    const res = await fetch("/api/auth/dev_switch_to_parent/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ student_id: user?.id }),
    });
    const data = await res.json();
    if (data.id) {
      localStorage.setItem("user", JSON.stringify(data));
      localStorage.setItem("access", data.access);
      localStorage.setItem("refresh", data.refresh);
      window.location.href = `/parents/${data.id}`;
    }
  }

  useEffect(() => {
    if (!access) return;
    if (!user) {
      window.location.href = "/login";
    }
  }, [access, user]);

  if (!access) {
    return <div>{children}</div>;
  }

  return (
    <div className="sm-page">
      <style>{NAV_STYLES}</style>

      {/* Navbar */}
      {!hideNav && (
        <nav className="sm-layout-nav">
          <div className="sm-nav-left">
            <Link className="sm-nav-logo" to={dashboardPath()}>
              <img src="/subjectmatter_wordmark.svg" alt="SubjectMatter" />
            </Link>
            <div className="sm-nav-links">

              {user?.role === "admin" && (<>
                <Link className="sm-nav-link" to="/admin">Home</Link>
                <Link className="sm-nav-link" to="/admin/tutors">Tutors</Link>
                <Link className="sm-nav-link" to="/admin/students">Students</Link>
                <Link className="sm-nav-link" to="/admin/payments">Payments</Link>
                <NavDropdown label="Messages">
                  <Link className="sm-nav-dropdown-item" to="/admin/sms">SMS</Link>
                  <Link className="sm-nav-dropdown-item" to="/admin/emails">Emails</Link>
                  <Link className="sm-nav-dropdown-item" to="/admin/messages/docs">Docs</Link>
                </NavDropdown>
                <Link className="sm-nav-link" to="/skills">Skills</Link>
                <Link className="sm-nav-link" to="/skills-s6">Skills S6</Link>
                <Link className="sm-nav-link" to="/templates">Templates</Link>
                <Link className="sm-nav-link" to="/knowledge">Knowledge</Link>
                <Link className="sm-nav-link" to="/feedback">Feedback</Link>
                <Link className="sm-nav-link" to="/principles">Principles</Link>
                <Link className="sm-nav-link" to="/docs">Docs</Link>
                <Link className="sm-nav-link" to="/admin/variables">Variables</Link>
              </>)}

              {user?.role === "tutor" && (<>
                <Link className="sm-nav-link" to={`/tutors/${user.id}/`}>Home</Link>
                <Link className="sm-nav-link" to={`/tutors/${user.id}/booking`}>Bookings</Link>
                <Link className="sm-nav-link" to={`/tutors/${user.id}/post-tuition`}>Post Tuition</Link>
                <Link className="sm-nav-link" to={`/tutors/${user.id}/payments`}>Payments</Link>
                <Link className="sm-nav-link" to={`/tutors/${user.id}/sms`}>Messages</Link>
                <Link className="sm-nav-link" to="/skills">Skills</Link>
                <Link className="sm-nav-link" to="/skills-s6">Skills S6</Link>
                <Link className="sm-nav-link" to="/templates">Templates</Link>
                <Link className="sm-nav-link" to="/knowledge">Knowledge</Link>
                <Link className="sm-nav-link" to="/docs">Docs</Link>
                <Link className="sm-nav-link" to={`/tutors/${user.id}/details`}>My details</Link>
              </>)}

              {user?.role === "parent" && (<>
                <Link className="sm-nav-link" to={`/parents/${user.id}`}>Home</Link>
                <Link className="sm-nav-link" to={`/parents/${user.id}/payments`}>Payments</Link>
              </>)}

              {user?.role === "teacher" && (<>
                <Link className="sm-nav-link" to={`/teachers/${user.id}`}>Home</Link>
                <Link className="sm-nav-link" to="/skills">Skills</Link>
                <Link className="sm-nav-link" to="/skills-s6">Skills S6</Link>
                <Link className="sm-nav-link" to="/templates">Templates</Link>
                <Link className="sm-nav-link" to="/knowledge">Knowledge</Link>
                <Link className="sm-nav-link" to="/docs">Docs</Link>
              </>)}

              {user?.role === "student" && (<>
                <Link className="sm-nav-link" to={`/students/${user.id}/`}>Home</Link>
                <Link className="sm-nav-link" to={`/students/${user.id}/booking`}>Bookings</Link>
                <Link className="sm-nav-link" to={`/students/${user.id}/past-tests`}>Past Tests</Link>
                <Link className="sm-nav-link" to={`/students/${user.id}/details`}>My details</Link>
              </>)}

            </div>
          </div>

          <div className="sm-nav-right">
            {devUsers.map(u => (
              <button key={u.label} className="sm-dev-btn" onClick={() => devLoginAs(u.email, u.password)}>
                {u.label}
              </button>
            ))}
            {user && (
              <>
                <span className="sm-nav-user">{user.first_name} ({user.role})</span>
                {user.role === "student" && (
                  <button className="sm-nav-link" onClick={switchToParent}>Parent</button>
                )}
                <button
                  className="sm-nav-link"
                  onClick={() => {
                    apiFetch("/api/auth/logout/", { method: "POST", credentials: "include" });
                    localStorage.removeItem("user");
                    localStorage.removeItem("access");
                    localStorage.removeItem("refresh");
                    window.location.href = "/login";
                  }}
                >
                  Sign out
                </button>
              </>
            )}
          </div>
        </nav>
      )}

      {/* Incoming call notification for students */}
      {!hideNav && user?.role === "student" && <IncomingCallBanner />}

      {header}

      {/* Page content */}
      <div className="container-fluid">{children}</div>
    </div>
  );
}
