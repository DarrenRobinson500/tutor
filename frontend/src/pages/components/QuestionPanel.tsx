import { useEffect, useRef, useState } from "react";
import { useRoomContext } from "@livekit/components-react";
import { RoomEvent } from "livekit-client";
import { apiFetch } from "../../utils/apiFetch";
import { PreviewPanel } from "./PreviewPanel";
import { Latex } from "./Latex";
import type { PreviewResponse, StudentRecordResponse } from "../../types/PreviewResponse";

const TOPIC = "session";

type Mode = "learn" | "assessment" | "manual";

interface SessionEvent {
  topic: string;
  type: "set_template" | "answer_result" | "session_complete" | "select_focus_area" | "assessment_next";
  template_id?: number | null;
  session_id?: number;
  learn_mode?: boolean;
  preview?: any;
  // answer_result / assessment_next fields
  answer?: string;
  correct?: boolean;
  // session_complete fields
  student_id?: number;
  stars_before?: number | null;
  stars_after?: number | null;
  stars_gained?: number | null;
  skill_description?: string | null;
  focus_areas?: FocusAreaItem[];
  // select_focus_area fields
  focus_area_id?: number;
}

interface FocusAreaItem {
  id: number;
  skill_id: number;
  skill_code: string;
  skill_description: string;
  mastery: number;
  competence_label: string;
  learning_done_this_week: boolean;
  tutoring_done_this_week: boolean;
  level_before_learning?: number | null;
  level_after_learning?: number | null;
  next_star_available?: string | null;
}

interface CompleteData {
  focus_areas: FocusAreaItem[];
  stars_before?: number | null;
  stars_after?: number | null;
  stars_gained?: number | null;
  skill_description?: string | null;
}

interface QuestionPanelProps {
  isTutor: boolean;
  roomName: string;
  studentId?: number;
}

interface Template {
  id: number;
  title: string;
  skill_detail_description?: string | null;
  grade?: string | null;
}

interface LearnQuestion {
  template_id: number;
  preview: PreviewResponse;
  skill_code: string;
  skill_description: string;
  difficulty: string;
  loop: number;
  loop_remaining: number;
  loop_total?: number;
  loop1_correct: number;
  loop1_total: number;
  mode: string;
}

interface AssessmentContext {
  template_id: number | null;
  skill?: string;
  skill_index?: number;
  total_skills?: number;
  difficulty?: string;
  complete?: boolean;
  error?: string;
}

function renderStars(count: number | null | undefined, max = 4): string {
  const n = Math.max(0, Math.min(Math.round(count ?? 0), max));
  return "★".repeat(n) + "☆".repeat(max - n);
}

function LearnCompleteView({
  completeData,
  isTutor,
  onStart,
}: {
  completeData: CompleteData;
  isTutor: boolean;
  onStart: (focusAreaId: number) => void;
}) {
  return (
    <div style={{ padding: 16 }}>
      <div className="fw-bold mb-3" style={{ fontSize: 18, color: "#198754" }}>
        ✓ Session Complete!
      </div>
      {completeData.skill_description && (
        <div className="mb-3 p-3 rounded border border-success bg-success bg-opacity-10">
          <div className="fw-semibold">{completeData.skill_description}</div>
          {completeData.stars_gained != null && (
            <div className="mt-1 text-muted" style={{ fontSize: 13 }}>
              {completeData.stars_before != null && completeData.stars_after != null && (
                <span style={{ fontFamily: "monospace" }}>
                  {renderStars(completeData.stars_before)} → {renderStars(completeData.stars_after)}
                </span>
              )}
              {completeData.stars_gained > 0
                ? ` (+${completeData.stars_gained} ★ gained)`
                : " (no change)"}
            </div>
          )}
        </div>
      )}
      <div className="fw-semibold mb-2" style={{ fontSize: 14 }}>
        {isTutor ? "Select next focus area to start:" : "Choose next focus area:"}
      </div>
      {completeData.focus_areas.length === 0 && (
        <div className="text-muted" style={{ fontSize: 13 }}>No focus areas found.</div>
      )}
      {completeData.focus_areas.map((fa) => {
        const cooldownDate = fa.next_star_available
          ? new Date(fa.next_star_available).toLocaleDateString("en-AU", { day: "numeric", month: "short" })
          : null;
        return (
          <div
            key={fa.id}
            className="d-flex align-items-center justify-content-between mb-2 p-2 rounded border"
            style={{ fontSize: 13 }}
          >
            <div>
              <div className="fw-semibold">{fa.skill_description}</div>
              <div style={{ fontSize: 15, letterSpacing: 1, color: "#f5a623" }}>
                {renderStars(fa.mastery)}
              </div>
              <div className="text-muted" style={{ fontSize: 11 }}>{fa.competence_label}</div>
              {cooldownDate && (
                <div className="text-warning" style={{ fontSize: 11 }}>
                  Next star available {cooldownDate}
                </div>
              )}
            </div>
            <button
              className="btn btn-sm btn-outline-primary"
              onClick={() => onStart(fa.id)}
            >
              Start →
            </button>
          </div>
        );
      })}
    </div>
  );
}

