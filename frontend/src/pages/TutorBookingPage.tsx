import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { Layout } from "./components/Layout";
import { ExistingBookingsWeek } from "./components/ExistingBookingsWeek";
import { apiFetch } from "../utils/apiFetch";

interface StudentInfo {
  user_id: number;
  first_name: string;
  last_name: string;
  email: string;
  year_level: string;
  area_of_study: string;
  next_ad_hoc_booking: any;
  next_weekly_booking: any;
}

interface WeekData {
  [date: string]: {
    day_status: "past" | "today" | "future";
    bookings: any[];
  };
}

export function TutorBookingPage() {
  const { id } = useParams();
  const [students, setStudents] = useState<StudentInfo[]>([]);
  const [selectedStudentId, setSelectedStudentId] = useState<number | null>(null);
  const [week1, setWeek1] = useState<WeekData | null>(null);
  const [week2, setWeek2] = useState<WeekData | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [weeklyDay, setWeeklyDay] = useState<number>(1); // Monday default
  const [weeklyTime, setWeeklyTime] = useState<string>("16:00");
  const [weeklyLoading, setWeeklyLoading] = useState(false);
  const [adhocStudentId, setAdhocStudentId] = useState<number | null>(null);
  const [adhocDate, setAdhocDate] = useState("");
  const [adhocTime, setAdhocTime] = useState("16:00");
  const [adhocLoading, setAdhocLoading] = useState(false);
  const [smsJobs, setSmsJobs] = useState<any[]>([]);
  const [smsMessages, setSmsMessages] = useState<any[]>([]);
  const [smsLoading, setSmsLoading] = useState(false);
  const [smsActive, setSmsActive] = useState<boolean | null>(null);

  const [editing, setEditing] = useState<{
    date: string;
    booking: any;
    index: number;
  } | null>(null);

  const [editStart, setEditStart] = useState("");
  const [editLoading, setEditLoading] = useState(false);
  const [confirmLoading, setConfirmLoading] = useState<number | null>(null);


  // Load booking and message data

  const load = async () => {
    if (!id) return;

    setLoading(true);
    setSmsLoading(true);

    try {
      const [bookingRes, smsRes] = await Promise.all([
        apiFetch(`/api/tutors/${id}/booking/`),
        apiFetch(`/api/tutors/${id}/sms/activity/`)
      ]);

      const bookingData = await bookingRes.json();
      const smsData = await smsRes.json();

      // Booking data
      setStudents(bookingData.students || []);
      setWeek1(bookingData.week1 || null);
      setWeek2(bookingData.week2 || null);

      // SMS data
      setSmsJobs(smsData.jobs || []);
      setSmsMessages(smsData.messages || []);
      setSmsActive(smsData.active);
      console.log("Set SMS Active:", smsActive)
      console.log("Set SMS Messages:", smsMessages)


    } finally {
      setLoading(false);
      setSmsLoading(false);
    }
  };


  useEffect(() => {
    load();
  }, [id]);

  // Timer

  useEffect(() => {
    const interval = setInterval(() => {
      setSmsJobs(jobs =>
        jobs.map(j => ({
          ...j,
          time_until_sent_seconds: j.time_until_sent_seconds - 1
        }))
      );
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  // Booking actions

  const openEditor = (date: string, booking: any, index: number) => {
    setEditing({ date, booking, index });
    setEditStart(booking.start_time);
  };

// -----------------UNIFIED FUNCTIONS (CONFIRM, CREATE, EDIT, SKIP) -------------------

  const handleBookingAction = async (
    bookingId: number,
    bookingType: string,
    action: "create" | "confirm" | "delete" | "skip" | "remove_skip" | "edit",
    extra: any = {}
  ) => {
    try {
      const res = await apiFetch(`/api/tutors/${id}/booking_action/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          id: bookingId,
          type: bookingType,
          action,
          ...extra,   // <‑‑ weekly/adhoc edit fields go here
        }),
      });

      const data = await res.json();

      if (!data.ok) {
        setMessage(data.error || "Action failed.");
        return;
      }

      if (action === "create") {
        setMessage("Booking created.");
      } else if (action === "confirm") {
        setMessage(data.confirmed ? "Booking confirmed." : "Booking unconfirmed.");
      } else if (action === "delete") {
        setMessage("Booking deleted.");
      } else if (action === "skip") {
        setMessage("Booking skipped.");
      } else if (action === "remove_skip") {
        setMessage("Skip removed.");
      } else if (action === "edit") {
        setMessage("Booking updated.");
      }
      setEditing(null);

      await load();
    } catch {
      setMessage("Error performing booking action.");
    }
  };

const createWeekly = () => {
  if (!selectedStudentId) {
    setMessage("Please select a student for the weekly booking.");
    return;
  }

  const pythonDay = (weeklyDay + 6) % 7;

  handleBookingAction(
    0,
    "weekly",
    "create",
    {
      booking_type: "weekly",
      student_id: selectedStudentId,
      weekday: pythonDay,
      time: weeklyTime,
    }
  );
};

const createAdhoc = () => {
  if (!adhocStudentId) {
    setMessage("Please select a student for the ad‑hoc booking.");
    return;
  }
  if (!adhocDate || !adhocTime) {
    setMessage("Please choose both a date and time.");
    return;
  }

  const datetime = `${adhocDate}T${adhocTime}:00`;

  handleBookingAction(
    0,
    "adhoc",
    "create",
    {
      booking_type: "adhoc",
      student_id: adhocStudentId,
      datetime,
    }
  );
};

  // -----------------------------
  // Render
  // -----------------------------
  return (
    <Layout>
      <div className="container mt-4">

        <div className="mb-3">
          <Link to={`/tutors/${id}/schedule`} className="btn btn-outline-secondary btn-sm">
            ⏱ Set my available hours
          </Link>
        </div>

        {loading && (
          <div className="text-center my-3">
            <div className="spinner-border text-primary" role="status" />
          </div>
        )}

        {/* Two-week calendar */}
        {week1 && (
          <>
            <h3>Calendar</h3>
            <ExistingBookingsWeek
              week={week1}
              handleBookingAction={handleBookingAction}
              editing={editing}
              setEditing={setEditing}
              tutorId={id}
            />
          </>
        )}

        {week2 && (
          <>
            <ExistingBookingsWeek
              week={week2}
              handleBookingAction={handleBookingAction}
              editing={editing}
              setEditing={setEditing}
              tutorId={id}
            />
          </>
        )}

        {message && <div className="alert alert-info">{message}</div>}

<div className="d-flex justify-content-between gap-5" style={{ flexWrap: "wrap" }}>

  {/* WEEKLY BOOKING PANEL */}
  <div
    style={{
      flex: 1,
      minWidth: "380px",
      background: "#f8f9fa",
      padding: "20px",
      borderRadius: "8px",
      border: "1px solid #e2e2e2"
    }}
  >
    <h4 className="text-center mb-3">Create Weekly Booking</h4>

    <div
      className="d-flex justify-content-center align-items-end gap-3 mb-2"
      style={{ flexWrap: "wrap" }}
    >
      <div>
        <label className="form-label" style={{ fontWeight: 600 }}>Student</label>
        <select
          className="form-select"
          value={selectedStudentId || ""}
          onChange={(e) => setSelectedStudentId(Number(e.target.value))}
        >
          <option value="">-- Choose a student --</option>
          {students
            .slice()
            .sort((a, b) =>
              `${a.first_name} ${a.last_name}`.localeCompare(
                `${b.first_name} ${b.last_name}`
              )
            )
            .map((s) => (
              <option key={s.user_id} value={s.user_id}>
                {s.first_name} {s.last_name}
              </option>
            ))}
        </select>
      </div>

      <div>
        <label className="form-label" style={{ fontWeight: 600 }}>Day</label>
        <select
          className="form-select"
          value={weeklyDay}
          onChange={(e) => setWeeklyDay(Number(e.target.value))}
        >
          <option value={1}>Monday</option>
          <option value={2}>Tuesday</option>
          <option value={3}>Wednesday</option>
          <option value={4}>Thursday</option>
          <option value={5}>Friday</option>
          <option value={6}>Saturday</option>
          <option value={0}>Sunday</option>
        </select>
      </div>

      <div>
        <label className="form-label" style={{ fontWeight: 600 }}>Time</label>
        <input
          type="time"
          className="form-control"
          value={weeklyTime}
          onChange={(e) => setWeeklyTime(e.target.value)}
        />
      </div>

      <div>
        <button
          className="btn btn-primary"
          onClick={createWeekly}
          disabled={weeklyLoading}
        >
          {weeklyLoading ? "Creating…" : "Create weekly booking"}
        </button>
      </div>
    </div>
  </div>

  {/* ONE-OFF BOOKING PANEL */}
  <div
    style={{
      flex: 1,
      minWidth: "380px",
      background: "#f8f9fa",
      padding: "20px",
      borderRadius: "8px",
      border: "1px solid #e2e2e2"
    }}
  >
    <h4 className="text-center mb-3">Create One-off Booking</h4>

    <div
      className="d-flex justify-content-center align-items-end gap-3 mb-2"
      style={{ flexWrap: "wrap" }}
    >
      <div>
        <label className="form-label" style={{ fontWeight: 600 }}>Student</label>
        <select
          className="form-select"
          value={adhocStudentId || ""}
          onChange={(e) => setAdhocStudentId(Number(e.target.value))}
        >
          <option value="">-- Choose a student --</option>
          {students
            .slice()
            .sort((a, b) =>
              `${a.first_name} ${a.last_name}`.localeCompare(
                `${b.first_name} ${b.last_name}`
              )
            )
            .map((s) => (
              <option key={s.user_id} value={s.user_id}>
                {s.first_name} {s.last_name}
              </option>
            ))}
        </select>
      </div>

      <div>
        <label className="form-label">Date</label>
        <input
          type="date"
          className="form-control"
          value={adhocDate}
          onChange={(e) => setAdhocDate(e.target.value)}
        />
      </div>

      <div>
        <label className="form-label">Time</label>
        <input
          type="time"
          className="form-control"
          value={adhocTime}
          onChange={(e) => setAdhocTime(e.target.value)}
        />
      </div>

      <div>
        <button
          className="btn btn-primary"
          onClick={createAdhoc}
          disabled={adhocLoading}
        >
          {adhocLoading ? "Creating…" : "Create one off booking"}
        </button>
      </div>
    </div>
  </div>

</div>

<h3 className="mt-5">
  Pending SMS Jobs{" "}
  {smsActive === null ? (
    <span className="text-muted">Loading…</span>
  ) : smsActive ? (
    <span className="text-success">Active</span>
  ) : (
    <span className="text-danger">Inactive</span>
  )}
</h3>





{smsLoading && (
  <div className="text-center my-3">
    <div className="spinner-border text-primary" role="status" />
  </div>
)}

<table className="table table-striped">
  <thead>
    <tr>
      <th>Student</th>
      <th>Body</th>
      <th>Created</th>
      <th>Scheduled For</th>
      <th>Send</th>
    </tr>
  </thead>
  <tbody>
    {smsJobs.map(job => (
      <tr key={job.id}>
        <td>{job.student_name}</td>
        <td>{job.body}</td>
        <td>{new Date(job.created_at).toLocaleString()}</td>
        <td>{new Date(job.scheduled_for).toLocaleString()}</td>
        <td>
          {Math.max(0, Math.floor(job.time_until_sent_seconds))}s
        </td>
      </tr>
    ))}
    {smsJobs.length === 0 && (
      <tr>
        <td colSpan={5} className="text-center text-muted">
          No pending SMS jobs.
        </td>
      </tr>
    )}
  </tbody>
</table>

<h3 className="mt-5">SMS Messages</h3>

<table className="table table-striped">
  <thead>
    <tr>
      <th>Direction</th>
      <th>Student</th>
      <th>Body</th>
      <th>Created</th>
      <th>Sent At</th>
    </tr>
  </thead>
  <tbody>
    {smsMessages.map(msg => (
      <tr key={msg.id}>
        <td>{msg.direction}</td>
        <td>{msg.student_name}</td>
        <td>{msg.body}</td>
        <td>{new Date(msg.created_at).toLocaleString()}</td>
        <td>{msg.sent_at ? new Date(msg.sent_at).toLocaleString() : "-"}</td>
      </tr>
    ))}
    {smsMessages.length === 0 && (
      <tr>
        <td colSpan={5} className="text-center text-muted">
          No messages yet.
        </td>
      </tr>
    )}
  </tbody>
</table>



      </div>
    </Layout>
  );
}