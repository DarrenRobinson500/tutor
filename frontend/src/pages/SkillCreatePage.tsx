// src/pages/SkillCreatePage.tsx
import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useSkillsApi } from "../api/useSkillsApi";
import { Layout } from "./components/Layout";


export function SkillCreatePage() {
  const { parentId } = useParams();
  const parent = parentId ? Number(parentId) : null;

  const navigate = useNavigate();
  const { createSkill, loading, error } = useSkillsApi();

  const [code, setCode] = useState("");
  const [description, setDescription] = useState("");
  const [grade, setGrade] = useState(5);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    await createSkill({
      parent,
      code,
      description,
      grade_level: grade,
      order_index: 0,
    });
    navigate(parent ? `/skills/${parent}` : "/skills");
  }

  return (
  <Layout>
    <div className="container mt-4">
      <h1 className="h4">Add Skill</h1>

      {error && <p className="text-danger">{error}</p>}

      <form onSubmit={handleSubmit}>
        <div className="mb-3">
          <label>Code</label>
          <input
            className="form-control"
            value={code}
            onChange={(e) => setCode(e.target.value)}
          />
        </div>

        <div className="mb-3">
          <label>Description</label>
          <textarea
            className="form-control"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </div>

        <div className="mb-3">
          <label>Grade Level</label>
          <input
            type="number"
            className="form-control"
            value={grade}
            onChange={(e) => setGrade(Number(e.target.value))}
          />
        </div>

        <button className="btn btn-primary" disabled={loading}>
          Create
        </button>
      </form>
    </div>
  </Layout>
  );
}