import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { Latex } from "./Latex";
import katex from "katex";
import "katex/dist/katex.min.css";
import { apiFetch } from "../../utils/apiFetch";
import type { PreviewResponse, StudentRecordResponse, KnowledgeItem, InlineKnowledge, MultipleAnswerEntry } from "../../types/PreviewResponse";
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
  disableOnWrong?: never;
  extraInputActions?: never;
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
  /** When true, a wrong answer locks all inputs and shows Next instead of Try Again */
  disableOnWrong?: boolean;
  /** Extra buttons rendered inline to the right of the "I don't know" button */
  extraInputActions?: React.ReactNode;

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
          <div dangerouslySetInnerHTML={{ __html: k.diagram_svg.replace("<svg ", '<svg style="width:90%;height:auto;display:block;" ') }} />
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
  disableOnWrong,
  extraInputActions,
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
  const [surdCoeff, setSurdCoeff] = useState("");
  const [surdRadicand, setSurdRadicand] = useState("");
  const [logInput, setLogInput] = useState("");
  const navigate = useNavigate();
  const [formatError, setFormatError] = useState<string | null>(null);
  const [noteText, setNoteText] = useState("");
  const [notes, setNotes] = useState<any[]>([]);
  const [isAddingNote, setIsAddingNote] = useState(false);
  const textInputRef = useRef<HTMLInputElement>(null);
  const surdCoeffRef = useRef<HTMLInputElement>(null);
  const surdRadicandRef = useRef<HTMLInputElement>(null);
  const [focusKey, setFocusKey] = useState(0);
  const [multiStepIndex, setMultiStepIndex] = useState(0);
  const [completedSteps, setCompletedSteps] = useState<Array<{ question: string; answer: string; correct: boolean }>>([]);
  const [multiInputs, setMultiInputs] = useState<string[]>([]);
  const multiInputRefs = useRef<Array<HTMLInputElement | null>>([]);

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
    setSurdCoeff("");
    setSurdRadicand("");
    setLogInput("");
    setFormatError(null);
    setMultiStepIndex(0);
    setCompletedSteps([]);
    setMultiInputs(preview?.multiple_answers ? preview.multiple_answers.map(() => "") : []);
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
  const inputsDisabled = isCorrect === true || (!!disableOnWrong && isCorrect === false);

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

  async function handleMultiStepWrongNext() {
    if (!activeStep) return;
    if (mode === "student") {
      const result = await recordAttempt({ text: textInput || activeStep.answer }, false);
      onStudentNext?.(result);
    }
    if (mode === "editor") { loadNextEditorPreview(); }
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

  // Parse LaTeX surd like "3\sqrt{5}", "\sqrt{3}", "4" → numeric value
  const parseSurdAnswer = (s: string): number | null => {
    const t = s.trim();
    if (/^\d+$/.test(t)) return parseInt(t);
    const m1 = t.match(/^\\sqrt\{(\d+)\}$/);
    if (m1) return Math.sqrt(parseInt(m1[1]));
    const m2 = t.match(/^(\d+)\\sqrt\{(\d+)\}$/);
    if (m2) return parseInt(m2[1]) * Math.sqrt(parseInt(m2[2]));
    return null;
  };

  // Parse student surd input: "3 * 5^0.5", "5^0.5", "3*sqrt(5)", "sqrt(5)", "4"
  const parseSurdInput = (s: string): number | null => {
    const t = s.trim().replace(/\s+/g, "");
    if (/^\d+$/.test(t)) return parseInt(t);
    const sqrtM = t.match(/^(\d+\*)?sqrt\((\d+)\)$/i);
    if (sqrtM) return (sqrtM[1] ? parseInt(sqrtM[1]) : 1) * Math.sqrt(parseInt(sqrtM[2]));
    const powM = t.match(/^(\d+\*)?(\d+)\^(?:0\.5+|\(0\.5\)|\(1\/2\))$/);
    if (powM) return (powM[1] ? parseInt(powM[1]) : 1) * Math.sqrt(parseInt(powM[2]));
    return null;
  };

  function answersMatch(input: string, correct: any, tolerance = 1e-9): boolean {
    // Surd comparison: correct answer is LaTeX like "3\sqrt{5}" or "\sqrt{3}"
    if (String(correct).includes("\\sqrt{")) {
      const cv = parseSurdAnswer(String(correct));
      const iv = parseSurdInput(String(input));
      if (cv !== null && iv !== null) return Math.abs(cv - iv) <= 1e-9;
      return false;
    }

    // Parse mixed numbers from raw strings BEFORE normalization strips spaces.
    // "10 11/15" → 10 + 11/15. Must run first.
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

    const normalize = (s: any) => {
      let v = String(s).trim().toLowerCase().replace(/\s+/g, "").replace(/\*\*/g, "^").replace(/,(?=\d{3})/g, "");
      // Strip outer square brackets: [-5,-1,1,6] → -5,-1,1,6  (list answers typed without brackets match)
      if (v.startsWith("[") && v.endsWith("]")) v = v.slice(1, -1);
      // Collapse redundant sign pairs: a + -b → a-b,  a - -b → a+b
      v = v.replace(/\+-/g, "-").replace(/--/g, "+");
      // x^(-n) → x^-n  (sympy wraps negative exponents in parens)
      v = v.replace(/\^\((-?[\w]+)\)/gi, "^$1");
      // x^{-n} → x^-n  (LaTeX brace notation)
      v = v.replace(/\^\{(-?[\w]+)\}/gi, "^$1");
      // x^1 = x, x^0 = 1
      v = v.replace(/^([a-z]\w*)\^1$/i, "$1");
      v = v.replace(/^([a-z]\w*)\^0$/i, "1");
      // 1/x^n  ↔  x^-n  (fraction form ≡ negative index)
      const fracIdx = v.match(/^1\/([a-z]\w*)\^(\d+)$/i);
      if (fracIdx) v = `${fracIdx[1]}^-${fracIdx[2]}`;
      // x^-n  →  canonical (already in right form; handles case where stored answer uses ^-)
      // Sort parenthesized factors: (x-4)(x-3) ≡ (x-3)(x-4)
      const fm = v.match(/^([^(]*)((?:\([^)]+\))+)$/);
      if (fm) {
        const factors = fm[2].match(/\([^)]+\)/g);
        if (factors && factors.length > 1) v = fm[1] + [...factors].sort().join('');
      }
      return v;
    };
    const a = normalize(input);
    const b = normalize(correct);
    console.log("[answersMatch]", { rawInput: input, rawCorrect: correct, normalized_a: a, normalized_b: b });

    // If the student entered a fraction, it must be fully simplified.
    // Check BEFORE exact-string match so that entering "12/60" when the
    // template answer is also "12/60" is still rejected.
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

    // Convert numeric fraction coefficients to decimals and compare again.
    // e.g. "-1/2x+5" ≡ "-0.5x+5"
    const fracToDecimal = (s: string) =>
      s.replace(/(-?\d+)\/(\d+)/g, (orig, n, d) => {
        const den = parseInt(d);
        return den === 0 ? orig : String(parseInt(n) / den);
      });
    if (fracToDecimal(a) === fracToDecimal(b)) return true;

    // If the correct answer has a leading $ (currency formatting) but the student
    // didn't type one, also accept the answer without the $ prefix.
    if (b.startsWith("$") && !a.startsWith("$") && a === b.slice(1)) return true;

    // Require format match: a percentage answer must be entered as a percentage
    if (b.endsWith("%") && !a.endsWith("%")) return false;

    // Parse a ratio like "1:2" → [1, 2] as integers (no simplification).
    // The student's ratio must already be in simplified form.
    const parseRatio = (s: string): number[] | null => {
      if (!s.includes(":")) return null;
      const parts = s.split(":").map(p => Number(p.trim()));
      if (parts.some(isNaN) || parts.some(p => p <= 0)) return null;
      return parts;
    };
    const gcdOf = (x: number, y: number): number => y === 0 ? x : gcdOf(y, x % y);
    const ra = parseRatio(a), rb = parseRatio(b);
    if (ra !== null && rb !== null && ra.length === rb.length) {
      // Reject the student's answer if it isn't already fully simplified.
      const studentGcd = ra.map(Math.round).reduce(gcdOf);
      if (studentGcd !== 1) return false;
      return ra.every((v, i) => Math.abs(v - rb[i]) < 1e-9);
    }

    // Parse a single number, fraction like "3/4", or percentage like "50%"
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
      // Use strict check — parseFloat("3x+2") would return 3, which is wrong
      // Also accept leading-dot decimals like ".5" (treat as "0.5")
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

    // Parse a product expression like "2x2x5x5"; returns {product, allPrime}
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

    // If the student entered a product, all factors must be prime
    if (pa !== null) {
      if (!pa.allPrime) return false;
      if (pb.product !== null && !isNaN(pb.product)) {
        return Math.abs(pa.product - pb.product) < 1e-9;
      }
    }

    // Parse plain-text mixed number like "2 1/3"
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

    // Parse power expression like "5^2" → 25
    const parsePower = (s: string): number | null => {
      const m = s.match(/^(\d+)\^(\d+)$/);
      if (!m) return null;
      return Math.pow(parseInt(m[1]), parseInt(m[2]));
    };
    const pa2 = parsePower(a), pb2 = parsePower(b) ?? parseFraction(b);
    if (pa2 !== null && pb2 !== null) return Math.abs(pa2 - pb2) <= tolerance;

    // Parse scientific notation: "3.2 × 10^3", "3.2 x 10^3", "3.2e3", "3.2e+3", "3.2e-3"
    const parseSci = (s: string): number | null => {
      // e-notation: 3.2e3, 3.2e+3, 3.2E-3
      const eMatch = s.match(/^(-?\d+(\.\d+)?)[eE]([+-]?\d+)$/);
      if (eMatch) return parseFloat(eMatch[1]) * Math.pow(10, parseInt(eMatch[3]));
      // "a × 10^b" or "a x 10^b" or "a * 10^b" (caret notation)
      const timesMatch = s.match(/^(-?\d+(\.\d+)?)\s*[×x\*]\s*10\^([+-]?\d+)$/);
      if (timesMatch) return parseFloat(timesMatch[1]) * Math.pow(10, parseInt(timesMatch[3]));
      // "a × 10⁻³" unicode superscript form (what the formatter outputs)
      const supMap: Record<string, string> = {"⁰":"0","¹":"1","²":"2","³":"3","⁴":"4","⁵":"5","⁶":"6","⁷":"7","⁸":"8","⁹":"9","⁺":"+","⁻":"-"};
      const uniMatch = s.match(/^(-?\d+(\.\d+)?)\s*×\s*10([⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻]+)$/);
      if (uniMatch) {
        const expStr = uniMatch[3].split("").map(c => supMap[c] ?? c).join("");
        return parseFloat(uniMatch[1]) * Math.pow(10, parseInt(expStr));
      }
      return null;
    };
    const sa = parseSci(a), sb = parseSci(b) ?? parseFraction(b);
    if (sa !== null && sb !== null) return Math.abs(sa - sb) <= tolerance;

    const na = parseFraction(a) ?? parseMixedNumber(a);
    const nb = parseFraction(b) ?? parseMixedNumber(b);
    if (na !== null && nb !== null) return Math.abs(na - nb) <= tolerance;

    // Parse log_b(x) or log(x, b) expressions and evaluate numerically.
    const parseLog = (s: string): number | null => {
      const t = s.replace(/\s/g, "");
      // log_2(10) or log_2(10) with optional underscore
      const m1 = t.match(/^log_?(\d+(?:\.\d+)?)\((-?[\d.]+(?:\/[\d.]+)?)\)$/i);
      if (m1) {
        const base = parseFloat(m1[1]);
        const argStr = m1[2];
        const argVal = argStr.includes("/")
          ? parseInt(argStr.split("/")[0]) / parseInt(argStr.split("/")[1])
          : parseFloat(argStr);
        if (base > 0 && base !== 1 && argVal > 0) return Math.log(argVal) / Math.log(base);
      }
      // log(x, b) — Python-style
      const m2 = t.match(/^log\((-?[\d.]+(?:\/[\d.]+)?),(-?[\d.]+(?:\/[\d.]+)?)\)$/i);
      if (m2) {
        const argStr = m2[1], baseStr = m2[2];
        const argVal = argStr.includes("/")
          ? parseInt(argStr.split("/")[0]) / parseInt(argStr.split("/")[1])
          : parseFloat(argStr);
        const base = baseStr.includes("/")
          ? parseInt(baseStr.split("/")[0]) / parseInt(baseStr.split("/")[1])
          : parseFloat(baseStr);
        if (base > 0 && base !== 1 && argVal > 0) return Math.log(argVal) / Math.log(base);
      }
      // log10(x)
      const m3 = t.match(/^log10\((-?[\d.]+(?:\/[\d.]+)?)\)$/i);
      if (m3) {
        const argVal = parseFloat(m3[1]);
        if (argVal > 0) return Math.log10(argVal);
      }
      return null;
    };
    const la = parseLog(input), lb = parseLog(correct) ?? parseFraction(b);
    // Log values stored by the backend use 6 sig-figs (%g), so the string-to-float
    // rounding error can be ~5e-9.  Use at least 1e-6 to absorb that noise.
    if (la !== null && lb !== null) return Math.abs(la - lb) <= Math.max(tolerance, 1e-6);

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
    if (format === "scientific_notation") {
      const validSci = /^-?\d+(\.\d+)?[eE][+-]?\d+$/.test(s)
        || /^-?\d+(\.\d+)?\s*[×x\*]\s*10\^[+-]?\d+$/.test(s)
        || /^-?\d+(\.\d+)?\s*×\s*10[⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻]+$/.test(s);
      if (!validSci) return "Enter in scientific notation, e.g. 3.2 × 10³ or 3.2e3";
    }
    if (format === "integer" && !/^-?\d+$/.test(s))
      return "Please enter a whole number, e.g. 42";
    if (format === "decimal" && !/^-?\d*\.?\d+$/.test(s))
      return "Please enter a decimal, e.g. 0.75";
    const decimalNMatch = format.match(/^decimal_(\d+)$/);
    if (decimalNMatch) {
      const n = parseInt(decimalNMatch[1]);
      if (!/^-?(\d+(\.\d+)?|\.\d+)$/.test(s))
        return `Please enter a decimal number, e.g. ${(1).toFixed(n)}`;
      const dotIdx = s.indexOf(".");
      const actualDp = dotIdx === -1 ? 0 : s.length - dotIdx - 1;
      if (actualDp !== 0 && actualDp !== n)
        return `Please give your answer to ${n} decimal place${n === 1 ? "" : "s"}, e.g. ${(1).toFixed(n)}`;
    }
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
    if (format === "equation" && !/^[A-Za-z0-9]+(\^-?[A-Za-z0-9]+)?$|^\d+\/[A-Za-z][A-Za-z0-9]*(\^[0-9]+)?$/.test(s))
      return "Please enter a base and optional power, e.g. x^-3 or 1/x^3";
    if (format === "log") {
      const t = s.replace(/\s/g, "");
      const valid = /^log_?\d+(\.\d+)?\(-?[\d.]+(?:\/[\d.]+)?\)$/i.test(t)
        || /^log\(-?[\d.]+(?:\/[\d.]+)?,-?[\d.]+(?:\/[\d.]+)?\)$/i.test(t)
        || /^log10\(-?[\d.]+(?:\/[\d.]+)?\)$/i.test(t);
      if (!valid) return "Enter as log_2(10) or log_10(100) — use the base and argument boxes";
    }
    if (format === "surd") {
      const t = s.replace(/\s+/g, "");
      const valid = /^\d+$/.test(t)
        || /^(\d+\*)?sqrt\(\d+\)$/i.test(t)
        || /^(\d+\*)?(\d+)\^(?:0\.5+|\(0\.5\)|\(1\/2\))$/.test(t);
      if (!valid) return "Enter e.g. 3 * 5^0.5 or 3*sqrt(5) for 3√5, or a whole number for a perfect square";
    }
    return null;
  }

  async function handleMultiAnswerSubmit() {
    const correctItems: MultipleAnswerEntry[] | null | undefined =
      (isStepMultiInput ? activeStep?.multiple_answers : null) ?? preview?.multiple_answers;
    if (!correctItems || correctItems.length === 0) return;
    if (multiInputs.some(v => v.trim() === "")) return;

    const hasLabels = correctItems.some(item => item.label);
    let allCorrect = true;

    if (hasLabels) {
      // Labeled inputs: positional — each box must match its own answer
      for (let i = 0; i < multiInputs.length; i++) {
        if (!answersMatch(multiInputs[i].trim(), correctItems[i].value)) {
          allCorrect = false;
          break;
        }
      }
    } else {
      // Unlabeled: order-insensitive (existing behaviour)
      const remaining = correctItems.map(item => item.value);
      for (const input of multiInputs) {
        const idx = remaining.findIndex(c => answersMatch(input.trim(), c));
        if (idx === -1) { allCorrect = false; break; }
        remaining.splice(idx, 1);
      }
    }

    const displayAnswer = multiInputs.map((v, i) => {
      const lbl = correctItems[i]?.label;
      return lbl ? `${lbl} = ${v}` : v;
    }).join(", ");
    setSelected(0);
    setIsCorrect(allCorrect);

    if (isStepMultiInput && allCorrect) {
      const multiStep2 = preview?.multi_step;
      const isLastStep = multiStepIndex === (multiStep2?.steps?.length ?? 1) - 1;
      if (!isLastStep) {
        setTimeout(() => { advanceMultiStep(activeStep?.question ?? "", displayAnswer, true); setMultiInputs([]); }, 800);
        return;
      }
    }

    if (mode === "student") {
      onImmediateAnswer?.(displayAnswer, allCorrect);
      const result = await recordAttempt({ text: displayAnswer }, allCorrect);
      if (allCorrect) {
        setTimeout(() => { onStudentNext?.(result); }, 2000);
      } else {
        setShowIncorrectFeedback(true);
        setBackendResult(result);
      }
    }
    if (mode === "editor" && allCorrect) {
      setTimeout(() => { loadNextEditorPreview(); }, 1000);
    }
  }

  async function handleTextSubmit() {
    const fmtErr = checkAnswerFormat(textInput, answerFormat);
    if (fmtErr) { setFormatError(fmtErr); return; }
    setFormatError(null);

    // Multi-step mode (AlgebraTable with multiple blanks)
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
      // Incorrect: just show "Incorrect — try again"; student retypes to clear it
      return;
    }

    // Single-answer mode
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

  async function handleSurdSubmit() {
    const coeff = surdCoeff.trim() === "" ? 1 : parseInt(surdCoeff);
    const radicand = surdRadicand.trim() === "" ? 1 : parseInt(surdRadicand);
    if (isNaN(coeff) || coeff === 0 || isNaN(radicand) || radicand < 1) {
      setFormatError("Enter a whole number (non-zero) for the coefficient and a positive whole number for the radicand");
      return;
    }
    setFormatError(null);
    const effectiveInput = radicand === 1 ? String(coeff) : `${coeff}*sqrt(${radicand})`;

    // Multi-step mode
    const multiStep = preview?.multi_step;
    if (multiStep?.steps?.length) {
      const step = multiStep.steps[multiStepIndex];
      const correct = answersMatch(effectiveInput, step.answer, step.tolerance ?? 1e-9);
      setSelected(0);
      setIsCorrect(correct);
      if (mode === "student") onImmediateAnswer?.(effectiveInput, correct);
      if (correct) {
        const isLastStep = multiStepIndex === multiStep.steps.length - 1;
        if (!isLastStep) {
          setTimeout(() => { advanceMultiStep(step.question ?? "", effectiveInput, true); }, 800);
        } else {
          if (mode === "student") {
            const result = await recordAttempt({ text: effectiveInput }, true);
            setTimeout(() => { onStudentNext?.(result); }, 2000);
          }
          if (mode === "editor") setTimeout(() => { loadNextEditorPreview(); }, 1000);
        }
      }
      return;
    }

    // Single-answer mode
    if (!correctInputAnswer) return;
    const correct = answersMatch(effectiveInput, correctInputAnswer.text, answerTolerance);
    const answerObj = { text: effectiveInput };
    setSelected(0);
    setIsCorrect(correct);
    if (mode === "student") {
      onImmediateAnswer?.(effectiveInput, correct);
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

  async function handleLogSubmit() {
    const effectiveInput = logInput.trim();
    const m = effectiveInput.replace(/\s/g, "").match(/^log_?(\d+(?:\.\d+)?)\((.+)\)$/i);
    if (!m) {
      setFormatError("Enter as log_2(10) — include the base and argument");
      return;
    }
    setFormatError(null);

    // Multi-step mode
    const multiStep = preview?.multi_step;
    if (multiStep?.steps?.length) {
      const step = multiStep.steps[multiStepIndex];
      const correct = answersMatch(effectiveInput, step.answer, step.tolerance ?? 1e-9);
      setSelected(0);
      setIsCorrect(correct);
      if (mode === "student") onImmediateAnswer?.(effectiveInput, correct);
      if (correct) {
        const isLastStep = multiStepIndex === multiStep.steps.length - 1;
        if (!isLastStep) {
          setTimeout(() => { advanceMultiStep(step.question ?? "", effectiveInput, true); }, 800);
        } else {
          if (mode === "student") {
            const result = await recordAttempt({ text: effectiveInput }, true);
            setTimeout(() => { onStudentNext?.(result); }, 2000);
          }
          if (mode === "editor") setTimeout(() => { loadNextEditorPreview(); }, 1000);
        }
      }
      return;
    }

    // Single-answer mode
    if (!correctInputAnswer) return;
    const correct = answersMatch(effectiveInput, correctInputAnswer.text, answerTolerance);
    const answerObj = { text: effectiveInput };
    setSelected(0);
    setIsCorrect(correct);
    if (mode === "student") {
      onImmediateAnswer?.(effectiveInput, correct);
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
            dangerouslySetInnerHTML={{
              __html: preview.diagram_svg.replace("<svg ", '<svg style="width:100%;height:auto;display:block;" '),
            }}
            style={{ width: "100%", marginBottom: 12 }}
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
  // Main question text always shown; per-step question shown below it when present
  const mainQuestion = safeLatex(preview.question);
  const stepQuestion = (isMultiStep && activeStep?.question)
    ? safeLatex(activeStep.question)
    : null;
  const isStepMC = isMultiStep && Boolean(activeStep?.choices?.length);
  const isStepMultiInput = isMultiStep && Boolean(activeStep?.multiple_answers?.length);
  const isAlgebraTable = preview?.diagram_code?.startsWith("AlgebraTable(");
  const isInputMode = (isMultiStep && !isStepMC && !isStepMultiInput) || answers.some((a: any) => a?.input_type === "text");
  const correctInputAnswer = answers.find((a: any) => a?.correct);
  const inputAnswerMeta = answers.find((a: any) => a?.input_type === "text");
  const answerFormat = (isMultiStep ? activeStep?.answer_format : null) ?? inputAnswerMeta?.answer_format ?? null;
  const answerUnit = (isMultiStep ? activeStep?.answer_unit : null) ?? (inputAnswerMeta as any)?.answer_unit ?? null;
  const DEFAULT_FORMAT_INSTRUCTIONS: Record<string, string> = {
    fraction:        "Enter as a fraction, e.g. 3/5",
    integer:         "Enter a whole number, e.g. 42",
    decimal:         "Enter as a decimal to one decimal place, e.g. 5.0",
    ratio:           "Enter as a ratio, e.g. 3:2",
    percent:         "Enter as a percentage, e.g. 35%",
    equation:        "Enter e.g. x^-3 or 1/x^3 — press ^ or xⁿ for the power, / for a fraction",
    proper_fraction: "Enter as a whole number, proper fraction (e.g. 3/4), or mixed number (e.g. 2 1/3)",
    log:             "Enter your answer in the form: log_2(10)",
  };
  const formatInstruction = activeStep?.format_instruction
    ?? inputAnswerMeta?.format_instruction
    ?? (answerFormat ? DEFAULT_FORMAT_INSTRUCTIONS[answerFormat] ?? null : null);
  const answerTolerance = inputAnswerMeta?.tolerance ?? 1e-9;
  const isMultiAnswerMode = !!(preview?.multiple_answers?.length) || isStepMultiInput;

  return (
    <div style={{ padding: 12, fontSize: 18 }}>
      <div style={{ marginBottom: isMultiStep ? 6 : 12 }}>
        <Latex>{mainQuestion}</Latex>
      </div>
      {isMultiStep && (
        <hr style={{ borderTop: "1px solid #000", margin: "6px 0 10px" }} />
      )}
      {questionKnowledge.map((k, i) => <KnowledgeCallout key={i} k={k} />)}
      {!isAlgebraTable && completedSteps.map((cs, i) => (
        <div key={i} style={{ marginBottom: 10, paddingLeft: 8, borderLeft: "3px solid #ccc" }}>
          {cs.question && (
            <div>
              <Latex>{safeLatex(cs.question)}</Latex>
            </div>
          )}
          <div style={{ color: cs.correct ? "#2e7d32" : "#c62828", marginTop: 2 }}>
            <Latex>{safeLatex(cs.answer)}</Latex>
          </div>
        </div>
      ))}

      {diagramSvg && (
        preview?.diagram_code?.startsWith("UnitCircle(") ? (
          <iframe
            srcDoc={diagramSvg}
            sandbox="allow-scripts"
            style={{ width: "100%", height: 440, border: "none", display: "block", marginBottom: 8 }}
            title="Unit circle diagram"
          />
        ) : (
          <div
            dangerouslySetInnerHTML={{
              __html: diagramSvg.replace(
                "<svg ",
                '<svg style="width:100%;height:auto;display:block;" '
              ),
            }}
            style={{ width: "100%", marginBottom: 8 }}
          />
        )
      )}

      {stepQuestion && (
        <div style={{ marginBottom: 12 }}>
          <Latex>{stepQuestion}</Latex>
        </div>
      )}

      {(isMultiStep || answers.length > 0) && !isStepMultiInput && (
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
                  disabled={inputsDisabled}
                  onClick={() => handleMultiStepChoiceClick(i, c)}
                >
                  <Latex>{safeLatex(c.text)}</Latex>
                </button>
              );
            })}
          </div>
          {selected === null && (
            <div className="d-flex gap-2 align-items-center mt-2">
              <button
                className="btn btn-outline-secondary btn-sm"
                onClick={handleIDontKnowMultiStep}
              >
                I don't know
              </button>
              {extraInputActions}
            </div>
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
                  disabled={inputsDisabled}
                  autoFocus={mode === "student"}
                />
              ) : answerFormat === "log" ? (
                <input
                  type="text"
                  className="form-control"
                  placeholder="e.g. log_2(10)"
                  value={logInput}
                  onChange={e => {
                    setLogInput(e.target.value);
                    setFormatError(null);
                    if (isCorrect === false) { setSelected(null); setIsCorrect(null); }
                  }}
                  onKeyDown={e => { if (e.key === "Enter") { e.preventDefault(); handleLogSubmit(); } }}
                  disabled={inputsDisabled}
                  autoFocus={mode === "student"}
                  style={{ width: 160, textAlign: "center", backgroundColor: inputsDisabled ? "#f8f9fa" : "#fff9c4" }}
                />
              ) : answerFormat === "surd" ? (
                <>
                  <input
                    type="text"
                    inputMode="numeric"
                    className="form-control"
                    style={{ width: 72, textAlign: "center", backgroundColor: "#fff9c4" }}
                    value={surdCoeff}
                    onChange={e => {
                      setSurdCoeff(e.target.value);
                      setFormatError(null);
                      if (isCorrect === false) { setSelected(null); setIsCorrect(null); }
                    }}
                    onKeyDown={e => { if (e.key === "Enter") surdRadicandRef.current?.focus(); }}
                    disabled={inputsDisabled}
                    ref={surdCoeffRef}
                    autoFocus={mode === "student"}
                  />
                  <span style={{ fontSize: 26, lineHeight: 1, userSelect: "none" }}>√</span>
                  <input
                    type="text"
                    inputMode="numeric"
                    className="form-control"
                    style={{ width: 72, textAlign: "center", backgroundColor: "#fff9c4" }}
                    value={surdRadicand}
                    onChange={e => {
                      setSurdRadicand(e.target.value);
                      setFormatError(null);
                      if (isCorrect === false) { setSelected(null); setIsCorrect(null); }
                    }}
                    onKeyDown={e => { if (e.key === "Enter") handleSurdSubmit(); }}
                    disabled={inputsDisabled}
                    ref={surdRadicandRef}
                  />
                </>
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
                disabled={inputsDisabled}
                ref={textInputRef}
              />
              )}
              {answerUnit && (
                <span style={{ fontSize: 16, userSelect: "none" }}>
                  {answerUnit.split("^").map((part: string, i: number) =>
                    i === 0 ? part : <sup key={i}>{part}</sup>
                  )}
                </span>
              )}
              <button
                className="btn btn-primary btn-sm"
                onClick={answerFormat === "surd" ? handleSurdSubmit : answerFormat === "log" ? handleLogSubmit : handleTextSubmit}
                disabled={inputsDisabled}
              >
                Submit
              </button>
              {isMultiStep ? (
                <button
                  className="btn btn-outline-secondary btn-sm"
                  onClick={handleIDontKnowMultiStep}
                  disabled={inputsDisabled}
                >
                  I don't know
                </button>
              ) : (
                <button
                  className="btn btn-outline-secondary btn-sm"
                  onClick={handleIDontKnow}
                  disabled={inputsDisabled}
                >
                  I don't know
                </button>
              )}
              {extraInputActions}
            </div>
            {formatError && (
              <div className="text-danger mt-1" style={{ fontSize: 18 }}>{formatError}</div>
            )}
            {formatInstruction && (
              <div className="text-muted mt-1" style={{ fontSize: 13 }}>
                Input format: <code>{formatInstruction}</code>
              </div>
            )}
            {answerFormat === "log" && (() => {
              const t = logInput.replace(/\s/g, "");
              const m = t.match(/^log_?(\d+(?:\.\d+)?)\((.+)\)$/i);
              if (!m) return null;
              let html = "";
              try { html = katex.renderToString(`\\boldsymbol{\\log_{${m[1]}}(${m[2]})}`, { throwOnError: false }); }
              catch { return null; }
              return (
                <div className="mt-1" style={{ fontSize: 18 }}>
                  Your answer: <span dangerouslySetInnerHTML={{ __html: html }} />
                </div>
              );
            })()}
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
                    disabled={inputsDisabled}
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
                  disabled={inputsDisabled}
                  onClick={() => handleAnswerClick(i, a)}
                >
                  <Latex>{safeLatex(a?.text)}</Latex>
                </button>
              );
            })}
          </div>
          <div className="d-flex gap-2 align-items-center mt-2">
            {selected === null && (
              <button
                className="btn btn-outline-secondary btn-sm"
                onClick={handleIDontKnow}
              >
                I don't know
              </button>
            )}
            {selected === null && extraInputActions}
          </div>
          </>
        )
      )}

      {isMultiAnswerMode && (
        <div>
          <div className="d-flex flex-wrap gap-2 align-items-center mt-2">
            {(isStepMultiInput ? activeStep!.multiple_answers! : preview!.multiple_answers!).map((item, i, arr) => (
              <div key={i} className="d-flex align-items-center gap-1">
                {item.label && (
                  <span style={{ fontSize: 18, userSelect: "none", whiteSpace: "nowrap" }}>
                    {item.label} =
                  </span>
                )}
                <input
                  type="text"
                  className="form-control"
                  style={{ maxWidth: item.width ?? 60, backgroundColor: '#fff9c4' }}
                  value={multiInputs[i] ?? ""}
                  onChange={e => {
                    const val = e.target.value;
                    setMultiInputs(prev => { const next = [...prev]; next[i] = val; return next; });
                    if (isCorrect === false) { setSelected(null); setIsCorrect(null); }
                  }}
                  onKeyDown={e => {
                    if (e.key === "Enter") {
                      if (i < arr.length - 1) {
                        multiInputRefs.current[i + 1]?.focus();
                      } else {
                        handleMultiAnswerSubmit();
                      }
                    }
                  }}
                  disabled={inputsDisabled}
                  ref={el => { multiInputRefs.current[i] = el; }}
                  autoFocus={i === 0 && mode === "student"}
                />
              </div>
            ))}
            <button
              className="btn btn-primary btn-sm"
              onClick={handleMultiAnswerSubmit}
              disabled={inputsDisabled || multiInputs.some(v => !v.trim())}
            >
              Submit
            </button>
            <button
              className="btn btn-outline-secondary btn-sm"
              onClick={handleIDontKnow}
              disabled={inputsDisabled}
            >
              I don't know
            </button>
            {extraInputActions}
          </div>
        </div>
      )}

      {selected !== null && (isCorrect || !disableOnWrong) && (
        <div className="mt-3" style={{ fontWeight: "bold", fontSize: 18, color: isCorrect ? "#2e7d32" : "#c62828" }}>
          {isCorrect ? "✓ Correct! Next question loading…" : "Try again"}
        </div>
      )}

      {selected !== null && !isCorrect && isMultiStep && activeStep && (
        <>
          <div
            className="mt-2 p-2"
            style={{ background: "#f8f9fa", borderLeft: "4px solid #dc3545", fontSize: 18 }}
          >
            {activeStep.solution
              ? <Latex>{activeStep.solution}</Latex>
              : <>The answer is <strong>{activeStep.answer}</strong></>
            }
          </div>
          {disableOnWrong && mode === "student" && (
            <button className="btn btn-primary btn-sm mt-2" onClick={handleMultiStepWrongNext}>
              Next
            </button>
          )}
        </>
      )}

      {selected !== null && !isCorrect && !isMultiStep && (solution || (isInputMode && correctInputAnswer) || isMultiAnswerMode) && (
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
              : isMultiAnswerMode
                ? <span>The correct answers are <strong>{preview?.multiple_answers?.map(item => item.label ? `${item.label} = ${item.value}` : item.value).join(", ")}</strong></span>
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
                      <div dangerouslySetInnerHTML={{ __html: k.diagram_svg.replace("<svg ", '<svg style="width:90%;height:auto;display:block;" ') }} />
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