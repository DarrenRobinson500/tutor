import { Link } from "react-router-dom";
import { useEffect } from "react";
import { apiFetch } from "../../utils/apiFetch";
import { dashboardPath } from "../../utils/dashboardPath";
import { IncomingCallBanner } from "./IncomingCallBanner";

const NAV_STYLES = `
  .sm-layout-nav {
    background: #2D2D2D;
    border-bottom: 3px solid #FF8C42;
    padding: 0 1.5rem;
    min-height: 60px;
    position: sticky;
    top: 0;
    z-index: 100;
  }
  .sm-layout-nav .container-fluid {
    min-height: 60px;
  }
  @media (max-width: 991px) {
    .sm-layout-nav {
      padding-bottom: 0.75rem;
    }
  }
  .sm-layout-nav .navbar-brand {
    display: flex;
    align-items: center;
    padding: 0;
    margin-right: 2rem;
  }
  .sm-layout-nav .navbar-brand img {
    height: 28px;
    width: auto;
  }
  .sm-layout-nav .nav-link {
    color: rgba(255,255,255,0.75) !important;
    font-size: 0.875rem;
    font-weight: 500;
    padding: 0.35rem 0.75rem !important;
    border-radius: 6px;
    transition: color 0.15s, background 0.15s;
  }
  .sm-layout-nav .nav-link:hover {
    color: #fff !important;
    background: rgba(255,140,66,0.15);
  }
  .sm-layout-nav .nav-link.active {
    color: #FF8C42 !important;
  }
  .sm-layout-nav .sm-nav-user {
    font-size: 0.8125rem;
    color: rgba(255,255,255,0.5);
    margin-right: 0.75rem;
  }
  .sm-layout-nav .sm-nav-logout {
    font-size: 0.8125rem;
    color: rgba(255,255,255,0.5);
    background: none;
    border: 1px solid rgba(255,255,255,0.15);
    border-radius: 6px;
    padding: 0.3rem 0.75rem;
    cursor: pointer;
    transition: color 0.15s, border-color 0.15s;
  }
  .sm-layout-nav .sm-nav-logout:hover {
    color: #fff;
    border-color: rgba(255,255,255,0.4);
  }
  .sm-dev-btn {
    font-size: 0.75rem;
    padding: 0.2rem 0.6rem;
    border-radius: 4px;
    border: 1px solid rgba(255,200,0,0.4);
    background: rgba(255,200,0,0.12);
    color: rgba(255,220,80,0.9);
    cursor: pointer;
    transition: background 0.15s;
  }
  .sm-dev-btn:hover {
    background: rgba(255,200,0,0.25);
    color: #ffd700;
  }
`;


const DEV_USERS = [
  { label: "Admin",   email: "Darren",  password: "Darren"  },
  { label: "Parent",  email: "Amanda",  password: "Amanda"  },
  { label: "Student", email: "Michael", password: "Michael" },
  { label: "Tutor",   email: "Alex",    password: "Alex"    },
];

