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

  return (
  <Layout>
    <div className="container mt-4">
      <div className="d-flex justify-content-between align-items-center mb-3">
        <h2>Tutors</h2>
        <a className="btn btn-outline-primary" href="/admin/tutors/new">+ New Tutor</a>
      </div>

      <ul className="list-group mt-3">
        {Array.isArray(tutors) && tutors.map((t: any) => (
          <li key={t.id} className="list-group-item d-flex justify-content-between">
            <span>{t.first_name} {t.last_name}</span>
            <a className="btn btn-outline-primary btn-sm" href={`/tutor/${t.id}`}>
              View Tutor Home
            </a>
          </li>
        ))}

      </ul>
    </div>
  </Layout>
  );
}