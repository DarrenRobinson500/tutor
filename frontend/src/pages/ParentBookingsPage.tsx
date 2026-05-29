import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { apiFetch } from "../utils/apiFetch";
import { ParentNav } from "./components/ParentNav";
import { WeeklyBookingCalendar } from "./components/WeeklyBookingCalendar";
import { PauseButton } from "./components/PausePicker";
import "./ParentHomePage.css";

interface StudentHome {
  id: number;
  name: string;
  first_name: string;
  tutor_id: number | null;
  tutor_name: string | null;
  tutor_mobile: string | null;
  booking_mode: string;
  next_booking: any;
  next_weekly_booking: any;
}

interface SlotData {
  weekly_slots: any;
  adhoc_slots: any;
}

export function ParentBookingsPage() {
  const { id } = useParams<{ id: string }>();


  const [children, setChildren] = useState<StudentHome[]>([]);
  const [slots, setSlots] = useState<Record<number, SlotData | null>>({});
  const [modifyingWeekly, setModifyingWeekly] = useState<Record<number, boolean>>({});
  const [messages, setMessages] = useState<Record<number, string>>({});
  const [actionLoading, setActionLoading] = useState(false);
  const [pageLoading, setPageLoading] = useState(true);

  useEffect(() => { loadAll(); }, [id]); // eslint-disable-line react-hooks/exhaustive-deps

  async function loadAll() {
    setPageLoading(true);
    try {
      const homeRes = await apiFetch("/api/auth/parent_home/");
      const homeData = await homeRes.json();
      const childList: { id: number }[] = homeData.children || [];

      const studentDatas = await Promise.all(
        childList.map(c =>
          apiFetch(`/api/students/${c.id}/home/`)
            .then(r => r.json())
            .then(d => ({ ...d, id: c.id } as StudentHome))
            .catch(() => null)
        )
      );

      const valid = studentDatas.filter(Boolean) as StudentHome[];
      setChildren(valid);

      // Load slots for children with no booking who have a tutor
      const slotsMap: Record<number, SlotData | null> = {};
      await Promise.all(
        valid.map(async s => {
          if (s.tutor_id && (s.booking_mode === "no_booking" || s.booking_mode === "weekly_booking")) {
            const r = await apiFetch(`/api/students/${s.id}/booking/`);
            slotsMap[s.id] = await r.json();
          } else {
            slotsMap[s.id] = null;
          }
        })
      );
      setSlots(slotsMap);
    } finally {
      setPageLoading(false);
    }
  }

  async function reloadChild(childId: number) {
    const [sRes, bRes] = await Promise.all([
      apiFetch(`/api/students/${childId}/home/`),
      apiFetch(`/api/students/${childId}/booking/`),
    ]);
    const studentData: StudentHome = { ...(await sRes.json()), id: childId };
    const slotData: SlotData = await bRes.json();
    setChildren(prev => prev.map(c => c.id === childId ? studentData : c));
    setSlots(prev => ({ ...prev, [childId]: slotData }));
  }

  async function handleAction(
    student: StudentHome,
    bookingId: number | null,
    bookingType: "weekly" | "adhoc",
    action: "create" | "delete" | "skip" | "remove_skip" | "edit",
    extra: any = {}
  ) {
    if (!student.tutor_id) return;
    setActionLoading(true);
    try {
      const res = await apiFetch(`/api/tutors/${student.tutor_id}/booking_action/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id: bookingId, type: bookingType, action, student_id: student.id, ...extra }),
      });
      const data = await res.json();

      if (!data.ok) {
        setMessages(prev => ({ ...prev, [student.id]: data.error || "Action failed." }));
        return;
      }

      const label: Record<string, string> = {
        create: "Booking created.",
        delete: "Booking deleted.",
        skip: (() => { const w = extra?.weeks ?? 1; return `Appointment paused for ${w} ${w === 1 ? "week" : "weeks"}.`; })(),
        remove_skip: "Pause removed.",
        edit: "Booking updated.",
      };
      setMessages(prev => ({ ...prev, [student.id]: label[action] ?? "Done." }));
      setModifyingWeekly(prev => ({ ...prev, [student.id]: false }));
      await reloadChild(student.id);
    } catch {
      setMessages(prev => ({ ...prev, [student.id]: "Something went wrong." }));
    } finally {
      setActionLoading(false);
    }
  }

  if (pageLoading) {
    return (
      <div style={{ minHeight: "60vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <img src="/subjectmatter_logo.svg" alt="" style={{ height: 48 }} />
      </div>
    );
  }

  return (
    <div className="ph-page">
      <ParentNav parentId={id!} />

      <header className="ph-header">
        <div className="ph-header-inner">
          <h1 className="ph-greeting">Bookings</h1>
        </div>
      </header>

      <main className="ph-body" style={{ maxWidth: 760 }}>
        {children.map(student => (
          <ChildBookingSection
            key={student.id}
            student={student}
            slotData={slots[student.id] ?? null}
            modifyingWeekly={modifyingWeekly[student.id] ?? false}
            setModifyingWeekly={val => setModifyingWeekly(prev => ({ ...prev, [student.id]: val }))}
            message={messages[student.id] ?? ""}
            actionLoading={actionLoading}
            onAction={(bookingId, bookingType, action, extra) =>
              handleAction(student, bookingId, bookingType, action, extra)
            }
          />
        ))}
      </main>
    </div>
  );
}

function ChildBookingSection({
  student,
  slotData,
  modifyingWeekly,
  setModifyingWeekly,
  message,
  actionLoading,
  onAction,
}: {
  student: StudentHome;
  slotData: SlotData | null;
  modifyingWeekly: boolean;
  setModifyingWeekly: (v: boolean) => void;
  message: string;
  actionLoading: boolean;
  onAction: (
    bookingId: number | null,
    bookingType: "weekly" | "adhoc",
    action: "create" | "delete" | "skip" | "remove_skip" | "edit",
    extra?: any
  ) => void;
}) {
  const booking = student.next_booking;

  const fmtPhone = (ph: string | null) =>
    ph?.replace(/\D/g, "").replace(/^(\d{4})(\d{3})(\d{3})$/, "$1 $2 $3") ?? ph;

  return (
    <section style={{ marginBottom: "2.5rem", borderBottom: "1px solid var(--sm-border, #E8E0D6)", paddingBottom: "2rem" }}>
      <h2 style={{ fontFamily: "var(--font-display, Lora, serif)", fontSize: "1.25rem", fontWeight: 600, marginBottom: "1rem" }}>
        {student.first_name}
        {student.tutor_name && (
          <span style={{ fontSize: "0.85rem", fontWeight: 400, color: "var(--sm-text-muted, #8A7F74)", marginLeft: "0.6rem" }}>
            with {student.tutor_name}
          </span>
        )}
      </h2>

      {!student.tutor_id ? (
        <p style={{ color: "var(--sm-text-muted, #8A7F74)", fontSize: 14 }}>No tutor assigned yet.</p>
      ) : !booking ? (
        <div className="alert alert-secondary">No upcoming bookings.</div>
      ) : (
        <div className="alert alert-success">
          <strong>Next appointment:</strong>
          <br />
          {(() => {
            const start = new Date(booking.start_iso);
            const weekday = start.toLocaleDateString([], { weekday: "long" });
            const dateStr = start.toLocaleDateString([], { day: "numeric", month: "long" });
            const time = start.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
            return `${weekday}, ${dateStr} at ${time}`;
          })()}
          {!booking.confirmed && (
            <span style={{ color: "#b00", fontWeight: 600 }}> (unconfirmed)</span>
          )}

          {student.booking_mode === "weekly_booking_but_adhoc_this_week" && student.next_weekly_booking && (
            <div className="mt-2" style={{ fontSize: "0.9rem" }}>
              {(() => {
                const w = new Date(`${student.next_weekly_booking.day_str}T${student.next_weekly_booking.start_time}:00`);
                return (
                  <span className="text-muted">
                    Regular weekly appointment is {w.toLocaleDateString([], { weekday: "long" })} at{" "}
                    {w.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}. It will resume next week.
                  </span>
                );
              })()}
            </div>
          )}

          <div className="mt-3 d-flex gap-2 flex-wrap">
            {(student.booking_mode === "weekly_booking_but_adhoc_this_week" || student.booking_mode === "adhoc") && (
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => onAction(booking.id, "adhoc", "delete")}
                disabled={actionLoading || !booking.student_can_edit}
              >
                Delete this one-off appointment
              </button>
            )}
            {student.booking_mode === "weekly_booking" && (
              <>
                <button
                  className="btn btn-secondary btn-sm"
                  onClick={() => setModifyingWeekly(true)}
                  disabled={actionLoading || !booking.student_can_edit}
                >
                  Modify time for this week
                </button>
                <PauseButton
                  disabled={!booking.student_can_edit}
                  loading={actionLoading}
                  onConfirm={(weeks) => onAction(booking.id, "weekly", "skip", { weeks })}
                />
              </>
            )}
            {student.booking_mode === "weekly_booking_but_paused" && (
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => onAction(booking.id, "weekly", "remove_skip")}
                disabled={actionLoading || !booking.student_can_edit}
              >
                Remove pause
              </button>
            )}
          </div>

          {student.tutor_mobile && (
            <div className="mt-3 text-muted" style={{ fontSize: "0.9rem" }}>
              Questions? Call or text {student.tutor_name} on {fmtPhone(student.tutor_mobile)}.
            </div>
          )}
        </div>
      )}

      {message && <div className="alert alert-info mt-2">{message}</div>}

      {actionLoading && (
        <div className="text-center my-2">
          <div className="spinner-border spinner-border-sm text-success" role="status" />
        </div>
      )}

      {/* No booking — show tutor's available slots */}
      {student.booking_mode === "no_booking" && slotData?.weekly_slots && (
        <>
          <div className="mt-3 mb-2" style={{ fontWeight: 600, fontSize: 14 }}>
            {student.tutor_name
              ? `${student.tutor_name}'s available appointments — select a regular weekly time for ${student.first_name}.`
              : "Available appointments"}
          </div>
          <WeeklyBookingCalendar
            availability={slotData.weekly_slots}
            mode="weekly"
            onBook={(weekday, time) => onAction(null, "weekly", "create", { weekday, time })}
            onDelete={() => {}}
          />
        </>
      )}

      {/* Modify weekly — show adhoc slots */}
      {modifyingWeekly && slotData?.adhoc_slots && (
        <>
          <div className="mt-3 mb-2" style={{ fontWeight: 600, fontSize: 14 }}>
            Select a new time for this week only. After this week the regular time will resume.
          </div>
          <WeeklyBookingCalendar
            availability={slotData.adhoc_slots}
            mode="modify_weekly"
            onBook={(dayKey, time) => {
              const isoStart = new Date(`${dayKey}T${time}:00`).toISOString();
              onAction(null, "adhoc", "create", { start_time: isoStart, pause_weekly: true });
            }}
            onDelete={() => {}}
          />
        </>
      )}
    </section>
  );
}
