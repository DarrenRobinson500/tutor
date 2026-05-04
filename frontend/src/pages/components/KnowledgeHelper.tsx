import { useEffect, useState } from "react";
import { apiFetch } from "../../utils/apiFetch";

interface KnowledgeSummary {
  id: number;
  title: string;
}

interface Props {
  templateId: number | null;
  onKnowledgeChange?: () => void;
  onInsert?: (snippet: string) => void;
}

export function KnowledgeHelper({ templateId, onKnowledgeChange, onInsert }: Props) {
  const [linked, setLinked] = useState<KnowledgeSummary[]>([]);
  const [all, setAll] = useState<KnowledgeSummary[]>([]);
  const [search, setSearch] = useState("");
  const [saving, setSaving] = useState(false);

  // Always load all knowledge items
  useEffect(() => {
    apiFetch("/api/knowledge/")
      .then(r => r.json())
      .then((items: KnowledgeSummary[]) => setAll(items));
  }, []);

  // Load linked knowledge for this template
  useEffect(() => {
    if (!templateId || all.length === 0) return;
    apiFetch(`/api/templates/${templateId}/`)
      .then(r => r.json())
      .then(tpl => {
        const ids: number[] = tpl.knowledge_ids ?? tpl.knowledge_items ?? [];
        setLinked(all.filter(k => ids.includes(k.id)));
      });
  }, [templateId, all]);

  async function patch(newIds: number[]) {
    if (!templateId) return;
    setSaving(true);
    await apiFetch(`/api/templates/${templateId}/`, {
      method: "PATCH",
      body: JSON.stringify({ knowledge_ids: newIds }),
    });
    setSaving(false);
  }

  async function add(item: KnowledgeSummary) {
    const newLinked = [...linked, item];
    setLinked(newLinked);
    setSearch("");
    onInsert?.(`{{ Knowledge("${item.title}") }}`);
    await patch(newLinked.map(k => k.id));
    onKnowledgeChange?.();
  }

  async function remove(id: number) {
    const newLinked = linked.filter(k => k.id !== id);
    setLinked(newLinked);
    await patch(newLinked.map(k => k.id));
    onKnowledgeChange?.();
  }

  const linkedIds = new Set(linked.map(k => k.id));
  const filtered = search
    ? all.filter(k => !linkedIds.has(k.id) && k.title.toLowerCase().includes(search.toLowerCase()))
    : [];

  return (
    <div style={{ padding: "8px 10px", background: "#1e1e1e", borderTop: "1px solid #333", color: "#ccc", fontSize: 12 }}>
      {/* Linked items */}
      {linked.length === 0 ? (
        <div style={{ color: "#888", marginBottom: 6 }}>No knowledge linked yet.</div>
      ) : (
        <div className="d-flex flex-wrap gap-1 mb-2">
          {linked.map(k => (
            <span
              key={k.id}
              style={{ background: "#2d2d2d", border: "1px solid #555", borderRadius: 3, padding: "2px 6px", display: "flex", alignItems: "center", gap: 4 }}
            >
              {onInsert && (
                <button
                  onClick={() => onInsert(`{{ Knowledge("${k.title}") }}`)}
                  title="Insert into solution"
                  style={{ background: "none", border: "none", color: "#7ec8e3", cursor: "pointer", padding: 0, fontSize: 11, lineHeight: 1 }}
                >
                  ↩
                </button>
              )}
              {k.title}
              <button
                onClick={() => remove(k.id)}
                style={{ background: "none", border: "none", color: "#f88", cursor: "pointer", padding: 0, fontSize: 12, lineHeight: 1 }}
              >
                ×
              </button>
            </span>
          ))}
        </div>
      )}

      {/* Search to add — inline results (no absolute positioning) */}
      <input
        value={search}
        onChange={e => setSearch(e.target.value)}
        placeholder="Search knowledge to add…"
        style={{ width: "100%", fontSize: 12, padding: "2px 6px", background: "#2d2d2d", color: "#fff", border: "1px solid #555", borderRadius: 3, marginBottom: filtered.length > 0 ? 2 : 0 }}
      />
      {filtered.length > 0 && (
        <div style={{ background: "#252526", border: "1px solid #555", borderRadius: 3, maxHeight: 140, overflowY: "auto" }}>
          {filtered.map(k => (
            <div
              key={k.id}
              onClick={() => add(k)}
              style={{ padding: "4px 8px", cursor: "pointer", color: "#ccc", fontSize: 12 }}
              onMouseEnter={e => (e.currentTarget.style.background = "#37373d")}
              onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
            >
              {k.title}
            </div>
          ))}
        </div>
      )}

      {saving && <div style={{ color: "#888", marginTop: 4 }}>Saving…</div>}
      {!templateId && <div style={{ color: "#f88", marginTop: 4 }}>Save the template first to link knowledge.</div>}
    </div>
  );
}
