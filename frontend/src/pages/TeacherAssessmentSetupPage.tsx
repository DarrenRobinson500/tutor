import { useEffect, useState, useCallback } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { Layout } from "./components/Layout";
import { apiFetch } from "../utils/apiFetch";

interface ClassMeta {
  id: number;
  name: string;
  year_level: string;
  student_count: number;
}

interface SkillRow {
  id: number;
  description: string;
  depth: number;
  parent_id: number | null;
  children_count: number;
}

export function TeacherAssessmentSetupPage() {
  const { teacherId, classId } = useParams();
  const navigate = useNavigate();

  const [classMeta, setClassMeta]   = useState<ClassMeta | null>(null);
  const [skills, setSkills]         = useState<SkillRow[]>([]);
  const [included, setIncluded]     = useState<Set<number>>(new Set());
  const [loading, setLoading]       = useState(true);
  const [starting, setStarting]     = useState(false);

  useEffect(() => {
    if (!teacherId || !classId) return;

    apiFetch(`/api/teachers/${teacherId}/class_detail/?class_id=${classId}`)
      .then(r => r.json())
      .then(async (data) => {
        setClassMeta({
          id: data.id,
          name: data.name,
          year_level: data.year_level,
          student_count: data.student_count,
        });

        const students: { id: number }[] = data.students ?? [];
        const grade = (data.year_level || "").replace(/\D/g, "");
        if (!grade) { setLoading(false); return; }

        // Load skill tree (use first student for grade context, or grade alone)
        const firstStudentId = students[0]?.id;
        const matrixUrl = firstStudentId
          ? `/api/skills/matrix/?grade=${grade}&student_id=${firstStudentId}`
          : `/api/skills/matrix/?grade=${grade}`;

        const matrixData = await apiFetch(matrixUrl).then(r => r.json()).catch(() => ({ skills: [] }));
        const skillList: SkillRow[] = (matrixData.skills ?? []).map((s: any) => ({
          id: s.id,
          description: s.description,
          depth: s.depth,
          parent_id: s.parent_id,
          children_count: s.children_count,
        }));
        setSkills(skillList);

        if (!students.length) { setLoading(false); return; }

        // Load focus areas for all students → default included = union of class focus skill IDs
        const focusResults = await Promise.all(
          students.map((s: { id: number }) =>
            apiFetch(`/api/focus-areas/?student_id=${s.id}`)
              .then(r => r.json())
              .then((areas: any[]) => Array.isArray(areas) ? areas.map((a: any) => a.skill_id as number) : [])
              .catch(() => [] as number[])
          )
        );
        const defaultIds = new Set<number>(focusResults.flat());
        setIncluded(defaultIds);
      })
      .finally(() => setLoading(false));
  }, [teacherId, classId]);

  function toggle(skillId: number) {
    setIncluded(prev => {
      const next = new Set(prev);
      if (next.has(skillId)) next.delete(skillId);
      else next.add(skillId);
      return next;
    });
  }

  async function handleStart() {
    if (included.size === 0) return;
    setStarting(true);
    try {
      // Preserve the order skills appear in the syllabus
      const orderedIds = skills
        .filter(s => s.children_count === 0 && included.has(s.id))
        .map(s => s.id);

      const res = await apiFetch(`/api/teachers/${teacherId}/start_assessment/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ class_id: Number(classId), skill_ids: orderedIds }),
      });
      const data = await res.json();
      if (data.assessment_id) {
        navigate(`/teachers/${teacherId}/classes/${classId}/assessment/${data.assessment_id}`);
      }
    } finally {
      setStarting(false);
    }
  }

  if (loading) return <Layout><div className="container mt-4">Loading…</div></Layout>;
  if (!classMeta) return <Layout><div className="container mt-4">Class not found.</div></Layout>;

  const leafCount = skills.filter(s => s.children_count === 0 && included.has(s.id)).length;

  return (
    <Layout>
      <div className="container mt-4" style={{ maxWidth: "52.5%" }}>

        {/* Header */}
        <div className="d-flex align-items-center gap-2 mb-1">
          <Link to={`/teachers/${teacherId}`} className="btn btn-sm btn-outline-secondary">
            ← Back
          </Link>
          <h2 className="mb-0">{classMeta.name} — Assessment Setup</h2>
          <span className="badge bg-secondary">Year {classMeta.year_level}</span>
        </div>
        <p className="text-muted mb-1" style={{ fontSize: 13 }}>
          {classMeta.student_count} student{classMeta.student_count !== 1 ? "s" : ""}
        </p>
        <p className="text-muted mb-4" style={{ maxWidth: 560 }}>
          Select the skills to include in this assessment. The default selection matches
          your class focus areas — adjust as needed. This does not change the class's
          focus areas.
        </p>

        {/* Start button */}
        <div className="d-flex align-items-center gap-3 mb-4">
          <button
            className="btn btn-success"
            onClick={handleStart}
            disabled={starting || leafCount === 0}
          >
            {starting ? "Starting…" : `▶ Start Assessment (${leafCount} skill${leafCount !== 1 ? "s" : ""})`}
          </button>
          {leafCount === 0 && (
            <span className="text-muted" style={{ fontSize: 13 }}>
              Select at least one skill to start.
            </span>
          )}
        </div>

        {/* Syllabus with toggles */}
        {skills.length === 0 ? (
          <p className="text-muted">No syllabus data available for this year level.</p>
        ) : (
          <table className="skills-matrix w-100">
            <thead>
              <tr>
                <th className="skill-header">Skill</th>
                <th className="skill-header" style={{ width: 180 }}></th>
              </tr>
            </thead>
            <tbody>
              {skills.map(skill => {
                const isParent = skill.children_count > 0;
                const isIncluded = !isParent && included.has(skill.id);
                return (
                  <tr key={skill.id} className={isParent ? "parent-row" : ""}>
                    <td style={{ paddingLeft: `${skill.depth * 20 + 10}px` }}>
                      {skill.description}
                    </td>
                    <td>
                      {!isParent && (
                        <button
                          className={`btn btn-sm ${isIncluded ? "btn-success" : "btn-outline-secondary"}`}
                          style={{ minWidth: 160 }}
                          onClick={() => toggle(skill.id)}
                        >
                          {isIncluded ? "Included in Assessment" : "Not included"}
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}

      </div>
    </Layout>
  );
}
