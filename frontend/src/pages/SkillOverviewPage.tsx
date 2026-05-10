import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Layout } from "./components/Layout";
import { apiFetch } from "../utils/apiFetch";

interface SkillDetailSummary {
  id: number;
  description: string;
  order_index: number;
}

interface KnowledgeSummary {
  id: number;
  title: string;
  skill_ids: number[];
}

interface TemplateSummary {
  id: number;
  name: string;
  description: string;
  skill_detail: string;
  difficulty: string;
  validated: boolean;
  grade: string;
  question_text: string;
}

const DIFFICULTIES = ["easy", "medium", "hard"] as const;

const DIFFICULTY_LABEL: Record<string, string> = {
  easy: "Easy",
  medium: "Medium",
  hard: "Hard",
};

function validationColour(group: TemplateSummary[]): string {
  if (group.length === 0) return "secondary";
  const validatedCount = group.filter(t => t.validated).length;
  if (validatedCount === group.length) return "success";
  if (validatedCount > 0) return "warning";
  return "danger";
}

export function SkillOverviewPage() {
  const { skillId, grade } = useParams<{ skillId: string; grade: string }>();
  const navigate = useNavigate();

  const storedUser = localStorage.getItem("user");
  const user = storedUser ? JSON.parse(storedUser) : null;
  const canEditSyllabus = user?.role === "admin" || user?.edit_syllabus === true;

  const [skillName, setSkillName] = useState<string>("");
  const [skillGrades, setSkillGrades] = useState<string[]>([]);
  const [detailSkills, setDetailSkills] = useState<SkillDetailSummary[]>([]);
  const [templates, setTemplates] = useState<TemplateSummary[]>([]);
  const [loading, setLoading] = useState(true);

  const [knowledge, setKnowledge] = useState<KnowledgeSummary[]>([]);
  const [showLinkModal, setShowLinkModal] = useState(false);
  const [allKnowledge, setAllKnowledge] = useState<KnowledgeSummary[]>([]);
  const [linking, setLinking] = useState(false);
  const [creatingSlot, setCreatingSlot] = useState<string | null>(null); // "grade:diff:detailId"
  const [creatingEmptySlot, setCreatingEmptySlot] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [pendingDelete, setPendingDelete] = useState<TemplateSummary | null>(null);
  const [shiftingGrade, setShiftingGrade] = useState<string | null>(null);

  useEffect(() => {
    if (!skillId) return;
    apiFetch(`/api/skills/${skillId}/`)
      .then(r => r.json())
      .then(d => {
        setSkillName(d.description ?? "");
        const raw: string = d.grades ?? "";
        const parsed = raw.split(",").map((g: string) => g.trim()).filter(Boolean);
        setSkillGrades(parsed);
      });
  }, [skillId]);

  // Fetch Skill Detail children (is_detail=True nodes)
  useEffect(() => {
    if (!skillId) return;
    apiFetch(`/api/skills/?parent=${skillId}`)
      .then(r => r.json())
      .then((data: SkillDetailSummary[]) => {
        const details = data.filter((s: any) => s.is_detail);
        details.sort((a, b) => a.order_index - b.order_index);
        setDetailSkills(details);
      });
  }, [skillId]);

  useEffect(() => {
    if (!skillId) return;
    setLoading(true);
    apiFetch(`/api/templates/filtered/?skill=${skillId}`)
      .then(r => r.json())
      .then((data: TemplateSummary[]) => {
        setTemplates(data);
        setLoading(false);
      });
  }, [skillId]);

  const fetchKnowledge = () => {
    if (!skillId) return;
    apiFetch(`/api/knowledge/?skill_id=${skillId}`)
      .then(r => r.json())
      .then((data: KnowledgeSummary[]) => setKnowledge(data));
  };

  useEffect(() => {
    fetchKnowledge();
  }, [skillId]);

  const openLinkModal = async () => {
    const res = await apiFetch("/api/knowledge/");
    const all: KnowledgeSummary[] = await res.json();
    const linkedIds = new Set(knowledge.map(k => k.id));
    setAllKnowledge(all.filter(k => !linkedIds.has(k.id)));
    setShowLinkModal(true);
  };

  const linkKnowledge = async (k: KnowledgeSummary) => {
    setLinking(true);
    const updatedSkillIds = [...k.skill_ids, parseInt(skillId!)];
    await apiFetch(`/api/knowledge/${k.id}/`, {
      method: "PATCH",
      body: JSON.stringify({ skill_ids: updatedSkillIds }),
    });
    setLinking(false);
    setShowLinkModal(false);
    fetchKnowledge();
  };

  const invalidateAll = async () => {
    if (!window.confirm(`Set all templates for "${skillName}" to unvalidated?`)) return;
    await apiFetch("/api/templates/invalidate_all/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ skill_id: skillId }),
    });
    const tRes = await apiFetch(`/api/templates/filtered/?skill=${skillId}`);
    setTemplates(await tRes.json());
  };

  const createForDetail = async (g: string, diff: string, detail: SkillDetailSummary) => {
    const key = `${g}:${diff}:${detail.id}`;
    setCreatingSlot(key);
    try {
      const res = await apiFetch("/api/templates/generate_for_subject/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ skill_detail_id: detail.id, grade: g, difficulty: diff }),
      });
      const data = await res.json();
      if (data.id) {
        navigate(`/templates/${data.id}`);
      }
    } catch (err) {
      console.error("Failed to create template:", err);
    } finally {
      setCreatingSlot(null);
    }
  };

  const createEmptyForDetail = async (g: string, diff: string, detail: SkillDetailSummary) => {
    const key = `${g}:${diff}:${detail.id}`;
    setCreatingEmptySlot(key);
    try {
      const res = await apiFetch("/api/templates/create_empty_for_subject/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ skill_detail_id: detail.id, grade: g, difficulty: diff }),
      });
      const data = await res.json();
      if (data.id) navigate(`/templates/${data.id}`, { state: { rawMode: true } });
    } catch (err) {
      console.error("Failed to create empty template:", err);
    } finally {
      setCreatingEmptySlot(null);
    }
  };

  const deleteTemplate = (t: TemplateSummary, e: React.MouseEvent) => {
    e.stopPropagation();
    setPendingDelete(t);
  };

  const confirmDelete = async () => {
    if (!pendingDelete) return;
    const t = pendingDelete;
    setPendingDelete(null);
    setDeletingId(t.id);
    await apiFetch(`/api/templates/${t.id}/`, { method: "DELETE" });
    setTemplates(prev => prev.filter(x => x.id !== t.id));
    setDeletingId(null);
  };

  const unlinkKnowledge = async (k: KnowledgeSummary) => {
    const updatedSkillIds = k.skill_ids.filter(id => id !== parseInt(skillId!));
    await apiFetch(`/api/knowledge/${k.id}/`, {
      method: "PATCH",
      body: JSON.stringify({ skill_ids: updatedSkillIds }),
    });
    fetchKnowledge();
  };

  const shiftGrade = async (grade: string, delta: number) => {
    setShiftingGrade(grade);
    await apiFetch("/api/templates/shift_grade/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ skill_id: skillId, grade, delta }),
    });
    const res = await apiFetch(`/api/templates/filtered/?skill=${skillId}`);
    setTemplates(await res.json());
    setShiftingGrade(null);
  };

  // Sort templates by their skill_detail's position in detailSkills
  function sortByDetail(group: TemplateSummary[]): TemplateSummary[] {
    return [...group].sort((a, b) => {
      const ai = detailSkills.findIndex(d => d.description === a.skill_detail);
      const bi = detailSkills.findIndex(d => d.description === b.skill_detail);
      if (ai !== -1 && bi !== -1) return ai - bi;
      if (ai !== -1) return -1;
      if (bi !== -1) return 1;
      return (a.skill_detail ?? "").localeCompare(b.skill_detail ?? "");
    });
  }

  const syllabus = new Set(skillGrades.map(String));
  const extraGrades = Array.from(new Set(templates.map(t => String(t.grade)).filter(g => g && !syllabus.has(g))));
  const syllabusList = skillGrades.length > 0 ? skillGrades.map(String) : grade ? [String(grade)] : [];
  const gradesToShow = [...syllabusList, ...extraGrades.filter(g => !syllabusList.includes(g))];

  return (
    <Layout>
      <div className="container-fluid py-3">

        {/* Header */}
        <div className="d-flex align-items-center gap-3 mb-4 flex-wrap">
          <button
            className="btn btn-outline-secondary btn-sm"
            onClick={() => navigate("/skills")}
          >
            ← Back
          </button>
          <h4 className="mb-0 flex-grow-1">{skillName}</h4>
          <button
            className="btn btn-outline-success btn-sm"
            onClick={() => navigate(`/knowledge/new?skill_id=${skillId}`)}
          >
            + Create Knowledge
          </button>
          <button
            className="btn btn-outline-secondary btn-sm"
            onClick={openLinkModal}
          >
            Link Knowledge
          </button>
          <button
            className="btn btn-outline-danger btn-sm"
            onClick={invalidateAll}
          >
            Invalidate All
          </button>
        </div>

        {detailSkills.length > 0 && (
          <div className="mb-4 p-3 bg-light rounded" style={{ fontSize: 14 }}>
            <ul className="mb-0 ps-3">
              {detailSkills.map(d => (
                <li key={d.id}>{d.description}</li>
              ))}
            </ul>
            {canEditSyllabus && (
              <button
                className="btn btn-outline-secondary btn-sm mt-2"
                style={{ fontSize: 12 }}
                onClick={() => navigate(`/skills/${skillId}/edit-details`)}
              >
                Edit Details
              </button>
            )}
          </div>
        )}
        {detailSkills.length === 0 && canEditSyllabus && (
          <div className="mb-4">
            <button
              className="btn btn-outline-secondary btn-sm"
              onClick={() => navigate(`/skills/${skillId}/edit-details`)}
            >
              + Add Skill Details
            </button>
          </div>
        )}

        {loading ? (
          <div className="d-flex justify-content-center py-5">
            <div className="spinner-border text-primary" role="status" />
          </div>
        ) : (
          <div className="d-flex flex-column gap-4">
            {gradesToShow.map(g => {
              const gradeTemplates = templates.filter(t => String(t.grade) === String(g));
              const isOutOfSyllabus = !syllabus.has(String(g));
              return (
                <div key={g}>
                  <div className="d-flex align-items-center gap-2 mb-2">
                    <h5 className="mb-0">Year {g}</h5>
                    {isOutOfSyllabus && (
                      <>
                        <span className="badge bg-warning text-dark">
                          Not in syllabus for this year
                        </span>
                        <button
                          className="btn btn-sm btn-outline-secondary"
                          style={{ padding: "1px 8px", fontWeight: "bold" }}
                          title={`Move all Year ${g} templates to Year ${parseInt(g) - 1}`}
                          disabled={shiftingGrade === g}
                          onClick={() => shiftGrade(g, -1)}
                        >
                          −
                        </button>
                        <button
                          className="btn btn-sm btn-outline-secondary"
                          style={{ padding: "1px 8px", fontWeight: "bold" }}
                          title={`Move all Year ${g} templates to Year ${g === "K" ? "1" : parseInt(g) + 1}`}
                          disabled={shiftingGrade === g}
                          onClick={() => shiftGrade(g, +1)}
                        >
                          +
                        </button>
                      </>
                    )}
                  </div>
                  <div className="row g-3">
                    {DIFFICULTIES.map(diff => {
                      const group = sortByDetail(gradeTemplates.filter(t => t.difficulty === diff));
                      const colour = validationColour(group);
                      const coveredSkillDetails = new Set(group.map(t => t.skill_detail).filter(Boolean));
                      const validatedSkillDetails = new Set(
                        group.filter(t => t.validated).map(t => t.skill_detail).filter(Boolean)
                      );
                      const detailTotal = detailSkills.length;
                      const detailCovered = detailSkills.filter(d => validatedSkillDetails.has(d.description)).length;
                      const missingDetails = detailSkills.filter(d => !coveredSkillDetails.has(d.description));
                      const coveredDetails = detailSkills.filter(d => coveredSkillDetails.has(d.description));
                      return (
                        <div key={diff} className="col-md-4">
                          <div className="card h-100">
                            <div className={`card-header bg-${colour} bg-opacity-25 d-flex justify-content-between align-items-center`}>
                              <strong>{DIFFICULTY_LABEL[diff]}</strong>
                              <span className={`badge bg-${colour} ${colour === "warning" ? "text-dark" : "text-white"}`}>
                                {detailTotal > 0 ? `${detailCovered} / ${detailTotal}` : `${group.filter(t => t.validated).length} / ${group.length}`}
                              </span>
                            </div>
                            <div className="card-body p-2">
                              <div className="d-flex flex-column gap-1">
                                {group.map(t => (
                                  <div
                                    key={t.id}
                                    className={`btn btn-sm text-start w-100 d-flex align-items-start gap-1 p-0 ${t.validated ? "btn-outline-success" : "btn-outline-secondary"}`}
                                  >
                                    <div
                                      className="flex-grow-1 p-2"
                                      style={{ cursor: "pointer" }}
                                      onClick={() => navigate(`/templates/${t.id}`)}
                                    >
                                      <div className="d-flex justify-content-between align-items-start">
                                        {t.skill_detail
                                          ? <strong className="small">{t.skill_detail}</strong>
                                          : <strong className="small text-danger fst-italic">No skill detail</strong>
                                        }
                                        {t.validated && (
                                          <span className="badge bg-success ms-2 flex-shrink-0">✓</span>
                                        )}
                                      </div>
                                      {t.question_text && (
                                        <div className="text-muted small mt-1" style={{ whiteSpace: "normal", lineHeight: 1.3 }}>
                                          {t.question_text}
                                        </div>
                                      )}
                                    </div>
                                    <button
                                      className="btn btn-sm btn-link text-danger p-1 flex-shrink-0"
                                      style={{ fontSize: 14, lineHeight: 1 }}
                                      disabled={deletingId === t.id}
                                      onClick={(e) => deleteTemplate(t, e)}
                                      title="Delete template"
                                    >
                                      {deletingId === t.id ? "…" : "✕"}
                                    </button>
                                  </div>
                                ))}
                                {missingDetails.map(detail => {
                                  const key = `${g}:${diff}:${detail.id}`;
                                  const isCreating = creatingSlot === key;
                                  return (
                                    <div
                                      key={detail.id}
                                      className="rounded p-2"
                                      style={{ border: "1px solid #f5c6cb", background: "#fff5f5" }}
                                    >
                                      <div className="small text-danger mb-1" style={{ lineHeight: 1.3 }}>{detail.description}</div>
                                      <div className="d-flex gap-1 flex-wrap">
                                        <button
                                          className="btn btn-sm btn-outline-danger"
                                          onClick={() => navigate(
                                            `/templates/new?skill_id=${skillId}&grade=${encodeURIComponent(String(g))}&difficulty=${encodeURIComponent(diff)}&skill_detail_id=${detail.id}`
                                          )}
                                        >
                                          Create Template - Image
                                        </button>
                                        <button
                                          className="btn btn-sm btn-outline-danger"
                                          disabled={isCreating}
                                          onClick={() => createForDetail(String(g), diff, detail)}
                                        >
                                          {isCreating ? "Creating…" : "Create Template"}
                                        </button>
                                        <button
                                          className="btn btn-sm btn-outline-danger"
                                          disabled={creatingEmptySlot === key}
                                          onClick={() => createEmptyForDetail(String(g), diff, detail)}
                                        >
                                          {creatingEmptySlot === key ? "Creating…" : "Create Empty"}
                                        </button>
                                      </div>
                                    </div>
                                  );
                                })}
                                {coveredDetails.map(detail => {
                                  const key = `${g}:${diff}:${detail.id}`;
                                  const isCreating = creatingSlot === key;
                                  return (
                                    <div
                                      key={`extra-${detail.id}`}
                                      className="rounded p-2"
                                      style={{ border: "1px solid #dee2e6", background: "#f8f9fa" }}
                                    >
                                      <div className="small text-secondary mb-1" style={{ lineHeight: 1.3 }}>{detail.description}</div>
                                      <div className="d-flex gap-1 flex-wrap">
                                        <button
                                          className="btn btn-sm btn-outline-secondary"
                                          onClick={() => navigate(
                                            `/templates/new?skill_id=${skillId}&grade=${encodeURIComponent(String(g))}&difficulty=${encodeURIComponent(diff)}&skill_detail_id=${detail.id}`
                                          )}
                                        >
                                          Add - Image
                                        </button>
                                        <button
                                          className="btn btn-sm btn-outline-secondary"
                                          disabled={isCreating}
                                          onClick={() => createForDetail(String(g), diff, detail)}
                                        >
                                          {isCreating ? "Creating…" : "Add Template"}
                                        </button>
                                        <button
                                          className="btn btn-sm btn-outline-secondary"
                                          disabled={creatingEmptySlot === key}
                                          onClick={() => createEmptyForDetail(String(g), diff, detail)}
                                        >
                                          {creatingEmptySlot === key ? "Creating…" : "Add Empty"}
                                        </button>
                                      </div>
                                    </div>
                                  );
                                })}
                                {group.length === 0 && missingDetails.length === 0 && (
                                  <p className="text-muted small mb-0 p-2">No templates yet</p>
                                )}
                              </div>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* ── Knowledge ─────────────────────────────────────── */}
        <div className="mt-4">
          <h5 className="mb-3">Knowledge</h5>
          {knowledge.length === 0 ? (
            <p className="text-muted small">No knowledge linked to this skill yet.</p>
          ) : (
            <div className="d-flex flex-column gap-2">
              {knowledge.map(k => (
                <div key={k.id} className="d-flex align-items-center gap-2 p-2 border rounded bg-white">
                  <span className="flex-grow-1">{k.title}</span>
                  <button
                    className="btn btn-outline-primary btn-sm"
                    onClick={() => navigate(`/knowledge/${k.id}`)}
                  >
                    Edit
                  </button>
                  <button
                    className="btn btn-outline-danger btn-sm"
                    onClick={() => unlinkKnowledge(k)}
                  >
                    Unlink
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* ── Delete Template Confirm Modal ─────────────────── */}
        {pendingDelete && (
          <div className="modal show d-block" style={{ background: "rgba(0,0,0,0.4)" }} onClick={() => setPendingDelete(null)}>
            <div className="modal-dialog modal-dialog-centered" onClick={e => e.stopPropagation()}>
              <div className="modal-content">
                <div className="modal-header border-0 pb-0">
                  <h5 className="modal-title">Delete template?</h5>
                  <button className="btn-close" onClick={() => setPendingDelete(null)} />
                </div>
                <div className="modal-body pt-2">
                  <p className="mb-0">
                    <strong>{pendingDelete.skill_detail || pendingDelete.name}</strong> will be permanently deleted. This cannot be undone.
                  </p>
                </div>
                <div className="modal-footer border-0">
                  <button className="btn btn-secondary" onClick={() => setPendingDelete(null)}>Cancel</button>
                  <button className="btn btn-danger" onClick={confirmDelete}>Delete</button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ── Link Knowledge Modal ───────────────────────────── */}
        {showLinkModal && (
          <div className="modal show d-block" style={{ background: "rgba(0,0,0,0.4)" }}>
            <div className="modal-dialog modal-dialog-scrollable">
              <div className="modal-content">
                <div className="modal-header">
                  <h5 className="modal-title">Link Existing Knowledge</h5>
                  <button className="btn-close" onClick={() => setShowLinkModal(false)} />
                </div>
                <div className="modal-body">
                  {allKnowledge.length === 0 ? (
                    <p className="text-muted">No unlinked knowledge items found.</p>
                  ) : (
                    <div className="d-flex flex-column gap-2">
                      {allKnowledge.map(k => (
                        <button
                          key={k.id}
                          className="btn btn-outline-secondary text-start"
                          disabled={linking}
                          onClick={() => linkKnowledge(k)}
                        >
                          {k.title}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
                <div className="modal-footer">
                  <button className="btn btn-secondary btn-sm" onClick={() => setShowLinkModal(false)}>
                    Cancel
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

      </div>
    </Layout>
  );
}
