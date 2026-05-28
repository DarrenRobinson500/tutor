import { useEffect, useState } from "react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer,
} from "recharts";
import { apiFetch } from "../../utils/apiFetch";

interface Snapshot { date: string; score: number; }

interface Competency {
  total_skills: number;
  avg_level: number | null;
  avg_label: string | null;
  distribution: number[];
}

interface ProgressData {
  snapshots: Snapshot[];
  competency: Competency;
  focus_areas: unknown[];
}

const LEVEL_COLOURS = [
  "#e5e7eb", // 0 Not Started
  "#fde68a", // 1 Developing
  "#fcd34d", // 2 Easy Complete
  "#6ee7b7", // 3 Emerging
  "#34d399", // 4 Competent
  "#10b981", // 5 Advanced
  "#059669", // 6 Mastered
];

const LEVEL_LABELS = [
  "Not Started", "Developing", "Easy Complete", "Emerging",
  "Competent", "Advanced", "Mastered",
];

export function ProgressChart({ studentId, overallPct }: { studentId: number | string; overallPct?: number }) {
  const [data, setData] = useState<ProgressData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    apiFetch(`/api/students/${studentId}/progress/`)
      .then(r => r.json())
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [studentId]);

  if (loading) return <p style={{ fontSize: 13, color: "#8A7F74", margin: 0 }}>Loading…</p>;

  if (!data) return <p style={{ fontSize: 13, color: "#8A7F74", margin: 0 }}>Could not load progress.</p>;

  const { snapshots, competency } = data;
  const hasSnapshots = snapshots.length >= 2;
  const hasCompetency = competency.total_skills > 0;
  const latestScore = overallPct ?? (snapshots.length > 0 ? Math.round(snapshots[snapshots.length - 1].score) : 0);

  if (!hasSnapshots && !hasCompetency) {
    return (
      <p style={{ fontSize: 13, color: "#8A7F74", margin: 0 }}>
        Complete an assessment to see progress.
      </p>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>

      {/* Overall score trend */}
      <div>
        <div style={{ fontSize: 12, fontWeight: 600, color: "#6b7280", marginBottom: 4, textTransform: "uppercase", letterSpacing: "0.04em" }}>
          {latestScore}% Percent of Year 7 Complete
        </div>
        <div style={{ fontSize: 11, color: "#9ca3af", marginBottom: 4 }}>Goal: 100% by end of year</div>
        {hasSnapshots && (
          <ResponsiveContainer width="100%" height={140}>
            <LineChart data={snapshots} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis dataKey="date" tick={{ fontSize: 10 }} />
              <YAxis domain={[0, 100]} ticks={[0, 50, 100]} tickFormatter={(v: number) => `${v}%`} tick={{ fontSize: 10 }} width={34} />
              <Tooltip formatter={(v: any) => [`${v}%`, "Percent"]} />
              <Line type="monotone" dataKey="score" stroke="#FF8C42" strokeWidth={2} dot={{ r: 3 }} connectNulls />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Skill competency summary */}
      {hasCompetency && (
        <div>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 6 }}>
            <div style={{ fontSize: 12, fontWeight: 600, color: "#6b7280", textTransform: "uppercase", letterSpacing: "0.04em" }}>
              Skills assessed
            </div>
            <div style={{ fontSize: 12, color: "#6b7280" }}>
              {competency.total_skills} skill{competency.total_skills !== 1 ? "s" : ""}
            </div>
          </div>
          {/* Distribution bar */}
          <div style={{ display: "flex", height: 10, borderRadius: 5, overflow: "hidden", gap: 1 }}>
            {competency.distribution.map((count, i) =>
              count > 0 ? (
                <div
                  key={i}
                  title={`Level ${i}: ${count} skill${count !== 1 ? "s" : ""}`}
                  style={{
                    flex: count,
                    background: LEVEL_COLOURS[i],
                    transition: "flex 0.4s",
                  }}
                />
              ) : null
            )}
          </div>
          {(() => {
            const lowestLevel = competency.distribution.findIndex(c => c > 0);
            const highestLevel = competency.distribution.reduce((hi, c, i) => c > 0 ? i : hi, 0);
            return (
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 10, color: "#9ca3af", marginTop: 3 }}>
                <span>{LEVEL_LABELS[lowestLevel] ?? "Not Started"}</span>
                <span>{LEVEL_LABELS[highestLevel] ?? "Mastered"}</span>
              </div>
            );
          })()}
        </div>
      )}


    </div>
  );
}
