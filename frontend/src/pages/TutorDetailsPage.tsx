import { useEffect, useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { Layout, PageHeader } from "./components/Layout";
import { apiFetch } from "../utils/apiFetch";

function DetailCell({ label, value }: { label: string; value: string }) {
  return (
    <div className="col-6 mb-3">
      <div style={{ fontSize: 12, color: "#8C8179", marginBottom: 2 }}>{label}</div>
      <div style={{ fontSize: 15, color: "#2D2D2D" }}>{value || "Not set"}</div>
    </div>
  );
}

export function TutorDetailsPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [tutor, setTutor] = useState<any>(null);
  const [lookingForStudents, setLookingForStudents] = useState(false);

  useEffect(() => {
    apiFetch(`/api/tutors/${id}/home/`)
      .then(r => r.json())
      .then(data => {
        setTutor(data);
        setLookingForStudents(data.looking_for_students ?? false);
      });
  }, [id]);

  async function toggleLooking() {
    const res = await apiFetch(`/api/tutors/${id}/toggle_looking/`, { method: "POST" });
    const data = await res.json();
    setLookingForStudents(data.looking_for_students);
  }

  if (!tutor) {
    return (
      <Layout>
        <div className="container mt-4">Loading…</div>
      </Layout>
    );
  }

  return (
    <Layout header={<PageHeader title="My Details" />}>
      <div className="container mt-4" style={{ maxWidth: 640 }}>
        {!tutor.approved && (
          <div className="alert alert-warning mb-3">Your account is pending approval.</div>
        )}

        <div className="row">
          <DetailCell label="Name" value={tutor.name} />
          <DetailCell label="Email" value={tutor.email} />
          <DetailCell label="Mobile" value={tutor.mobile} />
          <DetailCell label="Address" value={tutor.address} />
          <DetailCell label="Default Session Length" value={tutor.default_session_minutes ? `${tutor.default_session_minutes} minutes` : ""} />
          <DetailCell label="Buffer Between Sessions" value={tutor.buffer_minutes != null ? `${tutor.buffer_minutes} minutes` : ""} />
          <DetailCell label="Default Hourly Rate" value={tutor.default_hourly_rate != null ? `$${tutor.default_hourly_rate}` : ""} />
        </div>

        <div className="d-flex gap-2 mt-3 flex-wrap">
          <button
            className={`btn btn-sm ${lookingForStudents ? "btn-primary" : "btn-outline-primary"}`}
            onClick={toggleLooking}
          >
            {lookingForStudents ? "Looking for students" : "Not looking for students"}
          </button>
          <button
            className="btn btn-outline-primary btn-sm"
            onClick={() => navigate(`/tutors/${id}/edit?returnTo=/tutors/${id}/details`)}
          >
            Edit My Details
          </button>
          <Link to={`/tutors/${id}/schedule`} className="btn btn-outline-primary btn-sm">
            ⏱ Set my available hours
          </Link>
        </div>
      </div>
    </Layout>
  );
}
