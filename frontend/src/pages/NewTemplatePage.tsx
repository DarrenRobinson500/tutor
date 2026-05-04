import { useState, useEffect } from "react";
import { useYears } from "../utils/useYears";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Layout } from "./components/Layout";
import { apiFetch } from "../utils/apiFetch";

function toBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = reader.result as string;
      resolve(result.split(",")[1]);
    };
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

const PROMPT_PRESETS: { id: string; label: string; prompt: string }[] = [
  {
    id: "diagram",
    label: "Add a diagram to the question",
    prompt: `Include a 'diagram:' field in the template using one of the supported diagram types. ` +
      `Available types: Triangle, Rect, Circle, Line, Prism, Net, AlgebraTable, Cartesian, NumberLine, Angle, ParallelLines. ` +
      `Template parameters are substituted directly with {{ var }} syntax inside the diagram string (no extra braces needed). ` +
      `Example: diagram: 'Triangle(a: {{ a }}, b: {{ b }}, C: {{ angle }}, label_v: true)' ` +
      `or diagram: 'Rect(width: {{ w }}, height: {{ h }}, labels: true)'. ` +
      `For Triangle, specify any valid combination of sides (a, b, c) and angles (A, B, C in degrees) — ` +
      `valid cases are SSS, SAS, ASA, AAS, AA. Do NOT use SSA (two sides and a non-included angle). ` +
      `The diagram string must be on a single line. Do not split {{ }} expressions across lines.`,
  },
  {
    id: "input_answer",
    label: "Make this an Input Answer (not multi-choice)",
    prompt: "Use a single input answer (the 'input' key) instead of multiple-choice answers.",
  },
  {
    id: "choice_parameter",
    label: "Use the choice parameter",
    prompt: "Use a choice parameter (type: choice, values: [...]) instead of a range-based integer or decimal parameter.",
  },
  {
    id: "tolerance",
    label: "Allow approximate answers by using the tolerance parameter",
    prompt: "For the correct answer, use an 'input' answer with a 'tolerance' field (e.g. tolerance: 0.5) to allow approximate numeric responses.",
  },
  {
    id: "multi_part",
    label: "Use multi-part question",
    prompt: "Use a multi-part question by adding a 'parts' list under 'question'. Each part should have 'text' (the question for that part), 'answer' (the correct answer, using {{ }} expressions if needed), and 'solution' (explanation shown after answering). The top-level 'answers' and 'solution' fields should be left empty. Example structure: question: { text: 'Use the diagram to answer each question.', parts: [{ text: 'Part 1 question?', answer: '...', solution: '...' }] }",
  },
];

