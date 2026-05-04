import { useEffect, useState } from "react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer,
} from "recharts";
import { apiFetch } from "../../utils/apiFetch";

interface Snapshot {
  date: string;
  score: number;
}

export function ProgressChart({ studentId }: { studentId: number | string }) {
  const [snapshots, setSnapshots] = useState<Snapshot[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    apiFetch(`/api/students/${studentId}/progress/`)
      .then(r => r.json())
      .then(data => setSnapshots(data.snapshots ?? []))
      .catch(() => setSnapshots([]))
      .finally(() => setLoading(false));
  }, [studentId]);

  if (loading) {
    return <p className="text-muted" style={{ fontSize: 13 }}>Loading progress…</p>;
  }

  if (snapshots.length === 0) {
    return (
      <p className="text-muted" style={{ fontSize: 13 }}>
        Progress will appear here after tutoring sessions are completed.
      </p>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={240}>
      <LineChart data={snapshots} margin={{ top: 8, right: 16, left: 0, bottom: 4 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        <XAxis dataKey="date" tick={{ fontSize: 11 }} />
        <YAxis
          domain={[0, 100]}
          ticks={[0, 25, 50, 75, 100]}
          tickFormatter={(v: number) => `${v}%`}
          tick={{ fontSize: 11 }}
          width={42}
        />
        <Tooltip formatter={(value: any) => [`${value}%`, "Overall"]} />
        <Line
          type="monotone"
          dataKey="score"
          name="Overall"
          stroke="#2563eb"
          strokeWidth={2}
          dot={{ r: 4 }}
          connectNulls
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
