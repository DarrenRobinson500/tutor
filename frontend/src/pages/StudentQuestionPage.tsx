import { useParams, useNavigate, useSearchParams } from "react-router-dom";
import { useEffect, useState } from "react";
import { Layout } from "./components/Layout";
import { apiFetch } from "../utils/apiFetch";
import { PreviewPanel } from "./components/PreviewPanel";
import { DraggableCalculator } from "./components/Calculator";
import type { PreviewResponse } from "../types/PreviewResponse";
import type { StudentRecordResponse } from "../types/PreviewResponse";

const SESSION_LENGTH = 5;

async function flagFaultyTemplate(id: number) {
  try {
    await apiFetch(`/api/templates/${id}/flag_faulty/`, { method: "POST" });
  } catch {
    // best-effort
  }
}

interface CompletionData {
  level_before: number;
  level_after: number;
  gained: number;
}

export function StudentQuestionPage() {
  const { studentId, skillId } = useParams();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const focusAreaId = searchParams.get("focus_area_id");

  const [current, setCurrent] = useState<PreviewResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [skillName, setSkillName] = useState("");
  const [mastery, setMastery] = useState<number | null>(null);
  const [starsBefore, setStarsBefore] = useState<number>(0);
  const [competence, setCompetence] = useState("");
  const [templateId, setTemplateId] = useState<number | undefined>(undefined);
  const [seenTemplateIds, setSeenTemplateIds] = useState<number[]>([]);
  const [sessionTemplateIds, setSessionTemplateIds] = useState<number[]>([]);
  const [showCalculator, setShowCalculator] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [questionsAnswered, setQuestionsAnswered] = useState(0);
  const [completionData, setCompletionData] = useState<CompletionData | null>(null);

  useEffect(() => {
    async function loadInitial() {
      setLoading(true);

      const res = await apiFetch("/api/questions/record/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ student_id: studentId, skill_id: skillId, count: 1 }),
      });

      const data = await res.json();

      if (!data.next_question) {
        const faultyId = data.template_id;
        if (faultyId) flagFaultyTemplate(faultyId);
        setLoadError(
          data.error
            ? `Unable to load question: ${data.error}`
            : "Unable to load the next question. Please go back and try again."
        );
        setLoading(false);
        return;
      }

      const initialMastery = data.mastery ?? 0;
      setTemplateId(data.template_id);
      setCurrent(data.next_question);
      setSkillName(data.next_question.skill ?? "");
      setMastery(initialMastery);
      setStarsBefore(initialMastery);
      setCompetence(data.competence_label ?? "");
      setSeenTemplateIds([data.template_id]);
      setSessionTemplateIds(data.session_template_ids ?? []);
      setLoading(false);
    }

    loadInitial();
  }, [studentId, skillId]);

  async function handleComplete(afterMastery: number) {
    const before = starsBefore;
    if (focusAreaId) {
      try {
        const res = await apiFetch(`/api/focus-areas/${focusAreaId}/complete_learning/`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ level_before: before }),
        });
        const d = await res.json();
        setCompletionData(d);
      } catch {
        setCompletionData({ level_before: before, level_after: afterMastery, gained: afterMastery - before });
      }
    } else {
      setCompletionData({ level_before: before, level_after: afterMastery, gained: afterMastery - before });
    }
  }

  if (loading) {
    return (
      <Layout>
        <div className="container mt-4">Loading question…</div>
      </Layout>
    );
  }

  if (completionData !== null) {
    const { level_before, level_after, gained } = completionData;
    return (
      <Layout>
        <div className="container py-5 text-center" style={{ maxWidth: 560 }}>
          <div style={{ fontSize: 48, letterSpacing: 6, color: "#f5a623", marginBottom: 16 }}>
            {Array.from({ length: 6 }).map((_, i) => (
              <span key={i} style={{ opacity: i < level_after ? 1 : 0.2 }}>★</span>
            ))}
          </div>
          <h2 className="fw-bold mb-1" style={{ fontSize: 28 }}>
            {gained > 0
              ? `You gained ${gained} star${gained !== 1 ? "s" : ""}!`
              : "Great work!"}
          </h2>
          <p className="text-muted mb-3" style={{ fontSize: 15 }}>{skillName}</p>
          <div
            className="d-inline-flex align-items-center gap-3 px-4 py-2 rounded-pill mb-4"
            style={{ background: "#fff8e1", border: "1px solid #ffe082", fontSize: 18 }}
          >
            {Array.from({ length: 6 }).map((_, i) => (
              <span key={i} style={{ color: i < level_before ? "#f5a623" : "#ddd" }}>★</span>
            ))}
            <span style={{ color: "#888", fontSize: 14 }}>→</span>
            {Array.from({ length: 6 }).map((_, i) => (
              <span key={i} style={{ color: i < level_after ? "#f5a623" : "#ddd" }}>★</span>
            ))}
          </div>
          {gained === 0 && (
            <p className="text-muted mb-4" style={{ fontSize: 14 }}>
              Keep practising to earn your next star.
            </p>
          )}
          <br />
          <button
            className="btn btn-success btn-lg px-5"
            onClick={() => navigate(`/students/${studentId}`)}
          >
            Done
          </button>
        </div>
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
        <div className="row justify-content-center align-items-start">
          <div className="col-md-5">

            {/* Header: skill name, stars, progress */}
            <div className="d-flex justify-content-between align-items-start mb-2">
              <div>
                <h5 className="mb-0">{skillName}</h5>
                {mastery !== null && (
                  <div style={{ color: "#f5a623", fontSize: 18, lineHeight: 1.2 }}>
                    {Array.from({ length: 6 }).map((_, i) => (
                      <span key={i} style={{ opacity: i < mastery ? 1 : 0.2 }}>★</span>
                    ))}
                    {competence && (
                      <span className="text-muted ms-2" style={{ fontSize: 12 }}>{competence}</span>
                    )}
                  </div>
                )}
              </div>
              <span className="text-muted" style={{ fontSize: 13, whiteSpace: "nowrap" }}>
                Question {questionsAnswered + 1} of {SESSION_LENGTH}
              </span>
            </div>

            <hr />

            <PreviewPanel
              preview={current}
              mode="student"
              studentId={Number(studentId)}
              templateId={templateId!}
              seenTemplateIds={seenTemplateIds}
              sessionTemplateIds={sessionTemplateIds}
              showNotes={true}
              onStudentNext={(result: StudentRecordResponse) => {
                const newCount = questionsAnswered + 1;

                if (newCount >= SESSION_LENGTH) {
                  setQuestionsAnswered(newCount);
                  handleComplete(result.mastery ?? mastery ?? 0);
                  return;
                }

                if (!result.next_question) {
                  const faultyId = result.template_id ?? templateId;
                  if (faultyId) flagFaultyTemplate(faultyId);
                  setLoadError(`Unable to load the next question (Template #${faultyId}). Please go back and try again.`);
                  return;
                }

                const nextId = result.template_id;
                if (nextId) setSeenTemplateIds(prev => [...prev, nextId]);
                setQuestionsAnswered(newCount);
                setLoadError(null);
                setTemplateId(nextId ?? undefined);
                setCurrent(result.next_question);
                setMastery(result.mastery);
                setCompetence(result.competence_label ?? "");
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
      </div>
    </Layout>
  );
}
