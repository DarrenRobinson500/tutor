import React, { useEffect, useRef, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { SkillsMatrix } from "./components/SkillsMatrix";
import { Layout } from "./components/Layout";
import { apiFetch } from "../utils/apiFetch";
import { useSkillsApi, Skill } from "../api/useSkillsApi";


export default function SkillsPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [skill, setSkill] = useState<any>(null);
  const { listSkills, loadSyllabus, loading } = useSkillsApi();

  const storedUser = localStorage.getItem("user");
  const user = storedUser ? JSON.parse(storedUser) : null;
  const canEditSyllabus = user?.role === "admin" || user?.edit_syllabus === true;
  const [message, setMessage] = useState("");
  const [skills, setSkills] = useState<Skill[]>([]);
  const [importingSkills, setImportingSkills] = useState(false);
  const skillsUploadRef = useRef<HTMLInputElement>(null);

  // Load skill
  useEffect(() => {
    if (!id) { setSkill(null); return; }
    apiFetch(`/api/skills/${Number(id)}/`)
      .then(res => res.json())
      .then(data => setSkill(data));
  }, [id]);

  if (id && !skill) {
    return <Layout><div className="container mt-4">Loading...</div></Layout>;
  }

  const handleSkillsDownload = () => {
    apiFetch("/api/skills/export_all/")
      .then(res => {
        const disposition = res.headers.get("Content-Disposition") ?? "";
        const match = disposition.match(/filename="([^"]+)"/);
        const filename = match ? match[1] : "skills.yaml";
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
      .catch(() => setMessage("Skills download failed"));
  };

  const handleSkillsUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    e.target.value = "";
    setImportingSkills(true);
    const form = new FormData();
    form.append("file", file);
    apiFetch("/api/skills/import_bulk/", { method: "POST", body: form })
      .then(res => res.json())
      .then(data => {
        if (data.error) {
          setMessage(`Skills upload failed: ${data.error}`);
        } else {
          setMessage(`Skills import complete — ${data.status} (${data.seen} nodes processed)`);
        }
      })
      .catch(() => setMessage("Skills upload failed"))
      .finally(() => setImportingSkills(false));
  };

  const handleLoad = () => {
    loadSyllabus()
      .then(() => {
        setMessage("Syllabus loaded successfully");
        return listSkills(null);
      })
      .then(setSkills)
      .catch((err) => {
        setMessage(err.error || "Failed to load syllabus");
      });
  };

  return (
    <Layout>
      <div className="container mt-4">

        {message && <div className="alert alert-info">{message}</div>}

        <h1>Skills</h1>
        <div className="d-flex gap-2 mb-3">
          <button
            className="btn btn-outline-success"
            onClick={handleLoad}
            disabled={loading}
          >
            {loading ? "Loading…" : "Load Syllabus"}
          </button>
          <button
            className="btn btn-outline-success"
            onClick={() => navigate("/templates/new")}
          >
            + Create New Template from Image
          </button>
          {canEditSyllabus && <>
            <button
              className="btn btn-outline-secondary"
              onClick={handleSkillsDownload}
            >
              Download Skills
            </button>
            <button
              className="btn btn-outline-secondary"
              onClick={() => skillsUploadRef.current?.click()}
              disabled={importingSkills}
            >
              {importingSkills ? "Uploading…" : "Upload Skills"}
            </button>
            <input
              ref={skillsUploadRef}
              type="file"
              accept=".yaml,.yml,.json"
              className="d-none"
              onChange={handleSkillsUpload}
            />
          </>}
        </div>

        <SkillsMatrix courseSet="k10" />
      </div>
    </Layout>
  );
}
