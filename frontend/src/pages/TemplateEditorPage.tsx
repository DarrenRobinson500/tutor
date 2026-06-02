import debounce from "lodash.debounce";
import Editor from "@monaco-editor/react";

import { useEffect, useState, useRef } from "react";
import { useParams, useNavigate, useSearchParams, useLocation } from "react-router-dom";
import { TemplateMetadataBar } from "./components/TemplateMetadataBar";
import { SectionedEditorPanel } from "./components/SectionedEditorPanel";
import { ValuesPanel } from "./components/ValuesPanel";
import { PreviewPanel } from "./components/PreviewPanel";
import { DraggableCalculator } from "./components/Calculator";
import { Layout } from "./components/Layout";
import { apiFetch } from "../utils/apiFetch"
import { usePreferenceStore } from "../utils/pref";

import { useTemplateApi } from "../api/useTemplateApi";
// import { useValidationApi } from "../api/useValidationApi";
import type { TemplateMetadata } from "../types/TemplateMetadata";
import { ParameterHelper } from "./components/ParameterHelper";
import { DiagramHelper } from "./components/DiagramHelper";
import { KnowledgeHelper } from "./components/KnowledgeHelper";

interface PreviewResponse {
  question: string;
  answers: any[];
  params: Record<string, any>;
  solution: string;
  diagram_svg: string;
  diagram_code: string;
  substituted_yaml: string;
}

const DIFFICULTY_ORDER: Record<string, number> = { easy: 1, medium: 2, hard: 3 };

function sortTemplates(list: any[], mode: "difficulty" | "skill_detail"): any[] {
  return [...list].sort((a, b) => {
    const diffA = DIFFICULTY_ORDER[a.difficulty] ?? 99;
    const diffB = DIFFICULTY_ORDER[b.difficulty] ?? 99;
    const skillA = (a.skill_detail ?? "").toLowerCase();
    const skillB = (b.skill_detail ?? "").toLowerCase();
    if (mode === "difficulty") {
      return diffA !== diffB ? diffA - diffB : skillA.localeCompare(skillB);
    }
    const s = skillA.localeCompare(skillB);
    return s !== 0 ? s : diffA - diffB;
  });
}

