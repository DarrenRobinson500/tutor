import { useEffect, useState, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import debounce from "lodash.debounce";

import { Layout } from "./components/Layout";
import { EditorPanel } from "./components/EditorPanel";
import { ValuesPanel } from "./components/ValuesPanel";
import { PreviewPanel } from "./components/PreviewPanel";
import { TemplateMetadataBar } from "./components/TemplateMetadataBar";
import type { TemplateMetadata } from "../types/TemplateMetadata";

import { apiFetch } from "../utils/apiFetch";

interface TemplateData {
  id: number | null;
  name: string;
  difficulty: string;
  content: string;
  topic: string;
  subtopic: string;
  grade: string | null;
  skill_detail: number | null;
  skill_id: number | null;
  validated: boolean;
}

interface TrioResponse {
  easy: TemplateData | null;
  medium: TemplateData | null;
  hard: TemplateData | null;
}

interface PreviewResponse {
  question: string;
  answers: any[];
  params: Record<string, any>;
  solution: string;
  diagram_svg: string;
  diagram_code: string;
  substituted_yaml: string;
}

function NotesPanel({ slot, templateId }: { slot: ReturnType<typeof useTemplateSlot>; templateId: number }) {
  return (
    <div className="mt-2 mb-3">
      <div className="d-flex gap-2 align-items-center">
        <label style={{ fontSize: 12, whiteSpace: "nowrap", margin: 0 }}>Note</label>
        <input
          type="text"
          className="form-control form-control-sm"
          placeholder="Add a note…"
          value={slot.noteText}
          onChange={e => slot.setNoteText(e.target.value)}
          onKeyDown={e => { if (e.key === "Enter") slot.addNote(templateId, slot.noteText); }}
          disabled={slot.isAddingNote}
        />
        <button
          className="btn btn-sm btn-outline-secondary"
          onClick={() => slot.addNote(templateId, slot.noteText)}
          disabled={slot.isAddingNote || !slot.noteText.trim()}
          style={{ whiteSpace: "nowrap" }}
        >
          Add Note
        </button>
      </div>
      {slot.notes.length > 0 && (
        <div className="mt-1">
          {slot.notes.map(n => (
            <div key={n.id} className="text-muted border-bottom py-1 d-flex justify-content-between align-items-start" style={{ fontSize: 11 }}>
              <span>{n.text}</span>
              <button
                onClick={() => slot.deleteNote(n.id)}
                style={{ background: "none", border: "none", padding: "0 0 0 6px", cursor: "pointer", color: "#999", fontSize: 13, lineHeight: 1, flexShrink: 0 }}
                title="Delete note"
              >×</button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function useTemplateSlot(initial: TemplateData | null) {
  const [tpl, setTpl] = useState<TemplateData | null>(initial);
  const [content, setContent] = useState(initial?.content ?? "");
  const [preview, setPreview] = useState<PreviewResponse | null>(null);
  const [notes, setNotes] = useState<any[]>([]);
  const [noteText, setNoteText] = useState("");
  const [isAddingNote, setIsAddingNote] = useState(false);

  // Debounced preview
  const debouncedPreview = useRef(
    debounce(async (newContent: string, templateId?: number | null) => {
      const res = await apiFetch("/api/templates/preview/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: newContent, templateId: templateId ?? null, }),
      });
      const data = await res.json();
      setPreview(data.preview);
    }, 400)
  ).current;

  const updateContent = (newContent: string) => {
    setContent(newContent);
    if (tpl?.id) debouncedPreview(newContent, tpl?.id ?? null);
  };

  const loadNotes = async (templateId: number) => {
    const res = await apiFetch(`/api/notes/?template=${templateId}`);
    const data = await res.json();
    setNotes(Array.isArray(data) ? data : (data.results ?? []));
  };

  const addNote = async (templateId: number, text: string) => {
    if (!text.trim()) return;
    setIsAddingNote(true);
    try {
      const res = await apiFetch("/api/notes/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ template: templateId, text: text.trim() }),
      });
      if (res.ok) {
        const note = await res.json();
        setNotes(prev => [note, ...prev]);
        setNoteText("");
      }
    } finally {
      setIsAddingNote(false);
    }
  };

  const deleteNote = async (noteId: number) => {
    await apiFetch(`/api/notes/${noteId}/`, { method: "DELETE" });
    setNotes(prev => prev.filter(n => n.id !== noteId));
  };

  return { tpl, setTpl, content, setContent, preview, setPreview, updateContent, debouncedPreview, notes, noteText, setNoteText, isAddingNote, loadNotes, addNote, deleteNote };
}

export function TemplateGroupEditorPage() {
  const { groupId } = useParams();
  const navigate = useNavigate();

  const easy = useTemplateSlot(null);
  const medium = useTemplateSlot(null);
  const hard = useTemplateSlot(null);

  const [loading, setLoading] = useState(true);
  const [skillDetailName, setSkillDetailName] = useState<string | null>(null);

  // Load trio — defined below as loadGroup(), called here on mount
  useEffect(() => {
    loadGroup();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [groupId]);

function toMetadata(tpl: TemplateData): TemplateMetadata {
  return {
    id: tpl.id,
    name: tpl.name ?? "",
    description: "",          // Trio API does not return this
    subject: "",              // Trio API does not return this
    skill_detail_id: tpl.skill_detail ?? null,
    topic: tpl.topic ?? "",
    subtopic: tpl.subtopic ?? "",
    difficulty: tpl.difficulty ?? "",
    grade: tpl.grade ?? null,
    tags: [],                 // Trio API does not return this
    curriculum: [],           // Trio API does not return this
    status: "draft",          // Trio API does not return this
    version: 1,               // Trio API does not return this
    skill: null,              // Trio API does not return this
    validated: false,         // Trio API does not return this
    validated_filter: "all",  // Trio editor does not filter
    group: null,              // Trio API does not return this
  };
}


  // Validate handler for a single template
  const handleValidate = async (slot: ReturnType<typeof useTemplateSlot>) => {
    if (!slot.tpl?.id) return;
    const res = await apiFetch(`/api/templates/${slot.tpl.id}/toggle_validated/`, {
      method: "POST",
    });
    if (!res.ok) return;
    const data = await res.json();
    slot.setTpl(prev => prev ? { ...prev, validated: data.validated } : prev);
  };

  // Save handler for a single template
  const saveTemplate = async (slot: ReturnType<typeof useTemplateSlot>) => {
    if (!slot.tpl?.id) return;

    const payload = {
      name: slot.tpl.name,
      difficulty: slot.tpl.difficulty,
      topic: slot.tpl.topic,
      subtopic: slot.tpl.subtopic,
      grade: slot.tpl.grade,
      skill_detail: slot.tpl.skill_detail,
      content: slot.content,
    };

    const res = await apiFetch(`/api/templates/${slot.tpl.id}/`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      alert("Failed to save template");
      return;
    }

    const updated = await res.json();
    slot.setTpl(updated);
  };

const loadGroup = async () => {
  setLoading(true);

  const res = await apiFetch(`/api/template_groups/${groupId}/trio/`);
  const data: TrioResponse = await res.json();

  // EASY
  if (data.easy) {
    easy.setTpl(data.easy);
    easy.setContent(data.easy.content);
    easy.setPreview(null);
    easy.debouncedPreview(data.easy.content, data.easy.id);
    if (data.easy.id) easy.loadNotes(data.easy.id);
  } else {
    easy.setTpl(null);
    easy.setContent("");
    easy.setPreview(null);
  }

  // MEDIUM
  if (data.medium) {
    medium.setTpl(data.medium);
    medium.setContent(data.medium.content);
    medium.setPreview(null);
    medium.debouncedPreview(data.medium.content, data.medium.id);
    if (data.medium.id) medium.loadNotes(data.medium.id);
  } else {
    medium.setTpl(null);
    medium.setContent("");
    medium.setPreview(null);
  }

  // HARD
  if (data.hard) {
    hard.setTpl(data.hard);
    hard.setContent(data.hard.content);
    hard.setPreview(null);
    hard.debouncedPreview(data.hard.content, data.hard.id);
    if (data.hard.id) hard.loadNotes(data.hard.id);
  } else {
    hard.setTpl(null);
    hard.setContent("");
    hard.setPreview(null);
  }

  const detailId = data.easy?.skill_detail ?? data.medium?.skill_detail ?? data.hard?.skill_detail;
  if (detailId) {
    apiFetch(`/api/skills/${detailId}/`)
      .then(r => r.json())
      .then(d => setSkillDetailName(d.description ?? null));
  }

  setLoading(false);
};

const skillDetailId =
  easy.tpl?.skill_detail ??
  medium.tpl?.skill_detail ??
  hard.tpl?.skill_detail ??
  null;

const skillId =
  easy.tpl?.skill_id ??
  medium.tpl?.skill_id ??
  hard.tpl?.skill_id ??
  null;


  // Create missing difficulty version
  const createVersion = async (difficulty: "easy" | "medium" | "hard") => {
    const res = await apiFetch(`/api/template_groups/${groupId}/create_${difficulty}/`, {
      method: "POST",
    });

    if (!res.ok) {
      alert("Failed to create template");
      return;
    }

    const data = await res.json();
    await loadGroup();
  };

  if (loading) {
    return (
      <Layout>
        <div className="p-4">Loading templates…</div>
      </Layout>
    );
  }

  return (
    <Layout>
      {skillDetailName && <h3 className="mt-3 mb-0 px-3">{skillDetailName}</h3>}
<div className="d-flex mt-2 mb-2">
  {skillId && (
    <button
      className="btn btn-outline-primary"
      onClick={() => navigate(`/skills/${skillId}/overview`)}
    >
      Skill Overview
    </button>
  )}
</div>



      <div className="container-fluid">

        {/* ============================
            TOP ROW — EDITORS
        ============================= */}
        <div className="row" style={{ minHeight: "60vh" }}>

          {/* EASY */}
          <div className="col-md-4 d-flex flex-column">
            <div className="d-flex align-items-center gap-2 mt-2">
              <h5 className="mb-0">Easy</h5>
              {easy.tpl && (
                <>
                  <button
                    className={`btn btn-sm ${easy.tpl.validated ? "btn-success" : "btn-outline-secondary"}`}
                    onClick={() => handleValidate(easy)}
                  >
                    {easy.tpl.validated ? "Validated ✓" : "Validate"}
                  </button>
                  <button
                    className="btn btn-sm btn-outline-primary"
                    onClick={() => navigate(`/templates/${easy.tpl!.id}`)}
                  >
                    Open in Editor
                  </button>
                </>
              )}
            </div>
            {easy.tpl ? (
              <>

                <EditorPanel
                  content={easy.content}
                  onChange={easy.updateContent}
                  validation={null}
                  templateId={easy.tpl.id}
                />
              </>
            ) : (
              <button
                className="btn btn-outline-primary mt-3"
                onClick={() => createVersion("easy")}
              >
                Create Easy Version
              </button>
            )}
          </div>

          {/* MEDIUM */}
          <div className="col-md-4 d-flex flex-column">
            <div className="d-flex align-items-center gap-2 mt-2">
              <h5 className="mb-0">Medium</h5>
              {medium.tpl && (
                <>
                  <button
                    className={`btn btn-sm ${medium.tpl.validated ? "btn-success" : "btn-outline-secondary"}`}
                    onClick={() => handleValidate(medium)}
                  >
                    {medium.tpl.validated ? "Validated ✓" : "Validate"}
                  </button>
                  <button
                    className="btn btn-sm btn-outline-primary"
                    onClick={() => navigate(`/templates/${medium.tpl!.id}`)}
                  >
                    Open in Editor
                  </button>
                </>
              )}
            </div>
            {medium.tpl ? (
              <>

                <EditorPanel
                  content={medium.content}
                  onChange={medium.updateContent}
                  validation={null}
                  templateId={medium.tpl.id}
                />
              </>
            ) : (
              <button
                className="btn btn-outline-primary mt-3"
                onClick={() => createVersion("medium")}
              >
                Create Medium Version
              </button>
            )}
          </div>

          {/* HARD */}
          <div className="col-md-4 d-flex flex-column">
            <div className="d-flex align-items-center gap-2 mt-2">
              <h5 className="mb-0">Hard</h5>
              {hard.tpl && (
                <>
                  <button
                    className={`btn btn-sm ${hard.tpl.validated ? "btn-success" : "btn-outline-secondary"}`}
                    onClick={() => handleValidate(hard)}
                  >
                    {hard.tpl.validated ? "Validated ✓" : "Validate"}
                  </button>
                  <button
                    className="btn btn-sm btn-outline-primary"
                    onClick={() => navigate(`/templates/${hard.tpl!.id}`)}
                  >
                    Open in Editor
                  </button>
                </>
              )}
            </div>
            {hard.tpl ? (
              <>
                <EditorPanel
                  content={hard.content}
                  onChange={hard.updateContent}
                  validation={null}
                  templateId={hard.tpl.id}
                />
              </>
            ) : (
              <button
                className="btn btn-outline-primary mt-3"
                onClick={() => createVersion("hard")}
              >
                Create Hard Version
              </button>
            )}
          </div>

        </div>

        {/* ============================
            BOTTOM ROW — PREVIEWS
        ============================= */}
        <div className="row mt-4">

          {/* EASY PREVIEW */}
          <div className="col-md-4">
            <h6>Preview (Easy)</h6>
<PreviewPanel
  preview={easy.preview}
  templateContent={easy.content}
  mode="editor"
  onEditorNext={(newPreview) => easy.setPreview(newPreview)}
/>
            {easy.tpl?.id && <NotesPanel slot={easy} templateId={easy.tpl.id} />}
            <h6>Values</h6>
            <ValuesPanel
              substitutedYaml={easy.preview?.substituted_yaml ?? null}
              diagramCode={easy.preview?.diagram_code ?? null}
              backendSvg={easy.preview?.diagram_svg ?? null}
            />
          </div>

          {/* MEDIUM PREVIEW */}
          <div className="col-md-4">
            <h6>Preview (Medium)</h6>
<PreviewPanel
  preview={medium.preview}
  templateContent={medium.content}
  mode="editor"
  onEditorNext={(newPreview) => medium.setPreview(newPreview)}
/>
            {medium.tpl?.id && <NotesPanel slot={medium} templateId={medium.tpl.id} />}
            <h6>Values</h6>
            <ValuesPanel
              substitutedYaml={medium.preview?.substituted_yaml ?? null}
              diagramCode={medium.preview?.diagram_code ?? null}
              backendSvg={medium.preview?.diagram_svg ?? null}
            />
          </div>

          {/* HARD PREVIEW */}
          <div className="col-md-4">
            <h6>Preview (Hard)</h6>
<PreviewPanel
  preview={hard.preview}
  templateContent={hard.content}
  mode="editor"
  onEditorNext={(newPreview) => hard.setPreview(newPreview)}
/>
            {hard.tpl?.id && <NotesPanel slot={hard} templateId={hard.tpl.id} />}
            <h6>Values</h6>
            <ValuesPanel
              substitutedYaml={hard.preview?.substituted_yaml ?? null}
              diagramCode={hard.preview?.diagram_code ?? null}
              backendSvg={hard.preview?.diagram_svg ?? null}
            />
          </div>

        </div>
      </div>
    </Layout>
  );
}