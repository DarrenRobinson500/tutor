import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Layout } from "./components/Layout";
import { apiFetch } from "../utils/apiFetch";

interface TeacherClass {
  id: number;
  name: string;
  year_level: string;
  code: string;
  student_count: number;
  created_at: string;
  focus_areas: string[];
}

interface Profile {
  first_name: string;
  last_name: string;
  school_name: string;
}

export function TeacherHomePage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [classes, setClasses] = useState<TeacherClass[]>([]);
  const [loading, setLoading] = useState(true);

  // Create-class form
  const [showForm, setShowForm] = useState(false);
  const [className, setClassName] = useState("");
  const [yearLevel, setYearLevel] = useState("");
  const [creating, setCreating] = useState(false);
  const [formError, setFormError] = useState("");

  function load() {
    apiFetch(`/api/teachers/${id}/home/`)
      .then((r) => r.json())
      .then((data) => {
        setProfile(data.profile);
        setClasses(data.classes ?? []);
      })
      .finally(() => setLoading(false));
  }

  useEffect(() => { load(); }, [id]);

  async function handleCreateClass(e: React.FormEvent) {
    e.preventDefault();
    setFormError("");
    if (!className.trim() || !yearLevel.trim()) {
      setFormError("Class name and year level are required.");
      return;
    }
    setCreating(true);
    try {
      const res = await apiFetch(`/api/teachers/${id}/create_class/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: className.trim(), year_level: yearLevel.trim() }),
      });
      const data = await res.json();
      if (!res.ok) { setFormError(data.error || "Failed to create class."); return; }
      setShowForm(false);
      setClassName("");
      setYearLevel("");
      load();
    } finally {
      setCreating(false);
    }
  }

  if (loading) return <Layout><div className="container mt-4">Loading…</div></Layout>;

  return (
    <Layout>
      <div className="container mt-4">
        <div className="d-flex align-items-center justify-content-between mb-3">
          <div>
            <h1 className="mb-0">
              Welcome, {profile?.first_name}
            </h1>
            {profile?.school_name && (
              <p className="text-muted mb-0">{profile.school_name}</p>
            )}
          </div>
          <button
            className="btn btn-primary"
            onClick={() => setShowForm((v) => !v)}
          >
            {showForm ? "Cancel" : "+ New Class"}
          </button>
        </div>

        {/* ── Create class form ─────────────────────── */}
        {showForm && (
          <div className="card mb-4 border-primary">
            <div className="card-body">
              <h5 className="card-title mb-3">Create a New Class</h5>
              {formError && <div className="alert alert-danger">{formError}</div>}
              <form onSubmit={handleCreateClass}>
                <div className="row g-3 align-items-end">
                  <div className="col-md-4">
                    <label className="form-label fw-semibold">Class name</label>
                    <input
                      className="form-control"
                      placeholder="e.g. 7M, Year 10 Advanced"
                      value={className}
                      onChange={(e) => setClassName(e.target.value)}
                    />
                  </div>
                  <div className="col-md-3">
                    <label className="form-label fw-semibold">Year level</label>
                    <select
                      className="form-select"
                      value={yearLevel}
                      onChange={(e) => setYearLevel(e.target.value)}
                    >
                      <option value="">Select…</option>
                      {["K","1","2","3","4","5","6","7","8","9","10","11","12"].map((y) => (
                        <option key={y} value={y}>Year {y}</option>
                      ))}
                    </select>
                  </div>
                  <div className="col-md-3">
                    <button type="submit" className="btn btn-primary w-100" disabled={creating}>
                      {creating ? "Creating…" : "Create Class"}
                    </button>
                  </div>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* ── Class list ───────────────────────────── */}
        {classes.length === 0 ? (
          <div className="text-center py-5 text-muted">
            <p style={{ fontSize: "3rem" }}>📚</p>
            <h4>No classes yet</h4>
            <p>Create your first class to get started.</p>
            <button className="btn btn-primary" onClick={() => setShowForm(true)}>
              + New Class
            </button>
          </div>
        ) : (
          <div className="row g-3">
            {classes.map((tc) => (
              <div key={tc.id} className="col-md-4">
                <div
                  className="card h-100 shadow-sm"
                  style={{ cursor: "pointer", borderTop: "3px solid var(--sm-orange, #FF8C42)" }}
                  onClick={() => navigate(`/teachers/${id}/classes/${tc.id}`)}
                >
                  <div className="card-body">
                    <div className="d-flex justify-content-between align-items-start">
                      <h4 className="card-title mb-1">{tc.name}</h4>
                      <span className="badge bg-secondary">Year {tc.year_level}</span>
                    </div>
                    <p className="text-muted mb-1" style={{ fontSize: 13 }}>
                      {tc.student_count} student{tc.student_count !== 1 ? "s" : ""}
                    </p>
                    {tc.focus_areas?.length > 0 && (
                      <p className="text-muted mb-2" style={{ fontSize: 12 }}>
                        {tc.focus_areas.join(", ")}
                      </p>
                    )}
                    <div className="d-flex gap-2 mt-3">

                      <button
                        className="btn btn-sm btn-outline-primary"
                        onClick={(e) => {
                          e.stopPropagation();
                          navigate(`/teachers/${id}/classes/${tc.id}`);
                        }}
                      >
                        Students
                      </button>

                      <button
                        className="btn btn-sm btn-outline-primary"
                        onClick={(e) => {
                          e.stopPropagation();
                          navigate(`/teachers/${id}/classes/${tc.id}/focus`);
                        }}
                      >
                        Focus Areas
                      </button>

                      <button
                        className="btn btn-sm btn-outline-primary"
                        onClick={(e) => {
                          e.stopPropagation();
                          navigate(`/teachers/${id}/classes/${tc.id}/assessment-setup`);
                        }}
                      >
                        Class Assessment
                      </button>

                      <button
                        className="btn btn-sm btn-outline-primary"
                        onClick={(e) => {
                          e.stopPropagation();
                          navigate(`/teachers/${id}/classes/${tc.id}/gap-report`);
                        }}
                      >
                        Gap Report
                      </button>

                    </div>
                    <p className="text-muted mt-2 mb-0" style={{ fontSize: 11 }}>
                      Join code: <strong>{tc.code}</strong>
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </Layout>
  );
}