const DIFFICULTY_BADGE: Record<string, string> = {
  easy: "success",
  medium: "warning",
  hard: "danger",
};

const DIFFICULTY_LABEL: Record<string, string> = {
  easy: "Easy",
  medium: "Medium",
  hard: "Hard",
};

export function QuestionPanel({ isTutor, roomName, studentId }: QuestionPanelProps) {
  const room = useRoomContext();

  // Shared: the template the tutor has pushed to the room (used for non-learn display)
  const [activeTemplateId, setActiveTemplateId] = useState<number | null>(null);
  const [preview, setPreview] = useState<PreviewResponse | null>(null);
  const [loadingPreview, setLoadingPreview] = useState(false);

  const [templates] = useState<Template[]>([]);
  const [search, setSearch] = useState("");

  // ── Manual mode: student's year skills ────────────────────────────────────
  interface SkillRow { id: number; description: string; depth: number; parent_id: number | null; children_count: number; }
  const [manualSkills, setManualSkills] = useState<SkillRow[]>([]);
  const [manualGrade, setManualGrade] = useState<string>("");
  const [manualSkillLoading, setManualSkillLoading] = useState(false);

  const [mode, setMode] = useState<Mode>("learn");
  const [actionLoading, setActionLoading] = useState(false);

  // ── Tutor learn mode ───────────────────────────────────────────────────────
  const [learnSessionId, setLearnSessionId] = useState<number | null>(null);
  const [learnQuestion, setLearnQuestion] = useState<LearnQuestion | null>(null);
  const [learnComplete, setLearnComplete] = useState(false);
  const [learnError, setLearnError] = useState<string | null>(null);

  // ── Student learn mode ─────────────────────────────────────────────────────
  // Separate from activeTemplateId so advancing questions doesn't trigger the
  // activeTemplateId fetch-effect (which causes loadingPreview flicker / null preview).
  const [studentLearnMode, setStudentLearnMode] = useState(false);
  const [studentSessionId, setStudentSessionId] = useState<number | null>(null);
  const [studentTemplateId, setStudentTemplateId] = useState<number | null>(null);
  const [studentPreview, setStudentPreview] = useState<PreviewResponse | null>(null);
  const [studentLearnComplete, setStudentLearnComplete] = useState(false);
  const [studentLoadingPreview, setStudentLoadingPreview] = useState(false);

  // ── Answer visibility ──────────────────────────────────────────────────────
  const [lastAnswer, setLastAnswer] = useState<{ answer: string; correct: boolean } | null>(null);

  // ── Session completion — shared between tutor and student ─────────────────
  const [completeData, setCompleteData] = useState<CompleteData | null>(null);

  // ── Tutor preview key — increment to force PreviewPanel remount on new question ──
  const [tutorPreviewKey, setTutorPreviewKey] = useState(0);

  // ── Assessment mode (tutor) ────────────────────────────────────────────────
  const [assessContext, setAssessContext] = useState<AssessmentContext | null>(null);

  const initialised = useRef(false);
  const lastAnswerRef = useRef<{ answer: string; correct: boolean } | null>(null);
  // Carries a tutor-computed preview from the LiveKit event into the activeTemplateId
  // useEffect so the student uses the identical parametrised question without re-fetching.
  const pendingPreviewRef = useRef<{ templateId: number; preview: PreviewResponse } | null>(null);

  // Restore active template + learn mode on reconnect / late mount
  useEffect(() => {
    apiFetch(`/api/sessions/state/?room_name=${encodeURIComponent(roomName)}`)
      .then((r) => r.json())
      .then((data) => {
        console.log("[QuestionPanel] state restore:", data);
        if (!isTutor && data.learn_mode && data.learn_session_id && data.active_template_id) {
          // Student missed the LiveKit event — restore learn mode from server state
          setStudentLearnMode(true);
          setStudentSessionId(data.learn_session_id);
          setStudentLearnComplete(false);
          setStudentTemplateId(data.active_template_id);
          if (data.preview) {
            // Use the stored preview so student sees the same question as tutor
            console.log("[QuestionPanel] restored preview from session state");
            setStudentPreview(data.preview);
          } else {
            // Fallback: fetch fresh (different params, but better than nothing)
            setStudentLoadingPreview(true);
            apiFetch(`/api/templates/${data.active_template_id}/preview/`)
              .then((r) => r.json())
              .then((p) => { console.log("[QuestionPanel] restored preview from fetch (fallback)"); setStudentPreview(p); })
              .catch(() => setStudentPreview(null))
              .finally(() => setStudentLoadingPreview(false));
          }
        } else if (data.active_template_id) {
          setActiveTemplateId(data.active_template_id);
        }
      })
      .catch(() => {});
  }, [roomName]); // eslint-disable-line react-hooks/exhaustive-deps

  // Auto-start learn mode for tutor on mount
  useEffect(() => {
    if (!isTutor || initialised.current) return;
    initialised.current = true;
    startLearnMode();
  }, [isTutor]); // eslint-disable-line react-hooks/exhaustive-deps

  // Load student's year skills for manual mode
  useEffect(() => {
    if (!isTutor || !roomName) return;
    setManualSkillLoading(true);
    apiFetch(`/api/sessions/student_skills/?room_name=${encodeURIComponent(roomName)}`)
      .then((r) => r.json())
      .then((data) => {
        setManualSkills(data.skills ?? []);
        setManualGrade(data.grade ?? "");
      })
      .catch(() => {})
      .finally(() => setManualSkillLoading(false));
  }, [isTutor, roomName]); // eslint-disable-line react-hooks/exhaustive-deps

  // Listen for session events (template pushes from tutor → student)
  useEffect(() => {
    const handleData = (payload: Uint8Array, _p: any, _k: any, topic?: string) => {
      if (topic !== TOPIC) return;
      try {
        const event: SessionEvent = JSON.parse(new TextDecoder().decode(payload));

        // ── answer_result ────────────────────────────────────────────────────
        if (event.type === "answer_result") {
          const ar = { answer: event.answer ?? "", correct: !!event.correct };
          lastAnswerRef.current = ar;
          setLastAnswer(ar);
          return;
        }

        // ── assessment_next: student finished answering, tutor auto-advances ─
        if (event.type === "assessment_next") {
          if (isTutor) {
            const correct = event.correct ?? lastAnswerRef.current?.correct ?? false;
            requestAssessmentQuestion(correct ? "correct" : "wrong");
          }
          return;
        }

        // ── session_complete: student finished a learn loop ──────────────────
        if (event.type === "session_complete") {
          if (isTutor) {
            setLearnComplete(true);
            setLastAnswer(null);
            setActiveTemplateId(null);
            const completeData: CompleteData = {
              focus_areas: event.focus_areas ?? [],
              stars_before: event.stars_before ?? null,
              stars_after: event.stars_after ?? null,
              stars_gained: event.stars_gained ?? null,
              skill_description: event.skill_description ?? null,
            };
            // Use embedded focus areas from the event; fall back to API fetch if missing
            if ((event.focus_areas ?? []).length > 0) {
              setCompleteData(completeData);
            } else if (event.student_id) {
              apiFetch(`/api/focus-areas/?student_id=${event.student_id}`)
                .then((r) => r.json())
                .then((fas: FocusAreaItem[]) => setCompleteData({ ...completeData, focus_areas: fas }))
                .catch(() => setCompleteData(completeData));
            } else {
              setCompleteData(completeData);
            }
          }
          return;
        }

        // ── select_focus_area: student asks tutor to start a specific skill ──
        if (event.type === "select_focus_area") {
          if (isTutor && event.focus_area_id) {
            startLearnMode(event.focus_area_id);
          }
          return;
        }

        if (event.type !== "set_template") return;

        // Clear state whenever the question changes
        setLastAnswer(null);
        setCompleteData(null);

        if (!isTutor) {
          // Student: receive template from tutor
          const newLearnMode = !!event.learn_mode;
          console.log("[QuestionPanel] Student received set_template event:", {
            template_id: event.template_id,
            session_id: event.session_id,
            learn_mode: event.learn_mode,
            newLearnMode,
            hasPreview: !!event.preview,
          });
          setStudentLearnMode(newLearnMode);
          setStudentSessionId(event.session_id ?? null);
          setStudentLearnComplete(false);
          setCompleteData(null);

          if (newLearnMode && event.template_id) {
            setStudentTemplateId(event.template_id);
            if (event.preview) {
              setStudentPreview(event.preview);
            } else {
              setStudentLoadingPreview(true);
              apiFetch(`/api/templates/${event.template_id}/preview/`)
                .then((r) => r.json())
                .then((data) => setStudentPreview(data))
                .catch(() => setStudentPreview(null))
                .finally(() => setStudentLoadingPreview(false));
            }
          } else {
            if (event.preview && event.template_id) {
              pendingPreviewRef.current = { templateId: event.template_id, preview: event.preview };
            }
            setActiveTemplateId(event.template_id ?? null);
          }
        } else {
          // Tutor: student advanced to next question
          console.log("[QuestionPanel] Tutor received set_template from student:", {
            template_id: event.template_id,
            learn_mode: event.learn_mode,
            hasPreview: !!event.preview,
            previewQuestion: event.preview?.question?.slice?.(0, 60),
          });
          if (event.learn_mode && event.preview) {
            if (event.template_id) {
              pendingPreviewRef.current = { templateId: event.template_id, preview: event.preview };
            }
            setActiveTemplateId(event.template_id ?? null);
          } else if (event.learn_mode && event.template_id) {
            setActiveTemplateId(event.template_id ?? null);
            apiFetch(`/api/sessions/state/?room_name=${encodeURIComponent(roomName)}`)
              .then((r) => r.json())
              .then((data) => {
                if (data.preview) {
                  setPreview(data.preview);
                  setTutorPreviewKey((k) => k + 1);
                } else {
                  apiFetch(`/api/templates/${event.template_id}/preview/`)
                    .then((r) => r.json())
                    .then((p) => { setPreview(p); setTutorPreviewKey((k) => k + 1); })
                    .catch(() => {});
                }
              })
              .catch(() => {});
          } else if (!event.learn_mode) {
            setActiveTemplateId(event.template_id ?? null);
          }
        }
      } catch (e) {
        console.error("[QuestionPanel] DataReceived parse error:", e);
      }
    };
    room.on(RoomEvent.DataReceived, handleData);
    return () => { room.off(RoomEvent.DataReceived, handleData); };
  }, [room, isTutor]);

  // Fetch preview whenever activeTemplateId changes (all modes / roles).
  // Skip the fetch when the tutor already computed and pushed a preview via the LiveKit event.
  useEffect(() => {
    if (!activeTemplateId) { setPreview(null); return; }
    const pending = pendingPreviewRef.current;
    if (pending && pending.templateId === activeTemplateId) {
      pendingPreviewRef.current = null;
      setPreview(pending.preview);
      setTutorPreviewKey((k) => k + 1);
      return;
    }
    setLoadingPreview(true);
    apiFetch(`/api/templates/${activeTemplateId}/preview/`)
      .then((r) => r.json())
      .then((p) => {
        setPreview(p);
        setTutorPreviewKey((k) => k + 1); // force PreviewPanel remount with fresh data
      })
      .catch(() => setPreview(null))
      .finally(() => setLoadingPreview(false));
  }, [activeTemplateId]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Push template to student + persist on server ───────────────────────────

  const pushTemplate = async (
    templateId: number | null,
    opts?: { sessionId?: number; learnMode?: boolean; preview?: any }
  ) => {
    const event: SessionEvent = {
      topic: TOPIC,
      type: "set_template",
      template_id: templateId,
      session_id: opts?.sessionId,
      learn_mode: opts?.learnMode,
      preview: opts?.preview ?? null,
    };
    room.localParticipant.publishData(
      new TextEncoder().encode(JSON.stringify(event)),
      { reliable: true, topic: TOPIC }
    );
    await apiFetch("/api/sessions/set_template/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        room_name: roomName,
        template_id: templateId,
        learn_mode: opts?.learnMode ?? false,
        session_id: opts?.sessionId ?? null,
        preview: opts?.preview ?? null,
      }),
    }).catch(() => {});
    // Set ref BEFORE setActiveTemplateId so the useEffect uses this preview
    // instead of fetching independently (which would produce different random params).
    if (templateId != null && opts?.preview) {
      pendingPreviewRef.current = { templateId, preview: opts.preview };
    }
    setActiveTemplateId(templateId);
  };

  // ── Immediate answer broadcast (student → tutor) ──────────────────────────
  // Called by PreviewPanel the instant an answer is evaluated, before any delay.

  function handleImmediateAnswer(answer: string, correct: boolean) {
    room.localParticipant.publishData(
      new TextEncoder().encode(JSON.stringify({
        topic: TOPIC,
        type: "answer_result",
        answer,
        correct,
      })),
      { reliable: true, topic: TOPIC }
    );
  }

  // ── Tutor: start learn mode ────────────────────────────────────────────────

  async function startLearnMode(focusAreaId?: number) {
    setMode("learn");
    setLearnComplete(false);
    setLearnError(null);
    setLearnQuestion(null);
    setLearnSessionId(null);
    setLastAnswer(null);
    setCompleteData(null);
    setActionLoading(true);
    try {
      const body: Record<string, any> = { room_name: roomName };
      if (focusAreaId) body.focus_area_id = focusAreaId;
      const data = await apiFetch("/api/sessions/learn_mode/", {
        method: "POST",
        body: JSON.stringify(body),
      }).then((r) => r.json());

      if (data.error) { setLearnError(data.error); return; }

      console.log("[QuestionPanel] Tutor learn_mode response:", {
        session_id: data.session_id,
        template_id: data.question?.template_id,
        error: data.error,
      });
      setLearnSessionId(data.session_id);
      const q: LearnQuestion = data.question;
      setLearnQuestion(q);
      // pushTemplate stores q.preview in pendingPreviewRef; useEffect applies it.
      await pushTemplate(q.template_id, { sessionId: data.session_id, learnMode: true, preview: q.preview });
    } finally {
      setActionLoading(false);
    }
  }

  // ── Student: answer a learn-mode question ──────────────────────────────────

  async function submitStudentAnswer(result: StudentRecordResponse) {
    console.log("[QuestionPanel] submitStudentAnswer called:", {
      studentSessionId,
      studentTemplateId,
      correct: result.correct,
      result,
    });

    if (!studentSessionId || !studentTemplateId) {
      console.warn("[QuestionPanel] submitStudentAnswer: bailing early — missing sessionId or templateId", {
        studentSessionId,
        studentTemplateId,
      });
      return;
    }

    try {
      console.log("[QuestionPanel] Posting to /api/tests/", studentSessionId, "/answer/ with template", studentTemplateId);
      const res = await apiFetch(`/api/tests/${studentSessionId}/answer/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          template_id: studentTemplateId,
          correct: result.correct ?? false,
        }),
      });
      const data = await res.json();
      console.log("[QuestionPanel] /answer/ response:", data);

      if (data.complete) {
        console.log("[QuestionPanel] Session complete, setting studentLearnComplete=true");
        setStudentLearnComplete(true);
        setLastAnswer(null);
        // Fetch focus areas first so we can share them with the tutor in a single broadcast
        const completePayload: CompleteData = {
          focus_areas: [],
          stars_before: data.stars_before ?? null,
          stars_after: data.stars_after ?? null,
          stars_gained: data.stars_gained ?? null,
          skill_description: data.skill_description ?? null,
        };
        if (studentId != null) {
          try {
            const fas: FocusAreaItem[] = await apiFetch(`/api/focus-areas/?student_id=${studentId}`)
              .then((r) => r.json());
            completePayload.focus_areas = fas;
          } catch {}
        }
        setCompleteData(completePayload);
        // Broadcast session_complete to tutor with all data including focus areas
        room.localParticipant.publishData(
          new TextEncoder().encode(JSON.stringify({
            topic: TOPIC,
            type: "session_complete",
            student_id: studentId,
            stars_before: completePayload.stars_before,
            stars_after: completePayload.stars_after,
            stars_gained: completePayload.stars_gained,
            skill_description: completePayload.skill_description,
            focus_areas: completePayload.focus_areas,
          })),
          { reliable: true, topic: TOPIC }
        );
        return;
      }

      if (!data.question) {
        console.error("[QuestionPanel] /answer/ response has no 'question' field:", data);
        return;
      }

      const q: LearnQuestion = data.question;
      console.log("[QuestionPanel] Next question:", { template_id: q.template_id, hasPreview: !!q.preview });
      setStudentTemplateId(q.template_id);
      setStudentPreview(q.preview);

      // Save to server FIRST so the tutor can fetch it if needed, then broadcast signal
      await apiFetch("/api/sessions/set_template/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          room_name: roomName,
          template_id: q.template_id,
          learn_mode: true,
          session_id: studentSessionId,
          preview: q.preview,
        }),
      }).catch(() => {});

      // Tell tutor the question has advanced — include preview directly so tutor
      // doesn't need to re-fetch (avoids different random params)
      const event: SessionEvent = {
        topic: TOPIC,
        type: "set_template",
        template_id: q.template_id,
        session_id: studentSessionId ?? undefined,
        learn_mode: true,
        preview: q.preview,
      };
      room.localParticipant.publishData(
        new TextEncoder().encode(JSON.stringify(event)),
        { reliable: true, topic: TOPIC }
      );
    } catch (err) {
      console.error("[QuestionPanel] submitStudentAnswer failed:", err);
    }
  }

  // ── Tutor: assessment mode ─────────────────────────────────────────────────

  async function requestAssessmentQuestion(result: "correct" | "wrong" | null) {
    setActionLoading(true);
    try {
      let currentResult = result;
      for (let attempt = 0; attempt < 6; attempt++) {
        const data: AssessmentContext = await apiFetch("/api/sessions/next_question/", {
          method: "POST",
          body: JSON.stringify({ room_name: roomName, mode: "assessment", result: currentResult }),
        }).then((r) => r.json());

        setAssessContext(data);

        if (data.template_id) {
          // Fetch preview once — pushTemplate stores it in pendingPreviewRef so the
          // activeTemplateId useEffect uses it directly (no independent re-fetch).
          const questionPreview = await apiFetch(`/api/templates/${data.template_id}/preview/`)
            .then((r) => r.json())
            .catch(() => null);
          await pushTemplate(data.template_id, { preview: questionPreview });
          return;
        }

        if (data.complete) {
          await pushTemplate(null);
          return;
        }

        // No template returned for this skill — skip to the next one automatically.
        console.warn(`[Assessment] no template on attempt ${attempt + 1}, advancing`);
        currentResult = null;
      }
    } finally {
      setActionLoading(false);
    }
  }

  async function switchToAssessment() {
    setMode("assessment");
    setLearnQuestion(null);
    setLearnSessionId(null);
    setLearnComplete(false);
    setLearnError(null);
    setPreview(null); // clear stale learn-mode preview while new question loads
    await requestAssessmentQuestion(null);
  }

  // ── Helpers ────────────────────────────────────────────────────────────────

  const showStudentLearn = !isTutor && studentLearnMode && !!studentSessionId && !!studentTemplateId;
  console.log("[QuestionPanel] render — showStudentLearn:", showStudentLearn, {
    isTutor,
    studentLearnMode,
    studentSessionId,
    studentTemplateId,
    studentLearnComplete,
    studentPreview: !!studentPreview,
  });

  // ─────────────────────────────────────────────────────────────────────────

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column", overflow: "hidden" }}>

      {/* ── Tutor controls ── */}
      {isTutor && (
        <div className="border-bottom" style={{ flexShrink: 0, padding: "8px", background: "#f8f9fa" }}>
          {/* Mode toggle */}
          <div className="d-flex gap-2 mb-2">
            <button
              className={`btn btn-sm ${mode === "learn" ? "btn-primary" : "btn-outline-primary"}`}
              onClick={() => startLearnMode()}
              disabled={actionLoading}
            >
              Learn
            </button>
            <button
              className={`btn btn-sm ${mode === "assessment" ? "btn-primary" : "btn-outline-primary"}`}
              onClick={switchToAssessment}
              disabled={actionLoading}
            >
              Assessment
            </button>
            <button
              className={`btn btn-sm ${mode === "manual" ? "btn-primary" : "btn-outline-primary"}`}
              onClick={() => { setMode("manual"); setLearnQuestion(null); setAssessContext(null); pushTemplate(null); }}
            >
              Manual
            </button>
            <button
              className="btn btn-sm btn-outline-secondary ms-auto"
              onClick={() => window.location.reload()}
              title="Refresh page"
            >
              ↺ Refresh
            </button>
          </div>

          {/* Learn mode context */}
          {mode === "learn" && !learnError && !learnComplete && learnQuestion && (
            <div className="mb-2 px-1">
              <div className="d-flex align-items-center gap-2 mb-1">
                <span className="badge bg-success" style={{ fontSize: 11 }}>
                  Loop {learnQuestion.loop} of 2
                </span>
                <span className="text-muted" style={{ fontSize: 12 }}>
                  {learnQuestion.loop_remaining} question{learnQuestion.loop_remaining !== 1 ? "s" : ""} left
                </span>
              </div>
              <div className="d-flex align-items-center gap-2">
                <span className="fw-semibold" style={{ fontSize: 13 }}>{learnQuestion.skill_description}</span>
                <span
                  className={`badge bg-${DIFFICULTY_BADGE[learnQuestion.difficulty] ?? "secondary"}`}
                  style={{ fontSize: 11 }}
                >
                  {DIFFICULTY_LABEL[learnQuestion.difficulty] ?? learnQuestion.difficulty}
                </span>
              </div>
            </div>
          )}
          {mode === "learn" && learnError && (
            <div className="text-muted mb-2" style={{ fontSize: 12 }}>{learnError}</div>
          )}
          {mode === "learn" && learnComplete && (
            <div className="text-success mb-2 fw-semibold" style={{ fontSize: 12 }}>
              Learning complete for this week!
            </div>
          )}

          {/* Assessment context */}
          {mode === "assessment" && assessContext && !assessContext.error && !assessContext.complete && (
            <div className="mb-2 px-1" style={{ fontSize: 12, lineHeight: 1.6 }}>
              <span className="fw-semibold">{assessContext.skill}</span>
              <span className="text-muted ms-2">
                Skill {(assessContext.skill_index ?? 0) + 1}/{assessContext.total_skills}
                {" · "}{DIFFICULTY_LABEL[assessContext.difficulty ?? ""] ?? assessContext.difficulty}
              </span>
            </div>
          )}
          {mode === "assessment" && assessContext?.error && (
            <div className="text-danger mb-2" style={{ fontSize: 12 }}>{assessContext.error}</div>
          )}
          {mode === "assessment" && assessContext?.complete && (
            <div className="text-success mb-2 fw-semibold" style={{ fontSize: 12 }}>
              Assessment complete — all {assessContext.total_skills} skills covered.
            </div>
          )}

          {/* Assessment: Next button + loading spinner */}
          {mode === "assessment" && !assessContext?.complete && (
            <div className="d-flex align-items-center gap-2 mb-1">
              <button
                className="btn btn-sm btn-outline-primary"
                disabled={actionLoading}
                onClick={() => requestAssessmentQuestion(lastAnswerRef.current?.correct ? "correct" : lastAnswerRef.current ? "wrong" : null)}
              >
                Next question →
              </button>
              {actionLoading && <span className="spinner-border spinner-border-sm text-secondary" />}
            </div>
          )}


          {/* Manual: student's year skills picker */}
          {mode === "manual" && (
            <div style={{ maxHeight: 200, overflowY: "auto" }}>
              <div className="d-flex gap-2 mb-2 align-items-center">
                <input
                  className="form-control form-control-sm"
                  placeholder="Search skills…"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                />
                {activeTemplateId && (
                  <button className="btn btn-sm btn-outline-secondary" onClick={() => { pushTemplate(null); setSearch(""); }}>Clear</button>
                )}
              </div>
              {manualSkillLoading && <div className="text-muted" style={{ fontSize: 12 }}>Loading…</div>}
              {!manualSkillLoading && manualSkills
                .filter(s => !search || s.description.toLowerCase().includes(search.toLowerCase()))
                .map((s) => {
                  const isParent = s.children_count > 0;
                  return (
                    <button
                      key={s.id}
                      className={`d-block w-100 text-start btn btn-sm mb-1 ${
                        isParent
                          ? "btn-outline-secondary"
                          : "btn-outline-primary"
                      }`}
                      style={{
                        fontSize: 12,
                        paddingLeft: `${s.depth * 12 + 6}px`,
                        fontWeight: isParent ? 600 : 400,
                        cursor: isParent ? "default" : "pointer",
                        opacity: isParent ? 0.7 : 1,
                      }}
                      disabled={isParent}
                      onClick={async () => {
                        if (isParent) return;
                        try {
                          const res = await apiFetch("/api/templates/preview/", {
                            method: "POST",
                            headers: { "Content-Type": "application/json" },
                            body: JSON.stringify({ skill: s.id, grade: manualGrade }),
                          });
                          const data = await res.json();
                          if (data.template_id) pushTemplate(data.template_id);
                        } catch {}
                      }}
                    >
                      {s.description}
                    </button>
                  );
                })}
              {!manualSkillLoading && manualSkills.filter(s => !search || s.description.toLowerCase().includes(search.toLowerCase())).length === 0 && (
                <div className="text-muted" style={{ fontSize: 12 }}>No skills found.</div>
              )}
            </div>
          )}
        </div>
      )}

      {/* ── Question display ── */}
      <div style={{ flex: 1, overflowY: "auto", padding: 12 }}>
        {!isTutor && (
          <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 4 }}>
            <button
              className="btn btn-sm btn-outline-secondary"
              onClick={() => window.location.reload()}
              title="Refresh page"
              style={{ fontSize: 12 }}
            >
              ↺ Refresh
            </button>
          </div>
        )}

        {/* Student: learn complete */}
        {!isTutor && studentLearnComplete && (
          completeData ? (
            <LearnCompleteView
              completeData={completeData}
              isTutor={false}
              onStart={(focusAreaId) => {
                room.localParticipant.publishData(
                  new TextEncoder().encode(JSON.stringify({
                    topic: TOPIC,
                    type: "select_focus_area",
                    focus_area_id: focusAreaId,
                  })),
                  { reliable: true, topic: TOPIC }
                );
              }}
            />
          ) : (
            <div className="text-success text-center mt-4 fw-semibold" style={{ fontSize: 15 }}>
              Session complete!
            </div>
          )
        )}

        {/* Student: learn mode question */}
        {showStudentLearn && !studentLearnComplete && (
          <>
            {studentLoadingPreview && (
              <div className="text-center mt-4">
                <div className="spinner-border spinner-border-sm text-primary" role="status" />
              </div>
            )}
            {!studentLoadingPreview && studentPreview && studentId != null && (
              <>
                <PreviewPanel
                  mode="student"
                  templateId={studentTemplateId}
                  studentId={studentId}
                  preview={studentPreview}
                  onStudentNext={submitStudentAnswer}
                  onImmediateAnswer={handleImmediateAnswer}
                />
              </>
            )}
          </>
        )}

        {/* Tutor / non-learn student view */}
        {!showStudentLearn && !studentLearnComplete && (
          <>
            {(actionLoading || loadingPreview) && !preview && (
              <div className="text-center mt-4">
                <div className="spinner-border spinner-border-sm text-primary" role="status" />
              </div>
            )}
            {!actionLoading && !loadingPreview && !activeTemplateId && isTutor && learnComplete && completeData && (
              <LearnCompleteView
                completeData={completeData}
                isTutor={true}
                onStart={(focusAreaId) => startLearnMode(focusAreaId)}
              />
            )}
            {!actionLoading && !loadingPreview && !activeTemplateId && !(isTutor && learnComplete && completeData) && (
              <div className="text-muted text-center mt-4" style={{ fontSize: 14 }}>
                {isTutor
                  ? mode === "manual"
                    ? "Select a template above to push a question."
                    : mode === "learn" && learnComplete
                      ? "Learning complete for this week."
                      : mode === "learn" && learnError
                        ? learnError
                        : "Loading first question…"
                  : "Waiting for tutor to send a question…"}
              </div>
            )}
            {!loadingPreview && activeTemplateId && preview && (
              (isTutor && mode === "learn") ? (
                /* ── Learn mode: unified question view mirrors student's view ── */
                <div style={{ padding: 12, fontSize: 18 }}>
                  {/* Question text */}
                  <div style={{ marginBottom: 12 }}>
                    <Latex>{preview.question ?? ""}</Latex>
                  </div>

                  {/* Diagram */}
                  {preview.diagram_svg && (
                    <div style={{ display: "flex", justifyContent: "center", marginBottom: 12 }}>
                      <div dangerouslySetInnerHTML={{ __html: preview.diagram_svg }} />
                    </div>
                  )}

                  {/* Result overlay — shown immediately after student answers */}
                  {lastAnswer ? (
                    <div
                      className={`mt-2 p-3 rounded border ${
                        lastAnswer.correct
                          ? "border-success bg-success bg-opacity-10"
                          : "border-danger bg-danger bg-opacity-10"
                      }`}
                    >
                      <div className="fw-bold mb-1" style={{ fontSize: 16 }}>
                        {lastAnswer.correct ? "✓ Correct!" : "✗ Incorrect"}
                        {" — Student answered: "}
                        <span style={{ fontFamily: "monospace" }}>{lastAnswer.answer}</span>
                      </div>
                      {!lastAnswer.correct && (
                        <>
                          {/* Solution — mirrors what the student sees */}
                          <div
                            className="mt-2 p-2"
                            style={{
                              background: "#f8f9fa",
                              borderLeft: "4px solid #dc3545",
                              fontSize: 16,
                              whiteSpace: "pre-wrap",
                            }}
                          >
                            {preview.solution
                              ? <Latex>{preview.solution}</Latex>
                              : (() => {
                                  const correct = (preview.answers ?? []).find((a: any) => a?.correct);
                                  return correct
                                    ? <span>The correct answer is <strong>{String(correct.text ?? "").replace(/^\$/, "")}</strong></span>
                                    : <span className="text-muted">No solution provided.</span>;
                                })()
                            }
                          </div>
                          {/* Solution diagram */}
                          {preview.multi_step?.steps?.[0]?.svg && (
                            <div style={{ display: "flex", justifyContent: "center", marginTop: 8 }}>
                              <div dangerouslySetInnerHTML={{ __html: preview.multi_step.steps[0].svg }} />
                            </div>
                          )}
                          <div className="text-muted mt-2" style={{ fontSize: 13 }}>
                            Waiting for student to advance…
                          </div>
                        </>
                      )}
                      {lastAnswer.correct && (
                        <div className="text-muted" style={{ fontSize: 13 }}>
                          Next question loading…
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="text-muted" style={{ fontSize: 13 }}>
                      Waiting for student to answer…
                    </div>
                  )}
                </div>
              ) : isTutor ? (
                /* ── Tutor: Manual / Assessment editor view ── */
                <PreviewPanel
                  key={tutorPreviewKey}
                  mode="editor"
                  preview={preview}
                  templateContent=""
                  noteTemplateId={activeTemplateId ?? undefined}
                  onEditorNext={(newPreview) => setPreview(newPreview)}
                />
              ) : (
                /* ── Student: Assessment question with answer input ── */
                activeTemplateId != null && studentId != null ? (
                  <PreviewPanel
                    key={activeTemplateId}
                    mode="student"
                    templateId={activeTemplateId}
                    studentId={studentId}
                    preview={preview}
                    onStudentNext={(result) => {
                      room.localParticipant.publishData(
                        new TextEncoder().encode(JSON.stringify({
                          topic: TOPIC,
                          type: "assessment_next",
                          correct: result?.correct ?? false,
                        })),
                        { reliable: true, topic: TOPIC }
                      );
                    }}
                    onImmediateAnswer={handleImmediateAnswer}
                    disableOnWrong={true}
                  />
                ) : null
              )
            )}
          </>
        )}
      </div>
    </div>
  );
}
