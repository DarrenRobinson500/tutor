import { useEffect, useState } from "react";
import { Layout } from "./components/Layout";
import { apiFetch } from "../utils/apiFetch"


interface Tutor {
  id: number;
  first_name: string;
  last_name: string;
  email: string;
  username: string;
  role: string;
  assisted_assessment: boolean;
}

export function TutorListPage() {
  const [tutors, setTutors] = useState<Tutor[]>([]);

  useEffect(() => {
    apiFetch("/api/tutors/")
      .then(res => res.json())
      .then(data => {
        console.log("Tutor API response:", data);
        setTutors(Array.isArray(data) ? data : []);
      })
      .catch(() => setTutors([]));
  }, []);

  async function toggleAssistedAssessment(tutor: Tutor) {
    const res = await apiFetch(`/api/tutors/${tutor.id}/toggle_assisted_assessment/`, { method: "POST" });
    const data = await res.json();
    setTutors(prev => prev.map(t =>
      t.id === tutor.id ? { ...t, assisted_assessment: data.assisted_assessment } : t
    ));
  }

  return (
  <Layout>
    <div className="container mt-4">
      <div className="d-flex justify-content-between align-items-center mb-3">
        <h2>Tutors</h2>
        <a className="btn btn-outline-primary" href="/admin/tutors/new">+ New Tutor</a>
      </div>

      <table className="table table-bordered align-middle mt-3">
        <thead className="table-light">
          <tr>
            <th>Name</th>
            <th style={{ width: 200 }}>Assisted Assessment</th>
            <th style={{ width: 160 }}></th>
          </tr>
        </thead>
        <tbody>
          {tutors.map((t) => (
            <tr key={t.id}>
              <td>{t.first_name} {t.last_name}</td>
              <td>
                <div className="form-check form-switch">
                  <input
                    className="form-check-input"
                    type="checkbox"
                    role="switch"
                    checked={t.assisted_assessment}
                    onChange={() => toggleAssistedAssessment(t)}
                  />
                  <label className="form-check-label">
                    {t.assisted_assessment ? "Available" : "Not available"}
                  </label>
                </div>
              </td>
              <td>
                <a className="btn btn-outline-primary btn-sm" href={`/tutor/${t.id}`}>
                  View Tutor Home
                </a>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  </Layout>
  );
}
