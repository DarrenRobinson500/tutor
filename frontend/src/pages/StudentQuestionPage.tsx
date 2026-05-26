import { useParams, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import { Layout } from "./components/Layout";
import { apiFetch } from "../utils/apiFetch";
import { PreviewPanel } from "./components/PreviewPanel";
import { DraggableCalculator } from "./components/Calculator";
import type { PreviewResponse } from "../types/PreviewResponse";
import type { StudentRecordResponse } from "../types/PreviewResponse";

export function StudentQuestionPage() {
  const { studentId, skillId } = useParams();
  const navigate = useNavigate();
  const [current, setCurrent] = useState<PreviewResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [skillName, setSkillName] = useState("");
  const [mastery, setMastery] = useState<number | null>(null);
  const [competence, setCompetence] = useState("");
  const [templateId, setTemplateId] = useState<number | undefined>(undefined);
  const [seenTemplateIds, setSeenTemplateIds] = useState<number[]>([]);
  const [sessionTemplateIds, setSessionTemplateIds] = useState<number[]>([]);
  const [showCalculator, setShowCalculator] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    async function loadInitial() {
      setLoading(true);

      const res = await apiFetch("/api/questions/record/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          student_id: studentId,
          skill_id: skillId,
          count: 1
        })
      });

      const data = await res.json();

      if (!data.next_question) {
        console.error("No question returned:", data.error ?? data);
        setLoading(false);
        return;
      }

      setTemplateId(data.template_id);
      setCurrent(data.next_question);
      setSkillName(data.next_question.skill ?? "");
      setMastery(data.mastery);
      setCompetence(data.competence_label);
      setSeenTemplateIds([data.template_id]);
      setSessionTemplateIds(data.session_template_ids ?? []);
      setLoading(false);
    }

    loadInitial();
  }, [studentId, skillId]);

  if (loading) {
    return (
      <Layout>
        <div className="container mt-4">Loading question…</div>
      </Layout>
    );
  }

  if (loadError || !current) {
    return (
      <Layout>
        <div className="container mt-4">
          <div className="alert alert-warning">
            {loadError ?? "Unable to load the next question. Please try again."}
          </div>
          <button className="btn btn-primary" onClick={() => navigate(-1)}>
            Go back
          </button>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="container mt-4">

        {current && (
          <div className="row justify-content-center align-items-start">
            <div className="col-md-5">
              <h2>{skillName}</h2>
              <div className="text-muted small">Template #{templateId}</div>
              <hr/>
              <PreviewPanel
                preview={current}
                mode="student"
                studentId={Number(studentId)}
                templateId={templateId!}
                seenTemplateIds={seenTemplateIds}
                sessionTemplateIds={sessionTemplateIds}
                onStudentNext={(result: StudentRecordResponse) => {
                  if (result.loop_complete) {
                    navigate(`/students/${studentId}`);
                    return;
                  }
                  if (!result.next_question) {
                    setLoadError(`Unable to load the next question (Template #${result.template_id ?? templateId}). Please go back and try again.`);
                    return;
                  }
                  const nextId = result.template_id;
                  if (nextId) {
                    setSeenTemplateIds(prev => [...prev, nextId]);
                  }
                  setLoadError(null);
                  setTemplateId(nextId ?? undefined);
                  setCurrent(result.next_question);
                  setMastery(result.mastery);
                  setCompetence(result.competence_label);
                }}
                extraInputActions={
                  <button
                    className="btn btn-outline-secondary btn-sm"
                    onClick={() => setShowCalculator(v => !v)}
                  >
                    {showCalculator ? "Hide calculator" : "Show calculator"}
                  </button>
                }
              />

              {showCalculator && (
                <DraggableCalculator onClose={() => setShowCalculator(false)} />
              )}
            </div>
          </div>
        )}

      </div>
    </Layout>
  );
}