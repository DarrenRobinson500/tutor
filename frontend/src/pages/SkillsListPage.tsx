// src/pages/SkillsListPage.tsx
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useSkillsApi, Skill } from "../api/useSkillsApi";

interface SkillsListProps {
  parentId?: number;
  onSelect: (id: number) => void;
}


export function SkillsListPage({ parentId, onSelect }: SkillsListProps) {
  const navigate = useNavigate();
  const { listSkills, loadSyllabus, loading, error } = useSkillsApi();
  const [skills, setSkills] = useState<Skill[]>([]);
  const [message, setMessage] = useState("");

  useEffect(() => {
    listSkills(parentId).then(setSkills);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [parentId]);

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

    <div className="container mt-4">
      <button className="btn btn-primary mb-3" onClick={handleLoad}>Load Syllabus</button>

      {message && <div className="alert alert-info">{message}</div>}

      <h1 className="h3">Skills</h1>

      {loading && <p>Loading…</p>}
      {error && <p className="text-danger">{error}</p>}

      <table className="table table-hover">
        <thead>
          <tr>
            <th>Code</th>
            <th>Description</th>
            <th>Children</th>
            <th>Coverage</th>
          </tr>
        </thead>
        <tbody>
          {skills.map((skill) => (
            <tr
              key={skill.id}
              style={{ cursor: "pointer" }}
              onClick={() => navigate(`/skills/${skill.id}`)}
            >
              <td>{skill.code}</td>
              <td>{skill.description}</td>
              <td>{skill.children_count}</td>
              <td>{skill.detail_total > 0 ? `${skill.detail_covered} / ${skill.detail_total}` : "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>

  );
}