import React, { useState } from "react";
import { useNavigate } from "react-router-dom";

interface Booking {
  id?: number;
  start_time: string;
  end_time?: string;
  student_name?: string;
  booking_type: "weekly" | "adhoc" | "weekly_paused";
  confirmed?: boolean;
  duration_minutes?: number;
  student_id?: number;
}

interface DayData {
  day_status: "past" | "today" | "future";
  bookings: Booking[];
}

interface ExistingBookingsWeekProps {
  week: Record<string, DayData>;
  handleBookingAction: (
    bookingId: number,
    bookingType: string,
    action: "confirm" | "delete" | "skip" | "remove_skip" | "edit",
    extra?: any
  ) => void;
  editing: { date: string; booking: any; index: number } | null;
  setEditing: (value: any) => void;
  tutorId?: number | string;
}

export function ExistingBookingsWeek({
  week,
  handleBookingAction,
  editing, setEditing,
  tutorId,
}: ExistingBookingsWeekProps) {
  const navigate = useNavigate();

  // Single editor state (safe)
  const [editWeekday, setEditWeekday] = useState<number>(0);
  const [editDate, setEditDate] = useState<string>("");
  const [editTime, setEditTime] = useState<string>("16:00");
  const [editDuration, setEditDuration] = useState<number>(60);

  const dates = Object.keys(week).sort();

  const formatTime = (t: string) => {
    if (!t) return "";
    const [h, m] = t.split(":").map(Number);
    const d = new Date();
    d.setHours(h, m);
    return d.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
  };

  const dayBackground = (status: string) => {
    if (status === "past") return "#EEE";
    if (status === "today") return "#FFF9C4";
    return "#FFF";
  };

  const bookingBackground = (type: string) => {
    if (type === "weekly_paused") return "#E0E0E0";
    if (type === "weekly") return "#CFF4FC";
    if (type === "adhoc") return "#D1E7DD";
    return "#FFF";
  };

  const openEditor = (dateStr: string, b: Booking) => {
    setEditDate(dateStr);
    setEditTime(b.start_time);
    setEditDuration(b.duration_minutes || 60);
    setEditWeekday(new Date(dateStr).getDay());
  };

  const saveEdit = (b: Booking) => {
    if (b.booking_type === "adhoc") {
      const start_datetime = `${editDate}T${editTime}`;
        handleBookingAction(b.id!, b.booking_type, "edit", {
          start_time: `${editDate}T${editTime}`,
          duration: editDuration,
        });
    } else {
        const pythonDay = (editWeekday + 6) % 7;
        handleBookingAction(b.id!, b.booking_type, "edit", {
          weekday: pythonDay,
          start_time: editTime,
          duration: editDuration,
        });

    }
    setEditing(null);
  };

  return (
    <div
      className="weekly-booking-grid mb-4"
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(7, 1fr)",
        gap: "0px",
      }}
    >
      {dates.map((dateStr) => {
        const day = week[dateStr];
        const dayObj = new Date(dateStr);
        const formatted = dayObj.toLocaleDateString([], {
          weekday: "short",
          day: "numeric",
          month: "short",
        });

        return (
          <div
            key={dateStr}
            className="day-column"
            style={{
              border: "1px solid #ccc",
              padding: "10px",
              borderRadius: "6px",
              minHeight: "120px",
              background: dayBackground(day.day_status),
            }}
          >
            <h5 style={{ textAlign: "center" }}>{formatted}</h5>

            {day.bookings.map((b, idx) => {
              const isOpen =
                editing &&
                editing.date === dateStr &&
                editing.index === idx;


              return (
                <div key={idx}>
                  {/* Compact card */}
                  <button
                    className="card w-100 text-start"
                    style={{
                      padding: "6px 8px",
                      marginTop: "6px",
                      borderRadius: "6px",
                      border: "1px solid #ddd",
                      background: bookingBackground(b.booking_type),
                      fontSize: "0.8rem",
                    }}
                    onClick={() => {
                      if (isOpen) {
                        setEditing(null);
                      } else {
                        setEditing({ date: dateStr, index: idx });
                        openEditor(dateStr, b);
                      }
                    }}
                  >
                    <div>
                      <strong>{formatTime(b.start_time)}</strong>{" "}
                      <b>{b.student_name}</b>{" "}
                      {b.duration_minutes !== 60 && (
                        <span style={{ fontSize: "0.75rem", color: "#333" }}>
                          &nbsp;{b.duration_minutes} min
                        </span>
                      )}
                      {!b.confirmed && (
                        <span style={{ color: "#b00", fontWeight: 600 }}>
                          &nbsp;(unconfirmed)
                        </span>
                      )}
                    </div>

                    <div style={{ fontSize: "0.7rem", color: "#555", marginTop: "2px" }}>
                      {b.booking_type === "weekly" && "Weekly"}
                      {b.booking_type === "weekly_paused" && "Weekly (paused)"}
                      {b.booking_type === "adhoc" && "One-off"}
                      {" | "}
                      {b.confirmed ? "Confirmed" : "Not confirmed"}
                    </div>
                  </button>

                  {/* Join button — today only, when tutorId and student_id are known */}
                  {day.day_status === "today" && tutorId && b.student_id && (
                    <button
                      className="btn btn-success btn-sm w-100 mt-1"
                      style={{ fontSize: "0.75rem" }}
                      onClick={() => navigate(`/session/t${tutorId}-s${b.student_id}`)}
                    >
                      Join Session
                    </button>
                  )}

                  {/* Expanded editor */}
                  {isOpen && (
                    <div
                      className="border rounded p-2 mt-2"
                      style={{ background: "#fff" }}
                    >
                      {/* WEEKLY EDITOR */}
                      {b.booking_type !== "adhoc" && (
                        <>
                          <div className="mb-2">
                            <label className="form-label">Weekday</label>
                            <select
                              className="form-select"
                              value={editWeekday}
                              onChange={(e) => setEditWeekday(Number(e.target.value))}
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

                          <div className="mb-2">
                            <label className="form-label">Start Time</label>
                            <input
                              type="time"
                              className="form-control"
                              value={editTime}
                              onChange={(e) => setEditTime(e.target.value)}
                            />
                          </div>

                          <div className="mb-2">
                            <label className="form-label">Duration (minutes)</label>
                            <input
                              type="number"
                              className="form-control"
                              value={editDuration}
                              onChange={(e) => setEditDuration(Number(e.target.value))}
                            />
                          </div>
                        </>
                      )}

                      {/* ADHOC EDITOR */}
                      {b.booking_type === "adhoc" && (
                        <>
                          <div className="mb-2">
                            <label className="form-label">Date</label>
                            <input
                              type="date"
                              className="form-control"
                              value={editDate}
                              onChange={(e) => setEditDate(e.target.value)}
                            />
                          </div>

                          <div className="mb-2">
                            <label className="form-label">Start Time</label>
                            <input
                              type="time"
                              className="form-control"
                              value={editTime}
                              onChange={(e) => setEditTime(e.target.value)}
                            />
                          </div>

                          <div className="mb-2">
                            <label className="form-label">Duration (minutes)</label>
                            <input
                              type="number"
                              className="form-control"
                              value={editDuration}
                              onChange={(e) => setEditDuration(Number(e.target.value))}
                            />
                          </div>
                        </>
                      )}

                      <div className="d-flex gap-2 mt-3">

                        {/* Skip / Remove Skip */}
                        {b.booking_type === "weekly_paused" ? (
                          <button
                            className="btn btn-warning btn-sm"
                            onClick={() =>
                              handleBookingAction(b.id!, b.booking_type, "remove_skip")
                            }
                          >
                            Remove Skip
                          </button>
                        ) : (
                          b.booking_type === "weekly" && (
                            <button
                              className="btn btn-warning btn-sm"
                              onClick={() =>
                                handleBookingAction(b.id!, b.booking_type, "skip")
                              }
                            >
                              Skip
                            </button>
                          )
                        )}

                        {/* Save */}
                        <button
                          className="btn btn-success btn-sm"
                          onClick={() => saveEdit(b)}
                        >
                          Save
                        </button>

                        {/* Delete */}
                        <button
                          className="btn btn-danger btn-sm ms-auto"
                          onClick={() =>
                            handleBookingAction(b.id!, b.booking_type, "delete")
                          }
                        >
                          Delete
                        </button>

                        {/* Confirm */}
                        <button
                          className="btn btn-primary btn-sm"
                          onClick={() =>
                            handleBookingAction(b.id!, b.booking_type, "confirm")
                          }
                        >
                          {b.confirmed ? "Unconfirm" : "Confirm"}
                        </button>

                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        );
      })}
    </div>
  );
}