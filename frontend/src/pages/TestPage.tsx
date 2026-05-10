import { useState, useEffect, useCallback } from "react";
import { useParams, useNavigate, useSearchParams } from "react-router-dom";
import { Layout } from "./components/Layout";
import { PreviewPanel } from "./components/PreviewPanel";
import { DraggableCalculator } from "./components/Calculator";
import { apiFetch } from "../utils/apiFetch";
import { useYears } from "../utils/useYears";
import type { PreviewResponse, StudentRecordResponse } from "../types/PreviewResponse";

interface TestQuestion {
  template_id: number;
  preview: PreviewResponse;
  skill_code: string;
  skill_description: string;
  difficulty: string;
  current_skill_index: number;
  total_skills: number;
  correct_streak: number;
  incorrect_count: number;
}

interface SkillProgress {
  code: string;
  description: string;
  result: string;
}

interface Skill {
  id: number;
  description: string;
  children_count: number;
  detail?: string;
}

const TEST_LABEL: Record<string, string> = {
  easy:    "Easy Skills Test",
  medium:  "Moderate Skills Test",
  hard:    "Hard Skills Test",
  dynamic: "Skills Test",
};

const DIFFICULTY_BADGE: Record<string, string> = {
  easy: "success",
  medium: "warning",
  hard: "danger",
};

const RESULT_COLOR: Record<string, string> = {
  mastered: "#c3e6cb",
  hard: "#d4edda",
  medium: "#d1ecf1",
  easy: "#fff3cd",
  none: "#f8d7da",
};

const RESULT_LABEL: Record<string, string> = {
  mastered: "Advanced",
  hard:     "Advanced",
  medium:   "Proficient",
  easy:     "Developing",
  none:     "Not attempted",
};

// ── Inline metadata editor ────────────────────────────────────────────────────

interface MetadataEditorProps {
  templateId: number;
  onClose: () => void;
}

