import { useEffect, useState, useCallback } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { Layout } from "./components/Layout";
import { apiFetch } from "../utils/apiFetch";

// ── Types ────────────────────────────────────────────────────────────────────

interface ClassMeta {
  id: number;
  name: string;
  year_level: string;
  code: string;
  student_count: number;
}

interface StudentSummary {
  id: number;
  name: string;
  year_level: string;
}

interface FocusArea {
  id: number;
  skill_id: number;
  skill_code: string;
  skill_description: string;
  mastery: number;
  learning_done_this_week: boolean;
}

interface SkillRow {
  id: number;
  description: string;
  depth: number;
  parent_id: number | null;
  children_count: number;
  cells: Record<string, { validated: number }>;
}

// Per-skill aggregate across the class
interface SkillAggregate {
  id: number;
  description: string;
  depth: number;
  parent_id: number | null;
  children_count: number;
  hasTemplates: boolean;
  avgLevel: number;
  studentCount: number;
}

// ── Star display ─────────────────────────────────────────────────────────────

function SkillStars({ level }: { level: number }) {
  const standard = Math.min(level, 4);
  const empty = 4 - standard;
  return (
    <span className="skill-stars" aria-label={`${level} stars`}>
      {Array.from({ length: standard }).map((_, i) => (
        <span key={`s${i}`} className="star star-filled">★</span>
      ))}
      {Array.from({ length: empty }).map((_, i) => (
        <span key={`e${i}`} className="star star-empty">★</span>
      ))}
    </span>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export function TeacherClassFocusPage() {
  const { teacherId, classId } = useParams();
  const navigate = useNavigate();

  const [classMeta, setClassMeta] = useState<ClassMeta | null>(null);
  const [students, setStudents]   = useState<StudentSummary[]>([]);
  const [focusMap, setFocusMap]   = useState<Record<number, FocusArea[]>>({});
  const [skillAggs, setSkillAggs] = useState<SkillAggregate[]>([]);
  const [loading, setLoading]     = useState(true);

  const loadFocusAreas = useCallback(async (studentList: StudentSummary[]) => {
    const focusResults = await Promise.all(
      studentList.map(s =>
        apiFetch(`/api/focus-areas/?student_id=${s.id}`)
          .then(r => r.json())
          .then((areas: FocusArea[]) => ({ studentId: s.id, areas: Array.isArray(areas) ? areas : [] }))
          .catch(() => ({ studentId: s.id, areas: [] as FocusArea[] }))
      )
    );
    const fm: Record<number, FocusArea[]> = {};
    for (const { studentId, areas } of focusResults) fm[studentId] = areas;
    setFocusMap(fm);
  }, []);

  useEffect(() => {
    if (!teacherId || !classId) return;

    apiFetch(`/api/teachers/${teacherId}/class_detail/?class_id=${classId}`)
      .then(r => r.json())
      .then(async (data) => {
        setClassMeta({
          id: data.id,
          name: data.name,
          year_level: data.year_level,
          code: data.code,
          student_count: data.student_count,
        });

        const studentList: StudentSummary[] = (data.students ?? []).map((s: any) => ({
          id: s.id,
          name: s.name,
          year_level: s.year_level || data.year_level,
        }));
        setStudents(studentList);

        if (studentList.length === 0) { setLoading(false); return; }

        const grade = (data.year_level || "").replace(/\D/g, "");

        await loadFocusAreas(studentList);

        // Fetch syllabus matrix with each student's competency, then aggregate
        const matrixResults = await Promise.all(
          studentList.map(s =>
            apiFetch(`/api/skills/matrix/?grade=${grade}&student_id=${s.id}`)
              .then(r => r.json())
              .then((d: any) => ({ skills: d.skills ?? [], mastery: d.mastery ?? {} }))
              .catch(() => ({ skills: [], mastery: {} }))
          )
        );

        const baseSkills: SkillRow[] = matrixResults[0]?.skills ?? [];

        const levelSums: Record<number, number> = {};
        const levelCounts: Record<number, number> = {};
        for (const { mastery } of matrixResults) {
          for (const [skillIdStr, entry] of Object.entries(mastery as Record<string, { mastery: number }>)) {
            const sid = Number(skillIdStr);
            levelSums[sid]   = (levelSums[sid]   ?? 0) + (entry.mastery ?? 0);
            levelCounts[sid] = (levelCounts[sid]  ?? 0) + 1;
          }
        }

        const gradeStr = String(grade);
        const aggs: SkillAggregate[] = baseSkills.map((s: SkillRow) => {
          const cell = s.cells?.[gradeStr];
          const avgLevel = levelCounts[s.id]
            ? (levelSums[s.id] ?? 0) / studentList.length
            : 0;
          return {
            id: s.id,
            description: s.description,
            depth: s.depth,
            parent_id: s.parent_id,
            children_count: s.children_count,
            hasTemplates: (cell?.validated ?? 0) > 0,
            avgLevel,
            studentCount: studentList.length,
          };
        });
        setSkillAggs(aggs);
      })
      .finally(() => setLoading(false));
  }, [teacherId, classId]); // eslint-disable-line react-hooks/exhaustive-deps

  async function addClassFocus(skillId: number) {
    await apiFetch(`/api/teachers/${teacherId}/class_add_focus/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ class_id: Number(classId), skill_id: skillId }),
    });
    await loadFocusAreas(students);
  }

  async function removeClassFocus(skillId: number) {
    await apiFetch(`/api/teachers/${teacherId}/class_remove_focus/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ class_id: Number(classId), skill_id: skillId }),
    });
    await loadFocusAreas(students);
  }

  function handleStartAssessment() {
    navigate(`/teachers/${teacherId}/classes/${classId}/assessment-setup`);
  }

  // Derive which skill IDs are currently set as focus areas for any student in the class
  const classFocusSkillIds = new Set(
    Object.values(focusMap).flatMap(areas => areas.map(fa => fa.skill_id))
  );

  if (loading) return <Layout><div className="container mt-4">Loading…</div></Layout>;
  if (!classMeta) return <Layout><div className="container mt-4">Class not found.</div></Layout>;

  return (
    <Layout>
      <div className="container mt-4" style={{ maxWidth: "52.5%" }}>

        {/* ── Header ───────────────────────────────── */}
        <div className="d-flex align-items-center gap-2 mb-1">
          <Link to={`/teachers/${teacherId}`} className="btn btn-sm btn-outline-secondary">
            ← Back
          </Link>
          <h2 className="mb-0">{classMeta.name}</h2>
          <span className="badge bg-secondary">Year {classMeta.year_level}</span>
        </div>
        <div className="d-flex align-items-center justify-content-between mb-1">
          <p className="text-muted mb-0" style={{ fontSize: 13 }}>
            {classMeta.student_count} student{classMeta.student_count !== 1 ? "s" : ""}
          </p>
        </div>
        <p className="text-muted mb-4" style={{ maxWidth: 600 }}>
          Focus areas set the homework topics for students in your class. Add skills you want
          to prioritise — they will be set as focus areas for all enrolled students.
        </p>

        {/* ── Class Focus Areas ────────────────────── */}
        <h3 className="mt-2 mb-3">Class Focus Areas</h3>
        <ClassFocusSection
          students={students}
          focusMap={focusMap}
          onRemove={removeClassFocus}
        />

        <hr className="my-4" />

        {/* ── Syllabus ─────────────────────────────── */}
        <h3 className="mb-3">Syllabus</h3>
        <SyllabusSection
          skills={skillAggs}
          studentCount={classMeta.student_count}
          classFocusSkillIds={classFocusSkillIds}
          onAdd={addClassFocus}
          onRemove={removeClassFocus}
        />

      </div>
    </Layout>
  );
}

