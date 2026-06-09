import { useEffect, useState } from "react";
import { ProgressChart } from "./components/ProgressChart";
import { Link, useNavigate, useLocation } from "react-router-dom";
import { apiFetch } from "../utils/apiFetch";
import { dashboardPath } from "../utils/dashboardPath";
import "./ParentHomePage.css";
import { useYears } from "../utils/useYears";

/* ── Star rating ─────────────────────────────────────────────── */
function StarRating({ value, onChange }: { value: number; onChange: (v: number) => void }) {
  const [hovered, setHovered] = useState(0);
  return (
    <div style={{ display: "flex", gap: 4, fontSize: "1.8rem", cursor: "pointer" }}>
      {[1, 2, 3, 4, 5].map(n => (
        <span
          key={n}
          style={{ color: n <= (hovered || value) ? "#f59e0b" : "#d1d5db", transition: "color 0.1s" }}
          onMouseEnter={() => setHovered(n)}
          onMouseLeave={() => setHovered(0)}
          onClick={() => onChange(n)}
        >★</span>
      ))}
    </div>
  );
}

/* ── Remove tutor modal ──────────────────────────────────────── */
function RemoveTutorModal({
  childName,
  tutorName,
  onConfirm,
  onCancel,
}: {
  childName: string;
  tutorName: string;
  onConfirm: (rating: number | null, comment: string) => void;
  onCancel: () => void;
}) {
  const [rating, setRating] = useState(0);
  const [comment, setComment] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleConfirm() {
    setSubmitting(true);
    await onConfirm(rating > 0 ? rating : null, comment.trim());
    setSubmitting(false);
  }

  return (
    <div style={{
      position: "fixed", inset: 0, background: "rgba(0,0,0,0.45)",
      display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000,
    }}>
      <div style={{
        background: "#fff", borderRadius: 16, padding: "2rem", maxWidth: 440, width: "90%",
        boxShadow: "0 8px 32px rgba(0,0,0,0.18)",
      }}>
        <h3 style={{ marginBottom: "0.5rem", fontFamily: "var(--font-display, Lora, serif)", fontSize: "1.2rem" }}>
          Remove {tutorName}?
        </h3>
        <p style={{ color: "var(--sm-text-muted, #8A7F74)", fontSize: "0.9rem", marginBottom: "1.25rem" }}>
          This will cancel all upcoming sessions between {childName} and {tutorName}.
        </p>

        <div style={{ marginBottom: "1rem" }}>
          <div style={{ fontWeight: 600, fontSize: "0.9rem", marginBottom: "0.4rem" }}>
            How would you rate your experience with {tutorName}? <span style={{ color: "var(--sm-text-muted)", fontWeight: 400 }}>(optional)</span>
          </div>
          <StarRating value={rating} onChange={setRating} />
        </div>

        <div style={{ marginBottom: "1.5rem" }}>
          <label style={{ fontWeight: 600, fontSize: "0.9rem", display: "block", marginBottom: "0.4rem" }}>
            Any feedback? <span style={{ color: "var(--sm-text-muted)", fontWeight: 400 }}>(optional)</span>
          </label>
          <textarea
            className="sm-input"
            rows={3}
            placeholder="Tell us about your experience…"
            value={comment}
            onChange={e => setComment(e.target.value)}
            style={{ width: "100%", resize: "vertical" }}
          />
        </div>

        <div style={{ display: "flex", gap: "0.75rem", justifyContent: "flex-end" }}>
          <button className="sm-btn-secondary" onClick={onCancel} disabled={submitting}>
            Keep tutor
          </button>
          <button
            className="sm-btn-primary"
            style={{ background: "#dc3545", borderColor: "#dc3545" }}
            onClick={handleConfirm}
            disabled={submitting}
          >
            {submitting ? "Removing…" : "Remove tutor"}
          </button>
        </div>
      </div>
    </div>
  );
}

interface NextBooking {
  start_iso: string;
  start_time: string;
  end_time: string;
  day_str: string;
  booking_type: "weekly" | "adhoc";
  tutor_name: string | null;
  is_assisted_assessment?: boolean;
}

interface Child {
  id: number;
  first_name: string;
  last_name: string;
  username: string;
  year_level: string | null;
  school_name: string | null;
  test_count: number;
  latest_test_date: string | null;
  latest_session_date: string | null;
  tutor_name: string | null;
  next_booking: NextBooking | null;
  syllabus_percent: number | null;
  focus_areas: string[];
}

interface ParentData {
  parent: {
    id: number;
    first_name: string;
    last_name: string;
    email: string;
    mobile: string | null;
  };
  children: Child[];
}

interface PendingPayment {
  id: number;
  tutor_name: string;
  child_name: string;
  session_date: string;
  total_amount: string;
}

function PendingPaymentBanner({ payments, onPay }: { payments: PendingPayment[]; onPay: (id: number) => void }) {
  if (payments.length === 0) return null;
  return (
    <div style={{ marginBottom: "1.5rem" }}>
      {payments.map((p) => (
        <div
          key={p.id}
          style={{
            background: "var(--sm-bg-warm, #FFF8F0)",
            borderLeft: "4px solid var(--sm-orange, #FF8C42)",
            borderRadius: "0 var(--radius-xl, 16px) var(--radius-xl, 16px) 0",
            padding: "1rem 1.25rem",
            marginBottom: "0.75rem",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: "1rem",
            flexWrap: "wrap",
            boxShadow: "var(--shadow-card, 0 2px 8px rgba(0,0,0,.06))",
          }}
        >
          <div>
            <div style={{ fontWeight: 600, fontSize: "0.95rem", marginBottom: "0.2rem" }}>
              Payment due — session with {p.tutor_name}
            </div>
            <div style={{ fontSize: "0.82rem", color: "var(--sm-text-muted, #8A7F74)" }}>
              {p.child_name} · {new Date(p.session_date).toLocaleDateString("en-AU", { day: "numeric", month: "long", year: "numeric" })}
            </div>
          </div>
          <button className="sm-btn-primary" onClick={() => onPay(p.id)} style={{ whiteSpace: "nowrap" }}>
            Pay ${parseFloat(p.total_amount).toFixed(2)}
          </button>
        </div>
      ))}
    </div>
  );
}