export function NewTemplatePage() {
  const navigate = useNavigate();
  const years = useYears();
  const [searchParams] = useSearchParams();

  // Pre-filled from SkillOverviewPage when launched via "Create Template - Image"
  const pinSkillId        = searchParams.get("skill_id")        ?? undefined;
  const pinSkillDetailId  = searchParams.get("skill_detail_id") ?? undefined;
  const pinDifficulty     = searchParams.get("difficulty")      ?? undefined;

  const [imageFile, setImageFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [grade, setGrade] = useState(searchParams.get("grade") ?? "");
  const [additionalPrompt, setAdditionalPrompt] = useState("");
  const [checkedPresets, setCheckedPresets] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    function handlePaste(e: Event) {
      const items = (e as ClipboardEvent).clipboardData?.items;
      if (!items) return;
      for (const item of Array.from(items)) {
        if (item.type.startsWith("image/")) {
          const file = item.getAsFile();
          if (file) handleFile(file);
          break;
        }
      }
    }
    window.addEventListener("paste", handlePaste);
    return () => window.removeEventListener("paste", handlePaste);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function handleFile(file: File) {
    setImageFile(file);
    setPreviewUrl(URL.createObjectURL(file));
    setError(null);
  }

  async function handleGenerate() {
    if (!grade) return;
    setLoading(true);
    setError(null);
    try {
      const payload: Record<string, string> = {
        grade,
        additional_prompt: [
          additionalPrompt,
          ...PROMPT_PRESETS.filter(p => checkedPresets.has(p.id)).map(p => p.prompt),
        ].filter(Boolean).join(" "),
      };
      if (imageFile) {
        payload.image = await toBase64(imageFile);
        payload.mime_type = imageFile.type;
      }
      if (pinSkillId)       payload.skill_id        = pinSkillId;
      if (pinSkillDetailId) payload.skill_detail_id = pinSkillDetailId;
      if (pinDifficulty)    payload.difficulty      = pinDifficulty;

      const res = await apiFetch("/api/templates/generate_from_image/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.error ?? "Generation failed");
        return;
      }
      navigate(`/templates/${data.id}`);
    } catch (e: any) {
      setError(e.message ?? "Unexpected error");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Layout>
      <div className="container py-4" style={{ maxWidth: 600 }}>
        <div className="d-flex align-items-center gap-3 mb-4">
          <button
            className="btn btn-outline-secondary btn-sm"
            onClick={() => navigate("/templates")}
          >
            ← Back
          </button>
          <h4 className="mb-0">New Template from Screenshot</h4>
        </div>

        {/* Pinned context banner */}
        {(pinSkillDetailId || pinDifficulty) && (
          <div className="alert alert-info py-2 mb-3" style={{ fontSize: 13 }}>
            {pinSkillDetailId && <>Skill Detail ID: <strong>{pinSkillDetailId}</strong></>}
            {pinDifficulty && <>, difficulty {pinDifficulty}</>}
            {grade         && <>, Year {grade}</>}
          </div>
        )}

        {/* Drop zone */}
        <div
          className="border rounded p-4 text-center mb-3"
          style={{
            borderStyle: "dashed",
            cursor: "pointer",
            background: previewUrl ? "transparent" : "#f8f9fa",
            minHeight: 160,
          }}
          onClick={() => document.getElementById("img-input")?.click()}
          onDragOver={e => e.preventDefault()}
          onDrop={e => {
            e.preventDefault();
            const f = e.dataTransfer.files[0];
            if (f) handleFile(f);
          }}
        >
          {previewUrl ? (
            <img
              src={previewUrl}
              alt="preview"
              style={{ maxWidth: "100%", maxHeight: 300, objectFit: "contain" }}
            />
          ) : (
            <div className="text-muted">
              <div style={{ fontSize: 32, marginBottom: 8 }}>📷</div>
              Click, drag, or paste (Ctrl+V) a screenshot here
            </div>
          )}
        </div>

        <input
          id="img-input"
          type="file"
          accept="image/*"
          style={{ display: "none" }}
          onChange={e => {
            const f = e.target.files?.[0];
            if (f) handleFile(f);
          }}
        />

        <div className="mb-3">
          <label className="form-label fw-semibold">Additional AI Prompt <span className="text-muted fw-normal">(optional)</span></label>
          <textarea
            className="form-control mb-2"
            rows={2}
            placeholder="e.g. Include negative numbers. Make the answer a fraction."
            value={additionalPrompt}
            onChange={e => setAdditionalPrompt(e.target.value)}
          />
          {PROMPT_PRESETS.map(preset => (
            <div className="form-check" key={preset.id}>
              <input
                className="form-check-input"
                type="checkbox"
                id={`preset-${preset.id}`}
                checked={checkedPresets.has(preset.id)}
                onChange={e => {
                  setCheckedPresets(prev => {
                    const next = new Set(prev);
                    e.target.checked ? next.add(preset.id) : next.delete(preset.id);
                    return next;
                  });
                }}
              />
              <label className="form-check-label" htmlFor={`preset-${preset.id}`}>
                {preset.label}
              </label>
            </div>
          ))}
        </div>

        <div className="mb-3">
          <label className="form-label fw-semibold">Year / Grade</label>
          <select
            className="form-select"
            value={grade}
            onChange={e => setGrade(e.target.value)}
          >
            <option value="">— select year —</option>
            {years.map(y => <option key={y.code} value={y.code}>{y.label}</option>)}
          </select>
        </div>

        {error && <div className="alert alert-danger py-2 mb-3">{error}</div>}

        <button
          className="btn btn-primary w-100"
          onClick={handleGenerate}
          disabled={!imageFile || !grade || loading}
        >
          {loading ? (
            <>
              <span className="spinner-border spinner-border-sm me-2" />
              Generating…
            </>
          ) : (
            "Generate Template"
          )}
        </button>
      </div>
    </Layout>
  );
}
