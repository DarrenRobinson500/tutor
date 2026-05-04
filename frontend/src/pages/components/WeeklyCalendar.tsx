import React from "react";
import { WeekData } from "../../types/weekly";
// import { apiFetch } from "../../utils/apiFetch"

interface WeeklyCalendarProps {
  week: WeekData;
  mode: "student" | "tutor-availability" | "tutor-schedule" | "readonly";
  onSelectSlot?: (day: string, blockStart: string, blockEnd: string) => void;
  onToggleAvailability?: (weekday: number, time: string) => void;
  onSelectBooking?: (bookingId: number) => void;
  onDeleteBooking?: (bookingId: number) => void;
  showAllBookingLabels?: boolean;
}

function getSegmentColor(type: string) {
  switch (type) {
    case "available": return "#FFFFFF";
    case "blocked": return "#555555";
    case "booked_other": return "#B3D7FF";
    case "booked_self": return "#C7A0FF";
    case "outside": return "#EEEEEE";
    default: return "#EEEEEE";
  }
}

export function WeeklyCalendar({
  week,
  mode,
  onSelectSlot,
  onToggleAvailability,
  onSelectBooking,
  onDeleteBooking,
  showAllBookingLabels,
}: WeeklyCalendarProps) {

  const days = ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"];
  const hours = Array.from({ length: 24 }, (_, i) =>
    String(i).padStart(2, "0") + ":00"
  );

  return (
    <div className="weekly-calendar">

      {/* HEADER */}
      <div className="week-header" style={{ display: "flex", flexDirection: "row" }}>
        <div style={{ flex: "0 0 60px" }}></div>

        {week.map((day, i) => {
          const [year, month, dayNum] = day.date.split("-").map(Number);
          const dateObj = new Date(year, month - 1, dayNum);

          const formatted = dateObj.toLocaleDateString("en-AU", {
            day: "numeric",
            month: "short"
          });

          return (
            <div
              key={i}
              style={{
                flex: 1,
                textAlign: "center",
                fontWeight: "bold",
                display: "flex",
                flexDirection: "column",
                alignItems: "center"
              }}
            >
              <div>{days[i]}</div>
              <div style={{ fontSize: "0.8rem", color: "#666" }}>{formatted}</div>
            </div>
          );
        })}
      </div>

      {/* BODY */}
      <div className="week-body" style={{ display: "flex", flexDirection: "row" }}>

        {/* TIME COLUMN */}
        <div style={{ flex: "0 0 60px", display: "flex", flexDirection: "column" }}>
          {hours.map((h, i) => (
            <div
              key={i}
              style={{
                height: "24px",
                fontSize: "10px",
                color: "#444",
                paddingTop: "2px"
              }}
            >
              {h}
            </div>
          ))}
        </div>

        {/* DAY COLUMNS */}
        {week.map((day, dayIndex) => {

          // Detect availability block starts (still needed)
          const availabilityStarts = day.segments
            .map((seg, i) => {
              const prev = day.segments[i - 1];
              const isStart =
                seg.type === "available" &&
                (i === 0 || prev.type !== "available");
              return isStart ? i : null;
            })
            .filter(i => i !== null);

          return (
            <div
              key={dayIndex}
              style={{ flex: 1, display: "flex", flexDirection: "column", position: "relative" }}
            >

              {day.segments.map((seg, segIndex) => {
                const color = getSegmentColor(seg.type);

                let handleClick = () => {
                  if (mode === "tutor-availability") {
                    onToggleAvailability?.(dayIndex, seg.time);
                  }
                  if (mode === "tutor-schedule" && seg.bookingId) {
                    onSelectBooking?.(seg.bookingId);
                  }
                };

                // Availability block start/end detection
                let blockStart: string | null = null;
                let blockEnd: string | null = null;
                let blockMinutes: number | null = null;

                if (seg.type === "available") {
                  let startIndex = segIndex;
                  while (
                    startIndex > 0 &&
                    day.segments[startIndex - 1].type === "available"
                  ) {
                    startIndex--;
                  }

                  let endIndex = segIndex;
                  while (
                    endIndex + 1 < day.segments.length &&
                    day.segments[endIndex + 1].type === "available"
                  ) {
                    endIndex++;
                  }

                  blockStart = day.segments[startIndex].time.slice(0, 5);
                  blockEnd = day.segments[endIndex].time.slice(0, 5);

                  const [sh, sm] = blockStart.split(":").map(Number);
                  const [eh, em] = blockEnd.split(":").map(Number);
                  blockMinutes = (eh * 60 + em) - (sh * 60 + sm);

                  // Only students can click to book
                  if (mode === "student") {
                    handleClick = () => {
                      onSelectSlot?.(day.date, blockStart!, blockEnd!);
                    };
                  }

                }

                const isStartOfAvailability = availabilityStarts.includes(segIndex);

                return (
                  <div
                    key={segIndex}
                    style={{
                      backgroundColor: color,
                      position: "relative",
                      height: "6px",
                      margin: 0,
                      padding: 0,
                      border: "none"
                    }}
                    onClick={handleClick}
                  >

                    {/* Availability label */}
                    {isStartOfAvailability && blockEnd && blockMinutes !== null && blockMinutes >= 30 && (
                      <div
                        style={{
                          position: "absolute",
                          top: "0px",
                          left: "4px",
                          fontSize: "14px",
                          color: "#333",
                          pointerEvents: "none",
                          zIndex: 1
                        }}
                      >
                        Available: {seg.time.slice(0, 5)}-{blockEnd}
                      </div>
                    )}

                    {/* Booking label — now trivial */}
                    {seg.studentName && (
                      <div
                        style={{
                          position: "absolute",
                          top: "2px",
                          left: "4px",
                          fontSize: "14px",
                          color: "#333",
                          pointerEvents: "none",
                          zIndex: 1
                        }}
                      >
                        {seg.studentName}: {seg.time.slice(0, 5)}
                      </div>
                    )}

                    {/* Delete button (only on first slot of booking) */}
                    {seg.studentName && seg.bookingId && (
                      <>
                        {(mode === "tutor-schedule" || seg.type === "booked_self") && (
                          <button
                            onClick={(e) => {
                              e.stopPropagation(); // prevent selecting the block
                              if (seg.bookingId !== undefined) {
                                onDeleteBooking?.(seg.bookingId);
                              }
                            }}
                            style={{
                              position: "absolute",
                              top: "2px",
                              right: "4px",
                              background: "transparent",
                              border: "none",
                              color: "#900",
                              cursor: "pointer",
                              fontSize: "14px",
                              zIndex: 2
                            }}
                            title="Delete booking"
                          >
                            ✕
                          </button>
                        )}
                      </>
                    )}


                  </div>
                );
              })}

            </div>
          );
        })}

      </div>
    </div>
  );
}