import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { Latex } from "./Latex";
import "katex/dist/katex.min.css";
import { apiFetch } from "../../utils/apiFetch";
import type { PreviewResponse, StudentRecordResponse, KnowledgeItem, InlineKnowledge } from "../../types/PreviewResponse";
import { PowerInput } from "./PowerInput";


interface PreviewPanelBase {
  preview: PreviewResponse | null;
}

/**
 * EDITOR MODE
 * - No student fields allowed
 * - templateContent + onEditorNext required
 */
interface PreviewPanelEditorProps extends PreviewPanelBase {
  mode: "editor";
  templateContent: string;
  onEditorNext: (newPreview: PreviewResponse) => void;

  // explicitly forbidden in editor mode
  templateId?: never;
  studentId?: never;
  onStudentNext?: never;
  onImmediateAnswer?: never;
  seenTemplateIds?: never;
  sessionTemplateIds?: never;
}

/**
 * STUDENT MODE
 * - templateId + studentId required
 * - onStudentNext required
 * - templateContent/onEditorNext forbidden
 */
interface PreviewPanelStudentProps extends PreviewPanelBase {
  mode: "student";
  templateId: number;
  studentId: number;
  onStudentNext: (result: StudentRecordResponse) => void;
  /** Called the instant an answer is evaluated — before any advance delay.
   *  Use this to broadcast the result to remote participants immediately. */
  onImmediateAnswer?: (answer: string, correct: boolean) => void;
  seenTemplateIds?: number[];
  sessionTemplateIds?: number[];

  // explicitly forbidden in student mode
  templateContent?: never;
  onEditorNext?: never;
}

/**
 * UNION OF BOTH MODES
 */
export type PreviewPanelProps =
  | PreviewPanelEditorProps
  | PreviewPanelStudentProps;

function KnowledgeCallout({ k }: { k: InlineKnowledge }) {
  return (
    <div
      className="p-3 mb-2 rounded"
      style={{ background: "#fffde7", border: "1px solid #ffe082", fontSize: 15 }}
    >
      {k.title && (
        <div className="fw-semibold mb-1" style={{ fontSize: 14 }}>
          <Latex>{k.title}</Latex>
        </div>
      )}
      {k.text && (
        <div className="mb-1" style={{ lineHeight: 1.6 }}>
          <Latex>{k.text}</Latex>
        </div>
      )}
      {k.diagram_svg && (
        <div style={{ display: "flex", justifyContent: "center", width: "100%", margin: "8px 0" }}>
          <div dangerouslySetInnerHTML={{ __html: k.diagram_svg }} />
        </div>
      )}
      {k.text_2 && (
        <div style={{ lineHeight: 1.6 }}>
          <Latex>{k.text_2}</Latex>
        </div>
      )}
    </div>
  );
}

