import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { apiFetch } from "../../utils/apiFetch";

export interface Student {
  user_id: number;
  profile_id: number;
  first_name: string;
  last_name: string;
  mobile: string;
  email: string;
  active: boolean;
  year_level: string | null;
  area_of_study: string | null;
  syllabus_percent: number | null;
  next_booking: { start_iso: string; booking_type: string } | null;
}

export function TutorStudentList({ tutorId }: { tutorId: string }) {
  const [students, setStudents] = useState<Student[]>([]);
  const navigate = useNavigate();

  useEffect(() => {
    apiFetch(`/api/tutors/${tutorId}/students/`)
      .then(res => res.json())
      .then(data => setStudents(data));
  }, [tutorId]);

  function formatMobile(m: string | null | undefined) {
    if (!m) return "";
    const digits = m.replace(/\D/g, "");
    if (digits.length !== 10) return m; // fallback
    return `${digits.slice(0,4)} ${digits.slice(4,7)} ${digits.slice(7)}`;
  }

  function formatBooking(b: Student["next_booking"]) {
    if (!b) return "";
    const d = new Date(b.start_iso);
    return d.toLocaleDateString("en-AU", { weekday: "short", day: "numeric", month: "short" })
      + " " + d.toLocaleTimeString("en-AU", { hour: "numeric", minute: "2-digit", hour12: true }).toLowerCase();
  }

  return (
    <ul className="list-group mt-3">
      <li className="list-group-item">
        <div className="row fw-bold">
          <div className="col-2">Name</div>
          <div className="col-2">Mobile</div>
          <div className="col-1">Year</div>
          <div className="col-1">Progress</div>
          <div className="col-2">Next Booking</div>
          <div className="col-4">Actions</div>
        </div>
      </li>

      {students
        .slice()
        .sort((a, b) => {
          if (a.active !== b.active) return a.active ? -1 : 1;
          const nameA = `${a.first_name} ${a.last_name}`.toLowerCase();
          const nameB = `${b.first_name} ${b.last_name}`.toLowerCase();
          return nameA.localeCompare(nameB);
        })
        .map((s) => (
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

              <div className="col-2">{formatMobile(s.mobile)}</div>

              <div className="col-1">{s.year_level || ""}</div>
              <div className="col-1">{s.syllabus_percent != null ? `${s.syllabus_percent}%` : ""}</div>
              <div className="col-2" style={{ fontSize: 13, color: "#555" }}>{formatBooking(s.next_booking)}</div>

              <div className="col-4 d-flex flex-wrap gap-2">
                <Link
                  className={`btn btn-sm ${s.active ? "btn-outline-primary" : "btn-outline-primary disabled"}`}
                  to={`/students/${s.user_id}`}
                >
                  {s.first_name}'s Home Page
                </Link>

                <Link
                  className="btn btn-sm btn-outline-primary"
                  to={`/students/${s.user_id}/edit?returnTo=/tutors/${tutorId}`}
                >
                  Edit
                </Link>

                <button
                  className="btn btn-sm btn-outline-primary"
                  onClick={() => navigate(`/session/t${tutorId}-s${s.user_id}`)}
                  title={`Start online session with ${s.first_name}`}
                >
                  Call
                </button>

                {s.year_level ? (
                  <button
                    className="btn btn-sm btn-outline-primary"
                    onClick={() => navigate(`/students/${s.user_id}/focus-areas?returnTo=/tutors/${tutorId}`)}
                  >
                    Set focus areas
                  </button>
                ) : (
                  <Link
                    className="btn btn-sm btn-outline-primary"
                    to={`/students/${s.user_id}/edit?returnTo=/tutors/${tutorId}`}
                  >
                    Set grade
                  </Link>
                )}
              </div>
            </div>
          </li>
        ))}
    </ul>
  );
}