import { useEffect, useState, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Layout } from "./components/Layout";
import { apiFetch } from "../utils/apiFetch";

interface AssessmentMeta {
  id: number;
  class_id: number;
  class_name: string;
  year_level: string;
  status: string;
  started_at: string;
}

interface StudentRow {
  student_id: number;
  name: string;
  correct: number;
  incorrect: number;
  joined: boolean;
  username: string;
  plain_password: string | null;
}

export function TeacherAssessmentPage() {
  const { teacherId, classId, assessmentId } = useParams();
  const navigate = useNavigate();

  const [assessment, setAssessment] = useState<AssessmentMeta | null>(null);
  const [students, setStudents] = useState<StudentRow[]>([]);
  const [ending, setEnding] = useState(false);
  const [resetting, setResetting] = useState<number | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  async function fetchDashboard() {
    const res = await apiFetch(
      `/api/teachers/${teacherId}/assessment_dashboard/?assessment_id=${assessmentId}`
    );
    if (!res.ok) return;
    const data = await res.json();
    setAssessment(data.assessment);
    setStudents(data.students ?? []);
  }

  useEffect(() => {
    fetchDashboard();
    intervalRef.current = setInterval(fetchDashboard, 3000);
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [assessmentId]); // eslint-disable-line react-hooks/exhaustive-deps

  async function handleEnd() {
    setEnding(true);
    try {
      await apiFetch(`/api/teachers/${teacherId}/end_assessment/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ assessment_id: Number(assessmentId) }),
      });
      navigate(`/teachers/${teacherId}/classes/${classId}/focus`);
    } finally {
      setEnding(false);
    }
  }

  async function handleMarkAbsent(studentId: number) {
    await apiFetch(`/api/teachers/${teacherId}/mark_absent/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ assessment_id: Number(assessmentId), student_id: studentId }),
    });
    setStudents(prev => prev.filter(s => s.student_id !== studentId));
  }

  const notJoined  = students.filter(s => !s.joined);
  const joined     = students.filter(s => s.joined);
  const totalQ     = (s: StudentRow) => s.correct + s.incorrect;

  if (!assessment) return <Layout><div className="container mt-4">Loading…</div></Layout>;

  return (
    <Layout>
      <div className="container mt-4" style={{ maxWidth: 700 }}>

        {/* Header */}
        <div className="d-flex align-items-center justify-content-between mb-1">
          <div>
            <h2 className="mb-0">{assessment.class_name} — Assessment</h2>
            <p className="text-muted mb-0" style={{ fontSize: 13 }}>
              Year {assessment.year_level} · {students.length} student{students.length !== 1 ? "s" : ""}
            </p>
          </div>
          <button
            className="btn btn-danger"
            onClick={handleEnd}
            disabled={ending}
          >
            {ending ? "Ending…" : "End Assessment"}
          </button>
        </div>

        <p className="text-muted mb-4" style={{ fontSize: 13 }}>
          Live results — refreshing every 3 seconds. Students are working through their focus areas.
        </p>

        {/* Not-joined students */}
        {notJoined.length > 0 && (
          <>
            <h5 className="text-muted mb-2">
              Not yet joined ({notJoined.length})
            </h5>
            <table className="table table-sm mb-4">
              <thead className="table-light">
                <tr>
                  <th>Student</th>
                  <th>Username (email)</th>
                  <th>Password</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {notJoined.map(s => (
                  <tr key={s.student_id}>
                    <td className="fw-semibold">{s.name}</td>
                    <td className="text-muted" style={{ fontSize: 12 }}>
                      <code>{s.username}</code>
                    </td>
                    <td>
                      {s.plain_password
                        ? <strong>{s.plain_password}</strong>
                        : <span className="text-muted" style={{ fontSize: 12 }}>—</span>
                      }
                    </td>
                    <td className="text-end">
                      <button
                        className="btn btn-sm btn-outline-secondary"
                        onClick={() => handleMarkAbsent(s.student_id)}
                      >
                        Not here today
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        )}

        {/* Active students */}
        {joined.length > 0 && (
          <>
            <h5 className="mb-2">In progress ({joined.length})</h5>
            <table className="table align-middle">
              <thead className="table-light">
                <tr>
                  <th>Student</th>
                  <th className="text-center">Correct</th>
                  <th className="text-center">Incorrect</th>
                  <th>Progress</th>
                </tr>
              </thead>
              <tbody>
                {joined.map(s => {
                  const total = totalQ(s);
                  const pct = total > 0 ? (s.correct / total) * 100 : 0;
                  return (
                    <tr key={s.student_id}>
                      <td className="fw-semibold">{s.name}</td>
                      <td className="text-center">
                        <span className="badge bg-success">{s.correct}</span>
                      </td>
                      <td className="text-center">
                        <span className={`badge ${s.incorrect > 0 ? "bg-danger" : "bg-secondary"}`}>
                          {s.incorrect}
                        </span>
                      </td>
                      <td style={{ minWidth: 120 }}>
                        {total > 0 ? (
                          <div className="d-flex align-items-center gap-2">
                            <div className="progress flex-grow-1" style={{ height: 8 }}>
                              <div
                                className="progress-bar"
                                style={{
                                  width: `${pct}%`,
                                  background: pct >= 70 ? "#43a047" : pct >= 40 ? "#FF8C42" : "#e53935",
                                }}
                              />
                            </div>
                            <span style={{ fontSize: 12, whiteSpace: "nowrap" }}>
                              {total} answered
                            </span>
                          </div>
                        ) : (
                          <span className="text-muted" style={{ fontSize: 12 }}>No answers yet</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </>
        )}

        {students.length === 0 && (
          <div className="text-center py-5 text-muted">
            <p style={{ fontSize: "2rem" }}>👨‍🎓</p>
            <p>Waiting for students to join…</p>
          </div>
        )}

      </div>
    </Layout>
  );
}
