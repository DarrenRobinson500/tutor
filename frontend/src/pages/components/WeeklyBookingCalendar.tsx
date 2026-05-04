import React from "react";

interface Booking {
  id: number;
  start: string;
  end: string;
  status: string;
}

interface WeeklyBookingCalendarProps {
  availability: Record<any, string[]>;
  mode: "weekly" | "modify_weekly";
  onBook: (dayKey: any, time: string) => void;
  onDelete: (dayKey: any, time: string) => void;
}

export function WeeklyBookingCalendar({
  availability,
  mode,
  onBook,
  onDelete,
}: WeeklyBookingCalendarProps) {
  const WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

  const formatTime = (time: string) => {
    const [h, m] = time.split(":");
    let hour = parseInt(h, 10);
    const minute = m;
    const ampm = hour >= 12 ? "pm" : "am";
    hour = hour % 12 || 12;
    return `${hour}:${minute}${ampm}`;
  };

  const renderHeader = (key: any) => {
    if (mode === "weekly") return WEEKDAYS[key];
    const d = new Date(key);
    return d.toLocaleDateString([], {
      weekday: "short",
      day: "numeric",
      month: "short",
    });
  };

  const dayKeys =
    mode === "weekly"
      ? [0, 1, 2, 3, 4, 5, 6]
      : Object.keys(availability);

if (!availability ) {
  return <div>Loading calendar…</div>;
}


  return (
    <div
      className="weekly-booking-grid"
      style={{
        display: "grid",
        gridTemplateColumns: `repeat(${dayKeys.length}, 1fr)`,
        gap: "0px",
      }}
    >
      {dayKeys.map((key: any) => {
        const slots = availability[key] || [];

        return (
          <div
            key={key}
            className="day-column"
            style={{
              border: "1px solid #ccc",
              padding: "10px",
              borderRadius: "6px",
            }}
          >
            <h5 style={{ textAlign: "center" }}>{renderHeader(key)}</h5>

            {slots.length === 0 ? (
              <div className="text-muted" style={{ fontSize: "0.85rem" }}>
                No available slots
              </div>
            ) : (
              <>
                {slots.map((time: string) => (
                  <button
                    key={time}
                    className="btn btn-outline-primary w-100 mb-2"
                    style={{ fontSize: "0.8rem", padding: "4px 6px" }}
                    onClick={() => onBook(key, time)}
                  >
                    {formatTime(time)}
                  </button>
                ))}
              </>
            )}
          </div>
        );
      })}
    </div>
  );
}