function MetadataEditor({ templateId, onClose }: MetadataEditorProps) {
  const years = useYears();
  const [grade, setGrade] = useState("");
  const [difficulty, setDifficulty] = useState("");
  const [subject, setSubject] = useState("");
  const [selectedSkillId, setSelectedSkillId] = useState<number | null>(null);
  const [selectedSkillDesc, setSelectedSkillDesc] = useState("");
  const [selectedSkillDetail, setSelectedSkillDetail] = useState<string | null>(null);

  const [breadcrumb, setBreadcrumb] = useState<Skill[]>([]);
  const [children, setChildren] = useState<Skill[]>([]);
  const [loadingSkills, setLoadingSkills] = useState(false);

  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState(false);

  // Load template metadata
  useEffect(() => {
    apiFetch(`/api/templates/${templateId}/`)
      .then(r => r.json())
      .then((data: any) => {
        setGrade(data.grade ?? "");
        setDifficulty(data.difficulty ?? "");
        setSubject(data.subject ?? "");
        setSelectedSkillId(data.skill ?? null);

        if (data.skill) {
          Promise.all([
            apiFetch(`/api/skills/${data.skill}/`).then(r => r.json()),
            apiFetch(`/api/skills/${data.skill}/parents/`).then(r => r.json()),
          ]).then(([skillData, parents]: [Skill, Skill[]]) => {
            setSelectedSkillDesc(skillData.description);
            setSelectedSkillDetail(skillData.detail ?? null);
            setBreadcrumb(parents);
            const parentId = parents.length > 0 ? parents[parents.length - 1].id : null;
            loadChildren(parentId);
          });
        } else {
          loadChildren(null);
        }
      });
  }, [templateId]);

  function loadChildren(parentId: number | null) {
    setLoadingSkills(true);
    const url = parentId == null ? "/api/skills/" : `/api/skills/?parent=${parentId}`;
    apiFetch(url)
      .then(r => r.json())
      .then((data: Skill[]) => {
        setChildren(data);
        setLoadingSkills(false);
      });
  }

  function drillDown(skill: Skill) {
    if (skill.children_count > 0) {
      setBreadcrumb(prev => [...prev, skill]);
      loadChildren(skill.id);
    } else {
      setSelectedSkillId(skill.id);
      setSelectedSkillDesc(skill.description);
      setSelectedSkillDetail(skill.detail ?? null);
    }
  }

  function navigateBreadcrumb(index: number) {
    if (index === -1) {
      setBreadcrumb([]);
      loadChildren(null);
    } else {
      const crumb = breadcrumb[index];
      setBreadcrumb(prev => prev.slice(0, index + 1));
      loadChildren(crumb.id);
    }
  }

  async function handleSave() {
    setSaving(true);
    setSaveError(null);
    setSaveSuccess(false);
    try {
      const res = await apiFetch(`/api/templates/${templateId}/`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ grade, difficulty, subject, skill: selectedSkillId }),
      });
      if (!res.ok) {
        const data = await res.json();
        setSaveError(data.detail ?? "Save failed");
        return;
      }
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 2000);
    } catch (e: any) {
      setSaveError(e.message ?? "Unexpected error");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="border rounded p-3 mt-2 bg-light" style={{ fontSize: 14 }}>
      <div className="d-flex justify-content-between align-items-center mb-3">
        <strong>Edit Metadata</strong>
        <button className="btn btn-sm btn-outline-secondary" onClick={onClose}>✕</button>
      </div>

      {/* Grade / Difficulty / Subject */}
      <div className="row g-2 mb-3">
        <div className="col-sm-3">
          <label className="form-label mb-1">Year / Grade</label>
          <select className="form-select form-select-sm" value={grade} onChange={e => setGrade(e.target.value)}>
            <option value="">— select —</option>
            {years.map(y => <option key={y.code} value={y.code}>{y.label}</option>)}
          </select>
        </div>
        <div className="col-sm-3">
          <label className="form-label mb-1">Difficulty</label>
          <select className="form-select form-select-sm" value={difficulty} onChange={e => setDifficulty(e.target.value)}>
            <option value="">— select —</option>
            <option value="easy">Easy</option>
            <option value="medium">Medium</option>
            <option value="hard">Hard</option>
          </select>
        </div>
        <div className="col-sm-6">
          <label className="form-label mb-1">Subject</label>
          <input
            className="form-control form-control-sm"
            value={subject}
            onChange={e => setSubject(e.target.value)}
            placeholder="e.g. Fractions"
          />
        </div>
      </div>

      {/* Skill browser */}
      <div className="mb-3">
        <label className="form-label mb-1">Skill</label>

        {selectedSkillId && (
          <div className="alert alert-success py-1 px-2 d-flex justify-content-between align-items-center mb-2" style={{ fontSize: 13 }}>
            <span><strong>Selected:</strong> {selectedSkillDesc}</span>
            <button
              className="btn btn-sm btn-outline-secondary py-0"
              onClick={() => { setSelectedSkillId(null); setSelectedSkillDesc(""); setSelectedSkillDetail(null); }}
            >
              Clear
            </button>
          </div>
        )}

        {selectedSkillId && selectedSkillDetail && (
          <div className="mb-2 p-2 bg-white rounded border" style={{ fontSize: 12 }}>
            <ul className="mb-0 ps-3">
              {selectedSkillDetail.split("\n").filter(Boolean).map((line, i) => (
                <li key={i}>{line}</li>
              ))}
            </ul>
          </div>
        )}

        {/* Breadcrumb */}
        <nav className="mb-1">
          <ol className="breadcrumb mb-0" style={{ fontSize: 12 }}>
            <li className="breadcrumb-item">
              <button className="btn btn-link p-0 text-decoration-none" style={{ fontSize: 12 }} onClick={() => navigateBreadcrumb(-1)}>
                All Skills
              </button>
            </li>
            {breadcrumb.map((crumb, i) => (
              <li key={crumb.id} className="breadcrumb-item">
                <button className="btn btn-link p-0 text-decoration-none" style={{ fontSize: 12 }} onClick={() => navigateBreadcrumb(i)}>
                  {crumb.description}
                </button>
              </li>
            ))}
          </ol>
        </nav>

        {/* Skill list */}
        <div className="border rounded" style={{ maxHeight: 200, overflowY: "auto" }}>
          {loadingSkills ? (
            <div className="d-flex justify-content-center py-2">
              <div className="spinner-border spinner-border-sm text-primary" role="status" />
            </div>
          ) : children.length === 0 ? (
            <div className="text-muted p-2" style={{ fontSize: 13 }}>No skills found.</div>
          ) : (
            <div className="list-group list-group-flush">
              {children.map(skill => (
                <button
                  key={skill.id}
                  className="list-group-item list-group-item-action d-flex justify-content-between align-items-center py-1 px-2"
                  style={{ fontSize: 13 }}
                  onClick={() => drillDown(skill)}
                >
                  <span>{skill.description}</span>
                  {skill.children_count > 0 ? (
                    <span className="text-muted small">▶</span>
                  ) : (
                    selectedSkillId === skill.id
                      ? <span className="badge bg-success">Selected</span>
                      : <span className="badge bg-outline text-muted border">Select</span>
                  )}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {saveError && <div className="alert alert-danger py-1 px-2 mb-2" style={{ fontSize: 13 }}>{saveError}</div>}

      <div className="d-flex align-items-center gap-2">
        <button className="btn btn-sm btn-primary" onClick={handleSave} disabled={saving}>
          {saving ? <><span className="spinner-border spinner-border-sm me-1" />Saving…</> : "Save Metadata"}
        </button>
        {saveSuccess && <span style={{ color: "green", fontSize: 13 }}>Saved</span>}
      </div>
    </div>
  );
}

// ── TestPage ──────────────────────────────────────────────────────────────────

export function TestPage() {
  const { studentId } = useParams<{ studentId: string }>();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const testTypeParam = (searchParams.get("type") ?? "") as string;
  const modeParam = searchParams.get("mode") ?? "";
  const skillCodesParam = searchParams.get("skill_codes") ?? "";
  const focusAreaIdParam = searchParams.get("focus_area_id") ?? "";

  const storedUser = localStorage.getItem("user");
  const isTutor = storedUser ? JSON.parse(storedUser)?.role === "tutor" : false;

  const [sessionId, setSessionId] = useState<number | null>(null);
  const [testType, setTestType] = useState(testTypeParam);
  const [mode, setMode] = useState(modeParam);
  const [studentFirstName, setStudentFirstName] = useState("");
  const [question, setQuestion] = useState<TestQuestion | null>(null);
  const [skillProgress, setSkillProgress] = useState<SkillProgress[]>([]);
  const [status, setStatus] = useState<"loading" | "active" | "complete" | "error">("loading");
  const [errorMsg, setErrorMsg] = useState("");
  const [preview, setPreview] = useState<PreviewResponse | null>(null);
  const [showMetadata, setShowMetadata] = useState(false);
  const [showCalculator, setShowCalculator] = useState(false);
  const questionStartRef = useState<number>(() => Date.now())[0];
  const questionStartTime = useState<number>(Date.now());
  const [learnComplete, setLearnComplete] = useState<{
    starsBefore: number | null;
    starsAfter: number | null;
    starsGained: number | null;
    skillDescription: string | null;
  } | null>(null);

  useEffect(() => {
    startTest();
    apiFetch(`/api/students/${studentId}/`)
      .then(r => r.json())
      .then(d => {
        const name = d.first_name || d.user?.first_name;
        if (name) setStudentFirstName(name);
      })
      .catch(() => {});
  }, []);

  // Close metadata panel when question changes
  useEffect(() => {
    setShowMetadata(false);
    questionStartTime[1](Date.now());
  }, [question?.template_id]);

  async function startTest() {
    setStatus("loading");
    try {
      const body: Record<string, any> = { student_id: studentId, test_type: testTypeParam };
      if (modeParam) body.mode = modeParam;
      if (skillCodesParam) body.skill_codes = skillCodesParam.split(",").map(s => s.trim()).filter(Boolean);
      if (focusAreaIdParam) body.focus_area_id = parseInt(focusAreaIdParam, 10);

      const res = await apiFetch("/api/tests/start/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (!res.ok) { setErrorMsg(data.error || "Failed to start test"); setStatus("error"); return; }
      if (data.complete) { setStatus("complete"); setSessionId(data.session_id); return; }
      setSessionId(data.session_id);
      if (data.test_type) setTestType(data.test_type);
      if (data.mode) setMode(data.mode);
      setQuestion(data.question);
      setPreview(data.question.preview);
      if (data.skill_progress) setSkillProgress(data.skill_progress);
      questionStartTime[1](Date.now());
      setStatus("active");
    } catch (e: any) {
      setErrorMsg(e.message || "Unexpected error");
      setStatus("error");
    }
  }

  const handleAnswer = useCallback(async (result: StudentRecordResponse) => {
    if (!sessionId || !question) return;
    const timeTakenMs = Date.now() - questionStartTime[0];
    try {
      const res = await apiFetch(`/api/tests/${sessionId}/answer/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          template_id: question.template_id,
          correct: result.correct ?? false,
          time_taken_ms: timeTakenMs,
        }),
      });
      const data = await res.json();
      if (data.complete) {
        if (data.mode === "learning") {
          setLearnComplete({
            starsBefore: data.stars_before ?? null,
            starsAfter: data.stars_after ?? null,
            starsGained: data.stars_gained ?? null,
            skillDescription: data.skill_description ?? null,
          });
        }
        setStatus("complete");
        if (data.skill_progress) setSkillProgress(data.skill_progress);
        return;
      }
      setQuestion(data.question);
      setPreview(data.question.preview);
      if (data.skill_progress) setSkillProgress(data.skill_progress);
    } catch (e: any) {
      setErrorMsg(e.message || "Unexpected error");
      setStatus("error");
    }
  }, [sessionId, question, questionStartTime]);

  if (status === "loading") {
    return (
      <Layout>
        <div className="d-flex justify-content-center align-items-center" style={{ minHeight: 300 }}>
          <div className="spinner-border text-primary me-3" />
          <span>Loading test…</span>
        </div>
      </Layout>
    );
  }

  if (status === "error") {
    return (
      <Layout>
        <div className="container py-4">
          <div className="alert alert-danger">{errorMsg}</div>
          <button className="btn btn-secondary" onClick={() => navigate(-1)}>Back</button>
        </div>
      </Layout>
    );
  }

  if (status === "complete") {
    const isLearning = mode === "learning";

    if (isLearning && learnComplete) {
      const { starsBefore, starsAfter, starsGained, skillDescription } = learnComplete;
      const totalStars = starsAfter ?? 0;
      return (
        <Layout>
          <div className="container py-5 text-center" style={{ maxWidth: 560 }}>
            {/* Stars display */}
            <div style={{ fontSize: 48, letterSpacing: 6, color: "#f5a623", marginBottom: 16 }}>
              {Array.from({ length: 6 }).map((_, i) => (
                <span key={i} style={{ opacity: i < totalStars ? 1 : 0.2 }}>★</span>
              ))}
            </div>

            <h2 className="fw-bold mb-1" style={{ fontSize: 28 }}>
              {starsGained && starsGained > 0
                ? `You gained ${starsGained} star${starsGained !== 1 ? "s" : ""}!`
                : "Learning session complete!"}
            </h2>

            {skillDescription && (
              <p className="text-muted mb-2" style={{ fontSize: 15 }}>{skillDescription}</p>
            )}

            {starsBefore !== null && starsAfter !== null && (
              <div
                className="d-inline-flex align-items-center gap-3 px-4 py-2 rounded-pill mt-2 mb-4"
                style={{ background: "#fff8e1", border: "1px solid #ffe082", fontSize: 15 }}
              >
                <span>
                  {Array.from({ length: 6 }).map((_, i) => (
                    <span key={i} style={{ color: i < starsBefore ? "#f5a623" : "#ddd", fontSize: 18 }}>★</span>
                  ))}
                </span>
                <span style={{ color: "#888" }}>→</span>
                <span>
                  {Array.from({ length: 6 }).map((_, i) => (
                    <span key={i} style={{ color: i < starsAfter ? "#f5a623" : "#ddd", fontSize: 18 }}>★</span>
                  ))}
                </span>
              </div>
            )}

            {(!starsGained || starsGained === 0) && (
              <p className="text-muted mb-4" style={{ fontSize: 14 }}>
                Come back in 6 days to consolidate this skill and earn your next star.
              </p>
            )}

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

    return (
      <Layout>
        <div className="container py-4" style={{ maxWidth: 700 }}>
          <h3 className="mb-1">{isLearning ? "Learning session complete" : "Test Complete"}</h3>
          {skillProgress.length > 0 && (
            <div className="mb-4">
              <h5>Results by Skill</h5>
              <table className="table table-sm table-bordered">
                <thead className="table-dark">
                  <tr>
                    <th>Skill</th>
                    <th style={{ width: 140 }}>Level Reached</th>
                  </tr>
                </thead>
                <tbody>
                  {skillProgress.map((s) => (
                    <tr key={s.code}>
                      <td style={{ fontSize: 14 }}>{s.description || s.code}</td>
                      <td style={{ background: RESULT_COLOR[s.result] || "#fff", fontSize: 13, textAlign: "center" }}>
                        {RESULT_LABEL[s.result] || s.result}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <div className="d-flex gap-2">
            {sessionId && !isLearning && (
              <button
                className="btn btn-primary"
                onClick={async () => {
                  const res = await apiFetch(`/api/tests/${sessionId}/report/`);
                  if (!res.ok) { alert("Failed to generate report"); return; }
                  const blob = await res.blob();
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement("a");
                  a.href = url;
                  const now = new Date();
                  const dateStr = `${now.getDate()} ${now.toLocaleString("en-AU", { month: "long" })}`;
                  const name = studentFirstName || "Student";
                  a.download = `${name}'s report ${dateStr}.pdf`;
                  a.click();
                  URL.revokeObjectURL(url);
                }}
              >
                Download PDF Report
              </button>
            )}
            <button className="btn btn-outline-secondary" onClick={() => navigate(`/students/${studentId}`)}>
              Back to home
            </button>
          </div>
        </div>
      </Layout>
    );
  }

  if (!question || !preview) return null;

  const totalSkills = question.total_skills;
  const doneSkills = question.current_skill_index;
  const progressPct = totalSkills > 0 ? Math.round((doneSkills / totalSkills) * 100) : 0;

  return (
    <Layout>
      <div className="container py-3" style={{ maxWidth: 700 }}>
        <button
          className="btn btn-sm btn-outline-secondary mb-3"
          onClick={() => navigate(`/students/${studentId}`)}
        >
          ← Back
        </button>

        {/* Mode / test label */}
        {mode === "learning" && question && (
          <div className="d-flex align-items-center gap-3 mb-2">
            <span className="badge bg-success" style={{ fontSize: 12 }}>
              Loop {(question as any).loop ?? 1} of 2
            </span>
            <span className="text-muted" style={{ fontSize: 13 }}>
              {(question as any).loop_remaining ?? 0} question{(question as any).loop_remaining !== 1 ? "s" : ""} left in this loop
            </span>
          </div>
        )}
        {mode === "test" && (
          <h5 className="mb-2 text-muted fw-normal" style={{ fontSize: 14 }}>Skills Test</h5>
        )}
        {!mode && testType && TEST_LABEL[testType] && (
          <h5 className="mb-2 text-muted fw-normal" style={{ fontSize: 14 }}>
            {TEST_LABEL[testType]}
          </h5>
        )}
        {/* Header */}
        <div className="d-flex align-items-center justify-content-between mb-3">
          <div>
            <span className="fw-semibold" style={{ fontSize: 15 }}>
              {question.skill_description}
            </span>
            <span
              className={`badge bg-${DIFFICULTY_BADGE[question.difficulty] || "secondary"} ms-2`}
              style={{ fontSize: 11 }}
            >
              {question.difficulty}
            </span>
          </div>
          <span className="text-muted" style={{ fontSize: 13 }}>
            Skill {doneSkills + 1} of {totalSkills}
          </span>
        </div>

        {/* Progress bar */}
        <div className="progress mb-3" style={{ height: 6 }}>
          <div
            className="progress-bar bg-success"
            style={{ width: `${progressPct}%`, transition: "width 0.4s" }}
          />
        </div>

        {/* Question */}
        <PreviewPanel
          mode="student"
          templateId={question.template_id}
          studentId={Number(studentId)}
          preview={preview}
          onStudentNext={handleAnswer}
          disableOnWrong={mode !== "learning"}
        />

        {/* Calculator toggle */}
        <div className="mt-3">
          <button
            className="btn btn-outline-secondary btn-sm"
            onClick={() => setShowCalculator(v => !v)}
          >
            {showCalculator ? "Hide calculator" : "Show calculator"}
          </button>
        </div>

        {/* Floating calculator */}
        {showCalculator && (
          <DraggableCalculator onClose={() => setShowCalculator(false)} />
        )}

        {/* Tutor tools */}
        {isTutor && (
          <div className="mt-2 d-flex gap-2">
            <button
              className="btn btn-sm btn-outline-secondary"
              onClick={() => navigate(`/templates/${question.template_id}`)}
            >
              Edit template
            </button>
            <button
              className={`btn btn-sm ${showMetadata ? "btn-secondary" : "btn-outline-secondary"}`}
              onClick={() => setShowMetadata(v => !v)}
            >
              Edit metadata
            </button>
          </div>
        )}

        {isTutor && showMetadata && (
          <MetadataEditor
            templateId={question.template_id}
            onClose={() => setShowMetadata(false)}
          />
        )}

      </div>
    </Layout>
  );
}
