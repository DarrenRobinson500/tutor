import { useState } from "react";

export function PauseButton({
  disabled,
  loading,
  onConfirm,
}: {
  disabled?: boolean;
  loading?: boolean;
  onConfirm: (weeks: number) => void;
}) {
  const [open, setOpen] = useState(false);
  const [weeks, setWeeks] = useState(1);

  if (!open) {
    return (
      <button
        className="btn btn-secondary btn-sm"
        disabled={disabled}
        onClick={() => setOpen(true)}
      >
        Pause
      </button>
    );
  }

  return (
    <div
      style={{
        display: "inline-flex",
        flexDirection: "column",
        gap: "0.5rem",
        background: "#fff",
        border: "1px solid #dee2e6",
        borderRadius: 10,
        padding: "0.75rem 1rem",
        boxShadow: "0 4px 12px rgba(0,0,0,.1)",
        minWidth: 220,
      }}
    >
      <div style={{ fontSize: 13, fontWeight: 600, color: "#444" }}>
        Pause for how many weeks?
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
        <button
          className="btn btn-outline-secondary btn-sm"
          style={{ width: 30, padding: 0, fontWeight: 700 }}
          onClick={() => setWeeks(w => Math.max(1, w - 1))}
        >
          −
        </button>
        <span style={{ minWidth: 24, textAlign: "center", fontWeight: 700, fontSize: 16 }}>
          {weeks}
        </span>
        <button
          className="btn btn-outline-secondary btn-sm"
          style={{ width: 30, padding: 0, fontWeight: 700 }}
          onClick={() => setWeeks(w => Math.min(12, w + 1))}
        >
          +
        </button>
        <span style={{ fontSize: 13, color: "#666" }}>
          {weeks === 1 ? "week" : "weeks"}
        </span>
      </div>

      <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
        <button
          className="btn btn-warning btn-sm"
          disabled={loading}
          onClick={() => { onConfirm(weeks); setOpen(false); setWeeks(1); }}
        >
          {loading ? "…" : "Confirm pause"}
        </button>
        <button
          className="btn btn-link btn-sm text-muted p-0"
          style={{ fontSize: 12, textDecoration: "none" }}
          onClick={() => { setOpen(false); setWeeks(1); }}
        >
          cancel
        </button>
      </div>
    </div>
  );
}