export function TemplateEditorPage() {
  const [filteredList, setFilteredList] = useState<any[]>([]);
  const [currentIndex, setCurrentIndex] = useState<number>(0);
  const [skills, setSkills] = useState<any[]>([]);
  const [sortMode, setSortMode] = useState<"difficulty" | "skill_detail">("difficulty");
  const sortModeRef = useRef<"difficulty" | "skill_detail">("difficulty");
  sortModeRef.current = sortMode;
  const savedValidatedFilter = usePreferenceStore((s) =>
    s.get("template.validated_filter")
  );
  const savedLanguageFilter = usePreferenceStore((s) =>
    s.get("template.language_filter")
  );

  const emptyMetadata = {
    id: null,
    name: "",
    description: "",
    subject: "",
    skill_detail_id: null,
    topic: "",
    subtopic: "",
    difficulty: "",
    grade: "",
    tags: [],
    curriculum: [],
    status: "draft",
    version: 1,
    skill: null,
    validated: false,
    validated_filter: savedValidatedFilter ?? "all",
    language_filter: savedLanguageFilter ?? "en",
  };


  const navigate = useNavigate();
  const location = useLocation();
  const params = useParams();
  const { id } = params;
  const [searchParams] = useSearchParams();
  const [metadata, setMetadata] = useState<TemplateMetadata>(emptyMetadata);
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [content, setContent] = useState<string>("");
  const [validationResult] = useState<any>(null);

  const [previewResult, setPreviewResult] = useState<any>(null);
  const [preview, setPreview] = useState<PreviewResponse | null>(null);
  const rawMode = true;
  const [showCalculator, setShowCalculator] = useState(false);
  const [showParamHelper,    setShowParamHelper]    = useState(false);
  const [showDiagramHelper,  setShowDiagramHelper]  = useState(false);
  const [showKnowledgeHelper, setShowKnowledgeHelper] = useState(false);
  const [aiPrompt, setAiPrompt] = useState("");
  const [isAiUpdating, setIsAiUpdating] = useState(false);
  const [noteText, setNoteText] = useState("");
  const [notes, setNotes] = useState<any[]>([]);
  const [isAddingNote, setIsAddingNote] = useState(false);
  const { getTemplate, saveTemplate } = useTemplateApi();
  const [templateLanguage, setTemplateLanguage] = useState<string>('en');
  const [parentTemplateId, setParentTemplateId] = useState<number | null>(null);
  const [templateTranslations, setTemplateTranslations] = useState<{ id: number; language: string }[]>([]);

function buildMetadataFromTemplate(
  tpl: any,
  currentFilter: "all" | "validated" | "unvalidated"
): TemplateMetadata {
  return {
    id: tpl.id ?? null,
    name: tpl.name ?? "",
    description: tpl.description ?? "",
    subject: tpl.skill_detail_description ?? "",
    skill_detail_id: tpl.skill_detail ?? null,
    topic: tpl.topic ?? "",
    subtopic: tpl.subtopic ?? "",
    difficulty: tpl.difficulty ?? "",
    grade: tpl.grade ?? null,
    tags: tpl.tags ?? [],
    curriculum: tpl.curriculum ?? [],
    status: tpl.status ?? "draft",
    version: tpl.version ?? 1,
    skill: tpl.skill_id ?? null,
    validated: tpl.validated ?? false,
    validated_filter: currentFilter,
    group: tpl.group ?? null,
  };
}


const handleToggleValidated = async () => {
  if (!metadata.id) return;

  const res = await apiFetch(`/api/templates/${metadata.id}/toggle_validated/`, {
    method: "POST",
  });

  if (!res.ok) {
    alert("Failed to toggle validation");
    return;
  }

  const data = await res.json();
  const currentId = metadata.id;
  const saved = usePreferenceStore.getState().get("template.validated_filter");

  const removedFromFilter =
    (saved === "unvalidated" && data.validated) ||
    (saved === "validated" && !data.validated);

  if (removedFromFilter) {
    const remaining = filteredList.filter(t => t.id !== currentId);
    setFilteredList(remaining);

    if (remaining.length > 0) {
      setCurrentIndex(0);
      navigate(`/templates/${remaining[0].id}`);
    } else {
      setCurrentIndex(0);
      setMetadata(prev => ({ ...prev, id: null, validated: data.validated }));
      setContent("");
      setPreview(null);
      navigate("/templates/editor");
    }
  } else {
    setMetadata(prev => ({ ...prev, validated: data.validated }));
  }
};

  const rawAutosaveRef = useRef<number | null>(null);

  // Debounced function
  const debouncedPreview = useRef(
    debounce(async (content: string, templateId?: number | null) => {
      const res = await apiFetch("/api/templates/preview/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content, templateId: templateId ?? null }),
      });

      const data = await res.json();
//       console.log("Preview response:", data.preview);
//       console.log("Sending content to preview:", content);

      // ⭐ Only update the preview — do NOT modify metadata
      setPreview(data.preview);

    }, 400)
  ).current;

  // Load
  useEffect(() => {
    if (savedValidatedFilter) {
      setMetadata((prev) => ({
        ...prev,
        validated_filter: savedValidatedFilter
      }));
    }
  }, [savedValidatedFilter]);


  useEffect(() => {
    async function load() {
      if (!id) return;

      const tpl = await getTemplate(id);
      if (!tpl) return;

      setContent(tpl.content);
      setTemplateLanguage(tpl.language || 'en');
      setParentTemplateId(tpl.parent_template || null);
      setTemplateTranslations(tpl.translations ?? []);
      const currentFilter = usePreferenceStore.getState().get("template.validated_filter") ?? "all";
      setMetadata(prev =>
        buildMetadataFromTemplate(tpl, prev.validated_filter ?? currentFilter)
      );

      // Load the filtered list so navigation works without needing a filter change
      const currentLanguage = usePreferenceStore.getState().get("template.language_filter") ?? "en";
      const queryParams = new URLSearchParams({
        skill: String(tpl.skill_id ?? ""),
        grade: String(tpl.grade ?? ""),
        validated: currentFilter,
        language: currentLanguage,
      });
      const listRes = await apiFetch(`/api/templates/filtered/?${queryParams.toString()}`);
      const list = await listRes.json();
      const sorted = sortTemplates(list, sortModeRef.current);
      setFilteredList(sorted);
      const idx = sorted.findIndex((t: any) => t.id === tpl.id);
      setCurrentIndex(idx >= 0 ? idx : 0);

      const res = await apiFetch("/api/templates/preview/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: tpl.content, templateId: tpl.id }),
      });

      const data = await res.json();
      setPreview(data.preview);
    }
    load();
  }, [id, location.key]);

  // When arriving on /templates/editor with ?skill=&grade= (e.g. after a delete), apply filters
  useEffect(() => {
    if (id) return; // only applies to the bare editor route
    const skillParam = searchParams.get("skill");
    const gradeParam = searchParams.get("grade");
    if (!skillParam && !gradeParam) return;

    const skill = skillParam ? Number(skillParam) : null;
    const grade = gradeParam ?? "";
    const currentFilter = usePreferenceStore.getState().get("template.validated_filter") ?? "all";

    setMetadata(prev => ({ ...prev, skill, grade, validated_filter: currentFilter }));

    async function loadFiltered() {
      const currentLanguage = usePreferenceStore.getState().get("template.language_filter") ?? "en";
      const qp = new URLSearchParams({
        skill: skillParam ?? "",
        grade: gradeParam ?? "",
        validated: currentFilter,
        language: currentLanguage,
      });
      const listRes = await apiFetch(`/api/templates/filtered/?${qp.toString()}`);
      const list = await listRes.json();
      const sorted = sortTemplates(list, sortModeRef.current);
      setFilteredList(sorted);
      setCurrentIndex(0);
      if (sorted.length > 0) {
        navigate(`/templates/${sorted[0].id}`, { replace: true });
      }
    }
    loadFiltered();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Load Skills, Subjects
  useEffect(() => {
    async function loadSkills() {
      const grade = metadata.grade ?? "";
      const res = await apiFetch(`/api/skills/leaf/?grade=${grade}`);
      const data = await res.json();
      setSkills(data);
    }
    loadSkills();
  }, [metadata.grade]);


  // Handle Content Change
  function handleContentChange(newContent: string) {
    setContent(newContent);
    debouncedPreview(newContent, metadata.id);
  }

  // Handle going to skill
  const handleToSkill = () => {
    if (metadata.skill) {
      navigate(`/skills/${metadata.skill}`);
    }
  };

  // Handler - Save
  const handleSave = async () => {
    console.log("Save button clicked (TemplateEditorPage) — metadata:", metadata);

  // Build a clean payload that matches the Django Template model
  const payload = {
    name: metadata.name || "",
    description: metadata.description || "",
    topic: metadata.topic || "",
    subtopic: metadata.subtopic || "",
    difficulty: metadata.difficulty || "",
    grade: metadata.grade || null,
    tags: metadata.tags || [],
    curriculum: metadata.curriculum || [],
    skill_detail: metadata.skill_detail_id || null,
    content
  };

  // CREATE
  if (!metadata.id) {
    console.log("Creating new template with payload:", payload);

    const res = await apiFetch("/api/templates/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const errorText = await res.text();
      console.error("Template CREATE failed:", errorText);
      alert("Template creation failed. Check console for details.");
      return;
    }

    const data = await res.json();
    console.log("Template created:", data);

    // Store the new ID
    setMetadata(prev => ({ ...prev, id: data.id }));

    // Navigate to the new template page
    navigate(`/templates/${data.id}`);
    return;
  }

  // UPDATE
  console.log("Updating existing template:", metadata.id);

  const res = await apiFetch(`/api/templates/${metadata.id}/`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  // No data yet
  if (!res.ok) {
    const errorText = await res.text();
    console.error("Template UPDATE failed:", errorText);
    alert("Template update failed. Check console for details.");
    return;
  }

  const data = await res.json();
  console.log("Template updated:", data);

  // Update metadata (in case backend modifies anything)
  setMetadata(prev => ({ ...prev, ...data }));
};

  // Delete
  const handleDelete = async () => {
    if (!metadata.id) return;

    const confirmed = window.confirm("Are you sure you want to delete this template?");
    if (!confirmed) return;

    const res = await apiFetch(`/api/templates/${metadata.id}/`, {
      method: "DELETE",
    });

    if (!res.ok) {
      alert("Failed to delete template");
      return;
    }

    // Remove deleted template from the local list
    const remaining = filteredList.filter(t => t.id !== metadata.id);

    if (remaining.length > 0) {
      setFilteredList(remaining);
      setCurrentIndex(0);
      navigate(`/templates/${remaining[0].id}`);
    } else {
      // filteredList may be empty (user navigated directly by URL without applying filters).
      // Fetch from the API to find any other template with the same filters.
      const queryParams = new URLSearchParams({
        skill: String(metadata.skill ?? ""),
        grade: String(metadata.grade ?? ""),
        validated: metadata.validated_filter ?? "all",
        language: metadata.language_filter ?? "en",
      });
      const listRes = await apiFetch(`/api/templates/filtered/?${queryParams.toString()}`);
      const list = await listRes.json();
      const others = list.filter((t: any) => t.id !== metadata.id);

      if (others.length > 0) {
        setFilteredList(others);
        setCurrentIndex(0);
        navigate(`/templates/${others[0].id}`);
      } else {
        navigate(`/skills`);
      }
    }
  };



  const handlePreview = async () => {
    setPreviewResult({
      text: "This is a preview of your template.\n\nMore features coming soon."
    });
  };

  const handleAiUpdate = async (pro = false) => {
    if (!aiPrompt.trim()) return;
    setIsAiUpdating(true);
    try {
      const res = await apiFetch("/api/templates/update_with_ai/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content, instruction: aiPrompt, pro }),
      });
      const data = await res.json();
      if (!res.ok) {
        alert(data.error ?? "AI update failed");
        return;
      }
      handleContentChange(data.content);
      setAiPrompt("");
    } catch (e) {
      alert("AI update failed");
    } finally {
      setIsAiUpdating(false);
    }
  };

  const handleCopy = async () => {
    if (!metadata.id) return;
    const res = await apiFetch(`/api/templates/${metadata.id}/duplicate/`, { method: "POST" });
    if (!res.ok) {
      alert("Failed to duplicate template");
      return;
    }
    const data = await res.json();
    navigate(`/templates/${data.id}`);
  };

  const handleCopyHarder = async () => {
    if (!metadata.id) return;
    const NEXT: Record<string, string> = { easy: "medium", medium: "hard" };
    if (!NEXT[metadata.difficulty]) {
      alert("This template is already at Hard difficulty.");
      return;
    }
    const res = await apiFetch(`/api/templates/${metadata.id}/duplicate_harder/`, { method: "POST" });
    if (!res.ok) {
      alert("Failed to create harder version");
      return;
    }
    const data = await res.json();
    navigate(`/templates/${data.id}`);
  };

      const handleShowLanguages = () => {
        if (!metadata.id) return;
        navigate(`/templates/${metadata.id}/languages`);
      };

      const handleShowRelated = async () => {
        if (!metadata.id) return;

        // Case 1: Template already belongs to a group
        if (metadata.group) {
          navigate(`/templates/group/${metadata.group}`);
          return;
        }

        // Case 2: No group — create one and attach this template
        const res = await apiFetch(`/api/templates/${metadata.id}/create_group/`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
        });

        if (!res.ok) {
          alert("Failed to create related group");
          return;
        }

        const data = await res.json();

        // Update metadata so the page knows the template now has a group
        setMetadata(prev => ({ ...prev, group: data.group_id }));

        // Navigate to the multi-difficulty editor
        navigate(`/templates/group/${data.group_id}`);
      };

  const handleMetadataChange = async (updated: Partial<TemplateMetadata>) => {
    const newMeta = { ...metadata, ...updated };
    setMetadata(newMeta);

    if (updated.validated_filter) {
      usePreferenceStore.getState().set(
        "template.validated_filter",
        updated.validated_filter
      );
    }
    if (updated.language_filter) {
      usePreferenceStore.getState().set(
        "template.language_filter",
        updated.language_filter
      );
    }

    // If any of the filters change, reload the list
    const isFilterChange = "skill" in updated || "grade" in updated || "validated_filter" in updated || "language_filter" in updated;
    if (isFilterChange) {
      const params = new URLSearchParams();
      if (newMeta.skill) params.set("skill", String(newMeta.skill));
      if (newMeta.grade) params.set("grade", String(newMeta.grade));
      params.set("validated", newMeta.validated_filter ?? "all");
      if (newMeta.language_filter && newMeta.language_filter !== "all") params.set("language", newMeta.language_filter);

      if (updated.grade) {
        const res = await apiFetch(`/api/skills/leaf/?grade=${updated.grade}`);
        const data = await res.json();
        setSkills(data);
      }

      const res = await apiFetch(`/api/templates/filtered/?${params.toString()}`);
      const list = await res.json();
      const sorted = sortTemplates(list, sortModeRef.current);

      setFilteredList(sorted);
      setCurrentIndex(0);

      if (sorted.length > 0) {
        navigate(`/templates/${sorted[0].id}`);
      }
    }
  };

  const handleToggleSort = () => {
    const newMode = sortMode === "difficulty" ? "skill_detail" : "difficulty";
    setSortMode(newMode);
    sortModeRef.current = newMode;
    const sorted = sortTemplates(filteredList, newMode);
    setFilteredList(sorted);
    if (metadata.id) {
      const idx = sorted.findIndex((t: any) => t.id === metadata.id);
      setCurrentIndex(idx >= 0 ? idx : 0);
    }
  };

  const goNext = () => {
    if (currentIndex < filteredList.length - 1) {
      const nextIndex = currentIndex + 1;
      setCurrentIndex(nextIndex);
      navigate(`/templates/${filteredList[nextIndex].id}`);
    }
  };

  const goPrev = () => {
    if (currentIndex > 0) {
      const prevIndex = currentIndex - 1;
      setCurrentIndex(prevIndex);
      navigate(`/templates/${filteredList[prevIndex].id}`);
    }
  };

//   useEffect(() => {
//     console.log("FULL PREVIEW OBJECT:", preview);
//   }, [preview]);

  useEffect(() => {
    if (!metadata.id) { setNotes([]); return; }
    apiFetch(`/api/notes/?template=${metadata.id}`)
      .then(r => r.json())
      .then(data => setNotes(Array.isArray(data) ? data : (data.results ?? [])))
      .catch(() => {});
  }, [metadata.id]);

  const handleDeleteNote = async (noteId: number) => {
    await apiFetch(`/api/notes/${noteId}/`, { method: "DELETE" });
    setNotes(prev => prev.filter(n => n.id !== noteId));
  };

  const handleAddNote = async () => {
    if (!noteText.trim() || !metadata.id) return;
    setIsAddingNote(true);
    try {
      const res = await apiFetch("/api/notes/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ template: metadata.id, text: noteText.trim() }),
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




  // ── Raw editor helper handlers ───────────────────────────────────────────
  // These mirror SectionedEditorPanel's handlers but operate on the raw YAML string.

  function findTopLevelSection(lines: string[], key: string): { start: number; end: number } | null {
    let start = -1;
    let end = lines.length;
    for (let i = 0; i < lines.length; i++) {
      const m = lines[i].match(/^([a-zA-Z_][a-zA-Z0-9_]*)\s*:/);
      if (m && !lines[i].startsWith(" ") && !lines[i].startsWith("\t")) {
        if (m[1] === key) { start = i; }
        else if (start !== -1) { end = i; break; }
      }
    }
    return start === -1 ? null : { start, end };
  }

  function lastNonEmptyIdx(lines: string[], from: number, to: number): number {
    let idx = to - 1;
    while (idx > from && lines[idx].trim() === "") idx--;
    return idx;
  }

  const handleRawInsertParameter = (yaml: string) => {
    // yaml is already 2-space indented (e.g., "  n:\n    size: small")
    const lines = content.split("\n");
    const sec = findTopLevelSection(lines, "parameters");
    let newContent: string;
    if (!sec) {
      newContent = "parameters:\n" + yaml + "\n\n" + content;
    } else {
      const last = lastNonEmptyIdx(lines, sec.start, sec.end);
      const newLines = [...lines.slice(0, last + 1), ...yaml.split("\n"), ...lines.slice(last + 1)];
      newContent = newLines.join("\n");
    }
    handleContentChange(newContent);
  };

  const handleRawAddPart = () => {
    const newPart = `  - text: ""\n    answer: ""\n    solution: ""`;
    const lines = content.split("\n");
    const sec = findTopLevelSection(lines, "question");
    if (!sec) {
      handleContentChange(content.trimEnd() + "\nquestion:\n  parts:\n" + newPart + "\n");
      return;
    }
    const qLines = lines.slice(sec.start, sec.end);
    const partsIdx = qLines.findIndex(l => /^\s*parts\s*:/.test(l));
    let newLines: string[];
    if (partsIdx === -1) {
      const last = lastNonEmptyIdx(lines, sec.start, sec.end);
      newLines = [...lines.slice(0, last + 1), "  parts:", ...newPart.split("\n"), ...lines.slice(last + 1)];
    } else {
      let lastPart = sec.start + partsIdx;
      for (let i = sec.start + partsIdx + 1; i < sec.end; i++) {
        if (lines[i].startsWith("  ") || lines[i].trim() === "") lastPart = i;
        else break;
      }
      while (lastPart > sec.start + partsIdx && lines[lastPart].trim() === "") lastPart--;
      newLines = [...lines.slice(0, lastPart + 1), ...newPart.split("\n"), ...lines.slice(lastPart + 1)];
    }
    handleContentChange(newLines.join("\n"));
  };

  const handleRawInsertDiagram = (yaml: string) => {
    // yaml is full "diagram: ..." YAML string
    const lines = content.split("\n");
    const sec = findTopLevelSection(lines, "diagram");
    const yamlLines = yaml.trimEnd().split("\n");
    let newLines: string[];
    if (!sec) {
      const answersSec = findTopLevelSection(lines, "answers") ?? findTopLevelSection(lines, "answer");
      if (answersSec) {
        newLines = [...lines.slice(0, answersSec.start), ...yamlLines, "", ...lines.slice(answersSec.start)];
      } else {
        newLines = [...lines, "", ...yamlLines];
      }
    } else {
      newLines = [...lines.slice(0, sec.start), ...yamlLines, ...lines.slice(sec.end)];
    }
    handleContentChange(newLines.join("\n"));
    setShowDiagramHelper(false);
  };

  const handleRawInsertKnowledge = (snippet: string) => {
    // snippet is e.g. '{{ Knowledge("title") }}'
    const lines = content.split("\n");
    const sec = findTopLevelSection(lines, "post_answer");
    let newContent: string;
    if (!sec) {
      newContent = content.trimEnd() + "\n\npost_answer: " + JSON.stringify(snippet) + "\n";
    } else {
      const last = lastNonEmptyIdx(lines, sec.start, sec.end);
      const newLines = [...lines.slice(0, last + 1), "  " + snippet, ...lines.slice(last + 1)];
      newContent = newLines.join("\n");
    }
    handleContentChange(newContent);
  };

  return (
<Layout>
  <div className="template-editor-page">

    {/* Metadata */}
    <TemplateMetadataBar
      metadata={metadata}
      onChange={handleMetadataChange}
      onSave={handleSave}
      onDelete={handleDelete}
      onCopy={handleCopy}
      onCopyHarder={handleCopyHarder}
      onValidate={handleToggleValidated}
      onPreview={handlePreview}
      onToSkill={handleToSkill}
      isSaving={isSaving}
      saveError={saveError}
      saveSuccess={saveSuccess}
      onNext={goNext}
      onPrev={goPrev}
      sortMode={sortMode}
      onToggleSort={handleToggleSort}
      skills={skills}
      currentIndex={currentIndex}
      listLength={filteredList.length}
      onShowRelated={handleShowRelated}
      onShowLanguages={handleShowLanguages}
    />

    <div className="container-fluid">
      <div className="row" style={{ minHeight: "70vh" }}>

        {/* Panel 1: Editor (Template source) */}
        <div className={`${rawMode ? "col-md-4" : "col-md-6"} d-flex flex-column`}>
          <div className="card shadow-sm flex-grow-1 d-flex flex-column">
            <div className="card-header d-flex justify-content-between align-items-start gap-1 flex-wrap">
              <div className="d-flex align-items-center gap-2">
                <span>Question</span>
                {templateLanguage && templateLanguage !== 'en' && parentTemplateId && (
                  <button
                    className="btn btn-sm btn-outline-warning"
                    style={{ fontSize: 11 }}
                    onClick={() => navigate(`/templates/${parentTemplateId}`)}
                    title="Go to English version"
                  >
                    {templateLanguage.toUpperCase()} — View English version
                  </button>
                )}
                {templateLanguage === 'en' && templateTranslations.map(t => (
                  <button
                    key={t.id}
                    className="btn btn-sm btn-outline-info"
                    style={{ fontSize: 11 }}
                    onClick={() => navigate(`/templates/${t.id}`)}
                    title={`View ${t.language.toUpperCase()} translation`}
                  >
                    {t.language.toUpperCase()}
                  </button>
                ))}
              </div>
              <div className="d-flex gap-1 flex-wrap justify-content-end">
                <button
                  className={`btn btn-sm ${showParamHelper ? "btn-primary" : "btn-outline-primary"}`}
                  style={{ fontSize: 11 }}
                  onClick={() => { setShowParamHelper(v => !v); setShowDiagramHelper(false); setShowKnowledgeHelper(false); }}
                >＋ Parameter</button>
                <button
                  className="btn btn-sm btn-outline-warning"
                  style={{ fontSize: 11 }}
                  title="Remove $ signs and replace format_number with comma"
                  onClick={() => {
                    const cleaned = content
                      .replace(/\$/g, "")
                      .replace(/format_number/g, "comma");
                    handleContentChange(cleaned);
                  }}
                >Clear</button>
                <button
                  className="btn btn-sm btn-outline-secondary"
                  style={{ fontSize: 11 }}
                  onClick={handleRawAddPart}
                >＋ Part</button>
                <button
                  className={`btn btn-sm ${showDiagramHelper ? "btn-primary" : "btn-outline-secondary"}`}
                  style={{ fontSize: 11 }}
                  onClick={() => { setShowDiagramHelper(v => !v); setShowParamHelper(false); setShowKnowledgeHelper(false); }}
                >＋ Diagram</button>
                <button
                  className={`btn btn-sm ${showKnowledgeHelper ? "btn-primary" : "btn-outline-secondary"}`}
                  style={{ fontSize: 11 }}
                  onClick={() => { setShowKnowledgeHelper(v => !v); setShowParamHelper(false); setShowDiagramHelper(false); }}
                >＋ Knowledge</button>
              </div>
            </div>
            {showParamHelper && (
              <ParameterHelper onInsert={handleRawInsertParameter} />
            )}
            {showDiagramHelper && (
              <DiagramHelper onInsert={handleRawInsertDiagram} />
            )}
            {showKnowledgeHelper && (
              <KnowledgeHelper
                templateId={id ? Number(id) || null : null}
                onInsert={handleRawInsertKnowledge}
                onKnowledgeChange={async () => {
                  const res = await apiFetch("/api/templates/preview/", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ content, templateId: metadata.id }),
                  });
                  const data = await res.json();
                  if (data.preview) setPreview(data.preview);
                }}
              />
            )}
            <div style={{ flexShrink: 0 }}>
              {rawMode ? (
                <Editor
                  height={570}
                  defaultLanguage="yaml"
                  value={content}
                  onChange={(v) => {
                    const val = v ?? "";
                    handleContentChange(val);
                    if (rawAutosaveRef.current) window.clearTimeout(rawAutosaveRef.current);
                    rawAutosaveRef.current = window.setTimeout(() => {
                      rawAutosaveRef.current = null;
                      if (!id || val.trim().length < 5) return;
                      apiFetch("/api/templates/autosave/", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ templateId: id, content: val }),
                      }).catch(console.error);
                    }, 1500);
                  }}
                  theme="vs-dark"
                  onMount={(editor, _monaco) => {
                    editor.onKeyDown((e) => {
                      if ((e.ctrlKey || e.metaKey) && !e.shiftKey && e.keyCode === _monaco.KeyCode.KeyB) {
                        e.preventDefault();
                        e.stopPropagation();
                        const sel = editor.getSelection();
                        if (!sel) return;
                        const model = editor.getModel();
                        if (!model) return;
                        const selected = model.getValueInRange(sel);
                        editor.executeEdits("bold", [{
                          range: sel,
                          text: `**${selected}**`,
                          forceMoveMarkers: true,
                        }]);
                        editor.focus();
                      }
                    });
                  }}
                  options={{
                    fontSize: 13,
                    minimap: { enabled: false },
                    scrollBeyondLastLine: false,
                    wordWrap: "on",
                    lineNumbers: "on",
                    tabSize: 2,
                    insertSpaces: true,
                    quickSuggestions: false,
                    suggestOnTriggerCharacters: false,
                    hover: { enabled: false },
                    formatOnType: false,
                    formatOnPaste: false,
                    scrollbar: { vertical: "auto", horizontal: "hidden" },
                  }}
                />
              ) : (
                <SectionedEditorPanel
                  content={content}
                  onChange={handleContentChange}
                  validation={validationResult}
                  templateId={id ?? null}
                  preview={preview}
                  onKnowledgeChange={async () => {
                    const res = await apiFetch("/api/templates/preview/", {
                      method: "POST",
                      headers: { "Content-Type": "application/json" },
                      body: JSON.stringify({ content, templateId: metadata.id }),
                    });
                    const data = await res.json();
                    if (data.preview) setPreview(data.preview);
                  }}
                />
              )}
            </div>
          </div>
        </div>

        {/* Panel 2: Values (raw mode only) */}
        {rawMode && (
          <div className="col-md-4 d-flex flex-column">
            <div className="card shadow-sm flex-grow-1 d-flex flex-column">
              <div className="card-header">
                <span>Values</span>
              </div>
              <div
                style={{
                  height: 570,
                  overflowY: "auto",
                  background: "#1e1e1e",
                  padding: "8px 12px",
                  color: "#d4d4d4",
                }}
              >
                <ValuesPanel
                  substitutedYaml={preview?.substituted_yaml ?? null}
                  diagramCode={preview?.diagram_code ?? null}
                  backendSvg={null}
                />
              </div>
            </div>
          </div>
        )}

        {/* Panel 3: Preview (Student view + Diagram) */}
        <div className={`${rawMode ? "col-md-4" : "col-md-6"} d-flex flex-column`}>
          <div className="card shadow-sm flex-grow-1">
            <div className="card-header d-flex justify-content-between align-items-center">
              <span>Student Preview</span>
              <button
                className="btn btn-outline-secondary btn-sm"
                style={{ fontSize: 11 }}
                onClick={() => setShowCalculator(v => !v)}
              >
                {showCalculator ? "Hide calculator" : "Show calculator"}
              </button>
            </div>
            <div
              className="card-body p-2 d-flex flex-column"
              style={{ overflow: "hidden" }}
            >
              <PreviewPanel
                preview={preview}
                mode="editor"
                templateContent={content}
                onEditorNext={(newPreview) => {
                  setPreview(newPreview);
//                   goNext();
                }}
              />
              {showCalculator && (
                <DraggableCalculator onClose={() => setShowCalculator(false)} />
              )}

            </div>
          </div>
        </div>

      </div>

      {/* AI Prompt — below Panel 1 */}
      <div className="row mt-2">
        <div className="col-md-6">
          <div className="d-flex gap-2 align-items-center">
            <label style={{ fontSize: 12, whiteSpace: "nowrap", margin: 0 }}>AI Prompt</label>
            <input
              type="text"
              className="form-control form-control-sm"
              placeholder="e.g. Use the AlgebraTable diagram"
              value={aiPrompt}
              onChange={e => setAiPrompt(e.target.value)}
              onKeyDown={e => { if (e.key === "Enter") handleAiUpdate(); }}
              disabled={isAiUpdating}
            />
            <button
              className="btn btn-sm btn-primary"
              onClick={() => handleAiUpdate(false)}
              disabled={isAiUpdating || !aiPrompt.trim()}
              style={{ whiteSpace: "nowrap" }}
            >
              {isAiUpdating ? "Updating…" : "Update"}
            </button>
            <button
              className="btn btn-sm btn-success"
              onClick={() => handleAiUpdate(true)}
              disabled={isAiUpdating || !aiPrompt.trim()}
              style={{ whiteSpace: "nowrap" }}
            >
              {isAiUpdating ? "Updating…" : "Update+"}
            </button>
          </div>
        </div>
      </div>

      {/* Notes — below AI Prompt */}
      {metadata.id && (
        <div className="row mt-2">
          <div className="col-md-6">
            <div className="d-flex gap-2 align-items-center">
              <label style={{ fontSize: 12, whiteSpace: "nowrap", margin: 0 }}>Note</label>
              <input
                type="text"
                className="form-control form-control-sm"
                placeholder="Add a note about this template…"
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
                  <div key={n.id} className="text-muted border-bottom py-1 d-flex justify-content-between align-items-start" style={{ fontSize: 11 }}>
                    <span>{n.text}</span>
                    <button
                      onClick={() => handleDeleteNote(n.id)}
                      style={{ background: "none", border: "none", padding: "0 0 0 6px", cursor: "pointer", color: "#999", fontSize: 13, lineHeight: 1, flexShrink: 0 }}
                      title="Delete note"
                    >×</button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>

  </div>
</Layout>
  );
}