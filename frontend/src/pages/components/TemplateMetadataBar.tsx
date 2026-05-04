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
  skills: Array<{ id: number; description: string }>;
  subjects: string[];
  validated_filter?: "all" | "validated" | "unvalidated";
  onSubjectChange: (subject: string) => void;
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
  skills,
  subjects,
  onSubjectChange,
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
          style={{ minWidth: 0, flex: 1 }}
          value={metadata.skill ?? ""}
          onChange={(e) => onChange({ skill: Number(e.target.value) })}
        >
          <option value="">Select skill</option>
          {skills.map((s) => (
            <option key={s.id} value={s.id}>{s.description}</option>
          ))}
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

        <select
          className="form-select form-select-sm"
          style={{ width: "110px", flexShrink: 0 }}
          value={metadata.difficulty ?? ""}
          onChange={(e) => onChange({ difficulty: e.target.value })}
        >
          <option value="">Difficulty</option>
          <option value="easy">Easy</option>
          <option value="medium">Medium</option>
          <option value="hard">Hard</option>
        </select>

        <select
          className="form-select form-select-sm"
          style={{ minWidth: 0, flex: 2 }}
          value={metadata.subject ?? ""}
          onChange={(e) => onSubjectChange(e.target.value)}
        >
          <option value="">All subjects</option>
          {(subjects ?? []).map((subj) => (
            <option key={subj} value={subj}>{subj}</option>
          ))}
        </select>
      </div>

      {/* Row 2: Action buttons */}
      <div style={{ display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap" }}>
        <button className="btn btn-sm btn-outline-primary" onClick={onPrev}>Previous</button>
        <button className="btn btn-sm btn-outline-primary" onClick={onNext}>Next</button>

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
