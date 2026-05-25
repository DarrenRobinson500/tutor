import { useParams, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import { Layout } from "./components/Layout";
import { apiFetch } from "../utils/apiFetch";
import { PreviewPanel } from "./components/PreviewPanel";
import { DraggableCalculator } from "./components/Calculator";
import type { PreviewResponse, StudentRecordResponse } from "../types/PreviewResponse";

interface FocusSkill {
  id: number;
  description: string;
}

export function AssessmentQuestionPage() {
  const { studentId, assessmentId } = useParams();
  const navigate = useNavigate();

  const [focusSkills, setFocusSkills] = useState<FocusSkill[]>([]);
  const [skillIndex, setSkillIndex]   = useState(0);
  const [loading, setLoading]         = useState(true);
  const [done, setDone]               = useState(false);

  // Question state for current skill
  const [current, setCurrent]                   = useState<PreviewResponse | null>(null);
  const [templateId, setTemplateId]             = useState<number | undefined>(undefined);
  const [seenTemplateIds, setSeenTemplateIds]   = useState<number[]>([]);
  const [sessionTemplateIds, setSessionTemplateIds] = useState<number[]>([]);
  const [skillName, setSkillName]               = useState("");
  const [mastery, setMastery]                   = useState<number | null>(null);
  const [competence, setCompetence]             = useState("");
  const [showCalculator, setShowCalculator]     = useState(false);

  // Join assessment and get focus areas on mount
  useEffect(() => {
    async function join() {
      const res = await apiFetch(`/api/assessments/${assessmentId}/join/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ student_id: studentId }),
      });
      const data = await res.json();
      if (!data.ok || !data.focus_areas?.length) {
        setDone(true);
        setLoading(false);
        return;
      }
      setFocusSkills(data.focus_areas);
    }
    join();
  }, [assessmentId, studentId]);

  // Load question whenever skill index changes (after focus skills are set)
  useEffect(() => {
    if (!focusSkills.length) return;
    if (skillIndex >= focusSkills.length) {
      setDone(true);
      setLoading(false);
      return;
    }
    loadSkill(focusSkills[skillIndex].id);
  }, [focusSkills, skillIndex]); // eslint-disable-line react-hooks/exhaustive-deps

  async function loadSkill(skillId: number) {
    setLoading(true);
    setCurrent(null);
    const res = await apiFetch("/api/questions/record/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ student_id: studentId, skill_id: skillId, count: 1 }),
    });
    const data = await res.json();
    if (!data.next_question) { advanceSkill(); return; }

    setTemplateId(data.template_id);
    setCurrent(data.next_question);
    setSkillName(data.next_question.skill ?? focusSkills[skillIndex]?.description ?? "");
    setMastery(data.mastery);
    setCompetence(data.competence_label);
    setSeenTemplateIds([data.template_id]);
    setSessionTemplateIds(data.session_template_ids ?? []);
    setLoading(false);
  }

  async function recordAssessmentAnswer(correct: boolean) {
    await apiFetch(`/api/assessments/${assessmentId}/record_answer/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ student_id: studentId, correct }),
    }).catch(() => {});
  }

  function advanceSkill() {
    setSkillIndex(prev => prev + 1);
  }

  function handleStudentNext(result: StudentRecordResponse) {
    if (result.correct !== undefined) {
      recordAssessmentAnswer(result.correct);
    }
    advanceSkill();
  }

  if (done) {
    return (
      <Layout>
        <div className="container mt-4 text-center" style={{ maxWidth: 480 }}>
          <p style={{ fontSize: "3rem" }}>🎉</p>
          <h3>Assessment complete!</h3>
          <p className="text-muted">
            You've worked through all your focus areas. Great effort!
          </p>
          <button
            className="btn btn-primary mt-2"
            onClick={() => navigate(`/students/${studentId}`)}
          >
            Back to home
          </button>
        </div>
      </Layout>
    );
  }

  if (loading || !current) {
    return <Layout><div className="container mt-4">Loading question…</div></Layout>;
  }

  const skillCount = focusSkills.length;

  return (
    <Layout>
      <div className="container mt-4">

        {/* Progress indicator */}
        <div className="d-flex align-items-center gap-3 mb-3">
          <div className="text-muted" style={{ fontSize: 13 }}>
            Focus area {skillIndex + 1} of {skillCount}
          </div>
          <div className="progress flex-grow-1" style={{ height: 6, maxWidth: 200 }}>
            <div
              className="progress-bar bg-primary"
              style={{ width: `${((skillIndex + 1) / skillCount) * 100}%` }}
            />
          </div>
        </div>

        <div className="row justify-content-center align-items-start">
          <div className="col-md-5">
            <h2 className="mb-3">{skillName}</h2>
            <hr />
            <PreviewPanel
              preview={current}
              mode="student"
              studentId={Number(studentId)}
              templateId={templateId!}
              seenTemplateIds={seenTemplateIds}
              sessionTemplateIds={sessionTemplateIds}
              onStudentNext={handleStudentNext}
              disableOnWrong
            />
            <div className="mt-3">
              <button
                className="btn btn-outline-secondary btn-sm"
                onClick={() => setShowCalculator(v => !v)}
              >
                {showCalculator ? "Hide calculator" : "Show calculator"}
              </button>
            </div>
            {showCalculator && (
              <DraggableCalculator onClose={() => setShowCalculator(false)} />
            )}
          </div>
        </div>

      </div>
    </Layout>
  );
}
