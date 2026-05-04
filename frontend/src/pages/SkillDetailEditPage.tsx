import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Layout } from "./components/Layout";
import { apiFetch } from "../utils/apiFetch";

interface DetailSkill {
  id: number;
  description: string;
  order_index: number;
  code: string;
}

export function SkillDetailEditPage() {
  const { skillId } = useParams<{ skillId: string }>();
  const navigate = useNavigate();

  const [skillName, setSkillName] = useState("");
  const [grades, setGrades] = useState<string[]>([]);
  const [gradesDraft, setGradesDraft] = useState<string[]>([]);
  const [gradesEditing, setGradesEditing] = useState(false);
  const [gradesSaving, setGradesSaving] = useState(false);
  const [newGrade, setNewGrade] = useState("");
  const [details, setDetails] = useState<DetailSkill[]>([]);
  const [loading, setLoading] = useState(true);

  // Add form
  const [newDesc, setNewDesc] = useState("");
  const [adding, setAdding] = useState(false);
  const [addError, setAddError] = useState<string | null>(null);

  // Edit state: detailId → draft description
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editDraft, setEditDraft] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const [deletingId, setDeletingId] = useState<number | null>(null);

  useEffect(() => {
    if (!skillId) return;
    Promise.all([
      apiFetch(`/api/skills/${skillId}/`).then(r => r.json()),
      apiFetch(`/api/skills/?parent=${skillId}`).then(r => r.json()),
    ]).then(([skill, children]) => {
      setSkillName(skill.description ?? "");
      const parsed: string[] = (skill.grades ?? "")
        .split(",").map((g: string) => g.trim()).filter(Boolean);
      setGrades(parsed);
      setGradesDraft(parsed);
      const d = (children as any[]).filter(c => c.is_detail);
      d.sort((a, b) => a.order_index - b.order_index);
      setDetails(d);
      setLoading(false);
    });
  }, [skillId]);

  async function handleAdd() {
    const desc = newDesc.trim();
    if (!desc) return;
    setAdding(true);
    setAddError(null);
    try {
      const res = await apiFetch(`/api/skills/${skillId}/add_detail/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ description: desc }),
      });
      const data = await res.json();
      if (!res.ok) { setAddError(data.error ?? "Add failed"); return; }
      setDetails(prev => [...prev, data]);
      setNewDesc("");
    } finally {
      setAdding(false);
    }
  }

  async function handleSaveGrades() {
    setGradesSaving(true);
    const gradesStr = gradesDraft.join(", ");
    const res = await apiFetch(`/api/skills/${skillId}/`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ grades: gradesStr }),
    });
    if (res.ok) {
      setGrades([...gradesDraft]);
      setGradesEditing(false);
    }
    setGradesSaving(false);
  }

  async function handleSaveEdit(detailId: number) {
    const desc = editDraft.trim();
    if (!desc) return;
    setSaving(true);
    setSaveError(null);
    try {
      const res = await apiFetch(`/api/skills/${detailId}/`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ description: desc }),
      });
      const data = await res.json();
      if (!res.ok) { setSaveError(data.error ?? "Save failed"); return; }
      setDetails(prev => prev.map(d => d.id === detailId ? { ...d, description: data.description } : d));
      setEditingId(null);
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(detailId: number, description: string) {
    if (!window.confirm(`Delete "${description}"? Any templates linked to this detail will lose their skill detail.`)) return;
    setDeletingId(detailId);
    const res = await apiFetch(`/api/skills/${detailId}/`, { method: "DELETE" });
    if (res.ok || res.status === 204) {
      setDetails(prev => prev.filter(d => d.id !== detailId));
    } else {
      const data = await res.json().catch(() => ({}));
      alert(data.error ?? "Delete failed");
    }
    setDeletingId(null);
  }

  async function handleMove(detail: DetailSkill, direction: "up" | "down") {
    const idx = details.findIndex(d => d.id === detail.id);
    const swapIdx = direction === "up" ? idx - 1 : idx + 1;
    if (swapIdx < 0 || swapIdx >= details.length) return;
    const swap = details[swapIdx];

    // Swap order_index values
    await Promise.all([
      apiFetch(`/api/skills/${detail.id}/`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ order_index: swap.order_index }),
      }),
      apiFetch(`/api/skills/${swap.id}/`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ order_index: detail.order_index }),
      }),
    ]);

    setDetails(prev => {
      const next = [...prev];
      next[idx] = { ...swap, order_index: detail.order_index };
      next[swapIdx] = { ...detail, order_index: swap.order_index };
      next.sort((a, b) => a.order_index - b.order_index);
      return next;
    });
  }

  return (
    <Layout>
      <div className="container py-4" style={{ maxWidth: 700 }}>

        <div className="d-flex align-items-center gap-3 mb-4">
          <button
            className="btn btn-outline-secondary btn-sm"
            onClick={() => navigate(`/skills/${skillId}/overview`)}
          >
            ← Back
          </button>
          <h4 className="mb-0">Edit Skill Details — <span className="text-muted fw-normal">{skillName}</span></h4>
        </div>

        {loading ? (
          <div className="d-flex justify-content-center py-5">
            <div className="spinner-border text-primary" role="status" />
          </div>
        ) : (
          <>
            {/* Grades */}
            <div className="border rounded p-3 bg-light mb-4">
              <div className="d-flex align-items-center gap-2 mb-2">
                <label className="form-label fw-semibold mb-0">Syllabus Years</label>
                {!gradesEditing && (
                  <button
                    className="btn btn-sm btn-outline-secondary ms-auto"
                    onClick={() => { setGradesDraft([...grades]); setGradesEditing(true); setNewGrade(""); }}
                  >
                    Edit
                  </button>
                )}
              </div>

              {!gradesEditing ? (
                grades.length === 0
                  ? <p className="text-muted small mb-0">No years set.</p>
                  : <div className="d-flex gap-2 flex-wrap">
                      {grades.map(g => (
                        <span key={g} className="badge bg-primary fs-6 px-3 py-2 d-flex align-items-center gap-1">
                          Year {g}
                          <button
                            type="button"
                            className="btn-close btn-close-white"
                            style={{ fontSize: 10 }}
                            aria-label={`Remove Year ${g}`}
                            onClick={async () => {
                              const next = grades.filter(x => x !== g);
                              setGrades(next);
                              setGradesDraft(next);
                              await apiFetch(`/api/skills/${skillId}/`, {
                                method: "PATCH",
                                headers: { "Content-Type": "application/json" },
                                body: JSON.stringify({ grades: next.join(", ") }),
                              });
                            }}
                          />
                        </span>
                      ))}
                    </div>
              ) : (
                <>
                  <div className="d-flex gap-2 flex-wrap mb-2">
                    {gradesDraft.map(g => (
                      <span key={g} className="badge bg-primary fs-6 px-3 py-2 d-flex align-items-center gap-1">
                        Year {g}
                        <button
                          type="button"
                          className="btn-close btn-close-white"
                          style={{ fontSize: 10 }}
                          aria-label="Remove"
                          onClick={() => setGradesDraft(prev => prev.filter(x => x !== g))}
                        />
                      </span>
                    ))}
                    {gradesDraft.length === 0 && (
                      <span className="text-muted small">No years — add one below.</span>
                    )}
                  </div>

                  <div className="d-flex gap-2 align-items-center mb-2">
                    <input
                      type="number"
                      className="form-control form-control-sm"
                      style={{ width: 100 }}
                      placeholder="Year e.g. 8"
                      value={newGrade}
                      onChange={e => setNewGrade(e.target.value)}
                      onKeyDown={e => {
                        if (e.key === "Enter") {
                          const v = newGrade.trim();
                          if (v && !gradesDraft.includes(v)) {
                            setGradesDraft(prev => [...prev, v].sort((a, b) => Number(a) - Number(b)));
                            setNewGrade("");
                          }
                        }
                      }}
                    />
                    <button
                      className="btn btn-sm btn-outline-primary"
                      disabled={!newGrade.trim() || gradesDraft.includes(newGrade.trim())}
                      onClick={() => {
                        const v = newGrade.trim();
                        if (v) {
                          setGradesDraft(prev => [...prev, v].sort((a, b) => Number(a) - Number(b)));
                          setNewGrade("");
                        }
                      }}
                    >
                      + Add Year
                    </button>
                  </div>

                  <div className="d-flex gap-2">
                    <button
                      className="btn btn-sm btn-primary"
                      disabled={gradesSaving}
                      onClick={handleSaveGrades}
                    >
                      {gradesSaving ? "Saving…" : "Save"}
                    </button>
                    <button
                      className="btn btn-sm btn-outline-secondary"
                      onClick={() => { setGradesEditing(false); setGradesDraft([...grades]); }}
                    >
                      Cancel
                    </button>
                  </div>
                </>
              )}
            </div>

            {/* Existing details */}
            {details.length === 0 ? (
              <p className="text-muted">No skill details yet. Add one below.</p>
            ) : (
              <div className="d-flex flex-column gap-2 mb-4">
                {details.map((d, idx) => (
                  <div key={d.id} className="border rounded p-2 bg-white">
                    {editingId === d.id ? (
                      <div className="d-flex gap-2 align-items-start">
                        <textarea
                          className="form-control form-control-sm flex-grow-1"
                          rows={2}
                          value={editDraft}
                          onChange={e => setEditDraft(e.target.value)}
                          autoFocus
                        />
                        <div className="d-flex flex-column gap-1">
                          <button
                            className="btn btn-sm btn-primary"
                            onClick={() => handleSaveEdit(d.id)}
                            disabled={saving || !editDraft.trim()}
                          >
                            {saving ? "…" : "Save"}
                          </button>
                          <button
                            className="btn btn-sm btn-outline-secondary"
                            onClick={() => { setEditingId(null); setSaveError(null); }}
                          >
                            Cancel
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div className="d-flex align-items-center gap-2">
                        <div className="d-flex flex-column gap-0 me-1">
                          <button
                            className="btn btn-sm btn-link p-0 lh-1 text-muted"
                            style={{ fontSize: 11 }}
                            disabled={idx === 0}
                            onClick={() => handleMove(d, "up")}
                            title="Move up"
                          >▲</button>
                          <button
                            className="btn btn-sm btn-link p-0 lh-1 text-muted"
                            style={{ fontSize: 11 }}
                            disabled={idx === details.length - 1}
                            onClick={() => handleMove(d, "down")}
                            title="Move down"
                          >▼</button>
                        </div>
                        <span className="flex-grow-1" style={{ fontSize: 14 }}>{d.description}</span>
                        <button
                          className="btn btn-sm btn-outline-secondary"
                          onClick={() => { setEditingId(d.id); setEditDraft(d.description); setSaveError(null); }}
                        >
                          Edit
                        </button>
                        <button
                          className="btn btn-sm btn-outline-danger"
                          disabled={deletingId === d.id}
                          onClick={() => handleDelete(d.id, d.description)}
                        >
                          {deletingId === d.id ? "…" : "Delete"}
                        </button>
                      </div>
                    )}
                    {saveError && editingId === d.id && (
                      <div className="text-danger small mt-1">{saveError}</div>
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* Add new */}
            <div className="border rounded p-3 bg-light">
              <label className="form-label fw-semibold">Add Skill Detail</label>
              <textarea
                className="form-control form-control-sm mb-2"
                rows={2}
                placeholder="Enter the skill detail description…"
                value={newDesc}
                onChange={e => setNewDesc(e.target.value)}
              />
              {addError && <div className="text-danger small mb-2">{addError}</div>}
              <button
                className="btn btn-sm btn-primary"
                onClick={handleAdd}
                disabled={adding || !newDesc.trim()}
              >
                {adding ? "Adding…" : "Add"}
              </button>
            </div>
          </>
        )}
      </div>
    </Layout>
  );
}