export function Layout({ children }: { children: React.ReactNode }) {
  const storedUser = localStorage.getItem("user");
  const user = storedUser ? JSON.parse(storedUser) : null;
  const access = localStorage.getItem("access");
  const isDev = process.env.NODE_ENV === "development";

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

  async function devSwitch(name: string) {
    const res = await fetch("/api/auth/dev_login/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username: name })
    });

    const data = await res.json();

    if (data.id) {
      localStorage.setItem("user", JSON.stringify(data));
      window.location.reload();
    }
  }

  async function switchToParent() {
    const res = await fetch("/api/auth/dev_switch_to_parent/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ student_id: user?.id })
    });
    const data = await res.json();
    if (data.id) {
      localStorage.setItem("user", JSON.stringify(data));
      localStorage.setItem("access", data.access);
      localStorage.setItem("refresh", data.refresh);
      window.location.href = `/parents/${data.id}`;
    }
  }


  // Hooks must always run
  useEffect(() => {
    // If no access token, do nothing — Layout will just render children
    if (!access) return;

    if (!user) {
      window.location.href = "/login";
      return;
    }

//     if (user.role === "tutor") {
//       window.location.href = `/tutor/${user.id}`;
//     } else if (user.role === "student") {
//       window.location.href = `/student/${user.id}`;
//     } else if (user.role === "parent") {
//       window.location.href = `/parent/${user.id}`;
//     } else if (user.role === "admin") {
//       window.location.href = `/admin/tutors`;
//     }
  }, [access, user]);

  // Early return is now AFTER the hook
  if (!access) {
    return <div>{children}</div>;
  }

  return (
    <>
      <style>{NAV_STYLES}</style>

      {/* Navbar */}
      <nav className="navbar navbar-expand-lg sm-layout-nav">
        <div className="container-fluid px-0">
          <Link className="navbar-brand" to={dashboardPath()}>
            <img src="/subjectmatter_wordmark_orange.svg" alt="SubjectMatter" />
          </Link>
          <button className="navbar-toggler border-0" type="button" data-bs-toggle="collapse" data-bs-target="#mainNavbar" style={{ filter: "invert(1)" }}>
            <span className="navbar-toggler-icon"></span>
          </button>
          <div className="collapse navbar-collapse" id="mainNavbar">
            <ul className="navbar-nav me-auto mb-2 mb-lg-0">

              {user?.role === "admin" && (
                <>
                  <li className="nav-item"><Link className="nav-link" to="/admin">Home</Link></li>
                  <li className="nav-item"><Link className="nav-link" to="/admin/tutors">Tutors</Link></li>
                  <li className="nav-item"><Link className="nav-link" to="/admin/students">Students</Link></li>
                  <li className="nav-item"><Link className="nav-link" to="/admin/payments">Payments</Link></li>
                  <li className="nav-item"><Link className="nav-link" to="/admin/sms">Messages</Link></li>
                  <li className="nav-item"><Link className="nav-link" to="/admin/emails">Emails</Link></li>
                  <li className="nav-item"><Link className="nav-link" to="/skills">Skills</Link></li>
                  <li className="nav-item"><Link className="nav-link" to="/skills-s6">Skills S6</Link></li>
                  <li className="nav-item"><Link className="nav-link" to="/templates">Templates</Link></li>
                  <li className="nav-item"><Link className="nav-link" to="/knowledge">Knowledge</Link></li>
                  <li className="nav-item"><Link className="nav-link" to="/feedback">Feedback</Link></li>
                  <li className="nav-item"><Link className="nav-link" to="/principles">Principles</Link></li>
                  <li className="nav-item"><Link className="nav-link" to="/docs">Docs</Link></li>
</>
              )}

              {user?.role === "tutor" && (
                <>
                  <li className="nav-item"><Link className="nav-link" to={`/tutors/${user.id}/`}>Home</Link></li>
                  <li className="nav-item"><Link className="nav-link" to={`/tutors/${user.id}/booking`}>Bookings</Link></li>
                  <li className="nav-item"><Link className="nav-link" to={`/tutors/${user.id}/post-tuition`}>Post Tuition</Link></li>
                  <li className="nav-item"><Link className="nav-link" to={`/tutors/${user.id}/payments`}>Payments</Link></li>
                  <li className="nav-item"><Link className="nav-link" to={`/tutors/${user.id}/sms`}>Messages</Link></li>
                  <li className="nav-item"><Link className="nav-link" to="/skills">Skills</Link></li>
                  <li className="nav-item"><Link className="nav-link" to="/skills-s6">Skills S6</Link></li>
                  <li className="nav-item"><Link className="nav-link" to="/templates">Templates</Link></li>
                  <li className="nav-item"><Link className="nav-link" to="/knowledge">Knowledge</Link></li>
                  <li className="nav-item"><Link className="nav-link" to="/docs">Docs</Link></li>
                </>
              )}

              {user?.role === "parent" && (
                <>
                  <li className="nav-item"><Link className="nav-link" to={`/parents/${user.id}`}>Home</Link></li>
                  <li className="nav-item"><Link className="nav-link" to={`/parents/${user.id}/payments`}>Payments</Link></li>
                </>
              )}

              {user?.role === "teacher" && (
                <>
                  <li className="nav-item"><Link className="nav-link" to={`/teachers/${user.id}`}>Home</Link></li>
                  <li className="nav-item"><Link className="nav-link" to="/skills">Skills</Link></li>
                  <li className="nav-item"><Link className="nav-link" to="/skills-s6">Skills S6</Link></li>
                  <li className="nav-item"><Link className="nav-link" to="/templates">Templates</Link></li>
                  <li className="nav-item"><Link className="nav-link" to="/knowledge">Knowledge</Link></li>
                  <li className="nav-item"><Link className="nav-link" to="/docs">Docs</Link></li>
                </>
              )}

              {user?.role === "student" && (
                <>
                  <li className="nav-item"><Link className="nav-link" to={`/students/${user.id}/`}>Home</Link></li>
                  <li className="nav-item"><Link className="nav-link" to={`/students/${user.id}/booking`}>Bookings</Link></li>
                  <li className="nav-item"><Link className="nav-link" to={`/students/${user.id}/past-tests`}>Past Tests</Link></li>
                </>
              )}

            </ul>

            {isDev && (
              <div className="d-flex align-items-center gap-1 me-3">
                {DEV_USERS.map(u => (
                  <button key={u.label} className="sm-dev-btn" onClick={() => devLoginAs(u.email, u.password)}>
                    {u.label}
                  </button>
                ))}
              </div>
            )}

            {user && (
              <div className="d-flex align-items-center gap-2">
                <span className="sm-nav-user">{user.first_name} ({user.role})</span>
                {user.role === "student" && (
                  <button className="sm-nav-logout" onClick={switchToParent}>
                    Parent
                  </button>
                )}
                <button
                  className="sm-nav-logout"
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
              </div>
            )}

          </div>
        </div>
      </nav>

      {/* Incoming call notification for students */}
      {user?.role === "student" && <IncomingCallBanner />}

      {/* Page content */}
      <div className="container-fluid">{children}</div>
    </>
  );
}