import { useEffect, useState } from "react";
import { ProgressChart } from "./components/ProgressChart";
import { Link, useNavigate } from "react-router-dom";
import { apiFetch } from "../utils/apiFetch";
import { dashboardPath } from "../utils/dashboardPath";
import "./ParentHomePage.css";
import { useYears } from "../utils/useYears";

interface NextBooking {
  start_iso: string;
  start_time: string;
  end_time: string;
  day_str: string;
  booking_type: "weekly" | "adhoc";
  tutor_name: string | null;
}

interface Child {
  id: number;
  first_name: string;
  last_name: string;
  year_level: string | null;
  school_name: string | null;
  test_count: number;
  latest_test_date: string | null;
  latest_session_date: string | null;
  tutor_name: string | null;
  next_booking: NextBooking | null;
  syllabus_percent: number | null;
}

interface ParentData {
  parent: {
    id: number;
    first_name: string;
    last_name: string;
    email: string;
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

  async function downloadReport(sessionId: number) {
    setDownloading(sessionId);
    try {
      const res = await apiFetch(`/api/tests/${sessionId}/report/`);
      if (!res.ok) { alert("Failed to generate report"); return; }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = `progress_report_${sessionId}.pdf`;
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
                        {s.status === "abandoned" && (
                          <span className="badge bg-secondary ms-2" style={{ fontSize: 11 }}>Abandoned</span>
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
                          onClick={e => { e.stopPropagation(); downloadReport(s.id); }}
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
  const [tab, setTab] = useState<"overview" | "assessments">("overview");

  useEffect(() => {
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

    function fetchPending() {
      apiFetch("/api/payments/pending/")
        .then((r) => r.ok ? r.json() : { payments: [] })
        .then((d) => setPendingPayments(d.payments || []))
        .catch(() => {});
    }
    fetchPending();
    const interval = setInterval(fetchPending, 30000);
    return () => clearInterval(interval);
  }, []);

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

  async function handleRemoveTutor(childId: number) {
    try {
      const res = await apiFetch("/api/auth/remove_tutor/", {
        method: "POST",
        body: JSON.stringify({ child_id: childId }),
      });
      if (!res.ok) return;
      setData((prev) =>
        prev
          ? {
              ...prev,
              children: prev.children.map((c) =>
                c.id === childId ? { ...c, tutor_name: null } : c
              ),
            }
          : prev
      );
    } catch {}
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
            <Link to={`/parents/${parent.id}`} className="ph-nav-logout" style={{ textDecoration: "none" }}>Dashboard</Link>
            {hasTutor && <Link to={`/parents/${parent.id}/bookings`} className="ph-nav-logout" style={{ textDecoration: "none" }}>Bookings</Link>}
            {hasTutor && <Link to={`/parents/${parent.id}/payments`} className="ph-nav-logout" style={{ textDecoration: "none" }}>Payments</Link>}
          </div>
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

      {/* ── Tabs ─────────────────────────────────── */}
      <div className="ph-body" style={{ paddingBottom: 0 }}>
        <div style={{ display: "flex", gap: 0, borderBottom: "2px solid var(--sm-border-light, #E8E0D6)" }}>
          {(["overview", "assessments"] as const).map(t => (
            <button
              key={t}
              onClick={() => setTab(t)}
              style={{
                background: "none", border: "none", cursor: "pointer",
                padding: "0.6rem 1.25rem",
                fontFamily: "var(--font-body, Inter, sans-serif)",
                fontSize: "0.9rem", fontWeight: tab === t ? 600 : 400,
                color: tab === t ? "var(--sm-orange, #FF8C42)" : "var(--sm-text-muted, #8A7F74)",
                borderBottom: tab === t ? "2px solid var(--sm-orange, #FF8C42)" : "2px solid transparent",
                marginBottom: "-2px",
              }}
            >
              {t === "overview" ? "Overview" : "Assessments"}
            </button>
          ))}
        </div>
      </div>

      {/* ── Body ─────────────────────────────────── */}
      <main className="ph-body">

        {tab === "overview" && <>
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

        {tab === "assessments" && <AssessmentsTab children={children} />}

      </main>
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
}: {
  child: Child;
  parentId: number;
  launching: boolean;
  onLaunchAssessment: () => void;
  onFindTutor: () => void;
  onRemoveTutor: () => void;
}) {
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

      {child.next_booking && (
        <Link
          to={`/parents/${parentId}/bookings`}
          style={{ textDecoration: "none" }}
        >
          <div style={{
            display: "flex",
            alignItems: "flex-start",
            gap: "0.6rem",
            background: "var(--sm-bg-warm, #FFF8F0)",
            border: "1px solid var(--sm-orange-light, #FFDBB5)",
            borderRadius: "var(--radius-md, 8px)",
            padding: "0.65rem 0.85rem",
            fontSize: 13,
            cursor: "pointer",
          }}>
            <span style={{ fontSize: 16, lineHeight: 1.3, flexShrink: 0 }}>📅</span>
            <div>
              <div style={{ fontWeight: 600, color: "var(--sm-text, #2D2D2D)", marginBottom: 1 }}>
                Next appointment
              </div>
              <div style={{ color: "var(--sm-text-secondary, #5A5047)" }}>
                {fmtBooking(child.next_booking)}
              </div>
            </div>
          </div>
        </Link>
      )}

      <div className="mt-3">
        <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 6 }}>Progress</div>
        {child.syllabus_percent != null && child.syllabus_percent > 0 && child.year_level && (
          <div style={{ fontSize: 13, color: "var(--sm-text-secondary, #5A5047)", marginBottom: 8 }}>
            {child.first_name} is {child.syllabus_percent}% of the way through the Year {child.year_level.replace(/^year\s*/i, "")} syllabus.
          </div>
        )}
        <ProgressChart studentId={child.id} />
      </div>

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
          <div className="ph-tooltip-wrap" data-tooltip="A qualified tutor joins your child in a live session to walk them through each question. Great for younger learners or children who benefit from a little extra support. Book a time that suits you.">
            <button className="sm-btn-secondary" disabled style={{ width: "100%" }}>
              Assisted Assessment $20
            </button>
          </div>
        )}
        {!child.tutor_name && (
          <button className="sm-btn-secondary" onClick={onFindTutor}>
            Find Tutor
          </button>
        )}
        {hasTests && (
          <button className="sm-btn-secondary" disabled>
            View Report
          </button>
        )}
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
    if (!firstName.trim() || !lastName.trim() || !yearLevel) {
      setError("First name, last name and year level are required.");
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
        year_level: d.year_level,
        school_name: d.school_name,
        test_count: 0,
        latest_test_date: null,
        latest_session_date: null,
        tutor_name: null,
        next_booking: null,
        syllabus_percent: null,
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
