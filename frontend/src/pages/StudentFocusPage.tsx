import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Layout } from "./components/Layout";
import { apiFetch } from "../utils/apiFetch";

interface FocusArea {
  id: number;
  skill_id: number;
  skill_code: string;
  skill_description: string;
  order: number;
  mastery: number;
  competence_label: string;
  learning_done_this_week: boolean;
  level_before_learning: number | null;
  level_after_learning: number | null;
  label_before_learning: string | null;
  label_after_learning: string | null;
}

interface SkillRow {
  id: number;
  code: string;
  description: string;
  depth: number;
  children_count: number;
  parent_id: number | null;
}

interface MasteryEntry {
  mastery: number;
  competence_label: string;
}

const COMPETENCE_BADGE: Record<string, string> = {
  "Not Started":    "secondary",
  "Developing":     "secondary",
  "Easy Complete":  "warning",
  "Emerging":       "warning",
  "Competent":      "primary",
  "Advanced":       "info",
  "Mastered":       "success",
};

function LearningStatus({ fa }: { fa: FocusArea }) {
  if (!fa.learning_done_this_week) {
    return (
      <span className="fa-learning-status fa-learning-pending">
        Learning not completed yet
      </span>
    );
  }
  const before = fa.label_before_learning;
  const after  = fa.label_after_learning;
  if (before !== null && after !== null && before !== after) {
    return (
      <span className="fa-learning-status fa-learning-done fa-learning-improved">
        Learning completed: Skill level changed from <strong>{before}</strong> to <strong>{after}</strong>
      </span>
    );
  }
  const label = after ?? before ?? fa.competence_label;
  return (
    <span className="fa-learning-status fa-learning-done">
      Learning completed: Skill level <strong>{label}</strong>
    </span>
  );
}

const PARENT_STYLE: React.CSSProperties = {
  background: "#f0f0f0",
  fontWeight: 600,
};

/** Build a display list for the focus areas table, inserting parent header rows. */
function buildFocusDisplayRows(
  focusAreas: FocusArea[],
  skillMap: Map<number, SkillRow>
): Array<{ type: "parent"; skill: SkillRow } | { type: "focus"; fa: FocusArea; idx: number }> {
  const shown = new Set<number>();
  const rows: Array<{ type: "parent"; skill: SkillRow } | { type: "focus"; fa: FocusArea; idx: number }> = [];

  focusAreas.forEach((fa, idx) => {
    const skill = skillMap.get(fa.skill_id);
    if (skill) {
      // Collect ancestor chain from root → immediate parent
      const chain: SkillRow[] = [];
      let cur: SkillRow = skill;
      while (cur.parent_id !== null) {
        const parent = skillMap.get(cur.parent_id);
        if (!parent) break;
        chain.unshift(parent);
        cur = parent;
      }
      for (const ancestor of chain) {
        if (!shown.has(ancestor.id)) {
          shown.add(ancestor.id);
          rows.push({ type: "parent", skill: ancestor });
        }
      }
    }
    rows.push({ type: "focus", fa, idx });
  });

  return rows;
}