// ── Class Focus Areas section ─────────────────────────────────────────────────

function ClassFocusSection({
  students,
  focusMap,
  onRemove,
}: {
  students: StudentSummary[];
  focusMap: Record<number, FocusArea[]>;
  onRemove: (skillId: number) => Promise<void>;
}) {
  const [removing, setRemoving] = useState<number | null>(null);

  interface SkillEntry {
    skillId: number;
    description: string;
    code: string;
    students: { id: number; name: string; mastery: number; done: boolean }[];
  }
  const skillMap: Record<string, SkillEntry> = {};
  for (const s of students) {
    for (const fa of focusMap[s.id] ?? []) {
      if (!skillMap[fa.skill_code]) {
        skillMap[fa.skill_code] = {
          skillId: fa.skill_id,
          description: fa.skill_description,
          code: fa.skill_code,
          students: [],
        };
      }
      skillMap[fa.skill_code].students.push({
        id: s.id,
        name: s.name,
        mastery: fa.mastery,
        done: fa.learning_done_this_week,
      });
    }
  }

  const entries = Object.values(skillMap).sort((a, b) => b.students.length - a.students.length);

  if (entries.length === 0) {
    return (
      <div className="text-center py-4 text-muted">
        <p style={{ fontSize: "2.5rem" }}>🎯</p>
        <h5>No focus areas set</h5>
        <p>Use the Syllabus below to add focus areas for the class.</p>
      </div>
    );
  }

  async function handleRemove(skillId: number) {
    setRemoving(skillId);
    try { await onRemove(skillId); }
    finally { setRemoving(null); }
  }

  return (
    <div>
      {entries.map(entry => {
        const avgMastery = entry.students.reduce((s, st) => s + st.mastery, 0) / entry.students.length;
        const doneCount = entry.students.filter(st => st.done).length;
        return (
          <div key={entry.code} className="card mb-3 shadow-sm">
            <div className="card-body">
              <div className="d-flex align-items-start justify-content-between mb-2">
                <div className="d-flex align-items-center flex-wrap gap-3">
                  <h6 className="mb-0 fw-semibold">{entry.description}</h6>
                  <span className="text-muted" style={{ fontSize: 13 }}>
                    {entry.students.length} student{entry.students.length !== 1 ? "s" : ""}
                  </span>
                  <span className="text-muted" style={{ fontSize: 13 }}>
                    Avg <SkillStars level={Math.round(avgMastery)} />
                    <span className="ms-1">{avgMastery.toFixed(1)}</span>
                  </span>
                  <span
                    className={`badge ${doneCount === entry.students.length ? "bg-success" : doneCount > 0 ? "bg-warning text-dark" : "bg-secondary"}`}
                    title="Completed learning this week"
                  >
                    {doneCount}/{entry.students.length} this week
                  </span>
                </div>
                <button
                  className="btn btn-sm btn-outline-danger ms-3 flex-shrink-0"
                  disabled={removing === entry.skillId}
                  onClick={() => handleRemove(entry.skillId)}
                >
                  {removing === entry.skillId ? "Removing…" : "Remove"}
                </button>
              </div>
              <div className="d-flex flex-wrap gap-2">
                {entry.students.map(st => (
                  <Link
                    key={st.id}
                    to={`/students/${st.id}`}
                    className="badge text-decoration-none"
                    style={{
                      background: st.done ? "#e8f5e9" : "#f5f5f5",
                      color: st.done ? "#2e7d32" : "#555",
                      border: `1px solid ${st.done ? "#a5d6a7" : "#ddd"}`,
                      fontWeight: 500,
                      fontSize: 12,
                      padding: "4px 8px",
                    }}
                    title={`${st.name} — ${st.mastery} stars${st.done ? " · done this week" : ""}`}
                  >
                    {st.name.split(" ")[0]} {"★".repeat(st.mastery)}{"☆".repeat(Math.max(0, 4 - st.mastery))}
                  </Link>
                ))}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ── Syllabus section ──────────────────────────────────────────────────────────

function SyllabusSection({
  skills,
  studentCount,
  classFocusSkillIds,
  onAdd,
  onRemove,
}: {
  skills: SkillAggregate[];
  studentCount: number;
  classFocusSkillIds: Set<number>;
  onAdd: (skillId: number) => Promise<void>;
  onRemove: (skillId: number) => Promise<void>;
}) {
  const [busy, setBusy] = useState<number | null>(null);

  const childrenOf: Record<number, number[]> = {};
  for (const s of skills) {
    if (s.parent_id !== null) {
      if (!childrenOf[s.parent_id]) childrenOf[s.parent_id] = [];
      childrenOf[s.parent_id].push(s.id);
    }
  }
  const avgMap = Object.fromEntries(skills.map(s => [s.id, s.avgLevel]));

  function avgForNode(id: number): number {
    const children = childrenOf[id];
    if (!children?.length) return avgMap[id] ?? 0;
    const vals = children.map(avgForNode);
    return vals.reduce((a, b) => a + b, 0) / vals.length;
  }

  const leafSkills = skills.filter(s => s.children_count === 0);
  const overallAvg = leafSkills.length
    ? leafSkills.reduce((sum, s) => sum + s.avgLevel, 0) / leafSkills.length
    : 0;

  if (skills.length === 0) {
    return <p className="text-muted">No syllabus data available.</p>;
  }

  async function handleAdd(skillId: number) {
    setBusy(skillId);
    try { await onAdd(skillId); }
    finally { setBusy(null); }
  }

  async function handleRemove(skillId: number) {
    setBusy(skillId);
    try { await onRemove(skillId); }
    finally { setBusy(null); }
  }

  return (
    <>
      <div className="mb-3">
        <strong>Class average: </strong>
        <SkillStars level={Math.round(overallAvg)} />
        <span className="text-muted ms-2">{overallAvg.toFixed(1)} / 4</span>
        <span className="text-muted ms-3" style={{ fontSize: 13 }}>
          ({studentCount} student{studentCount !== 1 ? "s" : ""})
        </span>
      </div>

      <table className="skills-matrix w-100">
        <thead>
          <tr>
            <th className="skill-header">Skill</th>
            <th className="skill-header">Class average</th>
            <th className="skill-header"></th>
          </tr>
        </thead>
        <tbody>
          {skills.map(skill => {
            const isParent = skill.children_count > 0;
            const avg = avgForNode(skill.id);
            const isFocus = !isParent && classFocusSkillIds.has(skill.id);
            return (
              <tr key={skill.id} className={isParent ? "parent-row" : ""}>
                <td style={{ paddingLeft: `${skill.depth * 20 + 10}px` }}>
                  {skill.description}
                  {isFocus && (
                    <span className="badge bg-info ms-2" style={{ fontSize: 11 }}>Focus</span>
                  )}
                </td>
                <td>
                  <div className="d-flex align-items-center gap-2">
                    <SkillStars level={Math.round(avg)} />
                    <span className="text-muted" style={{ fontSize: "0.75rem" }}>
                      {avg.toFixed(1)}
                    </span>
                    {!isParent && skill.hasTemplates && (
                      <div
                        className="progress ms-2"
                        style={{ height: 6, width: 60 }}
                        title={`${avg.toFixed(1)} / 4`}
                      >
                        <div
                          className="progress-bar"
                          style={{
                            width: `${(avg / 4) * 100}%`,
                            background: avg >= 3 ? "#43a047" : avg >= 2 ? "#FF8C42" : "#e53935",
                          }}
                        />
                      </div>
                    )}
                  </div>
                </td>
                <td style={{ whiteSpace: "nowrap" }}>
                  {!isParent && (
                    isFocus ? (
                      <button
                        className="btn btn-sm btn-outline-danger"
                        disabled={busy === skill.id}
                        onClick={() => handleRemove(skill.id)}
                      >
                        {busy === skill.id ? "…" : "Remove"}
                      </button>
                    ) : (
                      <button
                        className="btn btn-sm btn-outline-primary"
                        disabled={busy === skill.id}
                        onClick={() => handleAdd(skill.id)}
                      >
                        {busy === skill.id ? "…" : "Add focus area"}
                      </button>
                    )
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </>
  );
}
