import React, { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { SkillsMatrix } from "./components/SkillsMatrix";
import { Layout } from "./components/Layout";
import { apiFetch } from "../utils/apiFetch";

export default function SkillsS6Page() {
  const navigate = useNavigate();
  const [message, setMessage] = useState("");
  const [importingSkills, setImportingSkills] = useState(false);
  const [importingYears, setImportingYears] = useState(false);
  const skillsUploadRef = useRef<HTMLInputElement>(null);
  const yearsUploadRef = useRef<HTMLInputElement>(null);

  const storedUser = localStorage.getItem("user");
  const user = storedUser ? JSON.parse(storedUser) : null;
  const canEditSyllabus = user?.role === "admin" || user?.edit_syllabus === true;

  const handleSkillsDownload = () => {
    apiFetch("/api/skills/export_all/?course_set=s6")
      .then(res => {
        const disposition = res.headers.get("Content-Disposition") ?? "";
        const match = disposition.match(/filename="([^"]+)"/);
        const filename = match ? match[1] : "skills_s6.yaml";
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

  const handleYearsUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    e.target.value = "";
    setImportingYears(true);
    const form = new FormData();
    form.append("file", file);
    apiFetch("/api/years/import_years/", { method: "POST", body: form })
      .then(res => res.json())
      .then(data => {
        if (data.error) {
          setMessage(`Years upload failed: ${data.error}`);
        } else {
          setMessage(`Years import complete — ${data.status} (${data.count} years processed)`);
        }
      })
      .catch(() => setMessage("Years upload failed"))
      .finally(() => setImportingYears(false));
  };

  return (
    <Layout>
      <div className="container mt-4">
        {message && <div className="alert alert-info">{message}</div>}

        <h1>Skills — Stage 6</h1>
        <div className="d-flex gap-2 mb-3">
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
              Download S6 Skills
            </button>
            <button
              className="btn btn-outline-secondary"
              onClick={() => skillsUploadRef.current?.click()}
              disabled={importingSkills}
            >
              {importingSkills ? "Uploading…" : "Upload S6 Skills"}
            </button>
            <input
              ref={skillsUploadRef}
              type="file"
              accept=".yaml,.yml,.json"
              className="d-none"
              onChange={handleSkillsUpload}
            />
            <button
              className="btn btn-outline-secondary"
              onClick={() => yearsUploadRef.current?.click()}
              disabled={importingYears}
            >
              {importingYears ? "Uploading…" : "Upload Years"}
            </button>
            <input
              ref={yearsUploadRef}
              type="file"
              accept=".yaml,.yml"
              className="d-none"
              onChange={handleYearsUpload}
            />
          </>}
        </div>

        <SkillsMatrix courseSet="s6" prefKey="skills_s6" />
      </div>
    </Layout>
  );
}
