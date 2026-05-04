import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { Layout } from "./components/Layout";
import { apiFetch } from "../utils/apiFetch";

interface SkillGap {
  skill_id: number;
  description: string;
  avg_level: number;
  students_at_zero: number;
  student_count: number;
  distribution: Record<string, number>;
}

interface GapReport {
  class: { id: number; name: string; year_level: string; code: string; student_count: number };
  skills: SkillGap[];
}

const LEVEL_LABELS = ["Not started", "Beginning", "Developing", "Proficient", "Mastered"];
const LEVEL_COLOURS = ["#e53935", "#ef6c00", "#f9a825", "#43a047", "#1565c0"];

export function TeacherGapReportPage() {
  const { teacherId, classId } = useParams();
  const [report, setReport] = useState<GapReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<"all" | "gaps">("gaps");

  useEffect(() => {
    apiFetch(`/api/teachers/${teacherId}/gap_report/?class_id=${classId}`)
      .then((r) => r.json())
      .then((data) => setReport(data))
      .finally(() => setLoading(false));
  }, [teacherId, classId]);

  if (loading) return <Layout><div className="container mt-4">Loading…</div></Layout>;
  if (!report) return <Layout><div className="container mt-4">Report not available.</div></Layout>;

  const skills = filter === "gaps"
    ? report.skills.filter((s) => s.avg_level < 2)
    : report.skills;

  const gapCount = report.skills.filter((s) => s.avg_level < 2).length;

  return (
    <Layout>
      <div className="container mt-4">

        {/* ── Header ───────────────────────────────── */}
        <div className="d-flex align-items-center gap-2 mb-1">
          <Link to={`/teachers/${teacherId}`} className="btn btn-sm btn-outline-secondary">
            ← Back
          </Link>
          <h2 className="mb-0">Gap Report — {report.class.name}</h2>
          <span className="badge bg-secondary">Year {report.class.year_level}</span>
        </div>
        <p className="text-muted mb-3" style={{ fontSize: 13 }}>
          {report.class.student_count} student{report.class.student_count !== 1 ? "s" : ""} · sorted by biggest gaps first
        </p>

        {/* ── Summary banner ────────────────────────── */}
        <div className="alert d-flex align-items-center gap-3 mb-4"
          style={{ background: gapCount > 5 ? "rgba(229,57,53,0.08)" : "rgba(67,160,71,0.08)", border: `1px solid ${gapCount > 5 ? "#e53935" : "#43a047"}` }}>
          <span style={{ fontSize: "1.8rem" }}>{gapCount > 5 ? "⚠" : "✅"}</span>
          <div>
            <strong>{gapCount} skill{gapCount !== 1 ? "s" : ""}</strong> below average across the class.
            {gapCount === 0 && " No significant gaps detected."}
          </div>
        </div>

        {/* ── Filter toggle ─────────────────────────── */}
        <div className="btn-group mb-3">
          <button
            className={`btn btn-sm ${filter === "gaps" ? "btn-danger" : "btn-outline-secondary"}`}
            onClick={() => setFilter("gaps")}
          >
            Gaps only ({gapCount})
          </button>
          <button
            className={`btn btn-sm ${filter === "all" ? "btn-primary" : "btn-outline-secondary"}`}
            onClick={() => setFilter("all")}
          >
            All skills ({report.skills.length})
          </button>
        </div>

        {skills.length === 0 && (
          <div className="text-center py-5 text-muted">
            <p style={{ fontSize: "2.5rem" }}>🎉</p>
            <h5>No gaps detected</h5>
            <p>All skills are averaging 2+ stars across the class.</p>
          </div>
        )}

        {/* ── Skills table ─────────────────────────── */}
        {skills.length > 0 && (
          <div className="table-responsive">
            <table className="table table-hover align-middle">
              <thead className="table-light">
                <tr>
                  <th style={{ width: "35%" }}>Skill</th>
                  <th>Class average</th>
                  <th>Distribution</th>
                  <th>At zero</th>
                </tr>
              </thead>
              <tbody>
                {skills.map((s) => {
                  const avgRounded = Math.round(s.avg_level * 10) / 10;
                  const colour = LEVEL_COLOURS[Math.min(Math.floor(s.avg_level), 4)];
                  const pct = (s.students_at_zero / s.student_count) * 100;
                  return (
                    <tr key={s.skill_id}>
                      <td className="fw-semibold" style={{ fontSize: 14 }}>{s.description}</td>
                      <td>
                        <div className="d-flex align-items-center gap-2">
                          <span style={{ color: colour, fontWeight: 700, minWidth: 28 }}>
                            {avgRounded}★
                          </span>
                          <small className="text-muted">
                            {LEVEL_LABELS[Math.min(Math.floor(s.avg_level), 4)]}
                          </small>
                        </div>
                      </td>
                      <td style={{ width: "30%" }}>
                        <div className="d-flex gap-1 align-items-center" style={{ height: 18 }}>
                          {[0, 1, 2, 3, 4].map((lv) => {
                            const count = s.distribution[String(lv)] ?? 0;
                            const share = s.student_count > 0 ? (count / s.student_count) * 100 : 0;
                            return (
                              <div
                                key={lv}
                                title={`${LEVEL_LABELS[lv]}: ${count} student${count !== 1 ? "s" : ""}`}
                                style={{
                                  flex: share || 0.5,
                                  background: LEVEL_COLOURS[lv],
                                  borderRadius: 3,
                                  height: "100%",
                                  opacity: share > 0 ? 1 : 0.15,
                                }}
                              />
                            );
                          })}
                        </div>
                      </td>
                      <td>
                        <span
                          className={`badge ${pct > 50 ? "bg-danger" : pct > 25 ? "bg-warning text-dark" : "bg-success"}`}
                        >
                          {s.students_at_zero}/{s.student_count}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </Layout>
  );
}
