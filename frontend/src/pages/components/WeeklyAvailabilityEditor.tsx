import { useState } from "react";
import { apiFetch } from "../../utils/apiFetch"

interface WeeklyAvailabilityProps {
  tutorId: string;
  availability: {
    id: number;
    weekday: number;
    start_time: string;
    end_time: string;
  }[];
  setAvailability: React.Dispatch<React.SetStateAction<any[]>>;
}

export function WeeklyAvailabilityEditor({
  tutorId,
  availability,
  setAvailability,
}: WeeklyAvailabilityProps) {
  const [weekday, setWeekday] = useState("1");
  const [start, setStart] = useState("09:00");
  const [end, setEnd] = useState("20:00");

  async function addSlot() {
  console.log("addSlot called");

    const res = await apiFetch(`/api/tutors/${tutorId}/add_availability/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        weekday,
        start_time: start,
        end_time: end,
      }),
    });

    const data = await res.json();

    setAvailability([
      ...availability,
      {
        id: data.id,
        weekday: Number(weekday),
        start_time: start,
        end_time: end,
      },
    ]);
  }

//   async function removeSlot(id: number) {
//     await apiFetch(`/api/tutors/${tutorId}/remove_availability/`, {
//       method: "POST",
//       headers: { "Content-Type": "application/json" },
//       body: JSON.stringify({ id }),
//     });
//
//     setAvailability(availability.filter(a => a.id !== id));
//   }

//   function weekdayName(n: number) {
//     return ["Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"][n];
//   }

  return (
    <div>
      {/* Add slot UI */}
      <div className="d-flex gap-2 mb-3">
        <select className="form-select" value={weekday} onChange={e => setWeekday(e.target.value)}>
          <option value="1">Monday</option>
          <option value="2">Tuesday</option>
          <option value="3">Wednesday</option>
          <option value="4">Thursday</option>
          <option value="5">Friday</option>
          <option value="6">Saturday</option>
          <option value="0">Sunday</option>
        </select>

        <input type="time" className="form-control" value={start} onChange={e => setStart(e.target.value)} />
        <input type="time" className="form-control" value={end} onChange={e => setEnd(e.target.value)} />

        <button className="btn btn-outline-primary" onClick={addSlot}>Add</button>
      </div>

    </div>
  );
}