/* ── My details tab ──────────────────────────────────────────── */

function MyDetailsTab({
  parent,
  onSaved,
}: {
  parent: ParentData["parent"];
  onSaved: (updated: Partial<ParentData["parent"]>) => void;
}) {
  const [firstName, setFirstName] = useState(parent.first_name);
  const [lastName,  setLastName]  = useState(parent.last_name);
  const [email,     setEmail]     = useState(parent.email);
  const [mobile,    setMobile]    = useState(parent.mobile ?? "");
  const [saving,    setSaving]    = useState(false);
  const [saved,     setSaved]     = useState(false);
  const [err,       setErr]       = useState("");

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true); setErr(""); setSaved(false);
    try {
      const res = await apiFetch("/api/auth/update_parent_details/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ first_name: firstName, last_name: lastName, email, mobile }),
      });
      const d = await res.json();
      if (!res.ok) { setErr(d.error || "Save failed."); return; }
      onSaved({ first_name: firstName, last_name: lastName, email, mobile: mobile || null });
      setSaved(true);
    } catch {
      setErr("Network error.");
    } finally {
      setSaving(false);
    }
  }

  const fieldStyle: React.CSSProperties = {
    width: "100%", padding: "0.5rem 0.75rem", fontSize: "0.95rem",
    border: "1px solid var(--sm-border-light, #E8E0D6)",
    borderRadius: "var(--radius-sm, 6px)", fontFamily: "inherit",
    background: "#fff",
  };
  const labelStyle: React.CSSProperties = {
    display: "block", fontSize: "0.82rem", fontWeight: 600,
    color: "var(--sm-text-muted, #8A7F74)", marginBottom: "0.25rem",
  };

  return (
    <form onSubmit={handleSave} style={{ maxWidth: 480, paddingTop: "1.5rem" }}>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginBottom: "1rem" }}>
        <div>
          <label style={labelStyle}>First name</label>
          <input style={fieldStyle} value={firstName} onChange={e => setFirstName(e.target.value)} required />
        </div>
        <div>
          <label style={labelStyle}>Last name</label>
          <input style={fieldStyle} value={lastName} onChange={e => setLastName(e.target.value)} required />
        </div>
      </div>
      <div style={{ marginBottom: "1rem" }}>
        <label style={labelStyle}>Email</label>
        <input style={fieldStyle} type="email" value={email} onChange={e => setEmail(e.target.value)} required />
      </div>
      <div style={{ marginBottom: "1.5rem" }}>
        <label style={labelStyle}>Mobile</label>
        <input style={fieldStyle} type="tel" value={mobile} onChange={e => setMobile(e.target.value)} placeholder="04xx xxx xxx" />
      </div>
      {err && <p style={{ color: "#C0392B", marginBottom: "0.75rem", fontSize: "0.9rem" }}>{err}</p>}
      {saved && <p style={{ color: "#27AE60", marginBottom: "0.75rem", fontSize: "0.9rem" }}>Details saved.</p>}
      <button type="submit" className="sm-btn-primary" disabled={saving} style={{ minWidth: 120 }}>
        {saving ? "Saving…" : "Save changes"}
      </button>
    </form>
  );
}

/* ── Assessments tab ─────────────────────────────────────────── */

interface SkillResult {
  skill_description: string;
  highest_difficulty_reached: string;
  questions_asked: number;
  questions_correct: number;
}

interface TestSession {
  id: number;
  started_at: string;
  completed_at: string | null;
  status: string;
  test_type?: string;
  skill_results: SkillResult[];
}

const DIFFICULTY_COLOR: Record<string, string> = {
  easy: "#198754", medium: "#fd7e14", hard: "#dc3545", none: "#adb5bd",
};

const TYPE_BADGE: Record<string, [string, string]> = {
  easy: ["bg-success", "Easy"], medium: ["bg-primary", "Moderate"], hard: ["bg-danger", "Hard"],
};

function formatChildNamesForBtn(names: string[]): string {
  if (names.length === 0) return "your child";
  if (names.length === 1) return names[0];
  if (names.length === 2) return `${names[0]} and ${names[1]}`;
  return `${names.slice(0, -1).join(", ")} and ${names[names.length - 1]}`;
}

function fmtDate(iso: string) {
  return new Date(iso).toLocaleDateString("en-AU", { day: "numeric", month: "short", year: "numeric" });
}
function fmtTime(iso: string) {
  return new Date(iso).toLocaleTimeString("en-AU", { hour: "2-digit", minute: "2-digit" });
}
function duration(start: string, end: string | null) {
  if (!end) return "";
  const mins = Math.round((new Date(end).getTime() - new Date(start).getTime()) / 60000);
  return mins < 60 ? `${mins} min` : `${Math.floor(mins / 60)}h ${mins % 60}m`;
}

