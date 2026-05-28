import React, { useEffect, useState } from "react";
import { apiFetch } from "../../utils/apiFetch";
import { useNavigate } from "react-router-dom";
import { usePreferenceStore } from "../../utils/pref";


interface CellData {
  colour: string;
  count: number | null;
  validated: number;
  unvalidated: number;
}


interface DetailCoverage {
  covered: number;
  total: number;
}

interface SkillRow {
  id: number;
  code: string;
  description: string;
  depth: number;
  parent_id: number | null;
  children_count: number;
  detail?: string;
  cells: Record<string, CellData>;
  detail_coverage?: Record<string, DetailCoverage> | null;
}

interface MatrixResponse {
  grades: (string | number)[];
  skills: SkillRow[];
}

interface SkillsMatrixProps {
  courseSet?: string;   // "s6" for Stage 6; omit for K-10
  prefKey?: string;     // preference key for persisting selected grade
}

export function SkillsMatrix({ courseSet, prefKey = "skills.selected_grade" }: SkillsMatrixProps) {
  const [data, setData] = useState<MatrixResponse | null>(null);
  const navigate = useNavigate();
  const savedGrade = usePreferenceStore(s => s.get(prefKey));
  const [selectedGrade, setSelectedGrade] = useState<string | number | null>(savedGrade ?? null);

  useEffect(() => {
    const grade = selectedGrade ?? "All";
    const csParam = courseSet ? `&course_set=${courseSet}` : "";
    apiFetch(`/api/skills/matrix/?grade=${grade}${csParam}`)
      .then(res => res.json())
      .then(data => setData(data));
  }, [selectedGrade, courseSet]);

  async function handleViewTemplate(skillId: number, grade: string | number) {
    try {
      const res = await apiFetch("/api/templates/preview/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ skill: skillId, grade }),
      });
      const data = await res.json();
      if (!data.ok) alert(data.error || "Preview failed, opening template for editing.");
      if (data.template_id) { navigate(`/templates/${data.template_id}`); return; }
      alert("No templates exist yet for this skill and grade.");
    } catch (err) {
      console.error("Failed to load first template:", err);
      alert("Unexpected error loading template.");
    }
  }

  if (!data) {
    return (
      <div className="d-flex justify-content-center align-items-center" style={{ height: "200px" }}>
        <div className="spinner-border text-primary" role="status">
          <span className="visually-hidden">Loading…</span>
        </div>
      </div>
    );
  }

  const isAllView = selectedGrade === null;

  return (
    <div className="skills-matrix-container">

      {/* Grade Filter Buttons */}
      <div className="mb-3 d-flex gap-2 align-items-center flex-wrap">
        {data.grades.map(g => (
          <button
            key={g}
            className={`btn ${selectedGrade === g ? "btn-primary" : "btn-outline-primary"}`}
            onClick={() => {
              setSelectedGrade(g);
              usePreferenceStore.getState().set(prefKey, g);
            }}
          >
            {g}
          </button>
        ))}
        <button
          className={`btn ${selectedGrade === null ? "btn-secondary" : "btn-outline-secondary"}`}
          onClick={() => {
            setSelectedGrade(null);
            usePreferenceStore.getState().set(prefKey, null);
          }}
        >
          All
        </button>
      </div>

      {/* ── ALL VIEW: full grade grid ── */}
      {isAllView ? (
        <div style={{ overflowX: "auto", maxHeight: "75vh", overflowY: "auto" }}>
          <table className="skills-matrix" style={{ fontSize: 12 }}>
            <thead>
              <tr>
                <th className="skill-header" style={{ minWidth: 220, position: "sticky", top: 0, left: 0, zIndex: 3, background: "#fff" }}>Skill</th>
                {data.grades.map(g => (
                  <th key={g} className="skill-header" style={{ textAlign: "center", minWidth: 36, position: "sticky", top: 0, zIndex: 2, background: "#fff" }}>
                    {g}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.skills.map(skill => (
                <tr
                  key={skill.id}
                  className={skill.children_count > 0 ? "parent-row" : ""}
                  style={{ cursor: (skill.children_count === 0 || skill.parent_id === null) ? "pointer" : undefined }}
                  onClick={() => {
                    if (skill.parent_id === null && skill.children_count > 0) navigate(`/skill-parents/${skill.id}/overview`);
                    else if (skill.children_count === 0) navigate(`/skills/${skill.id}/overview`);
                  }}
                >
                  <td style={{ paddingLeft: `${skill.depth * 16 + 8}px`, whiteSpace: "nowrap", position: "sticky", left: 0, zIndex: 1, background: skill.children_count > 0 ? "#f0f0f0" : "#fff" }} title={skill.detail || undefined}>
                    {skill.description}
                  </td>
                  {data.grades.map(g => {
                    const gStr = String(g);
                    const cell = skill.cells[gStr];
                    const covered = cell?.colour === "covered";
                    const count = cell?.count ?? 0;
                    const total = (cell?.validated ?? 0) + (cell?.unvalidated ?? 0);
                    const hasTemplates = count > 0;
                    const anomaly = hasTemplates && !covered; // templates outside syllabus

                    let bg = "transparent";
                    let color = "#999";
                    let cursor = "default";
                    let title = "";

                    if (covered && hasTemplates) {
                      bg = "#c8e6c9";   // green — in syllabus + has templates
                      color = "#1b5e20";
                      cursor = "pointer";
                      title = `${count} template${count !== 1 ? "s" : ""} — click for overview`;
                    } else if (covered) {
                      bg = "#e3f2fd";   // light blue — in syllabus, no templates yet
                      color = "#bbb";
                    } else if (anomaly) {
                      bg = "#fff3cd";   // amber — NOT in syllabus but templates exist
                      color = "#856404";
                      cursor = "pointer";
                      title = `${count} template${count !== 1 ? "s" : ""} (not in syllabus for this year) — click for overview`;
                    }

                    return (
                      <td
                        key={gStr}
                        style={{
                          background: bg,
                          color,
                          textAlign: "center",
                          cursor,
                          fontSize: 11,
                          fontWeight: hasTemplates ? 600 : 400,
                          padding: "2px 4px",
                          border: anomaly ? "1px solid #ffc107" : undefined,
                        }}
                        title={title}
                        onClick={() => {
                          if (hasTemplates) navigate(`/skills/${skill.id}/overview/${gStr}`);
                        }}
                      >
                        {hasTemplates ? <>{count}{total > count && <> <span style={{ color: "#9ca3af", fontWeight: 400 }}>{total}</span></>}</> : (covered ? "" : "")}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        /* ── SINGLE GRADE VIEW ── */
        (() => {
          const gradeStr = String(selectedGrade);

          // Aggregate detail_coverage from leaves up to every ancestor
          const parentOf: Record<number, number | null> = {};
          for (const s of data.skills) parentOf[s.id] = s.parent_id;

          const agg: Record<number, Record<string, { covered: number; total: number }>> = {};
          const gradeTotal: Record<string, { covered: number; total: number }> = {};

          for (const s of data.skills) {
            if (s.children_count > 0) continue;
            for (const diff of ["easy", "medium", "hard"]) {
              const dc = s.detail_coverage?.[diff];
              if (!dc || dc.total === 0) continue;
              let id: number | null = s.id;
              while (id !== null) {
                if (!agg[id]) agg[id] = {};
                if (!agg[id][diff]) agg[id][diff] = { covered: 0, total: 0 };
                agg[id][diff].covered += dc.covered;
                agg[id][diff].total   += dc.total;
                id = parentOf[id] ?? null;
              }
              if (!gradeTotal[diff]) gradeTotal[diff] = { covered: 0, total: 0 };
              gradeTotal[diff].covered += dc.covered;
              gradeTotal[diff].total   += dc.total;
            }
          }

          function mkCell(dc: { covered: number; total: number } | undefined, bold: boolean) {
            if (!dc || dc.total === 0) return <td style={{ textAlign: "center", color: "#adb5bd" }}>—</td>;
            const { covered, total } = dc;
            const color = covered === total ? "#198754" : covered > 0 ? "#fd7e14" : "#adb5bd";
            return (
              <td style={{ textAlign: "center", fontWeight: bold ? 700 : 600, color, fontSize: 13 }}>
                {covered}/{total}
              </td>
            );
          }

          return (
            <table className="skills-matrix">
              <thead>
                <tr>
                  <th className="skill-header">Skill</th>
                  <th className="skill-header" style={{ width: 80, textAlign: "center" }}>Easy</th>
                  <th className="skill-header" style={{ width: 80, textAlign: "center" }}>Medium</th>
                  <th className="skill-header" style={{ width: 80, textAlign: "center" }}>Hard</th>
                </tr>
              </thead>
              <tbody>
                {data.skills.map(skill => {
                  const isParent = skill.children_count > 0;
                  const getDc = (diff: string) =>
                    isParent ? agg[skill.id]?.[diff] : skill.detail_coverage?.[diff];
                  return (
                    <tr
                      key={skill.id}
                      className={isParent ? "parent-row" : ""}
                      style={{ cursor: (!isParent || skill.parent_id === null) ? "pointer" : undefined }}
                      onClick={() => {
                        if (isParent && skill.parent_id === null) navigate(`/skill-parents/${skill.id}/overview?grade=${gradeStr}`);
                        else if (!isParent) navigate(`/skills/${skill.id}/overview/${gradeStr}`);
                      }}
                    >
                      <td style={{ paddingLeft: `${skill.depth * 20 + 10}px` }} title={skill.detail || undefined}>
                        {skill.description}
                      </td>
                      {mkCell(getDc("easy"),   false)}
                      {mkCell(getDc("medium"), false)}
                      {mkCell(getDc("hard"),   false)}
                    </tr>
                  );
                })}
                <tr style={{ borderTop: "2px solid #dee2e6", background: "#f8f9fa" }}>
                  <td style={{ paddingLeft: 10, fontWeight: 700, fontSize: 13 }}>Total</td>
                  {mkCell(gradeTotal["easy"],   true)}
                  {mkCell(gradeTotal["medium"], true)}
                  {mkCell(gradeTotal["hard"],   true)}
                </tr>
              </tbody>
            </table>
          );
        })()
      )}
    </div>
  );
}