export function StudentFocusPage() {
  const { studentId } = useParams();
  const navigate = useNavigate();
  const params = new URLSearchParams(window.location.search);
  const returnTo = params.get("returnTo") || `/tutors`;

  const [student, setStudent] = useState<any>(null);
  const [focusAreas, setFocusAreas] = useState<FocusArea[]>([]);
  const [allSkills, setAllSkills] = useState<SkillRow[]>([]);
  const [skillMap, setSkillMap] = useState<Map<number, SkillRow>>(new Map());
  const [masteryMap, setMasteryMap] = useState<Record<number, MasteryEntry>>({});
  const [focusIds, setFocusIds] = useState<Set<number>>(new Set());

  useEffect(() => {
    apiFetch(`/api/students/${studentId}/`)
      .then(r => r.json())
      .then(setStudent);
  }, [studentId]);

  useEffect(() => {
    loadFocusAreas();
  }, [studentId]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!student?.year_level) return;
    apiFetch(`/api/skills/matrix/?grade=${student.year_level}&student_id=${studentId}`)
      .then(r => r.json())
      .then(data => {
        const skills = data.skills as SkillRow[];
        setAllSkills(skills);
        setSkillMap(new Map(skills.map(s => [s.id, s])));
        setMasteryMap(data.mastery || {});
      });
  }, [student?.year_level, studentId]);

  function loadFocusAreas() {
    apiFetch(`/api/focus-areas/?student_id=${studentId}`)
      .then(r => r.json())
      .then((data: FocusArea[]) => {
        setFocusAreas(data);
        setFocusIds(new Set(data.map(fa => fa.skill_id)));
      });
  }

  async function addFocus(skillId: number) {
    await apiFetch("/api/focus-areas/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ student_id: studentId, skill_id: skillId }),
    });
    loadFocusAreas();
  }

  async function removeFocus(focusAreaId: number) {
    await apiFetch(`/api/focus-areas/${focusAreaId}/`, { method: "DELETE" });
    loadFocusAreas();
  }

  async function moveFocus(focusAreaId: number, direction: "up" | "down") {
    await apiFetch(`/api/focus-areas/${focusAreaId}/move_${direction}/`, { method: "POST" });
    loadFocusAreas();
  }

  if (!student) return <Layout><div className="container mt-4">Loading…</div></Layout>;

  const firstName = student.first_name || student.name?.split(" ")[0] || "Student";
  const focusDisplayRows = buildFocusDisplayRows(focusAreas, skillMap);

  return (
    <Layout>
      <div className="container mt-4" style={{ maxWidth: "52.5%" }}>
        <button className="btn btn-link ps-0 mb-3" onClick={() => navigate(returnTo)}>
          ← Back
        </button>

        <h2>Focus areas for {firstName}</h2>
        {student.year_level && (
          <p className="text-muted">Year {student.year_level}</p>
        )}

        <p className="text-muted mt-2" style={{ maxWidth: 600 }}>
          Focus areas guide the questions used during {firstName}'s tutoring sessions and set
          the topics for their homework. Add the skills you want to prioritise and arrange
          them in order of importance.
        </p>

        {/* ── Current focus areas ── */}
        <h4 className="mt-4">Current focus areas</h4>
        {focusAreas.length === 0 ? (
          <p className="text-muted">No focus areas set yet.</p>
        ) : (
          <ul className="list-group mb-4">
            {focusDisplayRows.map((row, i) => {
              if (row.type === "parent") {
                return (
                  <li
                    key={`p-${row.skill.id}`}
                    className="list-group-item"
                    style={{ ...PARENT_STYLE, paddingLeft: `${row.skill.depth * 20 + 12}px` }}
                  >
                    {row.skill.description}
                  </li>
                );
              }
              const { fa, idx } = row;
              const skill = skillMap.get(fa.skill_id);
              const indent = skill ? skill.depth * 20 + 12 : 12;
              return (
                <li
                  key={fa.id}
                  className="list-group-item d-flex justify-content-between align-items-center"
                  style={{ paddingLeft: indent }}
                >
                  <div className="d-flex align-items-center gap-3">
                    <span className="text-muted fw-bold" style={{ minWidth: 24 }}>{idx + 1}</span>
                    <div className="d-flex flex-column gap-1">
                      <button
                        className="btn btn-sm btn-outline-secondary py-0 px-1 lh-1"
                        disabled={idx === 0}
                        onClick={() => moveFocus(fa.id, "up")}
                        title="Move up"
                      >▲</button>
                      <button
                        className="btn btn-sm btn-outline-secondary py-0 px-1 lh-1"
                        disabled={idx === focusAreas.length - 1}
                        onClick={() => moveFocus(fa.id, "down")}
                        title="Move down"
                      >▼</button>
                    </div>
                    <div>
                      <span className="fw-semibold">{fa.skill_description}</span>
                      <span className={`badge bg-${COMPETENCE_BADGE[fa.competence_label] ?? "secondary"} ms-2`}>
                        {fa.competence_label}
                      </span>
                      <div className="mt-1">
                        <LearningStatus fa={fa} />
                      </div>
                    </div>
                  </div>
                  <button
                    className="btn btn-sm btn-outline-danger"
                    onClick={() => removeFocus(fa.id)}
                  >
                    Remove
                  </button>
                </li>
              );
            })}
          </ul>
        )}

        {/* ── Skills for year ── */}
        <h4 className="mt-4">
          {student.year_level ? `Year ${student.year_level} skills` : "Skills"}
        </h4>
        {!student.year_level && (
          <p className="text-warning">Set the student's year level to see skills.</p>
        )}

        {allSkills.length > 0 && (
          <ul className="list-group">
            {allSkills.map(skill => {
              const isParent = skill.children_count > 0;
              const entry = masteryMap[skill.id];
              const label = entry?.competence_label ?? "Developing";
              const isFocus = focusIds.has(skill.id);
              const focusAreaId = focusAreas.find(fa => fa.skill_id === skill.id)?.id;

              if (isParent) {
                return (
                  <li
                    key={skill.id}
                    className="list-group-item"
                    style={{ ...PARENT_STYLE, paddingLeft: `${skill.depth * 20 + 12}px` }}
                  >
                    {skill.description}
                  </li>
                );
              }

              return (
                <li
                  key={skill.id}
                  className={`list-group-item d-flex justify-content-between align-items-center${isFocus ? " list-group-item-light" : ""}`}
                  style={{ paddingLeft: `${skill.depth * 20 + 12}px` }}
                >
                  <div>
                    <span>{skill.description}</span>
                    <span className={`badge bg-${COMPETENCE_BADGE[label] ?? "secondary"} ms-2`}>
                      {label}
                    </span>
                    {isFocus && <span className="badge bg-info ms-2">Focus</span>}
                  </div>
                  {isFocus ? (
                    <button
                      className="btn btn-sm btn-outline-danger"
                      onClick={() => focusAreaId && removeFocus(focusAreaId)}
                    >
                      Remove
                    </button>
                  ) : (
                    <button
                      className="btn btn-sm btn-outline-primary"
                      onClick={() => addFocus(skill.id)}
                    >
                      Add focus area
                    </button>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </Layout>
  );
}
