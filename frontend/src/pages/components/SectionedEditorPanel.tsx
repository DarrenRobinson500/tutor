import React, { useState, useEffect, useRef, useCallback } from "react";
import Editor from "@monaco-editor/react";
import type * as monacoTypes from "monaco-editor";
import { apiFetch } from "../../utils/apiFetch";
import { ParameterHelper } from "./ParameterHelper";
import { DiagramHelper } from "./DiagramHelper";
import { KnowledgeHelper } from "./KnowledgeHelper";

interface SectionedEditorPanelProps {
  content: string;
  onChange: (value: string) => void;
  validation: any;
  templateId: number | string | null;
  preview?: any | null;
  onKnowledgeChange?: () => void;
}

const SECTION_DEFS = [
  { key: "parameters", label: "Parameters" },
  { key: "validation", label: "Validation" },
  { key: "question", label: "Question" },
  { key: "diagram", label: "Diagram" },
  { key: "answers", label: "Answers" },
  { key: "solution", label: "Solution" },
  { key: "post_answer", label: "Post Answer" },
];

const STANDARD_KEYS = new Set(SECTION_DEFS.map((s) => s.key));

// Top-level YAML keys that are NOT parameters — they stay as their own sections
// rather than being absorbed into the Parameters block.
const NON_PARAM_SECTION_KEYS = new Set([
  ...SECTION_DEFS.map((s) => s.key),
  "title", "years", "difficulty", "introduction", "worked_example", "knowledge",
]);

type Sections = Record<string, string>;

// Strip the YAML key from a section, returning just the editable value.
// Block form  (key:\n  content) → un-indent content by 2.
// Inline form (key: value)      → strip "key: " prefix.
function extractDisplayValue(sectionContent: string, key: string): string {
  if (!sectionContent.trim()) return "";
  const lines = sectionContent.split("\n");
  const firstLine = lines[0];

  if (firstLine.trim() === key + ":") {
    // Block form — strip first line, un-indent rest by 2
    return lines
      .slice(1)
      .map((l) => (l.startsWith("  ") ? l.slice(2) : l))
      .join("\n")
      .trimEnd();
  }

  const inlinePrefix = key + ": ";
  if (firstLine.startsWith(inlinePrefix)) {
    // Inline form — strip "key: " from first line only
    return [firstLine.slice(inlinePrefix.length), ...lines.slice(1)].join("\n").trimEnd();
  }

  return sectionContent; // fallback (already stripped, e.g. extra keys)
}

// Re-add the YAML key to a display value, producing a full YAML section.
// If content looks like a mapping or list (needs block form) → key:\n  content.
// Otherwise → key: value (inline).
function wrapDisplayValue(displayValue: string, key: string): string {
  const trimmed = displayValue.trim();
  if (!trimmed) return "";

  const firstLine = trimmed.split("\n")[0];
  const isBlockContent =
    firstLine.startsWith("-") ||
    /^[a-zA-Z_][a-zA-Z0-9_]*\s*:/.test(firstLine);

  if (isBlockContent) {
    const indented = trimmed.split("\n").map((l) => (l ? "  " + l : l)).join("\n");
    return `${key}:\n${indented}`;
  }

  return `${key}: ${trimmed}`;
}

