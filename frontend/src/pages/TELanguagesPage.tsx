import { useEffect, useState, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import debounce from "lodash.debounce";

import { Layout } from "./components/Layout";
import { EditorPanel } from "./components/EditorPanel";
import { PreviewPanel } from "./components/PreviewPanel";
import { apiFetch } from "../utils/apiFetch";

interface PreviewResponse {
  question: string;
  answers: any[];
  params: Record<string, any>;
  solution: string;
  diagram_svg: string;
  diagram_code: string;
  substituted_yaml: string;
}

const LANGUAGES: { code: string; label: string }[] = [
  { code: "zh", label: "Chinese (Simplified)" },
  { code: "ar", label: "Arabic" },
  { code: "vi", label: "Vietnamese" },
  { code: "ko", label: "Korean" },
  { code: "hi", label: "Hindi" },
  { code: "es", label: "Spanish" },
  { code: "fr", label: "French" },
  { code: "it", label: "Italian" },
  { code: "pt", label: "Portuguese" },
];

function useLanguageSlot() {
  const [templateId, setTemplateId] = useState<number | null>(null);
  const [language, setLanguage] = useState<string>("");
  const [content, setContent] = useState<string>("");
  const [preview, setPreview] = useState<PreviewResponse | null>(null);
  const [loading, setLoading] = useState(false);

  const debouncedPreview = useRef(
    debounce(async (c: string, tplId?: number | null) => {
      const res = await apiFetch("/api/templates/preview/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: c, templateId: tplId ?? null }),
      });
      const data = await res.json();
      setPreview(data.preview ?? null);
    }, 400)
  ).current;

  const updateContent = (c: string) => {
    setContent(c);
    debouncedPreview(c, templateId);
  };

  return { templateId, setTemplateId, language, setLanguage, content, setContent, preview, setPreview, loading, setLoading, updateContent, debouncedPreview };
}

function LanguagePanel({
  slot,
  sourceId,
  otherLanguage,
  panelLabel,
}: {
  slot: ReturnType<typeof useLanguageSlot>;
  sourceId: number;
  otherLanguage: string;
  panelLabel: string;
}) {
  const navigate = useNavigate();

  async function handleLanguageSelect(lang: string) {
    if (!lang) {
      slot.setLanguage("");
      slot.setContent("");
      slot.setPreview(null);
      slot.setTemplateId(null);
      return;
    }
    slot.setLanguage(lang);
    slot.setLoading(true);
    try {
      const res = await apiFetch(`/api/templates/${sourceId}/get_translation/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ language: lang }),
      });
      const data = await res.json();
      if (!res.ok) { alert(data.error ?? "Translation failed"); return; }
      slot.setTemplateId(data.id);
      slot.setContent(data.content);
      slot.debouncedPreview(data.content, data.id);
    } finally {
      slot.setLoading(false);
    }
  }

  return (
    <div className="col-md-4 d-flex flex-column">
      <div className="d-flex align-items-center gap-2 mt-2 mb-2">
        <h5 className="mb-0">{panelLabel}</h5>
        <select
          className="form-select form-select-sm"
          style={{ width: "auto", minWidth: 180 }}
          value={slot.language}
          onChange={e => handleLanguageSelect(e.target.value)}
        >
          <option value="">Select language…</option>
          {LANGUAGES.filter(l => l.code !== otherLanguage).map(l => (
            <option key={l.code} value={l.code}>{l.label}</option>
          ))}
        </select>
        {slot.loading && <span className="text-muted" style={{ fontSize: 12 }}>Translating…</span>}
        {slot.templateId && (
          <button
            className="btn btn-sm btn-outline-primary"
            onClick={() => navigate(`/templates/${slot.templateId}`)}
          >
            Open in Editor
          </button>
        )}
      </div>

      {slot.content ? (
        <>
          <div style={{ height: 450, overflow: "hidden", flexShrink: 0 }}>
            <EditorPanel
              content={slot.content}
              onChange={slot.updateContent}
              validation={null}
              templateId={slot.templateId}
            />
          </div>
          <div className="mt-3">
            <h6>Preview</h6>
            <PreviewPanel
              preview={slot.preview}
              templateContent={slot.content}
              mode="editor"
              onEditorNext={p => slot.setPreview(p)}
            />
          </div>
        </>
      ) : (
        <div className="text-muted mt-4" style={{ fontSize: 13 }}>
          Select a language above to load the translation.
        </div>
      )}
    </div>
  );
}

export function TELanguagesPage() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [sourceId, setSourceId] = useState<number | null>(null);
  const [sourceContent, setSourceContent] = useState("");
  const [sourcePreview, setSourcePreview] = useState<PreviewResponse | null>(null);
  const [loading, setLoading] = useState(true);

  const debouncedSourcePreview = useRef(
    debounce(async (c: string, tplId?: number | null) => {
      const res = await apiFetch("/api/templates/preview/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: c, templateId: tplId ?? null }),
      });
      const data = await res.json();
      setSourcePreview(data.preview ?? null);
    }, 400)
  ).current;

  const slotA = useLanguageSlot();
  const slotB = useLanguageSlot();

  useEffect(() => {
    if (!id) return;
    apiFetch(`/api/templates/${id}/language_info/`)
      .then(r => r.json())
      .then(data => {
        setSourceId(data.source_id);
        setSourceContent(data.source_content ?? "");
        debouncedSourcePreview(data.source_content ?? "", data.source_id);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  if (loading) {
    return <Layout><div className="p-4">Loading…</div></Layout>;
  }

  return (
    <Layout>
      <div className="d-flex align-items-center gap-3 mt-3 mb-1 px-3">
        <h4 className="mb-0">Languages</h4>
        <button
          className="btn btn-sm btn-outline-secondary"
          onClick={() => navigate(`/templates/${id}`)}
        >
          ← Back to Editor
        </button>
      </div>

      <div className="container-fluid">
        <div className="row" style={{ minHeight: "60vh" }}>

          {/* Panel 1 — English (source) */}
          <div className="col-md-4 d-flex flex-column">
            <div className="d-flex align-items-center gap-2 mt-2 mb-2">
              <h5 className="mb-0">English</h5>
              {sourceId && (
                <button
                  className="btn btn-sm btn-outline-primary"
                  onClick={() => navigate(`/templates/${sourceId}`)}
                >
                  Open in Editor
                </button>
              )}
            </div>
            <div style={{ height: 450, overflow: "hidden", flexShrink: 0 }}>
              <EditorPanel
                content={sourceContent}
                onChange={c => { setSourceContent(c); debouncedSourcePreview(c, sourceId); }}
                validation={null}
                templateId={sourceId}
              />
            </div>
            <div className="mt-3">
              <h6>Preview</h6>
              <PreviewPanel
                preview={sourcePreview}
                templateContent={sourceContent}
                mode="editor"
                onEditorNext={p => setSourcePreview(p)}
              />
            </div>
          </div>

          {/* Panel 2 — Language A */}
          {sourceId && (
            <LanguagePanel
              slot={slotA}
              sourceId={sourceId}
              otherLanguage={slotB.language}
              panelLabel="Translation 1"
            />
          )}

          {/* Panel 3 — Language B */}
          {sourceId && (
            <LanguagePanel
              slot={slotB}
              sourceId={sourceId}
              otherLanguage={slotA.language}
              panelLabel="Translation 2"
            />
          )}

        </div>
      </div>
    </Layout>
  );
}
