import { useEffect, useState } from "react";
import { Layout } from "./components/Layout";
import { apiFetch } from "../utils/apiFetch";

interface AdminJob {
  id: number;
  job_type: "approve_tutor" | "approve_distributor";
  subject_id: number;
  first_name: string;
  last_name: string;
  email: string;
  triggered_at: string;
  // tutor-specific
  qualification?: string;
  bio?: string;
  year_levels?: string[];
  // distributor-specific
  mobile?: string;
}

const TYPE_LABEL: Record<string, string> = {
  approve_tutor: "Approve Tutor",
  approve_distributor: "Approve Distributor",
};

const TYPE_COLOUR: Record<string, string> = {
  approve_tutor: "#cfe2ff",
  approve_distributor: "#d1e7dd",
};

const TYPE_BORDER: Record<string, string> = {
  approve_tutor: "#9ec5fe",
  approve_distributor: "#a3cfbb",
};

export default function AdminHomePage() {
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

  return (
    <Layout>
      <div className="container py-4" style={{ maxWidth: 900 }}>
        <h2 className="mb-1">Admin home</h2>
        <p className="text-muted mb-4" style={{ fontSize: "0.9rem" }}>
          Pending jobs — action required.
        </p>

        {loading && <p className="text-muted">Loading…</p>}

        {apiError && (
          <div className="alert alert-danger" style={{ fontFamily: "monospace", fontSize: "0.85rem" }}>
            {apiError}
          </div>
        )}

        {!loading && jobs.length === 0 && (
          <div
            className="rounded p-4 text-center"
            style={{ background: "#f8f9fa", border: "1px solid #dee2e6", color: "#6c757d" }}
          >
            No pending jobs. You're all caught up.
          </div>
        )}

        {!loading && jobs.length > 0 && (
          <div className="d-flex flex-column gap-3">
            {jobs.map(job => (
              <div
                key={job.id}
                className="rounded p-3"
                style={{
                  background: TYPE_COLOUR[job.job_type] ?? "#fff3cd",
                  border: `1px solid ${TYPE_BORDER[job.job_type] ?? "#ffc107"}`,
                }}
              >
                {/* Header row */}
                <div className="d-flex align-items-center justify-content-between flex-wrap gap-2 mb-2">
                  <div className="d-flex align-items-center gap-2">
                    <span
                      className="badge"
                      style={{
                        background: TYPE_BORDER[job.job_type] ?? "#ffc107",
                        color: "#1a1a1a",
                        fontWeight: 600,
                        fontSize: "0.72rem",
                        letterSpacing: "0.04em",
                      }}
                    >
                      {TYPE_LABEL[job.job_type] ?? job.job_type}
                    </span>
                    <strong style={{ fontSize: "0.95rem" }}>
                      {job.first_name} {job.last_name}
                    </strong>
                    <span className="text-muted" style={{ fontSize: "0.85rem" }}>
                      {job.email}
                    </span>
                  </div>
                  <span className="text-muted" style={{ fontSize: "0.78rem" }}>
                    Applied {new Date(job.triggered_at).toLocaleDateString("en-AU", {
                      day: "numeric", month: "short", year: "numeric",
                    })}
                  </span>
                </div>

                {/* Profile details */}
                <div className="d-flex flex-wrap gap-3 mb-3" style={{ fontSize: "0.85rem" }}>
                  {job.qualification && (
                    <div>
                      <span className="text-muted">Qualification: </span>
                      <span>{job.qualification}</span>
                    </div>
                  )}
                  {job.mobile && (
                    <div>
                      <span className="text-muted">Mobile: </span>
                      <span>{job.mobile}</span>
                    </div>
                  )}
                  {job.year_levels && job.year_levels.length > 0 && (
                    <div>
                      <span className="text-muted">Year levels: </span>
                      <span>{job.year_levels.join(", ")}</span>
                    </div>
                  )}
                </div>

                {job.bio && (
                  <p
                    className="mb-3"
                    style={{
                      fontSize: "0.85rem",
                      color: "#333",
                      background: "rgba(0,0,0,0.04)",
                      borderRadius: 6,
                      padding: "8px 12px",
                      margin: 0,
                    }}
                  >
                    {job.bio}
                  </p>
                )}

                {/* Actions */}
                <div className="d-flex gap-2 mt-2">
                  <button
                    className="btn btn-sm btn-success"
                    disabled={working === job.id}
                    onClick={() => approve(job)}
                  >
                    {working === job.id ? "Approving…" : "Approve"}
                  </button>
                  <button
                    className="btn btn-sm btn-outline-secondary"
                    disabled={working === job.id}
                    onClick={() => dismiss(job)}
                  >
                    Dismiss
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </Layout>
  );
}