// Per-section display transforms: extract strips decoration for display,
// wrap re-adds it when composing back to YAML.
const SECTION_DISPLAY: Partial<Record<string, {
  extract: (rawValue: string) => string;
  wrap: (display: string, key: string) => string;
}>> = {
  validation: {
    extract: (rawValue) => {
      const lines = rawValue.split("\n").map((l) => l.trim()).filter(Boolean);
      return lines
        .map((line) => {
          let l = line.replace(/^-\s*/, "");          // strip leading "- "
          l = l.replace(/^["']|["']$/g, "");          // strip surrounding quotes
          l = l.replace(/^\{\{\s*/, "").replace(/\s*\}\}$/, ""); // strip {{ }}
          return l.trim();
        })
        .join("\n");
    },
    wrap: (display, key) => {
      const lines = display.split("\n").map((l) => l.trim()).filter(Boolean);
      if (lines.length === 0) return "";
      const items = lines.map((l) => `  - "{{ ${l} }}"`).join("\n");
      return `${key}:\n${items}`;
    },
  },
};

function parseYamlSections(yaml: string): { sections: Sections; extraKeys: string[] } {
  const extraKeys: string[] = [];
  const lines = yaml.split("\n");
  let currentKey: string | null = null;
  let currentLines: string[] = [];

  // Inner lines of the explicit `parameters:` block (already 2-space indented)
  const standardParamLines: string[] = [];
  // Lines from top-level parameter-like keys (we add 2-space indent)
  const extraParamLines: string[] = [];
  // All other known sections
  const rawSections: Sections = {};

  const flush = () => {
    if (currentKey === null) return;
    if (currentKey === "parameters") {
      // Collect the inner content of the parameters block (skip the header line)
      standardParamLines.push(...currentLines.slice(1));
    } else if (STANDARD_KEYS.has(currentKey)) {
      rawSections[currentKey] = currentLines.join("\n").trimEnd();
    } else if (NON_PARAM_SECTION_KEYS.has(currentKey)) {
      // Known non-parameter top-level key (title, introduction, etc.)
      rawSections[currentKey] = currentLines.join("\n").trimEnd();
      if (!extraKeys.includes(currentKey)) extraKeys.push(currentKey);
    } else {
      // Unrecognised top-level key → treat as a parameter, indent +2 for nesting
      extraParamLines.push(...currentLines.map((l) => "  " + l));
    }
  };

  for (const line of lines) {
    const keyMatch = line.match(/^([a-zA-Z_][a-zA-Z0-9_]*)\s*:/);
    if (keyMatch && !line.startsWith(" ") && !line.startsWith("\t")) {
      flush();
      const originalKey = keyMatch[1];
      // Treat "answer" (singular) as an alias for "answers" (plural) so it
      // appears in the Answers section rather than as an unrecognised extra key.
      currentKey = originalKey === "answer" ? "answers" : originalKey;
      const normalizedLine = currentKey !== originalKey
        ? line.replace(/^answer(\s*:)/, "answers$1")
        : line;
      currentLines = [normalizedLine];
    } else if (currentKey !== null) {
      currentLines.push(line);
    }
  }
  flush();

  // Merge the explicit parameters block and any absorbed extra-param keys
  const allParamLines = [...standardParamLines, ...extraParamLines];
  if (allParamLines.length > 0) {
    rawSections["parameters"] = "parameters:\n" + allParamLines.join("\n");
  }

  // Convert raw full-section strings to display values (key stripped)
  const sections: Sections = {};
  for (const [k, v] of Object.entries(rawSections)) {
    const rawDisplay = extractDisplayValue(v, k);
    const override = SECTION_DISPLAY[k];
    sections[k] = override ? override.extract(rawDisplay) : rawDisplay;
  }

  return { sections, extraKeys };
}

function composeSections(sections: Sections, extraKeys: string[]): string {
  const order = [...SECTION_DEFS.map((s) => s.key), ...extraKeys];
  return order
    .filter((key) => sections[key]?.trim())
    .map((key) => {
      const override = SECTION_DISPLAY[key];
      return override
        ? override.wrap(sections[key], key)
        : wrapDisplayValue(sections[key], key);
    })
    .join("\n\n");
}

async function saveToBackend(templateId: string | number | null, content: string) {
  if (!templateId || templateId === "new") return;
  if (content.trim().length < 5) return;
  const resp = await apiFetch("/api/templates/autosave/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ templateId, content }),
  });
  if (!resp.ok) throw new Error(`Autosave failed: ${resp.status}`);
}

// CSS for {{ }} highlight (idempotent)
{
  let style = document.getElementById("template-expr-style") as HTMLStyleElement | null;
  if (!style) {
    style = document.createElement("style");
    style.id = "template-expr-style";
    document.head.appendChild(style);
  }
  style.textContent = ".template-expression { color: #4fc3f7 !important; }";
}

function applyDecorations(
  monaco: typeof monacoTypes,
  editor: monacoTypes.editor.IStandaloneCodeEditor,
  collection: monacoTypes.editor.IEditorDecorationsCollection
) {
  const model = editor.getModel();
  if (!model) return;
  const text = model.getValue();
  const decorations: monacoTypes.editor.IModelDeltaDecoration[] = [];
  const regex = /\{\{.*?\}\}/g;
  let match;
  while ((match = regex.exec(text)) !== null) {
    const start = model.getPositionAt(match.index);
    const end = model.getPositionAt(match.index + match[0].length);
    decorations.push({
      range: new monaco.Range(start.lineNumber, start.column, end.lineNumber, end.column),
      options: { inlineClassName: "template-expression" },
    });
  }
  collection.set(decorations);
}

const MIN_EDITOR_HEIGHT = 22;
const MAX_EDITOR_HEIGHT = 400;

// Muted strip shown below each section with the rendered output for that section.
function DebugStrip({ sectionKey, preview }: { sectionKey: string; preview: any }) {
  if (!preview) return null;

  const base: React.CSSProperties = {
    fontSize: 11,
    fontFamily: "monospace",
    padding: "3px 10px",
    background: "#141414",
    color: "#6a9955",
    borderTop: "1px solid #2a2a2a",
    whiteSpace: "pre-wrap",
    wordBreak: "break-word",
  };

  const err: React.CSSProperties = { ...base, color: "#f44747" };

  if (sectionKey === "parameters") {
    const params = preview.params;
    if (!params || Object.keys(params).length === 0) return null;
    const text = Object.entries(params)
      .map(([k, v]) => `${k} = ${v}`)
      .join("   ");
    return <div style={base}>{text}</div>;
  }

  if (sectionKey === "validation") {
    const errors: string[] = preview.errors ?? [];
    const valErrors = errors.filter((e: string) => e.toLowerCase().includes("rule") || e.toLowerCase().includes("validation"));
    if (valErrors.length === 0) {
      if (!preview.params || Object.keys(preview.params).length === 0) return null;
      return <div style={base}>✓ passed</div>;
    }
    return <div style={err}>✗ {valErrors.join(" | ")}</div>;
  }

  if (sectionKey === "question") {
    const errors: string[] = preview.errors ?? [];
    const qErr = errors.find((e: string) => e.toLowerCase().includes("question"));
    if (qErr) return <div style={err}>✗ {qErr}</div>;
    if (!preview.question) return null;
    return <div style={base}>{preview.question}</div>;
  }

  if (sectionKey === "answers") {
    const answers: any[] = preview.answers ?? [];
    const multipleAnswers: string[] | null = preview.multiple_answers ?? null;
    if (answers.length === 0 && !multipleAnswers?.length) return null;
    if (multipleAnswers?.length) {
      const text = multipleAnswers.map((item: any, i: number) => {
        const val = typeof item === "object" ? item.value : item;
        const lbl = typeof item === "object" ? item.label : null;
        return lbl ? `${lbl} = ${val}` : `answer ${i + 1} = ${val}`;
      }).join("   ");
      return <div style={base}>{text}</div>;
    }
    const text = answers
      .map((a: any) => `${a.correct ? "✓" : "✗"} ${a.text}`)
      .join("   ");
    return <div style={base}>{text}</div>;
  }

  if (sectionKey === "solution") {
    if (!preview.solution) return null;
    return <div style={base}>{preview.solution}</div>;
  }

  return null;
}

function SectionEditor({
  sectionKey,
  label,
  value,
  collapsed,
  onToggle,
  onChange,
  onRegisterEditor,
  onFocusNext,
  onFocusPrev,
  outerRef,
  headerAction,
}: {
  sectionKey: string;
  label: string;
  value: string;
  collapsed: boolean;
  onToggle: () => void;
  onChange: (key: string, val: string) => void;
  onRegisterEditor: (editor: monacoTypes.editor.IStandaloneCodeEditor) => void;
  onFocusNext: () => void;
  onFocusPrev: () => void;
  outerRef: (el: HTMLDivElement | null) => void;
  headerAction?: React.ReactNode;
}) {
  const editorInstanceRef = useRef<monacoTypes.editor.IStandaloneCodeEditor | null>(null);
  const decorationsRef = useRef<monacoTypes.editor.IEditorDecorationsCollection | null>(null);
  const monacoRef = useRef<typeof monacoTypes | null>(null);
  const [editorHeight, setEditorHeight] = useState(MIN_EDITOR_HEIGHT);

  // Keep refs current so onKeyDown always calls the latest callbacks
  const onFocusNextRef = useRef(onFocusNext);
  const onFocusPrevRef = useRef(onFocusPrev);
  useEffect(() => { onFocusNextRef.current = onFocusNext; }, [onFocusNext]);
  useEffect(() => { onFocusPrevRef.current = onFocusPrev; }, [onFocusPrev]);

  useEffect(() => {
    if (editorInstanceRef.current && decorationsRef.current && monacoRef.current) {
      applyDecorations(monacoRef.current, editorInstanceRef.current, decorationsRef.current);
    }
  }, [value]);

  return (
    <div ref={outerRef} style={{ borderBottom: "1px solid #3c3c3c" }}>
      <div
        style={{
          background: "#252526",
          color: "#cccccc",
          padding: "5px 10px",
          cursor: "pointer",
          userSelect: "none",
          display: "flex",
          alignItems: "center",
          gap: 6,
          fontSize: 11,
          fontWeight: 600,
          letterSpacing: "0.04em",
          textTransform: "uppercase",
        }}
        onClick={onToggle}
      >
        <span style={{ fontSize: 9, opacity: 0.5, width: 10 }}>{collapsed ? "▶" : "▼"}</span>
        {label}
        {!value.trim() && (
          <span style={{ opacity: 0.35, fontWeight: 400, textTransform: "none", letterSpacing: 0 }}>
            — empty
          </span>
        )}
        {headerAction && (
          <span onClick={e => e.stopPropagation()} style={{ marginLeft: "auto" }}>
            {headerAction}
          </span>
        )}
      </div>
      {!collapsed && (
        <div style={{ height: editorHeight }}>
          <Editor
            height={editorHeight}
            defaultLanguage="yaml"
            value={value}
            onChange={(v) => onChange(sectionKey, v ?? "")}
            theme="vs-dark"
            onMount={(editor, monaco) => {
              editorInstanceRef.current = editor;
              monacoRef.current = monaco as unknown as typeof monacoTypes;
              decorationsRef.current = editor.createDecorationsCollection([]);
              applyDecorations(monacoRef.current, editor, decorationsRef.current);
              onRegisterEditor(editor);

              const updateHeight = () => {
                requestAnimationFrame(() => {
                  const h = Math.max(MIN_EDITOR_HEIGHT, Math.min(MAX_EDITOR_HEIGHT, editor.getContentHeight()));
                  setEditorHeight(h);
                });
              };
              editor.onDidContentSizeChange(updateHeight);
              updateHeight();

              // Ctrl+Enter → next section, Ctrl+Shift+Enter → previous section
              // Use onKeyDown (fires before Monaco's own handlers) with refs so
              // callbacks are always current even after re-renders.
              editor.onKeyDown((e) => {
                if ((e.ctrlKey || e.metaKey) && e.keyCode === monaco.KeyCode.Enter) {
                  e.preventDefault();
                  e.stopPropagation();
                  if (e.shiftKey) {
                    onFocusPrevRef.current();
                  } else {
                    onFocusNextRef.current();
                  }
                }
                if ((e.ctrlKey || e.metaKey) && !e.shiftKey && e.keyCode === monaco.KeyCode.KeyB) {
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
              lineNumbers: "off",
              tabSize: 2,
              insertSpaces: true,
              quickSuggestions: false,
              suggestOnTriggerCharacters: false,
              hover: { enabled: false },
              formatOnType: false,
              formatOnPaste: false,
              scrollbar: { vertical: "auto", horizontal: "hidden" },
              overviewRulerLanes: 0,
            }}
          />
        </div>
      )}
    </div>
  );
}

export function SectionedEditorPanel({
  content,
  onChange,
  templateId,
  preview = null,
  onKnowledgeChange,
}: SectionedEditorPanelProps) {
  const [sections, setSections] = useState<Sections>({});
  const [extraKeys, setExtraKeys] = useState<string[]>([]);
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});
  const [showParamHelper,    setShowParamHelper]    = useState(false);
  const [showDiagramHelper,  setShowDiagramHelper]  = useState(false);
  const [showKnowledgeHelper, setShowKnowledgeHelper] = useState(false);
  const lastComposedRef = useRef<string>("");
  const extraKeysRef = useRef<string[]>([]);
  const backendTimeoutRef = useRef<number | null>(null);
  const templateIdRef = useRef<string | number | null>(templateId);
  const editorInstancesRef = useRef<Map<string, monacoTypes.editor.IStandaloneCodeEditor>>(new Map());
  const sectionDivRefs = useRef<Map<string, HTMLDivElement>>(new Map());
  const collapsedRef = useRef<Record<string, boolean>>({});
  const pendingFocusRef = useRef<string | null>(null);

  useEffect(() => {
    extraKeysRef.current = extraKeys;
  }, [extraKeys]);

  useEffect(() => {
    collapsedRef.current = collapsed;
  }, [collapsed]);

  // When templateId changes (user navigated to a different template), immediately
  // flush any pending autosave to the OLD templateId so edits aren't lost.
  useEffect(() => {
    const prevId = templateIdRef.current;
    templateIdRef.current = templateId;
    if (prevId !== templateId && prevId && backendTimeoutRef.current) {
      window.clearTimeout(backendTimeoutRef.current);
      backendTimeoutRef.current = null;
      saveToBackend(prevId, lastComposedRef.current).catch(console.error);
    }
  }, [templateId]);

  const focusSection = useCallback((targetKey: string) => {
    sectionDivRefs.current.get(targetKey)?.scrollIntoView({ block: "nearest", behavior: "smooth" });
    editorInstancesRef.current.get(targetKey)?.focus();
  }, []);

  const focusAdjacentSection = useCallback((currentKey: string, direction: 1 | -1) => {
    const allKeys = [...SECTION_DEFS.map(d => d.key), ...extraKeysRef.current];
    const idx = allKeys.indexOf(currentKey);
    const targetIdx = idx + direction;
    if (targetIdx < 0 || targetIdx >= allKeys.length) return;
    const targetKey = allKeys[targetIdx];
    if (collapsedRef.current[targetKey]) {
      // Mark pending so onRegisterEditor fires focus as soon as the editor mounts
      pendingFocusRef.current = targetKey;
      setCollapsed(prev => ({ ...prev, [targetKey]: false }));
    } else {
      focusSection(targetKey);
    }
  }, [focusSection]);

  // Re-parse only when content changes from outside (not from our own edits)
  useEffect(() => {
    if (content === lastComposedRef.current) return;
    const { sections: parsed, extraKeys: ek } = parseYamlSections(content);
    setSections(parsed);
    setExtraKeys(ek);
    // Normalise lastComposedRef to the rounded-trip form so that any spurious
    // Monaco onChange echo (same values, different raw text) won't trigger a save.
    lastComposedRef.current = composeSections(parsed, ek);
    // Re-evaluate collapsed state: empty sections collapse, non-empty expand
    const next: Record<string, boolean> = {};
    for (const def of SECTION_DEFS) {
      next[def.key] = !parsed[def.key]?.trim();
    }
    for (const k of ek) {
      next[k] = false;
    }
    setCollapsed(next);
  }, [content]);

  const handleSectionChange = useCallback(
    (key: string, value: string) => {
      setSections((prev) => {
        const next = { ...prev, [key]: value };
        const composed = composeSections(next, extraKeysRef.current);

        onChange(composed);

        // Only autosave if content actually changed from the last known state.
        // This prevents echoes (Monaco firing onChange when value prop updates)
        // from scheduling a spurious write to the wrong template.
        if (composed !== lastComposedRef.current) {
          lastComposedRef.current = composed;
          if (backendTimeoutRef.current) window.clearTimeout(backendTimeoutRef.current);
          backendTimeoutRef.current = window.setTimeout(() => {
            backendTimeoutRef.current = null;
            saveToBackend(templateIdRef.current, composed).catch(console.error);
          }, 1500);
        }

        return next;
      });
    },
    [onChange]
  );

  const toggleCollapsed = useCallback((key: string) => {
    setCollapsed((prev) => ({ ...prev, [key]: !prev[key] }));
  }, []);

  const handleInsertParameter = useCallback((yaml: string) => {
    // ParameterHelper indents by 2 spaces; strip that to match the section display format
    const stripped = yaml.split("\n").map(l => l.startsWith("  ") ? l.slice(2) : l).join("\n");
    setSections(prev => {
      const current = prev["parameters"] ?? "";
      const next = { ...prev, parameters: current ? `${current}\n${stripped}` : stripped };
      const composed = composeSections(next, extraKeysRef.current);
      lastComposedRef.current = composed;
      onChange(composed);
      return next;
    });
    // Expand the section if it was collapsed
    setCollapsed(prev => ({ ...prev, parameters: false }));
  }, [onChange]);

  const handleAddPart = useCallback(() => {
    const newPart = `- text: ""\n  answer: ""\n  solution: ""`;
    setSections(prev => {
      const current = prev["question"] ?? "";
      const lines = current.split("\n");
      const partsIdx = lines.findIndex(l => /^parts:/.test(l.trim()));
      let next: string;
      if (partsIdx === -1) {
        // No parts block yet — append after existing question content
        next = current.trimEnd() + (current.trim() ? "\nparts:\n  " : "parts:\n  ") + newPart.replace(/\n/g, "\n  ");
      } else {
        // Find last line of parts block and append after it
        let lastIdx = partsIdx;
        for (let i = partsIdx + 1; i < lines.length; i++) {
          if (lines[i].startsWith("  ") || lines[i].trim() === "") lastIdx = i;
          else break;
        }
        const newLines = [
          ...lines.slice(0, lastIdx + 1),
          "  " + newPart.split("\n").join("\n  "),
          ...lines.slice(lastIdx + 1),
        ];
        next = newLines.join("\n");
      }
      const composed = composeSections({ ...prev, question: next }, extraKeysRef.current);
      lastComposedRef.current = composed;
      onChange(composed);
      return { ...prev, question: next };
    });
    setCollapsed(prev => ({ ...prev, question: false }));
  }, [onChange]);

  const handleInsertDiagram = useCallback((yaml: string) => {
    // yaml is full "diagram: ..." — strip the key prefix for the section display
    const value = yaml.replace(/^diagram:\s*\n?/, "").replace(/^diagram:\s*/, "");
    setSections(prev => {
      const next = { ...prev, diagram: value };
      const composed = composeSections(next, extraKeysRef.current);
      lastComposedRef.current = composed;
      onChange(composed);
      return next;
    });
    setCollapsed(prev => ({ ...prev, diagram: false }));
    setShowDiagramHelper(false);
  }, [onChange]);

  const handleInsertKnowledge = useCallback((snippet: string) => {
    setSections(prev => {
      const current = prev["post_answer"] ?? "";
      const next = { ...prev, post_answer: current ? `${current}\n${snippet}` : snippet };
      const composed = composeSections(next, extraKeysRef.current);
      lastComposedRef.current = composed;
      onChange(composed);
      return next;
    });
    setCollapsed(prev => ({ ...prev, post_answer: false }));
  }, [onChange]);

  const allSections = [
    ...SECTION_DEFS,
    ...extraKeys.map((k) => ({ key: k, label: k })),
  ];

  return (
    <div
      style={{
        height: 570,
        overflowY: "auto",
        background: "#1e1e1e",
        border: "1px solid #3c3c3c",
      }}
    >
      {allSections.map((def) => {
        const headerBtn = (() => {
          const btnStyle: React.CSSProperties = { fontSize: 10, padding: "1px 6px", lineHeight: 1.4, textTransform: "none", letterSpacing: 0, fontWeight: 400 };
          if (def.key === "parameters") return (
            <div style={{ display: "flex", gap: 4 }}>
              <button
                className={showParamHelper ? "btn btn-xs btn-primary" : "btn btn-xs btn-outline-primary"}
                style={btnStyle}
                onClick={() => setShowParamHelper(v => !v)}
              >＋ Parameter</button>
              <button
                className="btn btn-xs btn-outline-warning"
                style={btnStyle}
                title="Remove $ signs and replace format_number with comma"
                onClick={() => {
                  const cleaned = content
                    .replace(/\$/g, "")
                    .replace(/format_number/g, "comma");
                  onChange(cleaned);
                }}
              >Clear</button>
            </div>
          );
          if (def.key === "question") return (
            <button
              className="btn btn-xs btn-outline-secondary"
              style={btnStyle}
              onClick={handleAddPart}
            >＋ Part</button>
          );
          if (def.key === "diagram") return (
            <button
              className={showDiagramHelper ? "btn btn-xs btn-primary" : "btn btn-xs btn-outline-secondary"}
              style={btnStyle}
              onClick={() => setShowDiagramHelper(v => !v)}
            >＋ Diagram</button>
          );
          if (def.key === "post_answer") return (
            <button
              className={showKnowledgeHelper ? "btn btn-xs btn-primary" : "btn btn-xs btn-outline-secondary"}
              style={btnStyle}
              onClick={() => setShowKnowledgeHelper(v => !v)}
            >＋ Knowledge</button>
          );
          return undefined;
        })();

        return (
          <React.Fragment key={def.key}>
            <SectionEditor
              sectionKey={def.key}
              label={def.label}
              value={sections[def.key] ?? ""}
              collapsed={!!collapsed[def.key]}
              onToggle={() => toggleCollapsed(def.key)}
              onChange={handleSectionChange}
              onRegisterEditor={(editor) => {
                editorInstancesRef.current.set(def.key, editor);
                if (pendingFocusRef.current === def.key) {
                  pendingFocusRef.current = null;
                  editor.focus();
                  sectionDivRefs.current.get(def.key)?.scrollIntoView({ block: "nearest", behavior: "smooth" });
                }
              }}
              onFocusNext={() => focusAdjacentSection(def.key, 1)}
              onFocusPrev={() => focusAdjacentSection(def.key, -1)}
              outerRef={(el) => { if (el) sectionDivRefs.current.set(def.key, el); }}
              headerAction={headerBtn}
            />
            {def.key === "parameters" && showParamHelper && (
              <ParameterHelper onInsert={handleInsertParameter} />
            )}
            {def.key === "diagram" && showDiagramHelper && (
              <DiagramHelper onInsert={handleInsertDiagram} />
            )}
            {def.key === "post_answer" && showKnowledgeHelper && (
              <KnowledgeHelper
                templateId={typeof templateId === "string" ? Number(templateId) || null : templateId}
                onInsert={handleInsertKnowledge}
                onKnowledgeChange={onKnowledgeChange}
              />
            )}
            {!collapsed[def.key] && sections[def.key]?.trim() && (
              <DebugStrip sectionKey={def.key} preview={preview} />
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
}
