import { useState } from "react";
import { useNavigate } from "react-router-dom";
import type { TemplateMetadata } from "../../types/TemplateMetadata";

interface TemplateMetadataBarProps {
  metadata: TemplateMetadata;
  onChange: (updated: Partial<TemplateMetadata>) => void;
  onSave: () => void;
  onDelete: () => void;
  onCopy: () => void;
  onCopyHarder: () => void;
  onShowRelated: () => void;
  onShowLanguages: () => void;
  isSaving: boolean;
  saveSuccess: boolean;
  saveError: string | null;
  onValidate: () => void;
  onPreview: () => void;
  onToSkill: () => void;
  onNext: () => void;
  onPrev: () => void;
  sortMode: "difficulty" | "skill_detail";
  onToggleSort: () => void;
  skills: Array<{ id: number; description: string; parent_description?: string; root_description?: string; parent_is_root?: boolean }>;
  validated_filter?: "all" | "validated" | "unvalidated";
  currentIndex: number;
  listLength: number;
  validatedCount: number;
}



export function TemplateMetadataBar({
  metadata,
  onChange,
  onSave,
  onDelete,
  onCopy,
  onCopyHarder,
  onShowRelated,
  onShowLanguages,
  onValidate,
  onPreview,
  onToSkill,
  isSaving,
  saveError,
  saveSuccess,
  onNext,
  onPrev,
  sortMode,
  onToggleSort,
  skills,
  currentIndex,
  listLength,
  validatedCount,
}: TemplateMetadataBarProps) {
  const navigate = useNavigate();
  const [copied, setCopied] = useState(false);

  function handleCopy() {
    onCopy();
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  if (!metadata) {
    return <div style={{ padding: 12 }}>Loading…</div>;
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", padding: "8px 12px", gap: 6 }}>

      {/* Row 1: Filter dropdowns */}
      <div style={{ display: "flex", alignItems: "center", gap: 8, overflow: "hidden" }}>
        <span style={{ whiteSpace: "nowrap", fontSize: 13 }}>Grade:</span>
        <select
          className="form-select form-select-sm"
          style={{ width: "80px", flexShrink: 0 }}
          value={metadata.grade ?? ""}
          onChange={(e) => onChange({ grade: e.target.value })}
        >
          <option value="">—</option>
          {["K","1","2","3","4","5","6","7","8","9","10"].map(g => (
            <option key={g} value={g}>{g}</option>
          ))}
        </select>

        <select
          className="form-select form-select-sm"
          style={{ minWidth: 0, flex: 1, maxWidth: 440 }}
          value={metadata.skill ?? ""}
          onChange={(e) => onChange({ skill: Number(e.target.value) })}
        >
          <option value="">Select skill</option>
          {(() => {
            // Group by root_description, preserving insertion order
            const groups: Record<string, typeof skills> = {};
            for (const s of skills) {
              const root = s.root_description ?? "";
              if (!groups[root]) groups[root] = [];
              groups[root].push(s);
            }
            const roots = Object.keys(groups);
            if (roots.length <= 1 && (roots.length === 0 || roots[0] === "")) {
              return skills.map(s => (
                <option key={s.id} value={s.id}>{s.description}</option>
              ));
            }
            return roots.map(root => (
              <optgroup key={root} label={root}>
                {groups[root].map(s => (
                  <option key={s.id} value={s.id}>
                    {s.parent_is_root
                      ? s.description
                      : `${s.parent_description} - ${s.description}`}
                  </option>
                ))}
              </optgroup>
            ));
          })()}
        </select>

        <select
          className="form-select form-select-sm"
          style={{ width: "140px", flexShrink: 0 }}
          value={metadata.validated_filter ?? "all"}
          onChange={(e) =>
            onChange({ validated_filter: e.target.value as "all" | "validated" | "unvalidated" })
          }
        >
          <option value="all">All</option>
          <option value="validated">Validated</option>
          <option value="unvalidated">Unvalidated</option>
        </select>

        <select
          className="form-select form-select-sm"
          style={{ width: "120px", flexShrink: 0 }}
          value={metadata.language_filter ?? "en"}
          onChange={(e) => onChange({ language_filter: e.target.value })}
        >
          <option value="all">All languages</option>
          <option value="en">English</option>
          <option value="zh">Chinese</option>
          <option value="ar">Arabic</option>
          <option value="vi">Vietnamese</option>
          <option value="ko">Korean</option>
          <option value="hi">Hindi</option>
          <option value="es">Spanish</option>
          <option value="fr">French</option>
          <option value="it">Italian</option>
          <option value="pt">Portuguese</option>
        </select>

        {metadata.id && metadata.difficulty && (
          <span className="badge bg-secondary" style={{ fontSize: 12, fontWeight: 500 }}>
            {metadata.difficulty.charAt(0).toUpperCase() + metadata.difficulty.slice(1)}
          </span>
        )}
        {metadata.id && metadata.subject && (
          <span className="badge bg-secondary" title={metadata.subject} style={{ fontSize: 12, fontWeight: 500, maxWidth: 440, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {metadata.subject}
          </span>
        )}
      </div>

      {/* Row 2: Action buttons */}
      <div style={{ display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap" }}>
        <button className="btn btn-sm btn-outline-secondary" onClick={onToggleSort}>
          Sort: {sortMode === "difficulty" ? "Difficulty" : "Skill Detail"}
        </button>
        <button className="btn btn-sm btn-outline-primary" onClick={onPrev} disabled={currentIndex <= 0}>Previous</button>
        <span style={{ fontSize: 13, color: "#555", minWidth: 54, textAlign: "center" }}>
          {listLength > 0 ? `${currentIndex + 1} / ${listLength}` : "0 / 0"}
        </span>
        <button className="btn btn-sm btn-outline-primary" onClick={onNext} disabled={currentIndex >= listLength - 1}>Next</button>
        <span className="badge bg-secondary" style={{ fontSize: 12, fontWeight: 500 }}>
          {validatedCount} of {listLength}
        </span>

        {saveSuccess && <span style={{ color: "green", fontSize: 13 }}>Saved</span>}
        {saveError && <span style={{ color: "red", fontSize: 13 }}>{saveError}</span>}

        <div style={{ width: 16 }} />

        <button
          className="btn btn-sm btn-outline-primary"
          onClick={() => navigate(`/templates/${metadata.id}/metadata`)}
          disabled={!metadata.id}
        >
          Metadata
        </button>

        <button
          onClick={onValidate}
          className={metadata.validated ? "btn btn-sm btn-primary" : "btn btn-sm btn-outline-primary"}
        >
          {metadata.validated ? "Validated" : "Validate"}
        </button>

        <div style={{ width: 16 }} />

        <button
          className="btn btn-sm btn-outline-primary"
          onClick={onShowRelated}
        >
          Difficulty
        </button>

        <button
          className="btn btn-sm btn-outline-primary"
          onClick={onShowLanguages}
        >
          Languages
        </button>

        <div style={{ width: 16 }} />

        <button
          type="button"
          className="btn btn-sm btn-outline-primary"
          onClick={handleCopy}
          style={{ minWidth: 70 }}
        >
          {copied ? "Copied!" : "Copy"}
        </button>

        <button
          className="btn btn-sm btn-outline-primary"
          onClick={() => navigate("/templates/new")}
          title="Create template from image"
        >
          New Template from Image
        </button>

        <div style={{ width: 16 }} />

        {metadata.skill && metadata.grade && (
          <button
            className="btn btn-sm btn-outline-primary"
            onClick={() => navigate(`/skills/${metadata.skill}/overview/${metadata.grade}`)}
            title="Go to skill overview"
          >
            Skill Overview
          </button>
        )}


      </div>
    </div>
  );
}
