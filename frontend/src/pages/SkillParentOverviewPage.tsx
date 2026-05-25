import { useEffect, useRef, useState } from "react";
import { useParams, useNavigate, useSearchParams } from "react-router-dom";
import * as jsYaml from "js-yaml";
import { Layout } from "./components/Layout";
import { apiFetch } from "../utils/apiFetch";

interface SkillDetail {
  id: number;
  description: string;
  order_index: number;
}

interface ImportEntry {
  skill_detail: string;
  difficulty: string;
  yaml: string;
}

interface FailedImport extends ImportEntry {
  error: string;
}

type ImportPhase = "preview" | "importing" | "done";

interface ChildSkill {
  id: number;
  description: string;
  order_index: number;
  details: SkillDetail[];
}

export function SkillParentOverviewPage() {
  const { parentId } = useParams<{ parentId: string }>();
  const [searchParams] = useSearchParams();
  const grade = searchParams.get("grade");
  const navigate = useNavigate();

  const [parentName, setParentName] = useState("");
  const [children, setChildren] = useState<ChildSkill[]>([]);
  const [loading, setLoading] = useState(true);

  const importFileRef = useRef<HTMLInputElement>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [importYear, setImportYear] = useState<number | null>(null);
  const [importEntries, setImportEntries] = useState<ImportEntry[]>([]);
  const [importPhase, setImportPhase] = useState<ImportPhase>("preview");
  const [importProgress, setImportProgress] = useState({ done: 0, total: 0 });
  const [importSucceeded, setImportSucceeded] = useState(0);
  const [importFailed, setImportFailed] = useState<FailedImport[]>([]);
  const [importStopError, setImportStopError] = useState<string | null>(null);
  const [showImportModal, setShowImportModal] = useState(false);

  useEffect(() => {
    if (!parentId) return;

    apiFetch(`/api/skills/${parentId}/`)
      .then(r => r.json())
      .then(d => setParentName(d.description ?? ""));

    const loadChildren = async () => {
      const pid = parseInt(parentId);

      if (grade) {
        // Use the matrix API — filter_matrix_by_grade already limits the
        // response to covered leaf skills and their ancestors, so every Skill
        // that appears under this parent is in the syllabus for the grade.
        const res = await apiFetch(`/api/skills/matrix/?grade=${encodeURIComponent(grade)}`);
        const data = await res.json();
        const skills: any[] = data.skills ?? [];

        const childSkills = skills
          .filter(s => s.parent_id === pid)
          .sort((a, b) => (a.order_index ?? 0) - (b.order_index ?? 0));

        const withDetails = await Promise.all(
          childSkills.map(async skill => {
            const r = await apiFetch(`/api/skills/?parent=${skill.id}`);
            const dets: any[] = await r.json();
            const details: SkillDetail[] = dets
              .filter(s => s.is_detail)
              .sort((a, b) => (a.order_index ?? 0) - (b.order_index ?? 0));
            return { id: skill.id, description: skill.description, order_index: skill.order_index ?? 0, details };
          })
        );

        setChildren(withDetails);
      } else {
        // No grade selected — show all skills under this parent
        const res = await apiFetch(`/api/skills/?parent=${parentId}`);
        const all: any[] = await res.json();
        const childSkills = all
          .filter(s => !s.is_detail)
          .sort((a, b) => (a.order_index ?? 0) - (b.order_index ?? 0));

        const withDetails = await Promise.all(
          childSkills.map(async skill => {
            const r = await apiFetch(`/api/skills/?parent=${skill.id}`);
            const dets: any[] = await r.json();
            const details: SkillDetail[] = dets
              .filter(s => s.is_detail)
              .sort((a, b) => (a.order_index ?? 0) - (b.order_index ?? 0));
            return { id: skill.id, description: skill.description, order_index: skill.order_index ?? 0, details };
          })
        );

        setChildren(withDetails);
      }

      setLoading(false);
    };

    loadChildren();
  }, [parentId, grade]);

  function handleImportFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    setFileError(null);
    const file = e.target.files?.[0];
    if (!file) return;
    e.target.value = "";
    const reader = new FileReader();
    reader.onload = (ev) => {
      const text = ev.target?.result as string;
      let parsed: any;
      try { parsed = jsYaml.load(text); } catch {
        setFileError("Could not read file — please check it is valid YAML.");
        return;
      }
      if (!parsed || typeof parsed !== "object") {
        setFileError("Could not read file — please check it is valid YAML.");
        return;
      }
      if (parsed.year == null) {
        setFileError('Missing required field: "year". Add "year: 10" (or the relevant year) at the top of the file.');
        return;
      }
      const entries: ImportEntry[] = parsed.templates || [];
      if (!Array.isArray(entries) || entries.length === 0) {
        setFileError("No templates found in file.");
        return;
      }
      setImportYear(Number(parsed.year));
      setImportEntries(entries);
      setImportPhase("preview");
      setImportStopError(null);
      setImportSucceeded(0);
      setImportFailed([]);
      setShowImportModal(true);
    };
    reader.readAsText(file);
  }

  async function runImport() {
    if (importYear === null) return;
    setImportPhase("importing");
    setImportStopError(null);
    const uniqueNames = Array.from(new Set(importEntries.map(e => e.skill_detail)));
    const resolvedMap: Record<string, { id: number; skill_id: number }> = {};
    for (const name of uniqueNames) {
      const url = `/api/skills/resolve_detail/?name=${encodeURIComponent(name)}&year=${importYear}`;
      const r = await apiFetch(url);
      if (!r.ok) {
        setImportStopError(
          `Import stopped — skill detail not found in Year ${importYear}:\n"${name}"\nCheck the name matches exactly and the year is correct.`
        );
        setImportPhase("done");
        return;
      }
      resolvedMap[name] = await r.json();
    }
    const total = importEntries.length;
    setImportProgress({ done: 0, total });
    const failed: FailedImport[] = [];
    let succeeded = 0;
    for (let i = 0; i < importEntries.length; i++) {
      const entry = importEntries[i];
      const detail = resolvedMap[entry.skill_detail];
      setImportProgress({ done: i, total });
      const r = await apiFetch("/api/templates/import_named/", {
        method: "POST",
        body: JSON.stringify({ skill_detail_id: detail.id, year: importYear, difficulty: entry.difficulty, yaml: entry.yaml }),
      });
      if (r.ok) { succeeded++; } else {
        const body = await r.text().catch(() => "");
        failed.push({ ...entry, error: `HTTP ${r.status}: ${body}` });
      }
      setImportProgress({ done: i + 1, total });
    }
    setImportSucceeded(succeeded);
    setImportFailed(failed);
    setImportPhase("done");
  }

  function closeImportModal() { setShowImportModal(false); }

  function downloadFailedYaml() {
    const yaml = `year: ${importYear}\n\ntemplates:\n` +
      importFailed.map(f =>
        `  - skill_detail: ${JSON.stringify(f.skill_detail)}\n` +
        `    difficulty: ${f.difficulty}\n` +
        `    yaml: |\n` +
        f.yaml.split("\n").map(l => `      ${l}`).join("\n")
      ).join("\n\n");
    const blob = new Blob([yaml], { type: "text/yaml" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = "failed_imports.yaml"; a.click();
    URL.revokeObjectURL(url);
  }

  const heading = grade ? `${parentName} — Year ${grade}` : parentName;

  const plainText = [
    heading,
    ...children.map(skill =>
      [skill.description, ...skill.details.map(d => ` - ${d.description}`)].join("\n")
    ),
  ].join("\n");

  const handleCopy = () => {
    navigator.clipboard.writeText(plainText).catch(() => {});
  };

  return (
    <Layout>
      <div className="container mt-4" style={{ maxWidth: 800 }}>

        <div className="d-flex align-items-center gap-3 mb-4 flex-wrap">
          <button className="btn btn-outline-secondary btn-sm" onClick={() => navigate("/skills")}>
            ← Back
          </button>
          <h4 className="mb-0 flex-grow-1">{heading}</h4>
          <input
            ref={importFileRef}
            type="file"
            accept=".yaml,.yml"
            style={{ display: "none" }}
            onChange={handleImportFileChange}
          />
          <button
            className="btn btn-outline-primary btn-sm"
            onClick={() => { setFileError(null); importFileRef.current?.click(); }}
          >
            Add multiple templates
          </button>
          <button className="btn btn-outline-secondary btn-sm" onClick={handleCopy}>
            Copy
          </button>
        </div>

        {fileError && (
          <div className="alert alert-danger py-2 px-3 mb-3" style={{ fontSize: 13 }}>
            {fileError}
          </div>
        )}

        {loading ? (
          <div className="d-flex justify-content-center py-5">
            <div className="spinner-border text-primary" role="status" />
          </div>
        ) : (
          <pre style={{ fontFamily: "inherit", fontSize: 14, lineHeight: 1.7, whiteSpace: "pre-wrap", margin: 0 }}>
            {children.map(skill => (
              <span key={skill.id}>
                <span
                  style={{ fontWeight: 600, cursor: "pointer" }}
                  onClick={() => navigate(`/skills/${skill.id}/overview`)}
                >
                  {skill.description}
                </span>
                {"\n"}
                {skill.details.map(d => (
                  <span key={d.id}>{` - ${d.description}\n`}</span>
                ))}
              </span>
            ))}
          </pre>
        )}

        {showImportModal && (
          <div className="modal show d-block" style={{ background: "rgba(0,0,0,0.4)" }}>
            <div className="modal-dialog modal-dialog-centered modal-dialog-scrollable modal-lg" onClick={e => e.stopPropagation()}>
              <div className="modal-content">
                <div className="modal-header">
                  <h5 className="modal-title">Import templates — Year {importYear}</h5>
                  {importPhase !== "importing" && (
                    <button className="btn-close" onClick={closeImportModal} />
                  )}
                </div>
                <div className="modal-body">
                  {importPhase === "preview" && (
                    <>
                      <p className="mb-3 text-muted" style={{ fontSize: 14 }}>
                        <strong>{importEntries.length} template{importEntries.length !== 1 ? "s" : ""}</strong> ready to import
                      </p>
                      <div style={{ maxHeight: 320, overflowY: "auto" }}>
                        <table className="table table-sm table-bordered mb-0" style={{ fontSize: 13 }}>
                          <thead className="table-light">
                            <tr><th>Skill detail</th><th style={{ width: 90 }}>Difficulty</th></tr>
                          </thead>
                          <tbody>
                            {importEntries.map((e, i) => (
                              <tr key={i}>
                                <td>{e.skill_detail}</td>
                                <td className="text-capitalize">{e.difficulty}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </>
                  )}
                  {importPhase === "importing" && (
                    <div className="text-center py-3">
                      <div className="spinner-border text-primary mb-3" role="status" />
                      <p className="mb-0">Importing {importProgress.done} of {importProgress.total}…</p>
                    </div>
                  )}
                  {importPhase === "done" && (
                    <>
                      {importStopError ? (
                        <div className="alert alert-danger" style={{ whiteSpace: "pre-line", fontSize: 14 }}>{importStopError}</div>
                      ) : (
                        <>
                          <p className="mb-2" style={{ fontSize: 14 }}><strong>Import complete — Year {importYear}</strong></p>
                          <ul className="list-unstyled mb-3" style={{ fontSize: 14 }}>
                            <li>Succeeded: <strong>{importSucceeded}</strong></li>
                            <li>Failed: <strong>{importFailed.length}</strong></li>
                          </ul>
                          {importFailed.length > 0 && (
                            <>
                              <p className="text-danger mb-1" style={{ fontSize: 13 }}>Failed entries:</p>
                              <ul className="mb-3" style={{ fontSize: 13 }}>
                                {importFailed.map((f, i) => (
                                  <li key={i}>{f.skill_detail} — {f.difficulty}</li>
                                ))}
                              </ul>
                              <button className="btn btn-outline-secondary btn-sm" onClick={downloadFailedYaml}>
                                Download failed_imports.yaml
                              </button>
                            </>
                          )}
                        </>
                      )}
                    </>
                  )}
                </div>
                <div className="modal-footer">
                  {importPhase === "preview" && (
                    <>
                      <button className="btn btn-secondary btn-sm" onClick={closeImportModal}>Cancel</button>
                      <button className="btn btn-primary btn-sm" onClick={runImport}>Import</button>
                    </>
                  )}
                  {importPhase === "done" && (
                    <button className="btn btn-secondary btn-sm" onClick={closeImportModal}>Close</button>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

      </div>
    </Layout>
  );
}
