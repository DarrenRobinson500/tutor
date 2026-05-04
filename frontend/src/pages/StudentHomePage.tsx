import { useParams, useNavigate, Link } from "react-router-dom";
import React, { useState, useEffect } from "react";
// import { WeeklyCalendar } from "./components/WeeklyCalendar";
import { Layout } from "./components/Layout";
// import { WeekData } from "../types/weekly";
import { apiFetch } from "../utils/apiFetch";
import { ProgressChart } from "./components/ProgressChart";

interface CellData {
  colour: string;
  count: number | null;
  validated: number;
  unvalidated: number;
}

interface SkillRow {
  id: number;
  code: string;
  description: string;
  depth: number;
  parent_id: number | null;
  children_count: number;
  cells: Record<string, CellData>;
  detail_coverage: Record<string, { covered: number; total: number }> | null;
}

interface FocusArea {
  id: number;
  skill_code: string;
  skill_description: string;
  order: number;
  mastery: number;
  learning_done_this_week: boolean;
  tutoring_done_this_week: boolean;
  level_before_learning: number | null;
  level_after_learning: number | null;
  label_before_learning: string | null;
  label_after_learning: string | null;
}

/** Renders the 0–6 star display for a skill competency level. */
function SkillStars({ level }: { level: number }) {
  // Levels 0–4: up to 4 standard stars (filled + empty)
  // Levels 5–6: 4 standard filled + 1 or 2 bonus stars
  const standard = Math.min(level, 4);
  const bonus    = Math.max(0, level - 4);  // 0, 1 or 2
  const empty    = 4 - standard;

  return (
    <span className="skill-stars" aria-label={`${level} stars`}>
      {Array.from({ length: standard }).map((_, i) => (
        <span key={`s${i}`} className="star star-filled">★</span>
      ))}
      {Array.from({ length: empty }).map((_, i) => (
        <span key={`e${i}`} className="star star-empty">★</span>
      ))}
      {Array.from({ length: bonus }).map((_, i) => (
        <span key={`b${i}`} className="star star-bonus">✦</span>
      ))}
    </span>
  );
}