function AssessmentsTab({ children }: { children: Child[] }) {
  const [sessions, setSessions] = useState<Record<number, TestSession[]>>({});
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<number | null>(null);
  const [downloading, setDownloading] = useState<number | null>(null);

  useEffect(() => {
    if (children.length === 0) { setLoading(false); return; }
    Promise.all(
      children.map(c =>
        apiFetch(`/api/tests/past/?student_id=${c.id}`)
          .then(r => r.json())
          .then((data: TestSession[]) => ({ id: c.id, data }))
      )
    ).then(results => {
      const map: Record<number, TestSession[]> = {};
      results.forEach(r => { map[r.id] = r.data; });
      setSessions(map);
      setLoading(false);
    });
  }, [children]); // eslint-disable-line react-hooks/exhaustive-deps

  async function downloadReport(sessionId: number, firstName: string, startedAt: string) {
    setDownloading(sessionId);
    try {
      const res = await apiFetch(`/api/tests/${sessionId}/report/`);
      if (!res.ok) { alert("Failed to generate report"); return; }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      const d = new Date(startedAt);
      const filename = `${firstName} ${d.getDate()} ${d.toLocaleDateString("en-AU", { month: "short" })} ${String(d.getFullYear()).slice(2)}.pdf`;
      a.href = url; a.download = filename;
      document.body.appendChild(a); a.click(); document.body.removeChild(a);
      setTimeout(() => URL.revokeObjectURL(url), 100);
    } finally { setDownloading(null); }
  }

  if (loading) return (
    <div className="d-flex justify-content-center py-5">
      <div className="spinner-border text-primary" role="status" />
    </div>
  );

  const hasAny = children.some(c => (sessions[c.id] ?? []).length > 0);
  if (!hasAny) return <p style={{ color: "var(--sm-text-muted)" }}>No completed assessments yet.</p>;

  return (
    <div className="d-flex flex-column gap-4">
      {children.map(child => {
        const childSessions = sessions[child.id] ?? [];
        if (childSessions.length === 0) return null;
        return (
          <section key={child.id}>
            <h3 style={{ fontFamily: "var(--font-display, Lora, serif)", fontSize: "1.1rem", fontWeight: 600, marginBottom: "0.75rem" }}>
              {child.first_name} {child.last_name}
            </h3>
            <div className="d-flex flex-column gap-2">
              {childSessions.map(s => {
                const isOpen = expanded === s.id;
                const correct = s.skill_results.reduce((n, r) => n + r.questions_correct, 0);
                const asked   = s.skill_results.reduce((n, r) => n + r.questions_asked, 0);
                return (
                  <div key={s.id} className="card">
                    <button
                      className="card-header border-0 bg-white d-flex justify-content-between align-items-center w-100 text-start"
                      style={{ cursor: "pointer" }}
                      onClick={() => setExpanded(isOpen ? null : s.id)}
                    >
                      <div>
                        <span className="fw-semibold">{fmtDate(s.started_at)}</span>
                        <span className="text-muted ms-2" style={{ fontSize: 13 }}>{fmtTime(s.started_at)}</span>
                        {s.completed_at && (
                          <span className="text-muted ms-2" style={{ fontSize: 13 }}>· {duration(s.started_at, s.completed_at)}</span>
                        )}
                        {s.test_type && TYPE_BADGE[s.test_type] && (
                          <span className={`badge ${TYPE_BADGE[s.test_type][0]} ms-2`} style={{ fontSize: 11 }}>{TYPE_BADGE[s.test_type][1]}</span>
                        )}
                      </div>
                      <div className="d-flex align-items-center gap-3">
                        <span className="text-muted" style={{ fontSize: 13 }}>
                          {correct}/{asked} correct · {s.skill_results.length} skill{s.skill_results.length !== 1 ? "s" : ""}
                        </span>
                        <button
                          className="btn btn-outline-primary btn-sm"
                          style={{ fontSize: 12, padding: "2px 8px" }}
                          disabled={downloading === s.id}
                          onClick={e => { e.stopPropagation(); downloadReport(s.id, child.first_name, s.started_at); }}
                        >
                          {downloading === s.id ? "…" : "PDF"}
                        </button>
                        <span>{isOpen ? "▲" : "▼"}</span>
                      </div>
                    </button>
                    {isOpen && (
                      <div className="card-body p-0">
                        <table className="table table-sm mb-0">
                          <thead className="table-light">
                            <tr>
                              <th>Skill</th>
                              <th style={{ width: 110 }}>Difficulty</th>
                              <th style={{ width: 110 }}>Score</th>
                            </tr>
                          </thead>
                          <tbody>
                            {s.skill_results.map((r, i) => (
                              <tr key={i}>
                                <td style={{ fontSize: 13 }}>{r.skill_description || "—"}</td>
                                <td>
                                  <span className="badge" style={{ background: DIFFICULTY_COLOR[r.highest_difficulty_reached] ?? "#adb5bd", fontSize: 11 }}>
                                    {r.highest_difficulty_reached || "none"}
                                  </span>
                                </td>
                                <td style={{ fontSize: 13 }}>{r.questions_correct}/{r.questions_asked}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </section>
        );
      })}
    </div>
  );
}

export default function ParentHomePage() {
  const navigate = useNavigate();
  const [data, setData] = useState<ParentData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showAddChild, setShowAddChild] = useState(false);
  const [launchingFor, setLaunchingFor] = useState<number | null>(null);
  const [pendingPayments, setPendingPayments] = useState<PendingPayment[]>([]);
  const [isFirstVisit, setIsFirstVisit] = useState(false);
  const location = useLocation();
  const section = location.pathname.endsWith("/reports") ? "reports"
                : location.pathname.endsWith("/details") ? "details"
                : "overview";
  const [removingChild, setRemovingChild] = useState<Child | null>(null);
  const [assistedAssessmentChild, setAssistedAssessmentChild] = useState<Child | null>(null);
  const [devUsers, setDevUsers] = useState([
    { label: "Admin",   email: "Darren",  password: "Darren"  },
    { label: "Parent",  email: "Amanda",  password: "Amanda"  },
    { label: "Student", email: "Michael", password: "Michael" },
    { label: "Tutor",   email: "Alex",    password: "Alex"    },
  ]);

  useEffect(() => {
    fetch(`${(process.env.REACT_APP_API_URL ?? "").replace(/\/$/, "")}/api/settings/`)
      .then(r => r.json())
      .then((d: { dev_users?: typeof devUsers }) => {
        if (Array.isArray(d.dev_users) && d.dev_users.length) setDevUsers(d.dev_users);
      })
      .catch(() => {});
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

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
      if (role === "parent")  window.location.href = `/parents/${data.user.id}`;
      else if (role === "tutor")   window.location.href = `/tutors/${data.user.id}`;
      else if (role === "student") window.location.href = `/students/${data.user.id}`;
      else if (role === "admin")   window.location.href = "/admin";
      else window.location.href = "/";
    } catch { /* ignore */ }
  }

  function loadData() {
    apiFetch("/api/auth/parent_home/")
      .then((res) => {
        if (!res.ok) throw new Error("Not authorised");
        return res.json();
      })
      .then((d) => {
        const key = `parent_visited_${d.parent.id}`;
        if (!localStorage.getItem(key)) {
          setIsFirstVisit(true);
          localStorage.setItem(key, "1");
        }
        setData(d);
      })
      .catch(() => {
        setError("Unable to load dashboard. Please try signing in again.");
      })
      .finally(() => setLoading(false));

    apiFetch("/api/payments/pending/")
      .then((r) => r.ok ? r.json() : { payments: [] })
      .then((d) => setPendingPayments(d.payments || []))
      .catch(() => {});
  }

  useEffect(() => { loadData(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  function handleLogout() {
    localStorage.removeItem("access");
    localStorage.removeItem("refresh");
    localStorage.removeItem("user");
    navigate("/login?tab=parent");
  }

  async function handleLaunchAssessment(childId: number) {
    setLaunchingFor(childId);
    try {
      const res = await apiFetch("/api/auth/launch_assessment/", {
        method: "POST",
        body: JSON.stringify({ child_id: childId }),
      });
      const d = await res.json();
      if (!res.ok) { alert(d.error || "Could not launch assessment."); return; }
      navigate(
        `/assessment-launch?token=${d.token}&student_id=${d.student_id}`
      );
    } catch {
      alert("Something went wrong. Please try again.");
    } finally {
      setLaunchingFor(null);
    }
  }

  function handleFindTutor(child: Child) {
    if (!data) return;
    const match = (child.year_level ?? "").match(/\d+/);
    const yearGroup = match ? parseInt(match[0], 10) : undefined;
    navigate(`/parents/${data.parent.id}/find-tutor`, {
      state: {
        childId: child.id,
        childFirstName: child.first_name,
        yearGroup,
        parentHasDistributor: false,
      },
    });
  }

  function handleRemoveTutor(childId: number) {
    if (!data) return;
    const child = data.children.find(c => c.id === childId) ?? null;
    setRemovingChild(child);
  }

  async function confirmRemoveTutor(rating: number | null, comment: string) {
    if (!removingChild) return;
    try {
      const res = await apiFetch("/api/auth/remove_tutor/", {
        method: "POST",
        body: JSON.stringify({
          child_id: removingChild.id,
          rating,
          rating_comment: comment,
        }),
      });
      if (!res.ok) return;
      setData((prev) =>
        prev
          ? {
              ...prev,
              children: prev.children.map((c) =>
                c.id === removingChild.id ? { ...c, tutor_name: null } : c
              ),
            }
          : prev
      );
    } catch {}
    setRemovingChild(null);
  }

  function onChildAdded(child: Child) {
    setData((prev) =>
      prev ? { ...prev, children: [...prev.children, child] } : prev
    );
    setShowAddChild(false);
  }

  if (loading) {
    return (
      <div style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "#FFFBF5",
        fontFamily: "Inter, system-ui, sans-serif",
      }}>
        <img src="/subjectmatter_logo.svg" alt="" style={{ height: 56 }} />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div style={{ padding: "3rem", textAlign: "center", fontFamily: "Inter, system-ui, sans-serif" }}>
        <p style={{ color: "#C0392B" }}>{error || "Something went wrong."}</p>
        <Link to="/login?tab=parent" style={{ color: "#FF8C42" }}>Sign in again</Link>
      </div>
    );
  }

  const { parent, children } = data;
  const hasTutor = children.some(c => c.tutor_name);

  return (
    <div className="ph-page">

      {/* ── Navbar ───────────────────────────────── */}
      <nav className="ph-nav">
        <div className="ph-nav-left">
          <Link to={dashboardPath()} className="ph-nav-logo">
            <img src="/subjectmatter_wordmark.svg" alt="SubjectMatter" />
          </Link>
          <div className="ph-nav-links">
            <Link to={`/parents/${parent.id}`} className="ph-nav-logout" style={{ textDecoration: "none" }}>Home</Link>
            {hasTutor && <Link to={`/parents/${parent.id}/bookings`} className="ph-nav-logout" style={{ textDecoration: "none" }}>Bookings</Link>}
            {hasTutor && <Link to={`/parents/${parent.id}/payments`} className="ph-nav-logout" style={{ textDecoration: "none" }}>Payments</Link>}
            <Link to={`/parents/${parent.id}/reports`} className="ph-nav-logout" style={{ textDecoration: "none" }}>Reports</Link>
            <Link to={`/parents/${parent.id}/details`} className="ph-nav-logout" style={{ textDecoration: "none" }}>My details</Link>
            <Link to={`/parents/${parent.id}/principles`} className="ph-nav-logout" style={{ textDecoration: "none" }}>Helping your child</Link>
            <Link to={`/parents/${parent.id}/feedback`} className="ph-nav-logout" style={{ textDecoration: "none" }}>Feedback</Link>
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 4, marginRight: 12 }}>
          {devUsers.map(u => (
            <button
              key={u.label}
              onClick={() => devLoginAs(u.email, u.password)}
              style={{
                fontSize: "0.7rem", padding: "0.2rem 0.55rem", borderRadius: 4,
                border: "1px solid rgba(232,119,34,0.3)", background: "rgba(232,119,34,0.08)",
                color: "#b85c14", cursor: "pointer", fontFamily: "Inter, sans-serif",
              }}
            >
              {u.label}
            </button>
          ))}
        </div>
        <div className="ph-nav-right">
          <span className="ph-nav-user">{parent.first_name} {parent.last_name}</span>
          <button className="ph-nav-logout" onClick={handleLogout}>Sign out</button>
        </div>
      </nav>

      {/* ── Header ───────────────────────────────── */}
      <header className="ph-header">
        <div className="ph-header-inner">
          <h1 className="ph-greeting">{isFirstVisit ? `Welcome ${parent.first_name}.` : `Welcome back, ${parent.first_name}.`}</h1>
        </div>
      </header>

      {/* ── Body ─────────────────────────────────── */}
      <main className="ph-body">

        {section === "overview" && <>
          {/* Pending payment banner */}
          <PendingPaymentBanner
            payments={pendingPayments}
            onPay={(id) => navigate(`/payments/${id}/authorise`)}
          />

          {/* Children section */}
          <div className="ph-section-heading">
            <h2 className="ph-section-title">Your children</h2>
          </div>

          {children.length === 0 ? (
            <p style={{ color: "var(--sm-text-muted)", marginBottom: "var(--space-6)" }}>
              No children registered yet. Add one below.
            </p>
          ) : (
            <div className="ph-children-grid">
              {children.map((child) => (
                <ChildCard
                  key={child.id}
                  child={child}
                  parentId={parent.id}
                  launching={launchingFor === child.id}
                  onLaunchAssessment={() => handleLaunchAssessment(child.id)}
                  onFindTutor={() => handleFindTutor(child)}
                  onRemoveTutor={() => handleRemoveTutor(child.id)}
                  onViewReport={() => navigate(`/parents/${parent.id}/reports`)}
                  onAssistedAssessment={() => setAssistedAssessmentChild(child)}
                />
              ))}
            </div>
          )}

          {/* Add child */}
          {!showAddChild ? (
            <button className="ph-add-child-btn" onClick={() => setShowAddChild(true)}>
              + Register another child
            </button>
          ) : (
            <AddChildForm
              onAdded={onChildAdded}
              onCancel={() => setShowAddChild(false)}
            />
          )}
        </>}

        {section === "reports" && <AssessmentsTab children={children} />}

        {section === "details" && (
          <MyDetailsTab
            parent={parent}
            onSaved={(updated) => setData(d => d ? { ...d, parent: { ...d.parent, ...updated } } : d)}
          />
        )}

      </main>

      {removingChild && removingChild.tutor_name && (
        <RemoveTutorModal
          childName={removingChild.first_name}
          tutorName={removingChild.tutor_name}
          onConfirm={confirmRemoveTutor}
          onCancel={() => setRemovingChild(null)}
        />
      )}

      {assistedAssessmentChild && (
        <AssistedAssessmentModal
          child={assistedAssessmentChild}
          parentMobile={data?.parent.mobile ?? null}
          onClose={() => setAssistedAssessmentChild(null)}
          onBooked={() => loadData()}
        />
      )}
    </div>
  );
}

/* ── Assisted Assessment modal ───────────────────────────────── */
interface AASlot {
  tutor_id: number;
  tutor_name: string;
  weekday: number;
  day: string;
  day_full: string;
  start_time: string;
  end_time: string;
}

function fmtMobile(mobile: string): string {
  let digits = mobile.replace(/\D/g, "");
  if (digits.startsWith("61") && digits.length === 11) digits = "0" + digits.slice(2);
  if (digits.length === 10 && digits.startsWith("0")) {
    return `${digits.slice(0, 4)} ${digits.slice(4, 7)} ${digits.slice(7)}`;
  }
  return mobile;
}

function fmtSlotTime(t: string) {
  const [h, m] = t.split(":").map(Number);
  const period = h < 12 ? "am" : "pm";
  const h12 = h % 12 || 12;
  return m ? `${h12}:${m.toString().padStart(2, "0")}${period}` : `${h12}${period}`;
}

// weekday: 0=Mon … 6=Sun (Python convention). Returns the next occurrence of
// that weekday, including today if it matches.
function nextDateForWeekday(weekday: number): Date {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const jsTarget = (weekday + 1) % 7; // convert to JS: 0=Sun,1=Mon…
  let daysAhead = jsTarget - today.getDay();
  if (daysAhead <= 0) daysAhead += 7; // never show today — always next occurrence
  const d = new Date(today);
  d.setDate(today.getDate() + daysAhead);
  return d;
}

function fmtSlotDate(weekday: number): string {
  return nextDateForWeekday(weekday).toLocaleDateString("en-AU", {
    day: "numeric", month: "long",
  });
}

function AssistedAssessmentModal({
  child,
  parentMobile,
  onClose,
  onBooked,
}: {
  child: Child;
  parentMobile: string | null;
  onClose: () => void;
  onBooked: () => void;
}) {
  const [slots, setSlots] = useState<AASlot[] | null>(null);
  const [selected, setSelected] = useState<AASlot | null>(null);
  const [step, setStep] = useState<"slots" | "confirm" | "done">("slots");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    apiFetch("/api/assisted-assessment/slots/")
      .then(r => r.json())
      .then(setSlots)
      .catch(() => setSlots([]));
  }, []);

  async function handleConfirm() {
    if (!selected) return;
    setSubmitting(true);
    setError("");
    try {
      const res = await apiFetch("/api/assisted-assessment/book/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          child_id: child.id,
          tutor_id: selected.tutor_id,
          day_full: selected.day_full,
          date: (() => { const d = nextDateForWeekday(selected.weekday); return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`; })(),
          start_time: selected.start_time,
          end_time: selected.end_time,
        }),
      });
      const d = await res.json();
      if (!res.ok) { setError(d.error || "Something went wrong."); return; }
      setStep("done");
      onBooked();
    } catch {
      setError("Something went wrong. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  // Group slots by day (today's weekday shows as next week via nextDateForWeekday)
  const byDay: Record<string, AASlot[]> = {};
  (slots ?? []).forEach(s => {
    (byDay[s.day_full] ??= []).push(s);
  });
  const days = Object.keys(byDay).sort((a, b) =>
    nextDateForWeekday(byDay[a][0].weekday).getTime() - nextDateForWeekday(byDay[b][0].weekday).getTime()
  );

  const overlayStyle: React.CSSProperties = {
    position: "fixed", inset: 0, background: "rgba(0,0,0,0.45)",
    display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000,
  };
  const boxStyle: React.CSSProperties = {
    background: "#fff", borderRadius: 16, padding: "2rem",
    maxWidth: 540, width: "90%", maxHeight: "85vh", overflowY: "auto",
    boxShadow: "0 8px 32px rgba(0,0,0,0.18)",
  };

  return (
    <div style={overlayStyle} onClick={e => { if (e.target === e.currentTarget) onClose(); }}>
      <div style={boxStyle}>
        <h3 style={{ marginBottom: "0.4rem", fontFamily: "var(--font-display, Lora, serif)", fontSize: "1.2rem" }}>
          Assisted Assessment
        </h3>
        <p style={{ color: "var(--sm-text-muted, #8A7F74)", fontSize: "0.88rem", marginBottom: "1.25rem" }}>
          {selected ? selected.tutor_name.split(" ")[0] : "A tutor"} will guide {child.first_name} through the assessment live. Pay after.
        </p>

        {step === "slots" && (
          <>
            {slots === null && <p style={{ color: "var(--sm-text-muted)" }}>Loading available times…</p>}
            {slots !== null && days.length === 0 && (
              <p style={{ color: "var(--sm-text-muted)" }}>No availability at the moment. Please check back soon.</p>
            )}
            {days.map(day => (
              <div key={day} style={{ marginBottom: "1rem" }}>
                <div style={{ fontWeight: 600, fontSize: "0.85rem", marginBottom: "0.4rem", color: "var(--sm-text-muted, #8A7F74)", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                  {day} · {fmtSlotDate(byDay[day][0].weekday)}
                </div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
                  {byDay[day].map((s, i) => (
                    <button
                      key={i}
                      onClick={() => { setSelected(s); setStep("confirm"); }}
                      style={{
                        border: "1px solid var(--sm-orange-light, #FFDBB5)",
                        borderRadius: 8, padding: "0.45rem 0.85rem",
                        background: "var(--sm-bg-warm, #FFF8F0)",
                        cursor: "pointer", fontSize: "0.88rem",
                        color: "var(--sm-text, #2D2D2D)",
                      }}
                    >
                      {fmtSlotTime(s.start_time)} – {fmtSlotTime(s.end_time)}
                    </button>
                  ))}
                </div>
              </div>
            ))}
            <div style={{ display: "flex", justifyContent: "flex-end", marginTop: "1rem" }}>
              <button className="sm-btn-secondary" onClick={onClose}>Cancel</button>
            </div>
          </>
        )}

        {step === "confirm" && selected && (
          <>
            <div style={{
              background: "var(--sm-bg-warm, #FFF8F0)",
              border: "1px solid var(--sm-orange-light, #FFDBB5)",
              borderRadius: 10, padding: "1rem", marginBottom: "1.25rem",
            }}>
              <div style={{ fontWeight: 600, marginBottom: 4 }}>
                {selected.day_full} {fmtSlotDate(selected.weekday)} · {fmtSlotTime(selected.start_time)} – {fmtSlotTime(selected.end_time)}
              </div>
              <div style={{ fontSize: "0.88rem", color: "var(--sm-text-muted)" }}>
                {child.first_name} · with {selected.tutor_name}
              </div>
            </div>

            <p style={{ fontSize: "0.9rem", marginBottom: "1.5rem" }}>
              A confirmation SMS will be sent to{" "}
              <strong>{parentMobile ? fmtMobile(parentMobile) : "your registered number"}</strong>.{" "}
              Your number will be sent to {selected.tutor_name.split(" ")[0]} (who will help {child.first_name}) so that he can confirm details with you.
            </p>

            {error && <p style={{ color: "#dc3545", fontSize: "0.88rem", marginBottom: "0.75rem" }}>{error}</p>}

            <div style={{ display: "flex", gap: "0.75rem", justifyContent: "flex-end" }}>
              <button className="sm-btn-secondary" onClick={() => setStep("slots")} disabled={submitting}>
                Back
              </button>
              <button className="sm-btn-primary" onClick={handleConfirm} disabled={submitting}>
                {submitting ? "Booking…" : "Confirm Booking"}
              </button>
            </div>
          </>
        )}

        {step === "done" && (
          <>
            <p style={{ fontSize: "0.95rem", marginBottom: "1.5rem" }}>
              Booked! SMS confirmations have been sent. {selected?.tutor_name.split(" ")[0]} will be in touch to confirm the final details.
            </p>
            <div style={{ display: "flex", justifyContent: "flex-end" }}>
              <button className="sm-btn-primary" onClick={onClose}>Close</button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

/* ── Child card ──────────────────────────────────────────────── */
function fmtBooking(nb: NextBooking): string {
  const d = new Date(nb.start_iso);
  const dateStr = d.toLocaleDateString("en-AU", { weekday: "long", day: "numeric", month: "long" });
  const timeStr = d.toLocaleTimeString("en-AU", { hour: "numeric", minute: "2-digit", hour12: true });
  const endD = new Date(nb.start_iso);
  const [endH, endM] = nb.end_time.split(":").map(Number);
  endD.setHours(endH, endM);
  const endStr = endD.toLocaleTimeString("en-AU", { hour: "numeric", minute: "2-digit", hour12: true });
  return `${dateStr}, ${timeStr} – ${endStr}`;
}

function ChildCard({
  child,
  parentId,
  launching,
  onLaunchAssessment,
  onFindTutor,
  onRemoveTutor,
  onViewReport,
  onAssistedAssessment,
}: {
  child: Child;
  parentId: number;
  launching: boolean;
  onLaunchAssessment: () => void;
  onFindTutor: () => void;
  onRemoveTutor: () => void;
  onViewReport: () => void;
  onAssistedAssessment: () => void;
}) {
  const navigate = useNavigate();
  const initials = `${child.first_name[0] ?? ""}${child.last_name[0] ?? ""}`.toUpperCase();
  const hasTests = child.test_count > 0;
  const hasTutor = !!child.tutor_name;
  const displayDate = hasTutor ? child.latest_session_date : child.latest_test_date;
  const displayLabel = hasTutor ? "Last session" : "Last assessed";
  const statusText = displayDate
    ? `${displayLabel}: ${new Date(displayDate).toLocaleDateString("en-AU", { day: "numeric", month: "long", year: "numeric" })}`
    : hasTutor ? "No sessions yet" : "No assessment completed yet";

  return (
    <div className="ph-child-card">
      <div className="ph-child-header">
        <div className="ph-child-avatar">{initials}</div>
        <div>
          <div className="ph-child-name">{child.first_name} {child.last_name}</div>
          <div className="ph-child-meta">
            {child.year_level ? `Year ${child.year_level.replace(/^year\s*/i, "")}` : "Year not set"}
            {child.school_name ? ` · ${child.school_name}` : ""}
          </div>
          {child.tutor_name && (
            <div className="ph-child-tutor">
              Tutor: {child.tutor_name}
              <button className="ph-remove-tutor-btn" onClick={onRemoveTutor}>
                remove
              </button>
            </div>
          )}
        </div>
      </div>

      {displayDate && (
        <div className="ph-child-status done">
          <div className="ph-status-dot" />
          {statusText}
        </div>
      )}

      {child.next_booking && (() => {
        const isAA = child.next_booking.is_assisted_assessment;
        const cardInner = (
          <div style={{
            display: "flex",
            alignItems: "flex-start",
            gap: "0.6rem",
            background: "var(--sm-bg-warm, #FFF8F0)",
            border: "1px solid var(--sm-orange-light, #FFDBB5)",
            borderRadius: "var(--radius-md, 8px)",
            padding: "0.65rem 0.85rem",
            fontSize: 13,
            cursor: isAA ? "default" : "pointer",
          }}>
            <span style={{ fontSize: 16, lineHeight: 1.3, flexShrink: 0 }}>📅</span>
            <div>
              <div style={{ fontWeight: 600, color: "var(--sm-text, #2D2D2D)", marginBottom: 1 }}>
                {isAA ? "Assisted Assessment" : "Next appointment"}
              </div>
              <div style={{ color: "var(--sm-text-secondary, #5A5047)" }}>
                {fmtBooking(child.next_booking)}
              </div>
              {isAA && (
                <div style={{ marginTop: "0.4rem", color: "var(--sm-text-secondary, #5A5047)", fontSize: 12 }}>
                  10 minutes before the session ask {child.first_name} to login to{" "}
                  <a href="https://www.subject-matter.com.au" target="_blank" rel="noreferrer" style={{ color: "inherit" }}>
                    www.subject-matter.com.au
                  </a>{" "}
                  with username: <strong>{child.username}</strong> and their password.
                </div>
              )}
            </div>
          </div>
        );
        return isAA ? cardInner : (
          <Link to={`/parents/${parentId}/bookings`} style={{ textDecoration: "none" }}>
            {cardInner}
          </Link>
        );
      })()}

      {(child.syllabus_percent ?? 0) > 0 && (
        <div className="mt-3">
          <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 6 }}>Progress</div>
          <ProgressChart studentId={child.id} yearLevel={child.year_level} overallPct={child.syllabus_percent ?? undefined} />
        </div>
      )}

      {child.focus_areas.length > 0 && (
        <div className="mt-3">
          <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 6 }}>Focus areas</div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "0.35rem" }}>
            {child.focus_areas.map((fa, i) => (
              <span key={i} style={{
                fontSize: 12, padding: "2px 10px",
                background: "var(--sm-bg-warm, #FFF8F0)",
                border: "1px solid var(--sm-orange-light, #FFDBB5)",
                borderRadius: 20,
                color: "var(--sm-text, #2D2D2D)",
              }}>{fa}</span>
            ))}
          </div>
        </div>
      )}

      <div className="ph-child-actions">
        <div className="ph-tooltip-wrap" data-tooltip="Your child works through the assessment on their own (it takes about 30 min). We'll identify their strengths and areas to focus on. No cost, no commitment.">
          <button
            className="sm-btn-primary"
            onClick={onLaunchAssessment}
            disabled={launching}
            style={{ width: "100%" }}
          >
            {launching ? "Starting…" : "Start Free Assessment"}
          </button>
        </div>
        {!child.tutor_name && (
          <div className="ph-tooltip-wrap" data-tooltip="A qualified tutor joins your child in a live session to walk them through each question. Great for younger learners or children who benefit from a little extra support. Book a time that suits you. Pay when you're happy with the assessment.">
            <button
              className="sm-btn-secondary"
              onClick={onAssistedAssessment}
              style={{ width: "100%" }}
              disabled={!!child.next_booking?.is_assisted_assessment}
            >
              {child.next_booking?.is_assisted_assessment ? "Assisted Assessment Booked" : "Assisted Assessment $20"}
            </button>
          </div>
        )}
        {!child.tutor_name && (
          <button className="sm-btn-secondary" onClick={onFindTutor}>
            Find Tutor
          </button>
        )}
        {hasTests && (
          <button className="sm-btn-secondary" onClick={onViewReport}>
            View Report
          </button>
        )}
        <button
          className="sm-btn-secondary"
          style={{ display: "block", width: "100%", textAlign: "center" }}
          onClick={async () => {
            const res = await apiFetch("/api/auth/child_login/", {
              method: "POST",
              body: JSON.stringify({ child_id: child.id }),
            });
            const data = await res.json();
            if (!res.ok) return;
            localStorage.setItem("access", data.access);
            localStorage.setItem("refresh", data.refresh);
            localStorage.setItem("user", JSON.stringify(data.user));
            navigate(`/students/${child.id}`);
          }}
        >
          Go to {child.first_name}{child.first_name.endsWith("s") ? "'" : "'s"} home page
        </button>
      </div>
    </div>
  );
}

/* ── Add child form ──────────────────────────────────────────── */
function AddChildForm({
  onAdded,
  onCancel,
}: {
  onAdded: (child: Child) => void;
  onCancel: () => void;
}) {
  const years = useYears();
  const [firstName, setFirstName] = useState("");
  const [lastName,  setLastName]  = useState("");
  const [childEmail, setChildEmail] = useState("");
  const [yearLevel, setYearLevel] = useState("");
  const [schoolName, setSchoolName] = useState("");
  const [mobile, setMobile]       = useState("");
  const [password, setPassword]   = useState("");
  const [confirm, setConfirm]     = useState("");
  const [error,  setError]        = useState("");
  const [loading, setLoading]     = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    if (!firstName.trim() || !lastName.trim() || !childEmail.trim() || !yearLevel) {
      setError("First name, last name, email and year level are required.");
      return;
    }
    if (!password) {
      setError("Please choose a password for your child.");
      return;
    }
    if (password !== confirm) {
      setError("Passwords do not match.");
      return;
    }
    setLoading(true);
    try {
      const res = await apiFetch("/api/auth/add_child/", {
        method: "POST",
        body: JSON.stringify({
          first_name: firstName.trim(),
          last_name: lastName.trim(),
          child_email: childEmail.trim(),
          year_level: yearLevel,
          school_name: schoolName.trim(),
          mobile: mobile.trim(),
          password,
          confirm_password: confirm,
        }),
      });
      const d = await res.json();
      if (!res.ok) { setError(d.error || "Failed to add child."); return; }
      onAdded({
        id: d.id,
        first_name: d.first_name,
        last_name: d.last_name,
        username: d.username,
        year_level: d.year_level,
        school_name: d.school_name,
        test_count: 0,
        latest_test_date: null,
        latest_session_date: null,
        tutor_name: null,
        next_booking: null,
        syllabus_percent: null,
        focus_areas: [],
      });
    } catch {
      setError("Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="ph-add-child-form">
      <h3>Register another child</h3>
      {error && (
        <div className="sm-alert sm-alert-error" style={{ marginBottom: "1rem" }}>
          {error}
        </div>
      )}
      <form onSubmit={handleSubmit} noValidate>
        <div className="ph-form-row">
          <div className="sm-form-group">
            <label>First name</label>
            <input type="text" className="sm-input" placeholder="Alex"
              value={firstName} onChange={(e) => setFirstName(e.target.value)} required />
          </div>
          <div className="sm-form-group">
            <label>Last name</label>
            <input type="text" className="sm-input" placeholder="Smith"
              value={lastName} onChange={(e) => setLastName(e.target.value)} required />
          </div>
        </div>

        <div className="sm-form-group">
          <label>Email</label>
          <input type="email" className="sm-input" placeholder="alex@example.com"
            value={childEmail} onChange={(e) => setChildEmail(e.target.value)} required />
        </div>

        <div className="ph-form-row">
          <div className="sm-form-group">
            <label>Year level</label>
            <select className="sm-input" value={yearLevel}
              onChange={(e) => setYearLevel(e.target.value)} required>
              <option value="">Select…</option>
              {years.map((y) => (
                <option key={y.code} value={y.code}>{y.label}</option>
              ))}
            </select>
          </div>
          <div className="sm-form-group">
            <label>Mobile <span style={{ fontWeight: 400, color: "var(--sm-text-muted)" }}>(optional)</span></label>
            <input type="tel" className="sm-input" placeholder="04xx xxx xxx"
              value={mobile} onChange={(e) => setMobile(e.target.value)} />
          </div>
        </div>

        <div className="sm-form-group">
          <label>School name <span style={{ fontWeight: 400, color: "var(--sm-text-muted)" }}>(optional)</span></label>
          <input type="text" className="sm-input" placeholder="e.g. Pymble Ladies' College"
            value={schoolName} onChange={(e) => setSchoolName(e.target.value)} />
        </div>

        <div className="ph-form-row">
          <div className="sm-form-group">
            <label>Password</label>
            <input type="password" className="sm-input" placeholder="Choose a password"
              value={password} onChange={(e) => setPassword(e.target.value)} required />
          </div>
          <div className="sm-form-group">
            <label>Confirm password</label>
            <input type="password" className="sm-input" placeholder="Repeat password"
              value={confirm} onChange={(e) => setConfirm(e.target.value)} required />
          </div>
        </div>

        <div className="ph-form-actions">
          <button type="submit" className="sm-btn-primary" disabled={loading}>
            {loading ? "Adding…" : "Add Child"}
          </button>
          <button type="button" className="sm-btn-secondary" onClick={onCancel}>
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}
