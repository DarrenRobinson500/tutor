import { useEffect, useState } from "react";
import { Layout } from "./components/Layout";
import { apiFetch } from "../utils/apiFetch";

interface AdminJob {
  id: number;
  job_type: "approve_tutor" | "approve_distributor" | "setup_bank_details" | "call_tutor_overdue_review";
  subject_id: number | null;
  first_name: string;
  last_name: string;
  email: string;
  triggered_at: string;
  notes?: string;
  // tutor-specific
  qualification?: string;
  bio?: string;
  year_levels?: string[];
  // distributor-specific
  mobile?: string;
  // bank details
  bank_bsb?: string;
  bank_account?: string;
  bank_name?: string;
}

interface FeedbackItem {
  id: number;
  rating: number;
  rating_comment: string;
  student_name: string;
  tutor_name: string;
  tutor_id: number;
  session_date: string;
  paid_at: string | null;
}

const TYPE_LABEL: Record<string, string> = {
  approve_tutor: "Approve Tutor",
  approve_distributor: "Approve Distributor",
  setup_bank_details: "Setup Bank Details",
  call_tutor_overdue_review: "Call Tutor — Overdue Review",
};

const TYPE_COLOUR: Record<string, string> = {
  approve_tutor: "#cfe2ff",
  approve_distributor: "#d1e7dd",
  setup_bank_details: "#fff3cd",
  call_tutor_overdue_review: "#fde8e8",
};

const TYPE_BORDER: Record<string, string> = {
  approve_tutor: "#9ec5fe",
  approve_distributor: "#a3cfbb",
  setup_bank_details: "#ffc107",
  call_tutor_overdue_review: "#f5a0a0",
};

function Stars({ value }: { value: number }) {
  return (
    <span style={{ color: "#f59e0b", fontSize: "1.1rem", letterSpacing: 1 }}>
      {[1, 2, 3, 4, 5].map(n => (
        <span key={n} style={{ opacity: n <= value ? 1 : 0.2 }}>★</span>
      ))}
    </span>
  );
}

