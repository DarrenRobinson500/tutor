import React from "react";
import type { TemplateMetadata } from "../../types/TemplateMetadata";

interface TrioMetadataBarProps {
  metadata: TemplateMetadata;
  onSave: () => void;
  onDelete: () => void;
  onOpenFullEditor: () => void;
}

export function TrioMetadataBar({
  metadata,
  onSave,
  onDelete,
  onOpenFullEditor,
}: TrioMetadataBarProps) {
  return (
    <div className="d-flex justify-content-between align-items-center mb-2">
      <div>
        <strong>{metadata.name || "Untitled"}</strong>
        <span className="text-muted ms-2">({metadata.difficulty})</span>
      </div>

      <div className="d-flex gap-2">
        <button className="btn btn-sm btn-outline-secondary" onClick={onOpenFullEditor}>
          Open Full Editor
        </button>

        <button className="btn btn-sm btn-primary" onClick={onSave}>
          Save
        </button>

        <button className="btn btn-sm btn-danger" onClick={onDelete}>
          Delete
        </button>
      </div>
    </div>
  );
}