export function PreviewPanel({
  preview,
  mode,
  templateContent,
  onEditorNext,
  templateId,
  onStudentNext,
  onImmediateAnswer,
  studentId,
  seenTemplateIds,
  sessionTemplateIds,
}: PreviewPanelProps) {
  const [selected, setSelected] = useState<number | null>(null);
  const [isCorrect, setIsCorrect] = useState<boolean | null>(null);
  const [flagged, setFlagged] = useState(false);
  const [startTime, setStartTime] = useState<number>(Date.now());
  const [selectedAnswer, setSelectedAnswer] = useState<any>(null);
  const [showIncorrectFeedback, setShowIncorrectFeedback] = useState(false);
  const [backendResult, setBackendResult] = useState<any>(null);
  const [localTemplateId, setLocalTemplateId] = useState<number | null>(null);
  const [textInput, setTextInput] = useState("");
  const navigate = useNavigate();
  const [formatError, setFormatError] = useState<string | null>(null);
  const [noteText, setNoteText] = useState("");
  const [notes, setNotes] = useState<any[]>([]);
  const [isAddingNote, setIsAddingNote] = useState(false);
  const textInputRef = useRef<HTMLInputElement>(null);
  const [focusKey, setFocusKey] = useState(0);
  const [multiStepIndex, setMultiStepIndex] = useState(0);
  const [completedSteps, setCompletedSteps] = useState<Array<{ question: string; answer: string; correct: boolean }>>([]);

  useEffect(() => {
    if (mode === "student" && templateId !== undefined) {
      console.log("Setting localTemplateId to:", templateId);
      setLocalTemplateId(templateId);
    }
  }, [templateId, mode]);

  // Reset state on any preview change (including YAML edits).
  // Focus the input in student mode so the student can type immediately.
  useEffect(() => {
    setStartTime(Date.now());
    setSelected(null);
    setIsCorrect(null);
    setFlagged(false);
    setShowIncorrectFeedback(false);
    setSelectedAnswer(null);
    setBackendResult(null);
    setTextInput("");
    setFormatError(null);
    setMultiStepIndex(0);
    setCompletedSteps([]);
    if (mode === "student") {
      setTimeout(() => textInputRef.current?.focus(), 50);
    }
  }, [preview]);

  // Focus the input only when explicitly triggered by answering and advancing.
  useEffect(() => {
    if (focusKey === 0) return;
    setTimeout(() => textInputRef.current?.focus(), 50);
  }, [focusKey]);

  const effectiveTemplateId = templateId ?? localTemplateId;

  useEffect(() => {
    if (mode !== "student" || !effectiveTemplateId) { setNotes([]); return; }
    apiFetch(`/api/notes/?template=${effectiveTemplateId}`)
      .then(r => r.json())
      .then(data => setNotes(Array.isArray(data) ? data : (data.results ?? [])))
      .catch(() => {});
  }, [effectiveTemplateId, mode]);

  async function handleAddNote() {
    if (!noteText.trim() || !effectiveTemplateId) return;
    setIsAddingNote(true);
    try {
      const res = await apiFetch("/api/notes/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ template: effectiveTemplateId, text: noteText.trim() }),
      });
      if (res.ok) {
        const note = await res.json();
        setNotes(prev => [note, ...prev]);
        setNoteText("");
      }
    } finally {
      setIsAddingNote(false);
    }
  }

  const safeLatex = (value: any): string => {
    if (value === null || value === undefined) return "";
    if (typeof value === "string" || typeof value === "number") return String(value);
    try {
      return JSON.stringify(value);
    } catch {
      return "";
    }
  };

  async function recordAttempt(answer: any, correct: boolean, helpRequested?: boolean) {
    if (!preview) return null;

    const timeTaken = Date.now() - startTime;

    const res = await apiFetch("/api/questions/record/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        student_id: studentId,
        template_id: localTemplateId,
        params: preview.params,
        question_text: preview.question,
        correct_answer: preview.solution,
        selected_answer: answer?.text ?? null,
        correct,
        time_taken_ms: timeTaken,
        help_requested: helpRequested !== undefined ? helpRequested : flagged,
        seen_template_ids: seenTemplateIds ?? [],
        session_template_ids: sessionTemplateIds ?? [],
      }),
    });
    const data = await res.json();
    // Attach the answer text so callers (e.g. QuestionPanel) can broadcast it
    if (data && answer?.text != null) data.student_answer = answer.text;
    return data;
  }

  function advanceMultiStep(stepQuestion: string, studentAnswer: string, correct: boolean) {
    setCompletedSteps(prev => [...prev, { question: stepQuestion, answer: studentAnswer, correct }]);
    setMultiStepIndex(i => i + 1);
    setIsCorrect(null);
    setSelected(null);
    setTextInput("");
    setFocusKey(k => k + 1);
  }

  async function handleMultiStepChoiceClick(choiceIndex: number, choice: { text: string; correct: boolean }) {
    const multiStep = preview?.multi_step;
    if (!multiStep || !activeStep) return;
    setSelected(choiceIndex);
    const correct = choice.correct;
    setIsCorrect(correct);
    const isLastStep = multiStepIndex === multiStep.steps.length - 1;
    if (mode === "student") onImmediateAnswer?.(choice.text, correct);
    if (correct) {
      if (!isLastStep) {
        setTimeout(() => { advanceMultiStep(activeStep.question ?? "", choice.text, true); }, 800);
      } else {
        if (mode === "student") {
          const result = await recordAttempt({ text: choice.text }, true);
          setTimeout(() => { onStudentNext?.(result); }, 2000);
        }
        if (mode === "editor") {
          setTimeout(() => { loadNextEditorPreview(); }, 1000);
        }
      }
    }
    // Incorrect: just show "Incorrect — try again"; student clicks again to retry
  }

  async function handleIDontKnowMultiStep() {
    if (!multiStep || !activeStep) return;
    setFlagged(true);
    setSelected(0);
    setIsCorrect(false);

    const isLastStep = multiStepIndex === multiStep.steps.length - 1;
    if (isLastStep) {
      if (mode === "student") {
        onImmediateAnswer?.(activeStep?.answer ?? "", false);
        const result = await recordAttempt({ text: activeStep.answer }, false, true);
        setTimeout(() => { onStudentNext?.(result); }, 1500);
      }
      if (mode === "editor") {
        setTimeout(() => { loadNextEditorPreview(); }, 1500);
      }
    } else {
      setTimeout(() => {
        advanceMultiStep(activeStep.question ?? "", activeStep.answer ?? "", false);
      }, 1500);
    }
  }

  async function loadNextEditorPreview() {
    if (!templateContent) return;
    const res = await apiFetch("/api/templates/preview/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content: templateContent }),
    });
    const data = await res.json();
    if (data.ok && data.preview) {
      onEditorNext?.(data.preview);
      setFocusKey(k => k + 1);
    }
  }

  async function loadNextStudentPreview() {
    if (!templateId) return;
    const res = await apiFetch("/api/templates/preview/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ templateId }),
    });
    const data = await res.json();
    if (data.ok && data.preview) {
      onStudentNext?.(data.preview);
      setFocusKey(k => k + 1);
    }
  }

  async function handleIDontKnow() {
    setFlagged(true);
    setSelected(0);
    setIsCorrect(false);

    if (mode === "student") {
      onImmediateAnswer?.("", false);
      const result = await recordAttempt(null, false, true);
      setShowIncorrectFeedback(true);
      setBackendResult(result);
    }
    if (mode === "editor") {
      setTimeout(() => { loadNextEditorPreview(); }, 1500);
    }
  }

  async function handleIDontGetIt() {
    setFlagged(true);

    if (mode === "student") {
      onImmediateAnswer?.(selectedAnswer?.text ?? "", false);
      const result = await recordAttempt(selectedAnswer, false);
      setShowIncorrectFeedback(true);
      setBackendResult(result);
    }
  }

  function answersMatch(input: string, correct: any, tolerance = 1e-9): boolean {
    const parseMixed = (s: string): number | null => {
      const m = s.trim().match(/^(-?\d+)\s+(\d+)\/(\d+)$/);
      if (!m) return null;
      const whole = parseInt(m[1]), num = parseInt(m[2]), den = parseInt(m[3]);
      if (den === 0) return null;
      return whole + (whole < 0 ? -num / den : num / den);
    };
    const mixedA = parseMixed(String(input));
    const mixedB = parseMixed(String(correct));
    if (mixedA !== null || mixedB !== null) {
      const toNum = (s: string, mixed: number | null): number | null => {
        if (mixed !== null) return mixed;
        if (s.includes("/")) { const [n, d] = s.split("/").map(Number); return isNaN(n) || isNaN(d) || d === 0 ? null : n / d; }
        const n = parseFloat(s); return isNaN(n) ? null : n;
      };
      const na = toNum(String(input), mixedA), nb = toNum(String(correct), mixedB);
      if (na !== null && nb !== null) return Math.abs(na - nb) <= tolerance;
    }

    const normalize = (s: any) => String(s).trim().toLowerCase().replace(/\s+/g, "").replace(/\*\*/g, "^");
    const a = normalize(input);
    const b = normalize(correct);

    if (a.includes("/") && !a.includes("x") && !a.includes("×")) {
      const fracParts = a.split("/");
      if (fracParts.length === 2) {
        const fn = Math.abs(parseInt(fracParts[0]));
        const fd = Math.abs(parseInt(fracParts[1]));
        if (!isNaN(fn) && !isNaN(fd) && fd !== 0) {
          const gcdFn = (x: number, y: number): number => y === 0 ? x : gcdFn(y, x % y);
          if (gcdFn(fn, fd) !== 1) return false;
        }
      }
    }

    if (a === b) return true;
    if (b.startsWith("$") && !a.startsWith("$") && a === b.slice(1)) return true;
    if (b.endsWith("%") && !a.endsWith("%")) return false;

    const parseRatio = (s: string): number[] | null => {
      if (!s.includes(":")) return null;
      const parts = s.split(":").map(p => Number(p.trim()));
      if (parts.some(isNaN) || parts.some(p => p <= 0)) return null;
      return parts;
    };
    const gcdOf = (x: number, y: number): number => y === 0 ? x : gcdOf(y, x % y);
    const ra = parseRatio(a), rb = parseRatio(b);
    if (ra !== null && rb !== null && ra.length === rb.length) {
      const studentGcd = ra.map(Math.round).reduce(gcdOf);
      if (studentGcd !== 1) return false;
      return ra.every((v, i) => Math.abs(v - rb[i]) < 1e-9);
    }

    const parseFraction = (s: string): number | null => {
      if (s.endsWith("%")) {
        const digits = s.slice(0, -1);
        if (!/^-?\d+(\.\d+)?$/.test(digits)) return null;
        const n = parseFloat(digits);
        return isNaN(n) ? null : n / 100;
      }
      if (s.includes("/")) {
        const [num, den] = s.split("/").map(Number);
        return isNaN(num) || isNaN(den) || den === 0 ? null : num / den;
      }
      if (!/^-?(\d+(\.\d*)?|\.\d+)$/.test(s)) return null;
      const n = parseFloat(s);
      return isNaN(n) ? null : n;
    };

    const isPrime = (n: number): boolean => {
      if (!Number.isInteger(n) || n < 2) return false;
      for (let i = 2; i * i <= n; i++) {
        if (n % i === 0) return false;
      }
      return true;
    };

    const parseProduct = (s: string): { product: number; allPrime: boolean } | null => {
      const parts = s.split(/[x×*]/);
      if (parts.length < 2) return null;
      let product = 1;
      let allPrime = true;
      for (const part of parts) {
        const n = parseFraction(part.trim());
        if (n === null) return null;
        product *= n;
        if (!isPrime(n)) allPrime = false;
      }
      return { product, allPrime };
    };

    const pa = parseProduct(a);
    const pb = parseProduct(b) ?? { product: parseFraction(b) ?? NaN, allPrime: true };

    if (pa !== null) {
      if (!pa.allPrime) return false;
      if (pb.product !== null && !isNaN(pb.product)) {
        return Math.abs(pa.product - pb.product) < 1e-9;
      }
    }

    const parseMixedNumber = (s: string): number | null => {
      const parts = s.trim().split(/\s+/);
      if (parts.length !== 2) return null;
      const whole = parseFloat(parts[0]);
      if (isNaN(whole)) return null;
      const slashParts = parts[1].split("/");
      if (slashParts.length !== 2) return null;
      const num = parseInt(slashParts[0]), den = parseInt(slashParts[1]);
      if (isNaN(num) || isNaN(den) || den === 0) return null;
      return whole + num / den;
    };

    const parsePower = (s: string): number | null => {
      const m = s.match(/^(\d+)\^(\d+)$/);
      if (!m) return null;
      return Math.pow(parseInt(m[1]), parseInt(m[2]));
    };
    const pa2 = parsePower(a), pb2 = parsePower(b) ?? parseFraction(b);
    if (pa2 !== null && pb2 !== null) return Math.abs(pa2 - pb2) <= tolerance;

    const na = parseFraction(a) ?? parseMixedNumber(a);
    const nb = parseFraction(b) ?? parseMixedNumber(b);
    if (na !== null && nb !== null) return Math.abs(na - nb) <= tolerance;
    return false;
  }

  function checkAnswerFormat(input: string, format: string | null): string | null {
    if (!format) return null;
    const s = input.trim();
    if (format === "fraction") {
      if (!s.includes("/") && !/^-?\d+$/.test(s))
        return "Please enter your answer as a fraction, e.g. 7/20";
      if (/^-?\d+\s+\d+\/\d+$/.test(s))
        return "Please enter as an improper fraction, not a mixed number — e.g. 7/3 not 2 1/3";
    }
    if (format === "integer" && !/^-?\d+$/.test(s))
      return "Please enter a whole number, e.g. 42";
    if (format === "decimal" && !/^-?\d*\.?\d+$/.test(s))
      return "Please enter a decimal, e.g. 0.75";
    if (format === "ratio" && !/^\d+(\s*:\s*\d+)+$/.test(s))
      return "Please enter your answer as a ratio, e.g. 1:2";
    if ((format === "percent" || format === "percentage") && !/^-?\d+(\.\d+)?%$/.test(s))
      return "Please enter your answer as a percentage, e.g. 25%";
    if (format === "proper_fraction") {
      const fracMatch  = s.match(/^(\d+)\/(\d+)$/);
      const mixedMatch = s.match(/^(\d+)\s+(\d+)\/(\d+)$/);
      if (!(/^\d+$/.test(s)) && !fracMatch && !mixedMatch)
        return "Please enter a whole number, proper fraction (e.g. 3/4), or mixed number (e.g. 2 1/3)";
      if (fracMatch && parseInt(fracMatch[1]) >= parseInt(fracMatch[2]))
        return "Please enter as a proper fraction where the numerator is less than the denominator, or as a mixed number (e.g. 2 1/3)";
      if (mixedMatch && parseInt(mixedMatch[2]) >= parseInt(mixedMatch[3]))
        return "The fractional part must be proper — numerator less than denominator (e.g. 2 1/3)";
    }
    if (format === "equation" && !/^[A-Za-z0-9]+(\^[A-Za-z0-9]+)?$/.test(s))
      return "Please enter a base and optional power, e.g. 5^2 or A^3";
    return null;
  }

  async function handleTextSubmit() {
    const fmtErr = checkAnswerFormat(textInput, answerFormat);
    if (fmtErr) { setFormatError(fmtErr); return; }
    setFormatError(null);

    const multiStep = preview?.multi_step;
    if (multiStep?.steps?.length) {
      const step = multiStep.steps[multiStepIndex];
      const stepFmtErr = checkAnswerFormat(textInput, step.answer_format ?? null);
      if (stepFmtErr) { setFormatError(stepFmtErr); return; }
      const correct = answersMatch(textInput, step.answer, step.tolerance ?? 1e-9);
      setSelected(0);
      setIsCorrect(correct);
      if (mode === "student") onImmediateAnswer?.(textInput, correct);
      if (correct) {
        const isLastStep = multiStepIndex === multiStep.steps.length - 1;
        if (!isLastStep) {
          setTimeout(() => {
            advanceMultiStep(step.question ?? "", textInput, true);
          }, 800);
        } else {
          if (mode === "student") {
            const result = await recordAttempt({ text: textInput }, true);
            setTimeout(() => { onStudentNext?.(result); }, 2000);
          }
          if (mode === "editor") {
            setTimeout(() => { loadNextEditorPreview(); }, 1000);
          }
        }
      }
      return;
    }

    if (!correctInputAnswer) return;
    const correct = answersMatch(textInput, correctInputAnswer.text, answerTolerance);
    const answerObj = { text: textInput };
    setSelected(0);
    setIsCorrect(correct);

    if (mode === "student") {
      onImmediateAnswer?.(textInput, correct);
      const result = await recordAttempt(answerObj, correct);
      if (correct) {
        setTimeout(() => { onStudentNext?.(result); }, 2000);
      } else {
        setShowIncorrectFeedback(true);
        setBackendResult(result);
      }
    }
    if (mode === "editor" && correct) {
      setTimeout(() => { loadNextEditorPreview(); }, 1000);
    }
  }

  async function handleAnswerClick(index: number, answer: any) {
    setSelected(index);
    setSelectedAnswer(answer);

    const correct = Boolean(answer.correct);
    setIsCorrect(correct);

    if (mode === "student") {
      onImmediateAnswer?.(answer?.text ?? "", correct);
      const result = await recordAttempt(answer, correct);

      if (correct) {
          setTimeout(() => {
            onStudentNext?.(result);
          }, 2000);
          return;
      } else {
        setShowIncorrectFeedback(true);
        setBackendResult(result);
      }
    }

    if (mode === "editor" && correct) {
      setTimeout(() => {
        loadNextEditorPreview();
      }, 1000);
      return;
    }

  }

  if (!preview) {
    return (
      <div style={{ padding: 12, color: "#888" }}>
        Start typing or load a question to see a preview…
      </div>
    );
  }

  if (Array.isArray(preview.errors) && preview.errors.length > 0) {
    return (
      <div style={{ padding: 12 }}>
        <div style={{ color: "red", marginBottom: 12 }}>
          Backend reported errors:
          <ul>
            {preview.errors.map((e: string, i: number) => (
              <li key={i}>{safeLatex(e)}</li>
            ))}
          </ul>
        </div>

        {preview.question && (
          <div style={{ marginBottom: 12, fontWeight: "bold" }}>
            <Latex>{safeLatex(preview.question)}</Latex>
          </div>
        )}

        {preview.diagram_svg && (
          <div
            dangerouslySetInnerHTML={{ __html: preview.diagram_svg }}
            style={{ marginBottom: 12 }}
          />
        )}
      </div>
    );
  }

  const solution = safeLatex(preview.solution);
  const knowledgeItems: KnowledgeItem[] = preview.knowledge_items ?? [];
  const inlineKnowledgeAll: InlineKnowledge[] = preview.inline_knowledge ?? [];
  const questionKnowledge = inlineKnowledgeAll.filter(k => k.show === "question" || k.show === "both");
  const solutionKnowledge = inlineKnowledgeAll.filter(k => k.show === "solution" || k.show === "both" || k.show === "");
  const postAnswerKnowledge = inlineKnowledgeAll.filter(k => k.show === "post_answer");
  const postAnswer = preview.post_answer ?? "";
  const answers = Array.isArray(preview.answers) ? preview.answers : [];
  const sortedAnswers = [...answers.filter(Boolean)].sort((a: any, b: any) => {
    const na = parseFloat(a?.text);
    const nb = parseFloat(b?.text);
    if (!isNaN(na) && !isNaN(nb)) return na - nb;
    return 0;
  });
  const multiStep = preview.multi_step;
  const isMultiStep = Boolean(multiStep?.steps?.length);
  const activeStep = isMultiStep ? multiStep!.steps[multiStepIndex] : null;
  const diagramSvg = activeStep?.svg || preview.diagram_svg;
  const mainQuestion = safeLatex(preview.question);
  const stepQuestion = (isMultiStep && activeStep?.question)
    ? safeLatex(activeStep.question)
    : null;
  const isStepMC = isMultiStep && Boolean(activeStep?.choices?.length);
  const isInputMode = (isMultiStep && !isStepMC) || answers.some((a: any) => a?.input_type === "text");
  const correctInputAnswer = answers.find((a: any) => a?.correct);
  const inputAnswerMeta = answers.find((a: any) => a?.input_type === "text");
  const answerFormat = (isMultiStep ? activeStep?.answer_format : null) ?? inputAnswerMeta?.answer_format ?? null;
  const DEFAULT_FORMAT_INSTRUCTIONS: Record<string, string> = {
    fraction:        "Enter as a fraction, e.g. 3/5",
    integer:         "Enter a whole number, e.g. 42",
    decimal:         "Enter as a decimal to one decimal place, e.g. 5.0",
    ratio:           "Enter as a ratio, e.g. 3:2",
    percent:         "Enter as a percentage, e.g. 35%",
    equation:        "Enter a base and power, e.g. 5^2 (press ^ or the xⁿ button to enter the power)",
    proper_fraction: "Enter as a whole number, proper fraction (e.g. 3/4), or mixed number (e.g. 2 1/3)",
  };
  const formatInstruction = activeStep?.format_instruction
    ?? inputAnswerMeta?.format_instruction
    ?? (answerFormat ? DEFAULT_FORMAT_INSTRUCTIONS[answerFormat] ?? null : null);
  const answerTolerance = inputAnswerMeta?.tolerance ?? 1e-9;

  return (
    <div style={{ padding: 12, fontSize: 18 }}>
      <div style={{ marginBottom: stepQuestion ? 6 : 12 }}>
        <Latex>{mainQuestion}</Latex>
      </div>
      {questionKnowledge.map((k, i) => <KnowledgeCallout key={i} k={k} />)}
      {completedSteps.map((cs, i) => (
        <div key={i} style={{ marginBottom: 10, paddingLeft: 8, borderLeft: "3px solid #ccc" }}>
          {cs.question && (
            <div style={{ fontWeight: "bold" }}>
              <Latex>{safeLatex(cs.question)}</Latex>
            </div>
          )}
          <div style={{ color: cs.correct ? "#2e7d32" : "#c62828", marginTop: 2 }}>
            <Latex>{safeLatex(cs.answer)}</Latex>
          </div>
        </div>
      ))}

      {stepQuestion && (
        <div style={{ marginBottom: 12, fontWeight: "bold" }}>
          <Latex>{stepQuestion}</Latex>
        </div>
      )}

      {diagramSvg && (
        <div style={{ display: "flex", justifyContent: "center", width: "100%" }}>
          <div dangerouslySetInnerHTML={{ __html: diagramSvg }} />
        </div>
      )}

      {(isMultiStep || answers.length > 0) && (
        isStepMC ? (
          <>
          <div className="d-flex flex-row flex-wrap gap-2 mt-2">
            {activeStep!.choices!.map((c: any, i: number) => {
              const isSelected = selected === i;
              const btnClass = `btn btn-sm w-auto ${
                isSelected
                  ? isCorrect ? "btn-success" : "btn-danger"
                  : "btn-outline-primary"
              }`;
              return (
                <button
                  key={i}
                  className={btnClass}
                  style={{ minWidth: "90px" }}
                  disabled={isCorrect === true}
                  onClick={() => handleMultiStepChoiceClick(i, c)}
                >
                  <Latex>{safeLatex(c.text)}</Latex>
                </button>
              );
            })}
          </div>
          {selected === null && (
            <button
              className="btn btn-outline-secondary btn-sm mt-2"
              onClick={handleIDontKnowMultiStep}
            >
              I don't know
            </button>
          )}
          </>
        ) : isInputMode ? (
          <div>
            <div className="d-flex gap-2 align-items-center mt-2">
              {answerFormat === "equation" ? (
                <PowerInput
                  value={textInput}
                  onChange={v => {
                    setTextInput(v);
                    setFormatError(null);
                    if (isCorrect === false) {
                      setSelected(null);
                      setIsCorrect(null);
                    }
                  }}
                  onSubmit={handleTextSubmit}
                  disabled={isCorrect === true}
                  autoFocus={mode === "student"}
                />
              ) : (
              <input
                type="text"
                className="form-control"
                style={{ maxWidth: 200, backgroundColor: '#fff9c4' }}
                value={textInput}
                onChange={e => {
                  setTextInput(e.target.value);
                  setFormatError(null);
                  if (isCorrect === false) {
                    setSelected(null);
                    setIsCorrect(null);
                  }
                }}
                onKeyDown={e => { if (e.key === "Enter") handleTextSubmit(); }}
                disabled={isCorrect === true}
                ref={textInputRef}
              />
              )}
              <button
                className="btn btn-primary btn-sm"
                onClick={handleTextSubmit}
                disabled={isCorrect === true}
              >
                Submit
              </button>
              {isMultiStep ? (
                <button
                  className="btn btn-outline-secondary btn-sm"
                  onClick={handleIDontKnowMultiStep}
                  disabled={isCorrect === true}
                >
                  I don't know
                </button>
              ) : (
                <button
                  className="btn btn-outline-secondary btn-sm"
                  onClick={handleIDontKnow}
                  disabled={isCorrect === true}
                >
                  I don't know
                </button>
              )}
            </div>
            {formatError && (
              <div className="text-danger mt-1" style={{ fontSize: 18 }}>{formatError}</div>
            )}
            {formatInstruction && (
              <div className="text-muted mt-1" style={{ fontSize: 13 }}>
                Input format: <code>{formatInstruction}</code>
              </div>
            )}
          </div>
        ) : (
          <>
          <div className="d-flex flex-row flex-wrap gap-2">
            {sortedAnswers.map((a: any, i: number) => {
              const isSelected = selected === i;
              const btnClass = `btn btn-sm w-auto ${
                isSelected
                  ? isCorrect
                    ? "btn-success"
                    : "btn-danger"
                  : "btn-outline-primary"
              }`;

              if (a?.diagram_svg) {
                return (
                  <button
                    key={i}
                    className={btnClass}
                    style={{ padding: "4px" }}
                    onClick={() => handleAnswerClick(i, a)}
                    dangerouslySetInnerHTML={{ __html: a.diagram_svg }}
                  />
                );
              }

              return (
                <button
                  key={i}
                  className={btnClass}
                  style={{ minWidth: "90px" }}
                  onClick={() => handleAnswerClick(i, a)}
                >
                  <Latex>{safeLatex(a?.text)}</Latex>
                </button>
              );
            })}
          </div>
          {selected === null && (
            <button
              className="btn btn-outline-secondary btn-sm mt-2"
              onClick={handleIDontKnow}
            >
              I don't know
            </button>
          )}
          </>
        )
      )}

      {selected !== null && (
        <div className="mt-3" style={{ fontWeight: "bold", fontSize: 18, color: isCorrect ? "#2e7d32" : "#c62828" }}>
          {isCorrect ? "✓ Correct! Next question loading…" : "✗ Incorrect"}
        </div>
      )}

      {selected !== null && !isCorrect && isMultiStep && activeStep && (
        <div
          className="mt-2 p-2"
          style={{ background: "#f8f9fa", borderLeft: "4px solid #dc3545", fontSize: 18 }}
        >
          {activeStep.solution
            ? <Latex>{activeStep.solution}</Latex>
            : <>The answer is <strong>{activeStep.answer}</strong></>
          }
        </div>
      )}

      {selected !== null && !isCorrect && !isMultiStep && (solution || (isInputMode && correctInputAnswer)) && (
        <>
          <div
            className="mt-2 p-2"
            style={{
              background: "#f8f9fa",
              borderLeft: "4px solid #dc3545",
              fontSize: 18,
              whiteSpace: "pre-wrap",
            }}
          >
            {solution
              ? <Latex>{solution}</Latex>
              : <span>The correct answer is <strong>{correctInputAnswer?.text?.replace(/^\$/, "")}</strong></span>
            }
          </div>

          {solutionKnowledge.map((k, i) => <KnowledgeCallout key={i} k={k} />)}

          {knowledgeItems.length > 0 && (
            <div className="mt-3">
              {knowledgeItems.map(k => (
                <div
                  key={k.id}
                  className="p-3 mb-2 rounded"
                  style={{ background: "#fffde7", border: "1px solid #ffe082", fontSize: 15 }}
                >
                  {k.title && (
                    <div className="fw-semibold mb-1" style={{ fontSize: 14 }}>
                      <Latex>{k.title}</Latex>
                    </div>
                  )}
                  {k.text && (
                    <div className="mb-1" style={{ lineHeight: 1.6 }}>
                      <Latex>{k.text}</Latex>
                    </div>
                  )}
                  {k.diagram_svg && (
                    <div style={{ display: "flex", justifyContent: "center", width: "100%", margin: "8px 0" }}>
                      <div dangerouslySetInnerHTML={{ __html: k.diagram_svg }} />
                    </div>
                  )}
                  {k.text_2 && (
                    <div style={{ lineHeight: 1.6 }}>
                      <Latex>{k.text_2}</Latex>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {mode === "student" && backendResult && (
                <>
                  <button
                    className="btn btn-primary mt-2"
                    onClick={() => onStudentNext?.(backendResult)}
                  >
                    Next
                  </button>
                  <button
                    className="btn btn-sm btn-warning mt-2 ms-2"
                    onClick={handleIDontGetIt}
                  >
                    I don't get it
                  </button>
                  {(templateId ?? localTemplateId) && (
                    <button
                      className="btn btn-sm btn-secondary mt-2 ms-2"
                      onClick={() => navigate(`/templates/${templateId ?? localTemplateId}`)}
                    >
                      Edit template
                    </button>
                  )}
                </>
              )}
        </>
      )}

      {(postAnswerKnowledge.length > 0 || postAnswer) && (
        <div className="mt-3">
          {postAnswerKnowledge.map((k, i) => <KnowledgeCallout key={i} k={k} />)}
          {postAnswer && (
            <div style={{ fontSize: 16, lineHeight: 1.6 }}>
              <Latex>{postAnswer}</Latex>
            </div>
          )}
        </div>
      )}

      {flagged && (
        <div className="alert alert-info mt-2 p-2">
          Added to tutor review list
        </div>
      )}

      {mode === "student" && effectiveTemplateId && (
        <div style={{ marginTop: "2rem" }}>
          <div className="d-flex gap-2 align-items-center">
            <input
              type="text"
              className="form-control form-control-sm"
              style={{ maxWidth: 320 }}
              placeholder="Add a note about this question…"
              value={noteText}
              onChange={e => setNoteText(e.target.value)}
              onKeyDown={e => { if (e.key === "Enter") handleAddNote(); }}
              disabled={isAddingNote}
            />
            <button
              className="btn btn-sm btn-outline-secondary"
              onClick={handleAddNote}
              disabled={isAddingNote || !noteText.trim()}
              style={{ whiteSpace: "nowrap" }}
            >
              Add Note
            </button>
          </div>
          {notes.length > 0 && (
            <div className="mt-1">
              {notes.map(n => (
                <div key={n.id} className="text-muted border-bottom py-1" style={{ fontSize: 13 }}>
                  {n.text}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
