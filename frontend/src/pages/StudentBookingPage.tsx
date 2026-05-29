import { useParams, useNavigate } from "react-router-dom";
import React, { useState, useEffect } from "react";
import { Layout } from "./components/Layout";
import { apiFetch } from "../utils/apiFetch";
import { WeeklyBookingCalendar } from "./components/WeeklyBookingCalendar";
import { PauseButton } from "./components/PausePicker";

export function StudentBookingPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [student, setStudent] = useState<any>(null);

  const [weeklySlots, setWeeklySlots] = useState<any>(null);
  const [weeklyBookings, setWeeklyBookings] = useState<any>(null);

  const [adhocSlots, setAdhocSlots] = useState<any>(null);
  const [adhocBookings, setAdhocBookings] = useState<any>(null);

  const [modifyingWeekly, setModifyingWeekly] = useState(false);
  const [message, setMessage] = useState("");
  const [actionLoading, setActionLoading] = useState(false);

  // -----------------------------
  // Load student ONCE
  // -----------------------------
  useEffect(() => {
    apiFetch(`/api/students/${id}/home/`)
      .then(res => res.json())
      .then(data => setStudent(data));
  }, [id]);

  useEffect(() => {
    loadData();
  }, [id]);


  const loadData = async () => {
    if (!id) return;

    // Load student home data
    const homeRes = await apiFetch(`/api/students/${id}/home/`);
    const homeData = await homeRes.json();
    setStudent(homeData);

    // Load booking data
    const bookingRes = await apiFetch(`/api/students/${id}/booking/`);
    const bookingData = await bookingRes.json();

    setWeeklySlots(bookingData.weekly_slots);
  //  setWeeklyBookings(bookingData.weekly_bookings);
    setAdhocSlots(bookingData.adhoc_slots);
  //  setAdhocBookings(bookingData.adhoc_bookings);
  };

  // -----------------------------
  // Unified booking action
  // -----------------------------
  const handleBookingAction = async (
    bookingId: number | null,
    bookingType: "weekly" | "adhoc",
    action: "create" | "confirm" | "delete" | "skip" | "remove_skip" | "edit",
    extra: any = {}
  ) => {
    if (!student) return;

    setActionLoading(true);

    try {
      const res = await apiFetch(
        `/api/tutors/${student.tutor_id}/booking_action/`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            id: bookingId,
            type: bookingType,
            action,
            student_id: Number(id),
            ...extra,
          }),
        }
      );

      const data = await res.json();

      if (!data.ok) {
        setMessage(data.error || "Action failed.");
        return;
      }

      if (action === "create") setMessage("Booking created.");
      else if (action === "delete") setMessage("Booking deleted.");
      else if (action === "skip") {
        const w = extra?.weeks ?? 1;
        setMessage(`Appointment paused for ${w} ${w === 1 ? "week" : "weeks"}.`);
      }
      else if (action === "remove_skip") setMessage("Skip removed.");
      else if (action === "edit") setMessage("Booking updated.");

      await loadData();

      const homeRes = await apiFetch(`/api/students/${id}/home/`);
      setStudent(await homeRes.json());

    } catch {
      setMessage("Error performing booking action.");
    } finally {
      setActionLoading(false);
    }
  };

  // -----------------------------
  // Render next appointment card
  // -----------------------------

  const renderNextCard = (booking: any) => {
    if (!booking) {
      return (
        <div className="alert alert-secondary mt-3">
          You have no upcoming bookings.
        </div>
      );
    }

    // New backend format → reconstruct JS Date
    const start = new Date(booking.start_iso);
    const weekday = start.toLocaleDateString([], { weekday: "long" });
    const date = start.toLocaleDateString([], { day: "numeric", month: "long" });
    const time = start.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

    return (
      <div className="alert alert-success mt-3">
        <strong>Your next appointment:</strong>
        <br />
        {weekday}, {date} at {time}
        {!booking.confirmed && (
          <span style={{ color: "#b00", fontWeight: 600 }}> (unconfirmed)</span>
        )}

        {student.booking_mode === "weekly_booking_but_adhoc_this_week" &&
          student.next_weekly_booking && (
            <div className="mt-2" style={{ fontSize: "0.9rem" }}>
              {(() => {
                const w = new Date(
                  `${student.next_weekly_booking.day_str}T${student.next_weekly_booking.start_time}:00`
                );
                const wDay = w.toLocaleDateString([], { weekday: "long" });
                const wTime = w.toLocaleTimeString([], {
                  hour: "2-digit",
                  minute: "2-digit",
                });
                return (
                  <span className="text-muted">
                    Your regular weekly appointment is {wDay} at {wTime}. It will resume next week.
                  </span>
                );
              })()}
            </div>
          )}

        <div className="mt-3 d-flex gap-2">
          {(student.booking_mode === "weekly_booking_but_adhoc_this_week" || student.booking_mode === "adhoc") && (
            <button
              className="btn btn-secondary btn-sm"
              onClick={() =>
                handleBookingAction(student.next_booking.id, "adhoc", "delete", {})
              }
              disabled={actionLoading || !booking.student_can_edit}
            >
              Delete this one-off appointment
            </button>
          )}

          {student.booking_mode === "weekly_booking" && (
            <button
              className="btn btn-secondary btn-sm"
              onClick={() => setModifyingWeekly(true)}
              disabled={actionLoading || !booking.student_can_edit}
            >
              Modify my time for this week
            </button>
          )}

          {student.booking_mode === "weekly_booking" && (
            <PauseButton
              disabled={!booking.student_can_edit}
              loading={actionLoading}
              onConfirm={(weeks) =>
                handleBookingAction(booking.id, "weekly", "skip", { weeks })
              }
            />
          )}

          {student.booking_mode === "weekly_booking_but_paused" && (
            <button
              className="btn btn-secondary btn-sm"
              onClick={() =>
                handleBookingAction(booking.id, "weekly", "remove_skip")
              }
              disabled={actionLoading || !booking.student_can_edit}
            >
              Remove pause
            </button>
          )}
        </div>

        {booking.start_iso && new Date(booking.start_iso).toDateString() === new Date().toDateString() && student.tutor_id && (
          <div className="mt-3">
            <button
              className="btn btn-success btn-lg w-100"
              style={{ fontWeight: 600, fontSize: 16 }}
              onClick={() => navigate(`/session/t${student.tutor_id}-s${id}`)}
            >
              Join Session
            </button>
          </div>
        )}

        <div className="mt-3 text-muted" style={{ fontSize: "1rem" }}>
          If you have any questions about your appointment, call or text {student.tutor_name} on {student.tutor_mobile?.replace(/\D/g, "").replace(/^(\d{4})(\d{3})(\d{3})$/, "$1 $2 $3") ?? student.tutor_mobile}.
        </div>
      </div>
    );
  };

  if (!student) {
    return (
      <Layout>
        <div className="container mt-4">Loading…</div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="container mt-4">
        <h1>Bookings for: {student.name}</h1>

        <div className="row mt-4">
          <div className="col-md-12">

            {renderNextCard(student.next_booking)}

            {message && (
              <div className="alert alert-info mt-3">{message}</div>
            )}

            {actionLoading && (
              <div className="text-center my-3">
                <div className="spinner-border text-success" role="status" />
                <div style={{ marginTop: "0.5rem", fontWeight: 500 }}>
                  Processing…
                </div>
              </div>
            )}

            {(!student.next_booking ) && (
              <div className="mt-3 mb-2" style={{ fontWeight: 600 }}>
                {student?.tutor_name
                  ? `${student.tutor_name}'s Available Appointments. Select a time for your weekly appointment.`
                  : "Tutor's Weekly Calendar"}
              </div>
            )}

            {(modifyingWeekly) && (
              <div className="mt-3 mb-2" style={{ fontWeight: 600 }}>
                {student?.tutor_name
                  ? `${student.tutor_name}'s Available Appointments. Select a time for your next booking. (After this week your booking will revert to its normal time.)`
                  : "Tutor's Weekly Calendar"}
              </div>
            )}

            {modifyingWeekly && (
              <div className="alert alert-info mt-3">
                Select a new time for this week only.
              </div>
            )}

            <div>
              {student.booking_mode === "no_booking" && weeklySlots && (
                  <WeeklyBookingCalendar
                    availability={weeklySlots}
                    mode="weekly"
                    onBook={(weekday, time) =>
                      handleBookingAction(null, "weekly", "create", {
                        weekday,
                        time,
                      })
                    }
                    onDelete={(weekday, time) =>
                      handleBookingAction(null, "weekly", "delete", {
                        weekday,
                        time,
                      })
                    }
                  />
                )}

              {modifyingWeekly && adhocSlots && (
                  <WeeklyBookingCalendar
                    availability={adhocSlots}
                    mode="modify_weekly"
                    onBook={(dayKey, time) => {
                      const isoStart = new Date(`${dayKey}T${time}:00`).toISOString();
                      handleBookingAction(null, "adhoc", "create", {
                        start_time: isoStart,
                        pause_weekly: true
                      });
                      setModifyingWeekly(false);
                    }}
                    onDelete={() => {}}
                  />
                )}
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
}