function BankDetailsForm({ job, onSaved }: { job: AdminJob; onSaved: () => void }) {
  const [bsb, setBsb] = useState(job.bank_bsb ?? "");
  const [account, setAccount] = useState(job.bank_account ?? "");
  const [name, setName] = useState(job.bank_name ?? "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function handleSave() {
    if (!bsb.trim() || !account.trim()) {
      setError("BSB and account number are required.");
      return;
    }
    setSaving(true);
    setError("");
    try {
      const res = await apiFetch(`/api/admin-jobs/${job.id}/save_bank_details/`, {
        method: "POST",
        body: JSON.stringify({ bank_bsb: bsb.trim(), bank_account: account.trim(), bank_name: name.trim() }),
      });
      if (!res.ok) {
        const d = await res.json();
        setError(d.error ?? "Failed to save.");
      } else {
        onSaved();
      }
    } catch {
      setError("Network error.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div style={{ fontSize: "0.9rem" }}>
      <p className="text-muted mb-3" style={{ fontSize: "0.85rem" }}>
        Enter your bank account details. These will be shown to parents when they make a payment.
      </p>
      <div className="d-flex flex-column gap-2" style={{ maxWidth: 360 }}>
        <div>
          <label className="form-label mb-1" style={{ fontSize: "0.82rem", fontWeight: 600 }}>Account name</label>
          <input className="form-control form-control-sm" placeholder="e.g. SubjectMatter Pty Ltd" value={name} onChange={e => setName(e.target.value)} />
        </div>
        <div>
          <label className="form-label mb-1" style={{ fontSize: "0.82rem", fontWeight: 600 }}>BSB <span className="text-danger">*</span></label>
          <input className="form-control form-control-sm" placeholder="e.g. 062-000" value={bsb} onChange={e => setBsb(e.target.value)} />
        </div>
        <div>
          <label className="form-label mb-1" style={{ fontSize: "0.82rem", fontWeight: 600 }}>Account number <span className="text-danger">*</span></label>
          <input className="form-control form-control-sm" placeholder="e.g. 1234 5678" value={account} onChange={e => setAccount(e.target.value)} />
        </div>
        {error && <p className="text-danger mb-0" style={{ fontSize: "0.82rem" }}>{error}</p>}
        <div>
          <button className="btn btn-sm btn-success" onClick={handleSave} disabled={saving}>
            {saving ? "Saving…" : "Save bank details"}
          </button>
        </div>
      </div>
    </div>
  );
}

function PendingJobsTab() {
  const [jobs, setJobs] = useState<AdminJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [apiError, setApiError] = useState("");
  const [working, setWorking] = useState<number | null>(null);

  useEffect(() => { load(); }, []);

  async function load() {
    setLoading(true);
    setApiError("");
    try {
      const res = await apiFetch("/api/admin-jobs/");
      const data = await res.json();
      if (!res.ok) {
        setApiError(`API error ${res.status}: ${JSON.stringify(data)}`);
        return;
      }
      setJobs(Array.isArray(data) ? data : []);
    } catch (e: any) {
      setApiError(e.message ?? "Unknown error");
    } finally {
      setLoading(false);
    }
  }

  async function approve(job: AdminJob) {
    setWorking(job.id);
    try {
      await apiFetch(`/api/admin-jobs/${job.id}/approve/`, { method: "POST" });
      setJobs(prev => prev.filter(j => j.id !== job.id));
    } finally {
      setWorking(null);
    }
  }

  async function dismiss(job: AdminJob) {
    setWorking(job.id);
    try {
      await apiFetch(`/api/admin-jobs/${job.id}/dismiss/`, { method: "POST" });
      setJobs(prev => prev.filter(j => j.id !== job.id));
    } finally {
      setWorking(null);
    }
  }

  if (loading) return <p className="text-muted">Loading…</p>;

  if (apiError) return (
    <div className="alert alert-danger" style={{ fontFamily: "monospace", fontSize: "0.85rem" }}>{apiError}</div>
  );

  if (jobs.length === 0) return (
    <div className="rounded p-4 text-center" style={{ background: "#f8f9fa", border: "1px solid #dee2e6", color: "#6c757d" }}>
      No pending jobs. You're all caught up.
    </div>
  );

  return (
    <div className="d-flex flex-column gap-3">
      {jobs.map(job => (
        <div
          key={job.id}
          className="rounded p-3"
          style={{ background: TYPE_COLOUR[job.job_type] ?? "#fff3cd", border: `1px solid ${TYPE_BORDER[job.job_type] ?? "#ffc107"}` }}
        >
          <div className="d-flex align-items-center justify-content-between flex-wrap gap-2 mb-3">
            <div className="d-flex align-items-center gap-2">
              <span className="badge" style={{ background: TYPE_BORDER[job.job_type] ?? "#ffc107", color: "#1a1a1a", fontWeight: 600, fontSize: "0.72rem", letterSpacing: "0.04em" }}>
                {TYPE_LABEL[job.job_type] ?? job.job_type}
              </span>
              {job.first_name && (
                <>
                  <strong style={{ fontSize: "0.95rem" }}>{job.first_name} {job.last_name}</strong>
                  <span className="text-muted" style={{ fontSize: "0.85rem" }}>{job.email}</span>
                </>
              )}
            </div>
            <span className="text-muted" style={{ fontSize: "0.78rem" }}>
              {new Date(job.triggered_at).toLocaleDateString("en-AU", { day: "numeric", month: "short", year: "numeric" })}
            </span>
          </div>

          {job.job_type === "setup_bank_details" && (
            <BankDetailsForm job={job} onSaved={() => setJobs(prev => prev.filter(j => j.id !== job.id))} />
          )}

          {job.job_type !== "setup_bank_details" && (
            <>
              <div className="d-flex flex-wrap gap-3 mb-3" style={{ fontSize: "0.85rem" }}>
                {job.qualification && <div><span className="text-muted">Qualification: </span><span>{job.qualification}</span></div>}
                {job.mobile && <div><span className="text-muted">Mobile: </span><span>{job.mobile}</span></div>}
                {job.year_levels && job.year_levels.length > 0 && (
                  <div><span className="text-muted">Year levels: </span><span>{job.year_levels.join(", ")}</span></div>
                )}
              </div>
              {job.bio && (
                <p className="mb-3" style={{ fontSize: "0.85rem", color: "#333", background: "rgba(0,0,0,0.04)", borderRadius: 6, padding: "8px 12px", margin: 0 }}>
                  {job.bio}
                </p>
              )}
              {job.notes && (
                <p className="mb-3" style={{ fontSize: "0.85rem", color: "#333", background: "rgba(0,0,0,0.04)", borderRadius: 6, padding: "8px 12px", margin: 0 }}>
                  {job.notes.replace(/tutor_job_id:\d+\s*—\s*/, "")}
                </p>
              )}
              <div className="d-flex gap-2 mt-2">
                <button className="btn btn-sm btn-success" disabled={working === job.id} onClick={() => approve(job)}>
                  {working === job.id ? "Approving…" : "Approve"}
                </button>
                <button className="btn btn-sm btn-outline-secondary" disabled={working === job.id} onClick={() => dismiss(job)}>
                  Dismiss
                </button>
              </div>
            </>
          )}
        </div>
      ))}
    </div>
  );
}

function FeedbackTab() {
  const [items, setItems] = useState<FeedbackItem[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<number | null>(null);

  useEffect(() => {
    apiFetch("/api/payments/admin-feedback/")
      .then(r => r.json())
      .then(d => { setItems(Array.isArray(d) ? d : []); })
      .catch(() => setItems([]))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="text-muted">Loading…</p>;
  if (!items || items.length === 0) return <p className="text-muted">No feedback yet.</p>;

  const visible = filter ? items.filter(i => i.rating === filter) : items;
  const avg = items.reduce((s, i) => s + i.rating, 0) / items.length;

  const countByRating = [5, 4, 3, 2, 1].map(r => ({ r, count: items.filter(i => i.rating === r).length }));

  return (
    <div>
      {/* Summary bar */}
      <div className="d-flex align-items-center gap-4 mb-4 p-3 rounded" style={{ background: "#fffbf5", border: "1px solid #e8e0d6" }}>
        <div className="text-center">
          <div style={{ fontSize: "2rem", fontWeight: 700, color: "#f59e0b", lineHeight: 1 }}>{avg.toFixed(1)}</div>
          <Stars value={Math.round(avg)} />
          <div className="text-muted" style={{ fontSize: 12, marginTop: 2 }}>{items.length} review{items.length !== 1 ? "s" : ""}</div>
        </div>
        <div className="d-flex flex-column gap-1" style={{ fontSize: 13 }}>
          {countByRating.map(({ r, count }) => (
            <button
              key={r}
              onClick={() => setFilter(filter === r ? null : r)}
              style={{
                background: filter === r ? "#f59e0b20" : "none",
                border: filter === r ? "1px solid #f59e0b" : "1px solid transparent",
                borderRadius: 4,
                padding: "1px 8px",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: 6,
                color: "#444",
              }}
            >
              <span style={{ color: "#f59e0b" }}>{"★".repeat(r)}</span>
              <span className="text-muted">{count}</span>
            </button>
          ))}
        </div>
      </div>

      {filter && (
        <p className="text-muted mb-2" style={{ fontSize: 13 }}>
          Showing {filter}-star reviews · <button className="btn btn-link btn-sm p-0" style={{ fontSize: 13 }} onClick={() => setFilter(null)}>Clear filter</button>
        </p>
      )}

      <div className="d-flex flex-column gap-2">
        {visible.map(item => (
          <div key={item.id} className="rounded p-3" style={{ background: "#fff", border: "1px solid #e8e0d6", fontSize: 14 }}>
            <div className="d-flex justify-content-between align-items-start flex-wrap gap-2">
              <div>
                <Stars value={item.rating} />
                {item.rating_comment && (
                  <p className="mb-0 mt-1" style={{ color: "#333", fontStyle: "italic" }}>"{item.rating_comment}"</p>
                )}
              </div>
              <div className="text-end" style={{ fontSize: 12, color: "#8a7f74", flexShrink: 0 }}>
                <div>
                  <a href={`/tutors/${item.tutor_id}`} style={{ color: "inherit", fontWeight: 600 }}>{item.tutor_name}</a>
                </div>
                {item.student_name && <div>Student: {item.student_name}</div>}
                <div>{new Date(item.session_date).toLocaleDateString("en-AU", { day: "numeric", month: "short", year: "numeric" })}</div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function fmtDate(iso: string) {
  return new Date(iso).toLocaleDateString("en-AU", { day: "numeric", month: "short", year: "numeric" });
}

interface ActivityUser {
  id: number;
  first_name: string;
  last_name: string;
  email: string;
  date_joined: string;
}

interface TutorRemoval {
  id: number;
  tutor_first_name: string;
  tutor_last_name: string;
  tutor_email: string;
  notes: string;
  triggered_at: string;
}

interface ActivityData {
  parents: ActivityUser[];
  students: ActivityUser[];
  tutors: ActivityUser[];
  tutor_removals: TutorRemoval[];
}

function ActivityTab() {
  const [data, setData] = useState<ActivityData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiFetch("/api/admin/activity/")
      .then(r => r.json())
      .then(d => setData({
        parents:       Array.isArray(d.parents)       ? d.parents       : [],
        students:      Array.isArray(d.students)      ? d.students      : [],
        tutors:        Array.isArray(d.tutors)         ? d.tutors        : [],
        tutor_removals: Array.isArray(d.tutor_removals) ? d.tutor_removals : [],
      }))
      .catch(() => setData({ parents: [], students: [], tutors: [], tutor_removals: [] }))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="text-muted">Loading…</p>;
  if (!data) return null;


  function UserList({ users, emptyMsg }: { users: ActivityUser[]; emptyMsg: string }) {
    if (users.length === 0) return <p className="text-muted" style={{ fontSize: 13 }}>{emptyMsg}</p>;
    return (
      <div style={{ overflowX: "auto", borderRadius: 8, border: "1px solid #dee2e6" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.875rem" }}>
          <thead>
            <tr style={{ background: "#f8f9fa", borderBottom: "1px solid #dee2e6" }}>
              {["Name", "Email", "Joined"].map(h => (
                <th key={h} style={{ padding: "0.5rem 0.9rem", textAlign: "left", fontWeight: 600, fontSize: "0.75rem", textTransform: "uppercase", letterSpacing: "0.04em", color: "#6c757d" }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {users.map((u, i) => (
              <tr key={u.id} style={{ background: i % 2 === 0 ? "#fff" : "#f8f9fa", borderBottom: "1px solid #dee2e6" }}>
                <td style={{ padding: "0.55rem 0.9rem", fontWeight: 500 }}>{u.first_name} {u.last_name}</td>
                <td style={{ padding: "0.55rem 0.9rem", color: "#555" }}>{u.email}</td>
                <td style={{ padding: "0.55rem 0.9rem", color: "#888", whiteSpace: "nowrap" }}>{fmtDate(u.date_joined)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  return (
    <div className="d-flex flex-column gap-4">
      <section>
        <h5 className="mb-2">New Parents <span className="text-muted fw-normal" style={{ fontSize: "0.85rem" }}>({data.parents.length})</span></h5>
        <UserList users={data.parents} emptyMsg="No parents yet." />
      </section>
      <section>
        <h5 className="mb-2">New Students <span className="text-muted fw-normal" style={{ fontSize: "0.85rem" }}>({data.students.length})</span></h5>
        <UserList users={data.students} emptyMsg="No students yet." />
      </section>
      <section>
        <h5 className="mb-2">New Tutors <span className="text-muted fw-normal" style={{ fontSize: "0.85rem" }}>({data.tutors.length})</span></h5>
        <UserList users={data.tutors} emptyMsg="No tutors yet." />
      </section>
      <section>
        <h5 className="mb-2">Tutor Removals <span className="text-muted fw-normal" style={{ fontSize: "0.85rem" }}>({data.tutor_removals.length})</span></h5>
        {data.tutor_removals.length === 0 ? (
          <p className="text-muted" style={{ fontSize: 13 }}>No tutor removals yet.</p>
        ) : (
          <div style={{ overflowX: "auto", borderRadius: 8, border: "1px solid #dee2e6" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.875rem" }}>
              <thead>
                <tr style={{ background: "#f8f9fa", borderBottom: "1px solid #dee2e6" }}>
                  {["Tutor", "Email", "Details", "Removed"].map(h => (
                    <th key={h} style={{ padding: "0.5rem 0.9rem", textAlign: "left", fontWeight: 600, fontSize: "0.75rem", textTransform: "uppercase", letterSpacing: "0.04em", color: "#6c757d" }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.tutor_removals.map((r, i) => (
                  <tr key={r.id} style={{ background: i % 2 === 0 ? "#fff" : "#f8f9fa", borderBottom: "1px solid #dee2e6" }}>
                    <td style={{ padding: "0.55rem 0.9rem", fontWeight: 500 }}>{r.tutor_first_name} {r.tutor_last_name}</td>
                    <td style={{ padding: "0.55rem 0.9rem", color: "#555" }}>{r.tutor_email}</td>
                    <td style={{ padding: "0.55rem 0.9rem", color: "#444", whiteSpace: "pre-line", fontSize: "0.82rem" }}>{r.notes}</td>
                    <td style={{ padding: "0.55rem 0.9rem", color: "#888", whiteSpace: "nowrap" }}>{fmtDate(r.triggered_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}

interface ParentFeedbackItem {
  id: number;
  parent_id: number;
  parent_name: string;
  parent_email: string;
  body: string;
  created_at: string;
  admin_response: string | null;
  responded_at: string | null;
  responded_by_name: string | null;
}

function ParentFeedbackAdminTab() {
  const [items, setItems] = useState<ParentFeedbackItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [responding, setResponding] = useState<number | null>(null);
  const [responseText, setResponseText] = useState<Record<number, string>>({});

  useEffect(() => {
    apiFetch("/api/parent-feedback/")
      .then(r => r.json())
      .then(d => setItems(Array.isArray(d) ? d : []))
      .catch(() => setItems([]))
      .finally(() => setLoading(false));
  }, []);

  async function handleRespond(id: number) {
    const text = (responseText[id] || "").trim();
    if (!text) return;
    setResponding(id);
    try {
      const res = await apiFetch(`/api/parent-feedback/${id}/respond/`, {
        method: "POST",
        body: JSON.stringify({ response: text }),
      });
      const data = await res.json();
      if (res.ok) {
        setItems(prev => prev.map(item => item.id === id ? data : item));
        setResponseText(prev => { const n = { ...prev }; delete n[id]; return n; });
      }
    } finally {
      setResponding(null);
    }
  }

  if (loading) return <p className="text-muted">Loading…</p>;
  if (items.length === 0) return (
    <div className="rounded p-4 text-center" style={{ background: "#f8f9fa", border: "1px solid #dee2e6", color: "#6c757d" }}>
      No parent feedback yet.
    </div>
  );

  return (
    <div className="d-flex flex-column gap-3">
      {items.map(item => (
        <div key={item.id} className="rounded p-3" style={{ background: "#fff", border: "1px solid #e8e0d6" }}>
          <div className="d-flex justify-content-between align-items-start flex-wrap gap-2 mb-2">
            <div>
              <span className="fw-semibold" style={{ fontSize: "0.9rem" }}>{item.parent_name}</span>
              <span className="text-muted ms-2" style={{ fontSize: "0.82rem" }}>{item.parent_email}</span>
            </div>
            <div className="d-flex align-items-center gap-2">
              {item.admin_response
                ? <span className="badge" style={{ background: "#d1e7dd", color: "#0a3622", fontSize: 11 }}>Responded</span>
                : <span className="badge" style={{ background: "#fff3cd", color: "#664d03", fontSize: 11 }}>Needs response</span>}
              <span className="text-muted" style={{ fontSize: "0.78rem" }}>{fmtDate(item.created_at)}</span>
            </div>
          </div>

          <p style={{ fontSize: 14, color: "#333", lineHeight: 1.65, marginBottom: item.admin_response ? 12 : 16 }}>
            {item.body}
          </p>

          {item.admin_response && (
            <div style={{ borderLeft: "3px solid #E87722", paddingLeft: 12, marginBottom: 16 }}>
              <p style={{ fontSize: 11, fontWeight: 600, color: "#E87722", marginBottom: 3, textTransform: "uppercase", letterSpacing: "0.04em" }}>
                Your response · {item.responded_at ? fmtDate(item.responded_at) : ""}
              </p>
              <p style={{ fontSize: 14, color: "#333", lineHeight: 1.65, marginBottom: 0 }}>{item.admin_response}</p>
            </div>
          )}

          <div className="d-flex gap-2 align-items-start">
            <textarea
              className="form-control form-control-sm"
              rows={2}
              placeholder={item.admin_response ? "Update response…" : "Write a response…"}
              value={responseText[item.id] ?? ""}
              onChange={e => setResponseText(prev => ({ ...prev, [item.id]: e.target.value }))}
              style={{ resize: "vertical", fontSize: "0.85rem" }}
            />
            <button
              className="btn btn-sm btn-primary"
              style={{ whiteSpace: "nowrap" }}
              disabled={responding === item.id || !(responseText[item.id] || "").trim()}
              onClick={() => handleRespond(item.id)}
            >
              {responding === item.id ? "Sending…" : item.admin_response ? "Update" : "Send"}
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}

export default function AdminHomePage() {
  const storedUser = (() => { try { return JSON.parse(localStorage.getItem("user") ?? "{}"); } catch { return {}; } })();
  const firstName = storedUser.first_name ?? "Admin";

  return (
    <Layout>
      <div className="container py-4" style={{ maxWidth: 900 }}>

        <h1 style={{ fontFamily: "Lora, Georgia, serif", fontSize: "1.875rem", fontWeight: 700, color: "#2D2D2D", marginBottom: "2rem" }}>
          Welcome back, {firstName}.
        </h1>

        <section className="mb-5">
          <h5 className="fw-semibold mb-3">Pending Jobs</h5>
          <PendingJobsTab />
        </section>

        <section className="mb-5">
          <h5 className="fw-semibold mb-3">Tutor Feedback</h5>
          <FeedbackTab />
        </section>

        <section className="mb-5">
          <h5 className="fw-semibold mb-3">Parent Feedback</h5>
          <ParentFeedbackAdminTab />
        </section>

        <section className="mb-5">
          <h5 className="fw-semibold mb-3">Activity</h5>
          <ActivityTab />
        </section>

      </div>
    </Layout>
  );
}
