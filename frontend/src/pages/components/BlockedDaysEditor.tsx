import { useState } from "react";
import { apiFetch } from "../../utils/apiFetch"

interface BlockedDay {
  id: number;
  date: string; // ISO date string: "2025-01-30"
}

interface BlockedDaysProps {
  tutorId: string;
  blockedDays: BlockedDay[];
  setBlockedDays: React.Dispatch<React.SetStateAction<BlockedDay[]>>;
}

export function BlockedDaysEditor({
  tutorId,
  blockedDays,
  setBlockedDays,
}: BlockedDaysProps) {
  const [date, setDate] = useState("");

  async function blockDay() {
    if (!date) return;

    const res = await apiFetch(`/api/tutors/${tutorId}/block_day/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ date }),
    });

    const data = await res.json();

    setBlockedDays([
      ...blockedDays,
      { id: data.id, date },
    ]);

    setDate("");
  }

  async function unblockDay(id: number) {
    await apiFetch(`/api/tutors/${tutorId}/unblock_day/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id }),
    });

    setBlockedDays(blockedDays.filter(b => b.id !== id));
  }

  return (
    <div>
      {/* Add a blocked day */}
      <div className="d-flex gap-2 mb-3">
        <input
          type="date"
          className="form-control"
          value={date}
          onChange={e => setDate(e.target.value)}
        />
        <button className="btn btn-outline-primary" onClick={blockDay}>
          Block Day
        </button>
      </div>

      {/* List of blocked days */}
      <ul className="list-group">
        {blockedDays.map(b => (
          <li key={b.id} className="list-group-item d-flex justify-content-between">
            <span>{b.date}</span>
            <button
              className="btn btn-sm btn-danger"
              onClick={() => unblockDay(b.id)}
            >
              Unblock
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}