function FocusAreaCard({ fa, studentId }: { fa: FocusArea; studentId: string }) {
  const gained = (fa.level_after_learning ?? 0) - (fa.level_before_learning ?? 0);
  const improved = fa.learning_done_this_week && gained > 0;
  const stars = fa.learning_done_this_week
    ? (fa.level_after_learning ?? fa.mastery)
    : fa.mastery;

  if (!fa.learning_done_this_week) {
    const params = new URLSearchParams({
      mode: "learning",
      skill_codes: fa.skill_code,
      focus_area_id: String(fa.id),
    });
    return (
      <div className="fa-card">
        <div className="fa-card-name">{fa.skill_description}</div>
        <div className="fa-card-right">
          <SkillStars level={stars} />
          <Link
            to={`/students/${studentId}/test?${params.toString()}`}
            className="btn btn-success btn-sm"
          >
            Learn
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="fa-card fa-card-done">
      <div className="fa-card-name">{fa.skill_description}</div>
      <div className="fa-card-right">
        <SkillStars level={stars} />
        <div className="fa-card-status">
          <span className="fa-done-label">Learning completed</span>
          {improved && (
            <span className="fa-improved-label">
              +{gained} star{gained > 1 ? "s" : ""} this week
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

export function StudentHomePage() {
  const { id } = useParams();
  const [student, setStudent] = useState<any>(null);
  const navigate = useNavigate();
  const [syllabus, setSyllabus] = useState<SkillRow[]>([]);
  const [mastery, setMastery] = useState<any>({});
  const [focusAreas, setFocusAreas] = useState<FocusArea[]>([]);
  const [activeAssessment, setActiveAssessment] = useState<{ id: number; class_name: string } | null>(null);


  useEffect(() => {
    apiFetch(`/api/students/${id}/home/`)
      .then((res) => res.json())
      .then((data) => setStudent(data));
  }, [id]);

  useEffect(() => {
    if (!id) return;
    apiFetch(`/api/focus-areas/?student_id=${id}`)
      .then((res) => res.json())
      .then((data) => { if (Array.isArray(data)) setFocusAreas(data); });
  }, [id]);

  // Poll for active assessment every 5 seconds
  useEffect(() => {
    if (!id) return;
    function check() {
      apiFetch(`/api/assessments/active/?student_id=${id}`)
        .then(r => r.json())
        .then(data => setActiveAssessment(data.assessment ?? null))
        .catch(() => {});
    }
    check();
    const t = setInterval(check, 5000);
    return () => clearInterval(t);
  }, [id]);

//   const tutorId = student?.tutor_id;

  useEffect(() => {
    if (!student?.year_level) return;

    apiFetch(`/api/skills/matrix/?grade=${student.year_level}&student_id=${id}`)
      .then(res => res.json())
      .then(data => {
        setSyllabus(data.skills);
        setMastery(data.mastery);
      });
  }, [student]);

  if (!student) {
    return (
      <Layout>
        <div className="container mt-4">Loading…</div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="container mt-4">
        <h1>Welcome back {student.name?.split(" ")[0]}</h1>
        <p><strong>Email:</strong> {student.email}<br/>
        <strong>Year Level:</strong> {student.year_level || "Not set"}<br/>
        <strong>Area of Study:</strong> {student.area_of_study || "Not set"}
        </p>
        <button
          className="btn btn-outline-primary"
          onClick={() => navigate(`/students/${id}/edit?returnTo=/students/${id}`)}
        >
          Edit My Details
        </button>
        <div className="d-flex flex-wrap gap-2 mt-2">
          <Link to={`/students/${id}/test?type=dynamic`} className="btn btn-outline-success">
            Start Skills Test
          </Link>
        </div>

        {activeAssessment && (
          <div
            className="alert mt-4 d-flex align-items-center justify-content-between"
            style={{ background: "#e8f5e9", border: "2px solid #43a047", borderRadius: 8 }}
          >
            <div>
              <strong style={{ fontSize: 16 }}>📋 Assessment in progress</strong>
              <div className="text-muted" style={{ fontSize: 13 }}>
                Your teacher has started an assessment for {activeAssessment.class_name}.
              </div>
            </div>
            <button
              className="btn btn-success ms-3"
              onClick={() => navigate(`/students/${id}/assessment/${activeAssessment.id}`)}
            >
              Join Assessment
            </button>
          </div>
        )}

        {focusAreas.length > 0 && (
          <>
            <hr />
            <h3 className="mt-4">Your Focus Areas</h3>
            <div className="fa-card-list">
              {focusAreas.map(fa => (
                <FocusAreaCard key={fa.id} fa={fa} studentId={id!} />
              ))}
            </div>
          </>
        )}

        <hr />
        <h3 className="mt-4">Your Progress</h3>
        <ProgressChart studentId={id!} />

        <hr />
        <h3 className="mt-4">Your Syllabus</h3>

        {syllabus.length === 0 && (
          <p>No syllabus available for this year level.</p>
        )}

      {(() => {
        // Build a map of parent_id → direct child skill IDs
        const childrenOf: Record<number, number[]> = {};
        for (const skill of syllabus) {
          if (skill.parent_id !== null) {
            if (!childrenOf[skill.parent_id]) childrenOf[skill.parent_id] = [];
            childrenOf[skill.parent_id].push(skill.id);
          }
        }

        // Recursively compute average mastery for any skill node
        function avgMastery(skillId: number): number {
          const children = childrenOf[skillId];
          if (!children || children.length === 0) {
            return mastery[skillId]?.mastery ?? 0;
          }
          const vals = children.map(avgMastery);
          return vals.reduce((a, b) => a + b, 0) / vals.length;
        }

        // Overall average across all leaf skills
        const leafSkills = syllabus.filter(s => s.children_count === 0);
        const overallAvg = leafSkills.length > 0
          ? leafSkills.reduce((sum, s) => sum + (mastery[s.id]?.mastery ?? 0), 0) / leafSkills.length
          : 0;

        return (
          <>
            <div className="mb-2">
              <strong>Overall: </strong>
              <SkillStars level={Math.round(overallAvg)} />
              <span className="text-muted ms-2">{overallAvg.toFixed(1)}</span>
            </div>

      <table className="skills-matrix">
        <thead>
          <tr>
            <th className="skill-header">Skill</th>
            <th className="skill-header">Stars</th>
            <th className="skill-header">Actions</th>
          </tr>
        </thead>

        <tbody>
          {syllabus.map(skill => {
            const isParent = skill.children_count > 0;
            const gradeStr = student.year_level ? String(student.year_level) : null;
            const cell = gradeStr ? skill.cells[gradeStr] : null;
            const templateCount = gradeStr && cell ? cell.validated : null;

            // For parent skills use average of children; for leaves use recorded mastery
            const masteryAvg = avgMastery(skill.id);
            const masteryEntry = mastery[skill.id];
            const masteryLevel = isParent ? masteryAvg : (masteryEntry?.mastery ?? 0);
            const difficulty = masteryLevel <= 2 ? 'easy' : masteryLevel <= 4 ? 'medium' : 'hard';
            const coverage = skill.detail_coverage;
            const hasTemplatesAtDifficulty = coverage
              ? (coverage[difficulty]?.covered ?? 0) > 0
              : templateCount !== null && templateCount > 0;

            // Time-lock: if the student has at least 1 star, they must wait 6 days
            // from when that level was achieved before they can learn again.
            let lockedUntil: Date | null = null;
            if (!isParent && masteryLevel >= 1 && masteryEntry?.updated_at) {
              const updatedAt = new Date(masteryEntry.updated_at);
              const unlock = new Date(updatedAt.getTime() + 6 * 24 * 60 * 60 * 1000);
              if (unlock > new Date()) {
                lockedUntil = unlock;
              }
            }

            return (
              <tr key={skill.id} className={isParent ? "parent-row" : ""}>

                <td style={{ paddingLeft: `${skill.depth * 20 + 10}px` }}>
                  {skill.description}
                </td>

                <td>
                  <SkillStars level={Math.round(masteryLevel)} />
                  {isParent && leafSkills.length > 0 && (
                    <span className="text-muted ms-1" style={{ fontSize: '0.75rem' }}>
                      {masteryAvg.toFixed(1)}
                    </span>
                  )}
                </td>

                <td>
                  {templateCount !== null && templateCount > 0 && (
                    hasTemplatesAtDifficulty || lockedUntil ? (
                      <button
                        className={lockedUntil ? "btn btn-sm btn-outline-warning" : "btn btn-sm btn-outline-primary"}
                        onClick={() => navigate(`/students/${id}/test/${skill.id}`)}
                        title={lockedUntil ? `Next star available ${lockedUntil.toLocaleDateString('en-AU', { day: 'numeric', month: 'short' })}` : undefined}
                      >
                        {lockedUntil
                          ? `Practice — next star ${lockedUntil.toLocaleDateString('en-AU', { day: 'numeric', month: 'short' })}`
                          : "Learn"}
                      </button>
                    ) : (
                      <button className="btn btn-sm btn-outline-secondary" disabled>
                        No Templates
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
      })()}

      </div>
    </Layout>
  );
}