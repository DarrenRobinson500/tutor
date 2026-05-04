import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Layout } from "./components/Layout";
import { apiFetch } from "../utils/apiFetch";

interface PostTuitionJob {
  id: number;
  student_id: number | null;
  student_first_name: string | null;
  student_last_name: string | null;
  booking_date: string | null;
  booking_time: string | null;
  triggered_at: string;
}

export function PostTuitionListPage() {
  const { id: tutorId } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [jobs, setJobs] = useState<PostTuitionJob[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiFetch("/api/jobs/")
      .then((r) => r.json())
      .then((data: any[]) => {
        const pending = data.filter((j) => j.job_type === "post_tuition_review");
        setJobs(pending);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  function formatDate(dateStr: string | null) {
    if (!dateStr) return "—";
    const d = new Date(dateStr + "T00:00:00");
    return d.toLocaleDateString("en-AU", { weekday: "short", day: "numeric", month: "short", year: "numeric" });
  }

  return (
    <Layout>
      <div className="container py-4" style={{ maxWidth: 780 }}>
        <h2 className="mb-1">Post Tuition Reviews</h2>
        <p className="text-muted mb-4">
          Complete the following reviews for recent sessions.
        </p>

        {loading && (
          <div className="text-center py-4">
            <div className="spinner-border spinner-border-sm text-secondary" role="status" />
          </div>
        )}

        {!loading && jobs.length === 0 && (
          <div className="text-muted text-center py-4">No pending post-tuition reviews.</div>
        )}

        {!loading && jobs.length > 0 && (
          <div className="list-group">
            {jobs.map((job) => (
              <button
                key={job.id}
                className="list-group-item list-group-item-action d-flex align-items-center justify-content-between"
                onClick={() =>
                  navigate(
                    `/tutors/${tutorId}/post-tuition/review?job_id=${job.id}&student_id=${job.student_id ?? ""}${job.booking_date ? `&booking_date=${job.booking_date}` : ""}`
                  )
                }
              >
                <div>
                  <div className="fw-semibold">
                    {job.student_first_name ?? "Unknown"} {job.student_last_name ?? ""}
                  </div>
                  <div className="text-muted" style={{ fontSize: 13 }}>
                    {formatDate(job.booking_date)}
                    {job.booking_time ? ` at ${job.booking_time}` : ""}
                  </div>
                </div>
                <span className="text-muted" style={{ fontSize: 13 }}>Review →</span>
              </button>
            ))}
          </div>
        )}
      </div>
    </Layout>
  );
}
