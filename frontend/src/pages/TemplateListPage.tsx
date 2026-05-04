import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import { Layout } from "./components/Layout";
import { useTemplateApi } from "../api/useTemplateApi";
import { apiFetch } from "../utils/apiFetch";
import type { TemplateSummary } from "../types/TemplateMetadata";


export function TemplateListPage() {
  const navigate = useNavigate();
  const { listTemplates, deleteTemplate, loading, error } = useTemplateApi();

  const storedUser = localStorage.getItem("user");
  const user = storedUser ? JSON.parse(storedUser) : null;
  const canEditSyllabus = user?.role === "admin" || user?.edit_syllabus === true;

  const [templates, setTemplates] = useState<TemplateSummary[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [gradeOptions, setGradeOptions] = useState<string[]>([]);
  const [skillOptions, setSkillOptions] = useState<string[]>([]);
  const [diffOptions, setDiffOptions] = useState<string[]>([]);
  const [hasNotesOnly, setHasNotesOnly] = useState(() => localStorage.getItem("templateList_hasNotesOnly") === "true");
  const [noSubjectOnly, setNoSubjectOnly] = useState(() => localStorage.getItem("templateList_noSubjectOnly") === "true");
  const [filterGrade, setFilterGrade] = useState(() => localStorage.getItem("templateList_filterGrade") ?? "");
  const [filterSkill, setFilterSkill] = useState(() => localStorage.getItem("templateList_filterSkill") ?? "");
  const [filterDifficulty, setFilterDifficulty] = useState(() => localStorage.getItem("templateList_filterDifficulty") ?? "");
  const [page, setPage] = useState(1);
  const PAGE_SIZE = 20;
  const [importing, setImporting] = useState(false);
  const [transferMessage, setTransferMessage] = useState("");
  const uploadRef = useRef<HTMLInputElement>(null);

  const handleDownload = () => {
    apiFetch("/api/templates/export_all/")
      .then(res => {
        const disposition = res.headers.get("Content-Disposition") ?? "";
        const match = disposition.match(/filename="([^"]+)"/);
        const filename = match ? match[1] : "templates.yaml";
        return res.blob().then(blob => ({ blob, filename }));
      })
      .then(({ blob, filename }) => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = filename;
        a.click();
        URL.revokeObjectURL(url);
      })
      .catch(() => setTransferMessage("Download failed"));
  };

  const handleUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    e.target.value = "";
    setImporting(true);
    const form = new FormData();
    form.append("file", file);
    apiFetch("/api/templates/import_bulk/", { method: "POST", body: form })
      .then(res => res.json())
      .then(async data => {
        if (data.error) {
          setTransferMessage(`Upload failed: ${data.error}`);
        } else {
          let msg = `Import complete — created: ${data.created}, skipped (duplicates): ${data.skipped}, errors: ${data.errors}`;
          if (data.first_error) msg += ` — first error: ${data.first_error}`;
          setTransferMessage(msg);
          await load();
        }
      })
      .catch(() => setTransferMessage("Upload failed"))
      .finally(() => setImporting(false));
  };

  async function load() {
    const data = await listTemplates({
      hasNotesOnly, noSubjectOnly,
      grade: filterGrade, skill: filterSkill, difficulty: filterDifficulty,
      page, pageSize: PAGE_SIZE,
    });
    setTemplates(data.results);
    setTotalCount(data.count);
    setGradeOptions(data.grade_options);
    setSkillOptions(data.skill_options);
    setDiffOptions(data.diff_options);
    return data;
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hasNotesOnly, noSubjectOnly, filterGrade, filterSkill, filterDifficulty, page]);


  async function handleDelete(e: React.MouseEvent, id: number) {
    e.stopPropagation(); // prevent row click navigation

    await deleteTemplate(id);
    setTemplates((prev) => prev.filter((t) => t.id !== id));
  }

  const totalPages = Math.max(1, Math.ceil(totalCount / PAGE_SIZE));
  const pageTemplates = templates;

  return (
    <Layout>
    <div>
      <div className="container mt-4">
        <div className="d-flex justify-content-between align-items-center mb-3">
          <h1 className="h3">Templates {!loading && `(${totalCount})`}</h1>

          <div className="d-flex gap-2 flex-wrap">
            <div className="btn-group" role="group">
              <button
                className={`btn ${!hasNotesOnly ? "btn-primary" : "btn-outline-primary"}`}
                onClick={() => { setHasNotesOnly(false); localStorage.setItem("templateList_hasNotesOnly", "false"); }}
              >
                All Questions
              </button>
              <button
                className={`btn ${hasNotesOnly ? "btn-primary" : "btn-outline-primary"}`}
                onClick={() => { setHasNotesOnly(true); localStorage.setItem("templateList_hasNotesOnly", "true"); }}
              >
                Questions with Notes
              </button>
            </div>
            <button
              className={`btn ${noSubjectOnly ? "btn-primary" : "btn-outline-primary"}`}
              onClick={() => setNoSubjectOnly(v => { const next = !v; localStorage.setItem("templateList_noSubjectOnly", String(next)); return next; })}
            >
              {noSubjectOnly ? "Showing: No Subject" : "No Subject"}
            </button>
            <button
              className="btn btn-outline-primary"
              onClick={() => navigate("/templates/new")}
            >
              Create New Template
            </button>
            {canEditSyllabus && <>
              <button className="btn btn-outline-secondary" onClick={handleDownload}>
                Download All Templates
              </button>
              <button
                className="btn btn-outline-secondary"
                onClick={() => uploadRef.current?.click()}
                disabled={importing}
              >
                {importing ? "Uploading…" : "Upload All Templates"}
              </button>
              <input ref={uploadRef} type="file" accept=".yaml,.yml,.json" className="d-none" onChange={handleUpload} />
              {process.env.REACT_APP_SHOW_DELETE_ALL === "true" && <button
                className="btn btn-outline-danger"
                onClick={async () => {
                  if (!window.confirm(`Delete all ${templates.length} templates? This cannot be undone.`)) return;
                  const res = await apiFetch("/api/templates/delete_all/", { method: "POST" });
                  const data = await res.json();
                  if (data.error) {
                    setTransferMessage(`Delete failed: ${data.error}`);
                  } else {
                    setTemplates([]);
                    setTransferMessage(`Deleted ${data.deleted} templates.`);
                  }
                }}
              >
                Delete All Templates
              </button>}
            </>}
          </div>
        </div>

        {transferMessage && <div className="alert alert-info py-2 mt-2">{transferMessage}</div>}

        {loading && <p>Loading templates…</p>}
        {error && <p className="text-danger">{error}</p>}

        {!loading && (totalCount > 0 || filterGrade || filterSkill || filterDifficulty) && (
          <div className="d-flex gap-2 flex-wrap align-items-center mb-3">
            <select
              className="form-select form-select-sm"
              style={{ width: "auto" }}
              value={filterGrade}
              onChange={e => { setFilterGrade(e.target.value); localStorage.setItem("templateList_filterGrade", e.target.value); setPage(1); }}
            >
              <option value="">All Grades</option>
              <option value="__none__">No grade</option>
              {gradeOptions.map(g => <option key={g} value={g}>{g}</option>)}
            </select>

            <select
              className="form-select form-select-sm"
              style={{ width: "auto" }}
              value={filterSkill}
              onChange={e => { setFilterSkill(e.target.value); localStorage.setItem("templateList_filterSkill", e.target.value); setPage(1); }}
            >
              <option value="">All Skills</option>
              <option value="__none__">No skill</option>
              {skillOptions.map(s => <option key={s} value={s}>{s}</option>)}
            </select>

            <select
              className="form-select form-select-sm"
              style={{ width: "auto" }}
              value={filterDifficulty}
              onChange={e => { setFilterDifficulty(e.target.value); localStorage.setItem("templateList_filterDifficulty", e.target.value); setPage(1); }}
            >
              <option value="">All Difficulties</option>
              <option value="__none__">No difficulty</option>
              {diffOptions.map(d => <option key={d} value={d}>{d.charAt(0).toUpperCase() + d.slice(1)}</option>)}
            </select>

            {(filterGrade || filterSkill || filterDifficulty) && (
              <button
                className="btn btn-sm btn-outline-secondary"
                onClick={() => {
                  setFilterGrade(""); localStorage.setItem("templateList_filterGrade", "");
                  setFilterSkill(""); localStorage.setItem("templateList_filterSkill", "");
                  setFilterDifficulty(""); localStorage.setItem("templateList_filterDifficulty", "");
                  setPage(1);
                }}
              >
                Clear filters
              </button>
            )}

            {totalCount > 0 && <span className="text-muted small ms-1">{totalCount} total</span>}
          </div>
        )}

        {!loading && totalCount === 0 && (
          <p>No templates found.</p>
        )}

        {totalCount > 0 && (
          <table className="table table-hover">
            <thead className="table-light">
              <tr>
                <th>Grade</th>
                <th>Skill</th>
                <th>Question</th>
                <th>Difficulty</th>
                <th>Notes</th>
                <th style={{ width: 80 }}></th>
              </tr>
            </thead>

            <tbody>
              {pageTemplates.map((tpl) => (
                <tr
                  key={tpl.id}
                  onClick={() => navigate(`/templates/${tpl.id}`)}
                  style={{ cursor: "pointer" }}
                >
                  <td>{tpl.grade}</td>
                  <td>{tpl.skill}<hr></hr>{tpl.skill_detail}</td>
                  <td>{tpl.question_text}</td>
                  <td>{tpl.difficulty ? tpl.difficulty.charAt(0).toUpperCase() + tpl.difficulty.slice(1) : ""}</td>
                  <td style={{ maxWidth: 260 }}>
                    {tpl.notes?.map((n, i) => (
                      <div key={i} className="text-muted" style={{ fontSize: 12, lineHeight: 1.4 }}>
                        {n}
                      </div>
                    ))}
                  </td>

                  <td>
                    <button
                      className="btn btn-outline-danger btn-sm"
                      onClick={(e) => handleDelete(e, tpl.id)}
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {totalPages > 1 && (
          <nav className="d-flex align-items-center gap-2 mt-2 mb-4">
            <button className="btn btn-sm btn-outline-secondary" disabled={page === 1} onClick={() => setPage(1)}>«</button>
            <button className="btn btn-sm btn-outline-secondary" disabled={page === 1} onClick={() => setPage(p => p - 1)}>‹</button>
            <span className="text-muted small">Page {page} of {totalPages}</span>
            <button className="btn btn-sm btn-outline-secondary" disabled={page === totalPages} onClick={() => setPage(p => p + 1)}>›</button>
            <button className="btn btn-sm btn-outline-secondary" disabled={page === totalPages} onClick={() => setPage(totalPages)}>»</button>
          </nav>
        )}
      </div>
    </div>


</Layout>

  );
}
