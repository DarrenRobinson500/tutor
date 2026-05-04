import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { Layout } from "./components/Layout";
import { apiFetch } from "../utils/apiFetch";

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

const TYPE_BADGE: Record<string, [string, string]> = {
  easy:   ["bg-success", "Easy"],
  medium: ["bg-primary", "Moderate"],
  hard:   ["bg-danger",  "Hard"],
};

const DIFFICULTY_COLOR: Record<string, string> = {
  easy:   "#198754",
  medium: "#fd7e14",
  hard:   "#dc3545",
  none:   "#adb5bd",
};

function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("en-AU", { day: "numeric", month: "short", year: "numeric" });
}

function formatTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleTimeString("en-AU", { hour: "2-digit", minute: "2-digit" });
}

function duration(start: string, end: string | null): string {
  if (!end) return "";
  const mins = Math.round((new Date(end).getTime() - new Date(start).getTime()) / 60000);
  if (mins < 60) return `${mins} min`;
  return `${Math.floor(mins / 60)}h ${mins % 60}m`;
}

export function PastTestsPage() {
  const { studentId } = useParams<{ studentId: string }>();
  const [sessions, setSessions] = useState<TestSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<number | null>(null);
  const [downloading, setDownloading] = useState<number | null>(null);

  async function downloadReport(sessionId: number) {
    setDownloading(sessionId);
    try {
      const res = await apiFetch(`/api/tests/${sessionId}/report/`);
      if (!res.ok) {
        const err = await res.json().catch(() => ({ error: `Server error ${res.status}` }));
        alert(err.error || "Failed to generate report");
        return;
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `progress_report_${sessionId}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      setTimeout(() => URL.revokeObjectURL(url), 100);
    } finally {
      setDownloading(null);
    }
  }

  useEffect(() => {
    if (!studentId) return;
    apiFetch(`/api/tests/past/?student_id=${studentId}`)
      .then(r => r.json())
      .then((data: TestSession[]) => {
        setSessions(data);
        setLoading(false);
      });
  }, [studentId]);

  return (
    <Layout>
      <div className="container py-4" style={{ maxWidth: 700 }}>
        <h4 className="mb-4">Past Tests</h4>

        {loading ? (
          <div className="d-flex justify-content-center py-5">
            <div className="spinner-border text-primary" role="status" />
          </div>
        ) : sessions.length === 0 ? (
          <p className="text-muted">No completed tests yet.</p>
        ) : (
          <div className="d-flex flex-column gap-3">
            {sessions.map(s => {
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
                      <span className="fw-semibold">{formatDate(s.started_at)}</span>
                      <span className="text-muted ms-2" style={{ fontSize: 13 }}>{formatTime(s.started_at)}</span>
                      {s.completed_at && (
                        <span className="text-muted ms-2" style={{ fontSize: 13 }}>
                          · {duration(s.started_at, s.completed_at)}
                        </span>
                      )}
                      {s.test_type && TYPE_BADGE[s.test_type] && (
                        <span className={`badge ${TYPE_BADGE[s.test_type][0]} ms-2`} style={{ fontSize: 11 }}>
                          {TYPE_BADGE[s.test_type][1]}
                        </span>
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
                                <span
                                  className="badge"
                                  style={{
                                    background: DIFFICULTY_COLOR[r.highest_difficulty_reached] ?? "#adb5bd",
                                    fontSize: 11,
                                  }}
                                >
                                  {r.highest_difficulty_reached || "none"}
                                </span>
                              </td>
                              <td style={{ fontSize: 13 }}>
                                {r.questions_correct}/{r.questions_asked}
                              </td>
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
        )}
      </div>
    </Layout>
  );
}
