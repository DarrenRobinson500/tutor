import { useEffect, useRef, forwardRef, useImperativeHandle } from "react";
import { apiFetch } from "../../utils/apiFetch"

import Editor, { useMonaco } from "@monaco-editor/react";
import type * as monacoTypes from "monaco-editor";

export interface EditorHandle {
  insertText: (text: string) => void;
}

interface EditorPanelProps {
  content: string;
  onChange: (value: string) => void;
  validation: any;
  templateId: number | string | null;
}

async function saveToBackend(templateId: string | number | null, content: string) {
  if (!templateId || templateId === "new") {
    console.log("Autosave skipped: no valid templateId yet");
    return;
  }
  if (content.trim().length < 5) {
    console.log("Autosave skipped: content too short");
    return;
  }
  const resp = await apiFetch("/api/templates/autosave/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ templateId, content }),
  });
  console.log("AUTOSAVE SENDING", { templateId, content });

  if (!resp.ok) {
    throw new Error(`Autosave failed: ${resp.status}`);
  }
}

// Inject CSS for {{ }} highlight
{
  let style = document.getElementById("template-expr-style") as HTMLStyleElement | null;
  if (!style) {
    style = document.createElement("style");
    style.id = "template-expr-style";
    document.head.appendChild(style);
  }
  style.textContent = ".template-expression { color: #4fc3f7 !important;  }";
}

function applyExpressionDecorations(
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

export const EditorPanel = forwardRef<EditorHandle, EditorPanelProps>(
  ({ content, onChange, validation, templateId }, ref) => {
    const editorInstanceRef = useRef<monacoTypes.editor.IStandaloneCodeEditor | null>(null);
    const decorationsRef = useRef<monacoTypes.editor.IEditorDecorationsCollection | null>(null);
    const monacoRef = useRef<typeof monacoTypes | null>(null);
    const backendTimeoutRef = useRef<number | null>(null);

    const monacoInstance = useMonaco();

    useImperativeHandle(ref, () => ({
      insertText(text: string) {
        const editor = editorInstanceRef.current;
        const monaco = monacoRef.current;
        if (!editor || !monaco) return;
        const position = editor.getPosition();
        if (!position) return;
        editor.executeEdits("parameter-helper", [{
          range: new monaco.Range(
            position.lineNumber, position.column,
            position.lineNumber, position.column
          ),
          text,
          forceMoveMarkers: true,
        }]);
        editor.focus();
      }
    }));

    // Disable Monaco YAML code actions to prevent worker crashes
    useEffect(() => {
      if (!monacoInstance) return;
      monacoInstance.languages.registerCodeActionProvider("yaml", {
        provideCodeActions() {
          return { actions: [], dispose() {} };
        }
      });
    }, [monacoInstance]);

    // Update decorations whenever content changes
    useEffect(() => {
      const editor = editorInstanceRef.current;
      const collection = decorationsRef.current;
      const monaco = monacoRef.current;
      if (editor && collection && monaco) {
        applyExpressionDecorations(monaco, editor, collection);
      }
    }, [content]);

    useEffect(() => {
      if (backendTimeoutRef.current) {
        window.clearTimeout(backendTimeoutRef.current);
      }

      backendTimeoutRef.current = window.setTimeout(() => {
        saveToBackend(templateId, content).catch((err) => {
          console.error("Backend autosave failed", err);
        });
      }, 1500);

      return () => {
        if (backendTimeoutRef.current) {
          window.clearTimeout(backendTimeoutRef.current);
        }
      };
    }, [content, templateId]);

    return (
      <Editor
        height="100%"
        defaultLanguage="yaml"
        value={content}
        onChange={(value) => onChange(value || "")}
        theme="vs-dark"
        onMount={(editor, monaco) => {
          editorInstanceRef.current = editor;
          monacoRef.current = monaco as unknown as typeof monacoTypes;
          decorationsRef.current = editor.createDecorationsCollection([]);
          applyExpressionDecorations(monacoRef.current, editor, decorationsRef.current);

          // Ctrl+B — wrap selection in **bold**
          editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyB, () => {
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
          });
        }}
        options={{
          fontSize: 14,
          minimap: { enabled: false },
          scrollBeyondLastLine: false,
          wordWrap: "on",
          lineNumbers: "on",
          tabSize: 2,
          insertSpaces: true,
          autoIndent: "full",

          // Disable worker-dependent features
          quickSuggestions: false,
          suggestOnTriggerCharacters: false,
          hover: { enabled: false },
          formatOnType: false,
          formatOnPaste: false,
        }}
      />
    );
  }
);
