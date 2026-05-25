/* eslint-disable react-hooks/exhaustive-deps */

import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { Layout } from "./components/Layout";
import { TutorStudentList } from "./components/TutorStudentList";
import { TutorJobsPanel } from "./components/TutorJobsPanel";
import { WeeklyCalendar } from "./components/WeeklyCalendar";
import { WeekData } from "../types/weekly";
import { apiFetch } from "../utils/apiFetch"

function getSundayStart(date: Date): string {
  const d = new Date(date);
  const day = d.getDay();
  const sunday = new Date(d);
  sunday.setDate(d.getDate() - day);
  return sunday.toISOString().slice(0, 10);
}

interface FeedbackItem {
  id: number;
  rating: number;
  rating_comment: string;
  student_name: string;
  parent_name: string;
  session_date: string;
  paid_at: string | null;
}

function Stars({ value }: { value: number }) {
  return (
    <span style={{ color: "#f59e0b", letterSpacing: 1 }}>
      {[1, 2, 3, 4, 5].map(n => (
        <span key={n} style={{ opacity: n <= value ? 1 : 0.2 }}>★</span>
      ))}
    </span>
  );
}

function RecentFeedback({ tutorId }: { tutorId: string }) {
  const [items, setItems] = useState<FeedbackItem[] | null>(null);

  useEffect(() => {
    apiFetch(`/api/tutors/${tutorId}/feedback/`)
      .then(r => r.json())
      .then(setItems)
      .catch(() => setItems([]));
  }, [tutorId]);

  if (items === null) return null;
  if (items.length === 0) return null;

  const avg = items.reduce((s, i) => s + i.rating, 0) / items.length;

  return (
    <div className="mt-4">
      <div className="d-flex align-items-baseline gap-2 mb-2">
        <h4 className="mb-0">Recent Feedback</h4>
        <span className="text-muted" style={{ fontSize: 13 }}>
          avg <strong style={{ color: "#f59e0b" }}>{avg.toFixed(1)}</strong> from {items.length} review{items.length !== 1 ? "s" : ""}
        </span>
      </div>
      <div className="d-flex flex-column gap-2">
        {items.slice(0, 5).map(item => (
          <div
            key={item.id}
            className="rounded p-3"
            style={{ background: "#fffbf5", border: "1px solid #e8e0d6", fontSize: 14 }}
          >
            <div className="d-flex justify-content-between align-items-center mb-1">
              <Stars value={item.rating} />
              <span className="text-muted" style={{ fontSize: 12 }}>
                {item.student_name && <>{item.student_name} · </>}
                {item.session_date
                  ? new Date(item.session_date).toLocaleDateString("en-AU", { day: "numeric", month: "short", year: "numeric" })
                  : ""}
              </span>
            </div>
            {item.rating_comment && (
              <p className="mb-0" style={{ color: "#444", fontStyle: "italic" }}>
                "{item.rating_comment}"
              </p>
            )}
            {item.parent_name && (
              <p className="mb-0 mt-1" style={{ fontSize: 12, color: "#8A7F74" }}>{item.parent_name}</p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

export function TutorHomePage() {
  const { id } = useParams();
  const [tutor, setTutor] = useState<any>(null);
  const [week, setWeek] = useState<WeekData | null>(null);
  const [weekStart, setWeekStart] = useState<string | null>(null);
  const [lookingForStudents, setLookingForStudents] = useState<boolean>(false);

  useEffect(() => {
    apiFetch(`/api/tutors/${id}/home/`)
      .then(res => res.json())
      .then(data => {
        setTutor(data);
        setLookingForStudents(data.looking_for_students ?? false);
      })
      .catch(err => {
        console.error("Failed to load tutor home:", err);
        setTutor(null);
      });
  }, [id]);

  async function toggleLooking() {
    const res = await apiFetch(`/api/tutors/${id}/toggle_looking/`, { method: "POST" });
    const data = await res.json();
    setLookingForStudents(data.looking_for_students);
  }

  if (!tutor) return <div className="container mt-4">Loading…</div>;

  return (
    <Layout>
      <div className="container mt-4">
        <div className="d-flex align-items-center gap-2 mb-1">
          <h2 className="mb-0">{tutor.name}</h2>
          {!tutor.approved && (
            <span className="badge text-bg-warning">Pending approval</span>
          )}
        </div>
        <p>
          Email: {tutor.email}<br/>
          Mobile: {tutor.mobile || "Not set"}<br/>
          Address: {tutor.address || "Not set"}
        </p>

        <div className="d-flex gap-2 mb-3">
          <button
            className={`btn ${lookingForStudents ? "btn-primary" : "btn-outline-primary"}`}
            onClick={toggleLooking}
          >
            {lookingForStudents ? "Looking for students" : "Not looking for students"}
          </button>
          <button
            className="btn btn-outline-primary"
            onClick={() => window.location.href = `/tutors/${id}/edit?returnTo=/tutors/${id}`}
          >
            Edit My Details
          </button>
        </div>
        <hr />

        <TutorJobsPanel tutorId={id!} />

        <RecentFeedback tutorId={id!} />

        <h4 className="mt-4">Students</h4>
        <div className="d-flex justify-content-between align-items-center mb-3">
          <a className="btn btn-outline-primary btn-sm" href={`/admin/students/new?tutor=${id}`}>
            + New Student
          </a>
        </div>

        <TutorStudentList tutorId={id!} />

        <hr />
      </div>
    </Layout>
  );
}
