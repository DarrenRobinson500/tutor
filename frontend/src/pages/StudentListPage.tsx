import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Layout } from "./components/Layout";
import { apiFetch } from "../utils/apiFetch";

interface Student {
  user_id: number;
  profile_id: number;
  first_name: string;
  last_name: string;
  mobile: string | null;
  email: string;
  active: boolean;
  year_level: string | null;
  area_of_study: string | null;
  tutor_name: string | null;
  tutor_id: number | null;
}

function formatMobile(m: string | null | undefined) {
  if (!m) return "";
  const digits = m.replace(/\D/g, "");
  if (digits.length !== 10) return m;
  return `${digits.slice(0, 4)} ${digits.slice(4, 7)} ${digits.slice(7)}`;
}

export function StudentListPage() {
  const [students, setStudents] = useState<Student[]>([]);

  useEffect(() => {
    apiFetch("/api/students/")
      .then(res => res.json())
      .then(data => setStudents(data));
  }, []);

  return (
    <Layout>
      <div className="container mt-4">
        <div className="d-flex justify-content-between align-items-center mb-3">
          <h2>Students</h2>
        </div>

        <ul className="list-group mt-3">
          <li className="list-group-item">
            <div className="row fw-bold">
              <div className="col-2">Name</div>
              <div className="col-2">Tutor</div>
              <div className="col-2">Mobile</div>
              <div className="col-1">Year</div>
              <div className="col-1">Area</div>
              <div className="col-4">Actions</div>
            </div>
          </li>

          {students.map((s) => (
            <li
              key={s.user_id}
              className={`list-group-item ${!s.active ? "bg-light text-muted" : ""}`}
            >
              <div className="row align-items-center">
                <div className="col-2 fw-bold">
                  {s.first_name} {s.last_name}
                  {!s.active && (
                    <span className="badge bg-secondary ms-2">inactive</span>
                  )}
                </div>

                <div className="col-2 text-muted" style={{ fontSize: 13 }}>
                  {s.tutor_name || <span className="text-danger">Unassigned</span>}
                </div>

                <div className="col-2">{formatMobile(s.mobile)}</div>

                <div className="col-1">{s.year_level || ""}</div>
                <div className="col-1">{s.area_of_study || ""}</div>

                <div className="col-4 d-flex flex-row gap-2">
                  <Link
                    className={`btn btn-sm ${s.active ? "btn-outline-primary" : "btn-outline-secondary disabled"}`}
                    to={`/students/${s.user_id}`}
                    style={{ minWidth: "60px", whiteSpace: "nowrap", textAlign: "center" }}
                  >
                    View
                  </Link>
                  <Link
                    className="btn btn-sm btn-outline-secondary"
                    to={`/students/${s.user_id}/edit?returnTo=/admin/students`}
                    style={{ minWidth: "40px", whiteSpace: "nowrap", textAlign: "center" }}
                  >
                    Edit
                  </Link>
                </div>
              </div>
            </li>
          ))}
        </ul>
      </div>
    </Layout>
  );
}
