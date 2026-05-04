import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { apiFetch } from "../../utils/apiFetch";
import type { Student } from "./TutorStudentList";

interface DerivedJob {
  kind: "derived";
  label: string;
  to: string;
}

interface StoredJob {
  kind: "stored";
  id: number;
  label: string;
  to: string;
}

type Job = DerivedJob | StoredJob;

const JOB_LABELS: Record<string, (firstName: string | null) => string> = {
  post_tuition_review: (n) => `Post Tuition Review${n ? ` — ${n}` : ""}`,
  send_progress_message: (n) => `Send progress message for ${n}`,
  review_focus_area: (n) => `Review focus area for ${n}`,
  review_available_hours: () => `Review my available hours`,
  setup_weekly_session: (n) => `Set up weekly session${n ? ` for ${n}` : ""}`,
};

const JOB_LINKS: Record<string, (tutorId: string, studentId: number, jobId: number) => string> = {
  post_tuition_review: (tutorId, studentId, jobId) =>
    `/tutors/${tutorId}/post-tuition/review?student_id=${studentId}&job_id=${jobId}`,
  send_progress_message: (tutorId) => `/tutors/${tutorId}/sms`,
  review_focus_area: (tutorId, studentId) =>
    `/students/${studentId}/focus-areas?returnTo=/tutors/${tutorId}`,
  review_available_hours: (tutorId) => `/tutors/${tutorId}/schedule`,
  setup_weekly_session: (tutorId) => `/tutors/${tutorId}/booking`,
};

export function TutorJobsPanel({ tutorId }: { tutorId: string }) {
  const [jobs, setJobs] = useState<Job[]>([]);

  useEffect(() => {
    load();
  }, [tutorId]); // eslint-disable-line react-hooks/exhaustive-deps

  async function load() {
    const [students, storedRaw]: [Student[], any[]] = await Promise.all([
      apiFetch(`/api/tutors/${tutorId}/students/`).then(r => r.json()),
      apiFetch(`/api/jobs/`).then(r => r.json()),
    ]);

    const activeStudents = students.filter(s => s.active);
    const activeStudentIds = new Set(activeStudents.map(s => s.user_id));

    const derived: DerivedJob[] = [];

    // Check if tutor has any availability set
    const availData = await apiFetch(`/api/tutors/${tutorId}/availability/`)
      .then(r => r.json())
      .catch(() => ({ availability: [] }));
    if (!(availData.availability?.length > 0)) {
      derived.push({
        kind: "derived",
        label: "Set available hours",
        to: `/tutors/${tutorId}/schedule`,
      });
    }

    activeStudents.forEach(s => {
      if (!s.year_level) {
        derived.push({
          kind: "derived",
          label: `Add ${s.first_name}'s grade`,
          to: `/students/${s.user_id}/edit?returnTo=/tutors/${tutorId}`,
        });
      }
    });

    const focusRes = await Promise.all(
      activeStudents
        .filter(s => s.year_level)
        .map(s =>
          apiFetch(`/api/focus-areas/?student_id=${s.user_id}`)
            .then(r => r.json())
            .then((areas: any[]) => ({ student: s, hasFocus: areas.length > 0 }))
        )
    );

    focusRes.forEach(({ student: s, hasFocus }) => {
      if (!hasFocus) {
        derived.push({
          kind: "derived",
          label: `Set focus area for ${s.first_name}`,
          to: `/students/${s.user_id}/focus-areas?returnTo=/tutors/${tutorId}`,
        });
      }
    });

    const stored: StoredJob[] = storedRaw.filter((j: any) =>
      j.student_id == null || activeStudentIds.has(j.student_id)
    ).map((j: any) => {
      let to = (JOB_LINKS[j.job_type] ?? (() => `/tutors/${tutorId}`))(String(j.tutor_id), j.student_id, j.id);
      if (j.job_type === 'post_tuition_review' && j.booking_date) {
        to += `&booking_date=${j.booking_date}`;
      }
      return {
        kind: "stored",
        id: j.id,
        label: (JOB_LABELS[j.job_type] ?? ((n: string) => j.job_type))(j.student_first_name),
        to,
      };
    });

    setJobs([...derived, ...stored]);
  }

  if (jobs.length === 0) return null;

  return (
    <div className="mb-4">
      <h4>Jobs</h4>
      <div className="row row-cols-4 gx-4 gy-2">
        {jobs.map((job, i) => (
          <div key={i} className="col">
            {job.kind === "stored" ? (
              <Link to={job.to} className="text-decoration-none d-block">
                <div
                  className="px-3 py-2 rounded fw-semibold"
                  style={{ background: "#fff3cd", border: "1px solid #ffc107" }}
                >
                  {job.label}
                </div>
              </Link>
            ) : (
              <Link to={job.to} className="text-decoration-none d-block">
                <div
                  className="px-3 py-2 rounded fw-semibold"
                  style={{ background: "#fff3cd", border: "1px solid #ffc107" }}
                >
                  {job.label}
                </div>
              </Link>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
