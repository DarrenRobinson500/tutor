import { useState } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { Layout } from "./components/Layout";
import { apiFetch } from "../utils/apiFetch";
import { useYears } from "../utils/useYears";

export function StudentCreatePage() {
  const [searchParams] = useSearchParams();
  const tutorId = searchParams.get("tutor");
  const navigate = useNavigate();
  const years = useYears();

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [yearLevel, setYearLevel] = useState("");
  const [result, setResult] = useState<any>(null);

  async function handleSubmit(e: any) {
    e.preventDefault();

    const res = await apiFetch("/api/students/create_student/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name,
        email,
        password,
        year_level: yearLevel,
        tutor_id: tutorId,
      }),
    });

    const data = await res.json();
    setResult(data);

    if (tutorId) {
      setTimeout(() => {
        navigate(`/tutors/${tutorId}`);
      }, 1500);
    }
  }

  return (
    <Layout>
      <div className="container mt-4">
        <h2>Create New Student</h2>

        <form onSubmit={handleSubmit} className="mt-3">
          <div className="mb-3">
            <label className="form-label">Student Name</label>
            <input className="form-control"
                   value={name}
                   onChange={e => setName(e.target.value)} />
          </div>

          <div className="mb-3">
            <label className="form-label">Email (username)</label>
            <input className="form-control"
                   value={email}
                   onChange={e => setEmail(e.target.value)} />
          </div>

          <div className="mb-3">
            <label className="form-label">Password (optional)</label>
            <input className="form-control"
                   value={password}
                   onChange={e => setPassword(e.target.value)}
                   placeholder="Leave blank for auto-generated" />
          </div>

          <div className="mb-3">
            <label className="form-label">Year Level</label>
            <select
              className="form-select"
              value={yearLevel}
              onChange={e => setYearLevel(e.target.value)}
            >
              <option value="">— select —</option>
              {years.map(y => (
                <option key={y.code} value={y.code}>{y.label}</option>
              ))}
            </select>
          </div>

          <button className="btn btn-primary">Create Student</button>
        </form>

        {result && (
          <div className="alert alert-success mt-4">
            <h5>Student Created</h5>
            <p><strong>Name:</strong> {result.name}</p>
            <p><strong>Email:</strong> {result.email}</p>
          </div>
        )}
      </div>
    </Layout>
  );
}