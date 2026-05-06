import { useEffect, useState } from "react";
import { ProgressChart } from "./components/ProgressChart";
import { Link, useNavigate } from "react-router-dom";
import { apiFetch } from "../utils/apiFetch";
import "./ParentHomePage.css";
import { useYears } from "../utils/useYears";

interface Child {
  id: number;
  first_name: string;
  last_name: string;
  year_level: string | null;
  school_name: string | null;
  test_count: number;
  latest_test_date: string | null;
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

export default function ParentHomePage() {
  const navigate = useNavigate();
  const [data, setData] = useState<ParentData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showAddChild, setShowAddChild] = useState(false);
  const [launchingFor, setLaunchingFor] = useState<number | null>(null);

  useEffect(() => {
    apiFetch("/api/auth/parent_home/")
      .then((res) => {
        if (!res.ok) throw new Error("Not authorised");
        return res.json();
      })
      .then((d) => setData(d))
      .catch(() => {
        setError("Unable to load dashboard. Please try signing in again.");
      })
      .finally(() => setLoading(false));
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
        childFirstName: child.first_name,
        yearGroup,
        parentHasDistributor: false,
      },
    });
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

  return (
    <div className="ph-page">

      {/* ── Navbar ───────────────────────────────── */}
      <nav className="ph-nav">
        <Link to="/" className="ph-nav-logo">
          <img src="/subjectmatter_wordmark.svg" alt="SubjectMatter" />
        </Link>
        <div className="ph-nav-right">
          <span className="ph-nav-user">{parent.first_name} {parent.last_name}</span>
          <Link to={`/parents/${parent.id}/payments`} className="ph-nav-logout" style={{ textDecoration: "none" }}>Payments</Link>
          <button className="ph-nav-logout" onClick={handleLogout}>Sign out</button>
        </div>
      </nav>

      {/* ── Header ───────────────────────────────── */}
      <header className="ph-header">
        <div className="ph-header-inner">
          <h1 className="ph-greeting">Welcome back, {parent.first_name}.</h1>
        </div>
      </header>

      {/* ── Body ─────────────────────────────────── */}
      <main className="ph-body">

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
                launching={launchingFor === child.id}
                onLaunchAssessment={() => handleLaunchAssessment(child.id)}
                onFindTutor={() => handleFindTutor(child)}
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

      </main>
    </div>
  );
}

/* ── Child card ──────────────────────────────────────────────── */
function ChildCard({
  child,
  launching,
  onLaunchAssessment,
  onFindTutor,
}: {
  child: Child;
  launching: boolean;
  onLaunchAssessment: () => void;
  onFindTutor: () => void;
}) {
  const initials = `${child.first_name[0] ?? ""}${child.last_name[0] ?? ""}`.toUpperCase();
  const hasTests = child.test_count > 0;

  const statusText = hasTests
    ? `Last assessed: ${new Date(child.latest_test_date!).toLocaleDateString("en-AU", { day: "numeric", month: "long", year: "numeric" })}`
    : "No assessment completed yet";

  return (
    <div className="ph-child-card">
      <div className="ph-child-header">
        <div className="ph-child-avatar">{initials}</div>
        <div>
          <div className="ph-child-name">{child.first_name} {child.last_name}</div>
          <div className="ph-child-meta">
            {child.year_level || "Year not set"}
            {child.school_name ? ` · ${child.school_name}` : ""}
          </div>
        </div>
      </div>

      {hasTests && (
        <div className="ph-child-status done">
          <div className="ph-status-dot" />
          {statusText}
        </div>
      )}

      <div className="mt-3">
        <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 6 }}>Progress</div>
        <ProgressChart studentId={child.id} />
      </div>

      <div className="ph-child-actions">
        <button
          className="sm-btn-primary"
          onClick={onLaunchAssessment}
          disabled={launching}
        >
          {launching ? "Starting…" : "Start Free Assessment"}
        </button>
        <button className="sm-btn-secondary" disabled>
          Assisted Assessment $20
        </button>
        <button className="sm-btn-secondary" onClick={onFindTutor}>
          Find Tutor
        </button>
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
