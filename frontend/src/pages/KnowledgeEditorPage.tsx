import { useEffect, useState, useCallback, useRef } from "react";
import { useParams, useNavigate, useSearchParams } from "react-router-dom";
import debounce from "lodash.debounce";
import { Layout } from "./components/Layout";
import { Latex } from "./components/Latex";
import { apiFetch } from "../utils/apiFetch";

interface KnowledgeItem {
  id: number | null;
  title: string;
  text: string;
  diagram: string;
  text_2: string;
  skill_ids: number[];
}

const EMPTY: KnowledgeItem = {
  id: null,
  title: "",
  text: "",
  diagram: "",
  text_2: "",
  skill_ids: [],
};

// ─── Preview ────────────────────────────────────────────────────────────────

function KnowledgePreview({ item, diagramSvg }: { item: KnowledgeItem; diagramSvg: string }) {
  const hasContent = item.title || item.text || item.diagram || item.text_2;
  if (!hasContent) {
    return (
      <div className="text-muted text-center py-5" style={{ fontSize: 14 }}>
        Fill in the fields on the left to see a preview.
      </div>
    );
  }

  return (
    <div className="card shadow-sm">
      <div className="card-body p-4">
        {item.title && (
          <h5 className="mb-3 fw-semibold">
            <Latex>{item.title}</Latex>
          </h5>
        )}
        {item.text && (
          <div className="mb-3" style={{ fontSize: 16, lineHeight: 1.6 }}>
            <Latex>{item.text}</Latex>
          </div>
        )}
        {diagramSvg && (
          <div
            className="mb-3 text-center"
            dangerouslySetInnerHTML={{ __html: diagramSvg }}
          />
        )}
        {item.text_2 && (
          <div style={{ fontSize: 16, lineHeight: 1.6 }}>
            <Latex>{item.text_2}</Latex>
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Page ────────────────────────────────────────────────────────────────────

export function KnowledgeEditorPage() {
  const { id } = useParams<{ id: string }>();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const [item, setItem] = useState<KnowledgeItem>(EMPTY);
  const [diagramSvg, setDiagramSvg] = useState("");
  const [diagramError, setDiagramError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  const [showImageSection, setShowImageSection] = useState(false);
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imagePreviewUrl, setImagePreviewUrl] = useState<string | null>(null);
  const [imagePrompt, setImagePrompt] = useState("");
  const [generating, setGenerating] = useState(false);
  const [generateError, setGenerateError] = useState<string | null>(null);
  const imageInputRef = useRef<HTMLInputElement>(null);

  // Load existing item
  useEffect(() => {
    if (!id) return;
    apiFetch(`/api/knowledge/${id}/`)
      .then(r => r.json())
      .then((d: KnowledgeItem) => setItem(d));
  }, [id]);

  // Pre-fill skill_ids from query param on new items
  useEffect(() => {
    if (id) return;
    const skillId = searchParams.get("skill_id");
    if (skillId) {
      setItem(prev => ({ ...prev, skill_ids: [parseInt(skillId)] }));
    }
  }, [searchParams, id]);

  // Debounced diagram preview
  const fetchDiagram = useCallback(
    debounce(async (code: string) => {
      if (!code.trim() || code.trim().toLowerCase() === "none") {
        setDiagramSvg("");
        setDiagramError(null);
        return;
      }
      try {
        const res = await apiFetch("/api/knowledge/preview/", {
          method: "POST",
          body: JSON.stringify({ diagram: code }),
        });
        const data = await res.json();
        setDiagramSvg(data.diagram_svg || "");
        setDiagramError(data.error || null);
      } catch {
        setDiagramError("Failed to render diagram");
      }
    }, 600),
    []
  );

  useEffect(() => {
    fetchDiagram(item.diagram);
  }, [item.diagram]);

  useEffect(() => {
    if (!showImageSection) return;
    const handlePaste = (e: Event) => {
      const items = (e as ClipboardEvent).clipboardData?.items;
      if (!items) return;
      for (const it of Array.from(items)) {
        if (it.type.startsWith("image/")) {
          const f = it.getAsFile();
          if (f) handleImageFile(f);
          break;
        }
      }
    };
    window.addEventListener("paste", handlePaste);
    return () => window.removeEventListener("paste", handlePaste);
  }, [showImageSection]);

  const handleImageFile = (file: File) => {
    setImageFile(file);
    setImagePreviewUrl(URL.createObjectURL(file));
    setGenerateError(null);
  };

  const generateFromImage = async () => {
    if (!imageFile) return;
    setGenerating(true);
    setGenerateError(null);
    try {
      const reader = new FileReader();
      const b64: string = await new Promise((resolve, reject) => {
        reader.onload = () => resolve((reader.result as string).split(",")[1]);
        reader.onerror = reject;
        reader.readAsDataURL(imageFile);
      });
      const res = await apiFetch("/api/knowledge/generate_from_image/", {
        method: "POST",
        body: JSON.stringify({ image: b64, mime_type: imageFile.type, additional_prompt: imagePrompt }),
      });
      const data = await res.json();
      if (!res.ok) {
        setGenerateError(data.error ?? "Generation failed");
        return;
      }
      setItem(prev => ({
        ...prev,
        title: data.title || prev.title,
        text: data.text || prev.text,
        diagram: data.diagram || prev.diagram,
        text_2: data.text_2 || prev.text_2,
      }));
      setSaved(false);
      setShowImageSection(false);
    } catch (e: any) {
      setGenerateError(e.message ?? "Unexpected error");
    } finally {
      setGenerating(false);
    }
  };

  const update = (field: keyof KnowledgeItem, value: any) => {
    setItem(prev => ({ ...prev, [field]: value }));
    setSaved(false);
  };

  const save = async () => {
    if (!item.title.trim()) {
      setSaveError("Title is required.");
      return;
    }
    setSaving(true);
    setSaveError(null);
    try {
      const method = item.id ? "PATCH" : "POST";
      const url = item.id ? `/api/knowledge/${item.id}/` : "/api/knowledge/";
      const res = await apiFetch(url, {
        method,
        body: JSON.stringify(item),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(JSON.stringify(err));
      }
      const saved = await res.json();
      setItem(saved);
      setSaved(true);
      if (!item.id) {
        navigate(`/knowledge/${saved.id}`, { replace: true });
      }
    } catch (e: any) {
      setSaveError(e.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Layout>
      <div style={{ display: "flex", height: "calc(100vh - 56px)", overflow: "hidden" }}>

        {/* ── Left: Editor ─────────────────────────────────────── */}
        <div
          style={{
            width: "50%",
            overflowY: "auto",
            padding: 20,
            borderRight: "1px solid #dee2e6",
            background: "#fff",
          }}
        >
          {/* Toolbar */}
          <div className="d-flex align-items-center gap-2 mb-3 flex-wrap">
            <button
              className="btn btn-outline-secondary btn-sm"
              onClick={() => navigate(-1)}
            >
              ← Back
            </button>
            <h5 className="mb-0 flex-grow-1">
              {item.id ? "Edit Knowledge" : "New Knowledge"}
            </h5>
            {!item.id && (
              <button
                className="btn btn-outline-secondary btn-sm"
                onClick={() => setShowImageSection(v => !v)}
              >
                📷 From Image
              </button>
            )}
            {saved && <span className="text-success small">Saved</span>}
            <button
              className="btn btn-primary btn-sm"
              onClick={save}
              disabled={saving}
            >
              {saving ? "Saving…" : "Save"}
            </button>
          </div>

          {/* Image generation section */}
          {showImageSection && (
            <div className="border rounded p-3 mb-3 bg-light">
              <div
                className="border rounded p-3 text-center mb-2"
                style={{
                  borderStyle: "dashed",
                  cursor: "pointer",
                  background: imagePreviewUrl ? "transparent" : "#fff",
                  minHeight: 120,
                }}
                onClick={() => imageInputRef.current?.click()}
                onDragOver={e => e.preventDefault()}
                onDrop={e => {
                  e.preventDefault();
                  const f = e.dataTransfer.files[0];
                  if (f) handleImageFile(f);
                }}
              >
                {imagePreviewUrl ? (
                  <img
                    src={imagePreviewUrl}
                    alt="preview"
                    style={{ maxWidth: "100%", maxHeight: 200, objectFit: "contain" }}
                  />
                ) : (
                  <div className="text-muted small">
                    <div style={{ fontSize: 28, marginBottom: 4 }}>📷</div>
                    Click, drag, or paste (Ctrl+V) an image here
                  </div>
                )}
              </div>
              <input
                ref={imageInputRef}
                type="file"
                accept="image/*"
                style={{ display: "none" }}
                onChange={e => { const f = e.target.files?.[0]; if (f) handleImageFile(f); }}
              />
              <textarea
                className="form-control form-control-sm mb-2"
                rows={2}
                placeholder="Additional instructions (optional)"
                value={imagePrompt}
                onChange={e => setImagePrompt(e.target.value)}
              />
              {generateError && (
                <div className="text-danger small mb-2">{generateError}</div>
              )}
              <button
                className="btn btn-primary btn-sm w-100"
                onClick={generateFromImage}
                disabled={!imageFile || generating}
              >
                {generating ? (
                  <><span className="spinner-border spinner-border-sm me-2" />Generating…</>
                ) : "Generate Knowledge"}
              </button>
            </div>
          )}

          {saveError && (
            <div className="alert alert-danger py-2 small">{saveError}</div>
          )}

          {/* Title */}
          <div className="mb-3">
            <label className="form-label fw-semibold small">Title</label>
            <input
              className="form-control"
              value={item.title}
              onChange={e => update("title", e.target.value)}
              placeholder="e.g. Circumference of a circle"
            />
          </div>

          {/* Text */}
          <div className="mb-3">
            <label className="form-label fw-semibold small">Text</label>
            <textarea
              className="form-control font-monospace"
              rows={5}
              value={item.text}
              onChange={e => update("text", e.target.value)}
              placeholder={"Enter explanation or formula.\nUse $...$ for inline LaTeX, $$...$$ for display."}
              style={{ fontSize: 13 }}
            />
          </div>

          {/* Diagram */}
          <div className="mb-3">
            <label className="form-label fw-semibold small">Diagram</label>
            <textarea
              className="form-control font-monospace"
              rows={3}
              value={item.diagram}
              onChange={e => update("diagram", e.target.value)}
              placeholder="e.g. Circle(radius: 5, label_r: true, label_d: true)"
              style={{ fontSize: 13 }}
            />
            {diagramError && (
              <div className="text-danger small mt-1">{diagramError}</div>
            )}
          </div>

          {/* Text 2 */}
          <div className="mb-3">
            <label className="form-label fw-semibold small">Text 2</label>
            <textarea
              className="form-control font-monospace"
              rows={5}
              value={item.text_2}
              onChange={e => update("text_2", e.target.value)}
              placeholder={"Additional notes, worked example, or formula.\nUse $...$ for inline LaTeX, $$...$$ for display."}
              style={{ fontSize: 13 }}
            />
          </div>
        </div>

        {/* ── Right: Preview ───────────────────────────────────── */}
        <div
          style={{
            width: "50%",
            overflowY: "auto",
            padding: 24,
            background: "#f8f9fa",
          }}
        >
          <div className="text-muted small mb-3 fw-semibold text-uppercase" style={{ letterSpacing: 1 }}>
            Preview
          </div>
          <KnowledgePreview item={item} diagramSvg={diagramSvg} />
        </div>

      </div>
    </Layout>
  );
}
