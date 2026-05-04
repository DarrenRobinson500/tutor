import { useEffect, useState } from "react";
import { Layout } from "./components/Layout";
import { apiFetch } from "../utils/apiFetch";

interface PaymentRow {
  id: number;
  date_tuition: string | null;
  student_name: string;
  tutor_name: string;
  amount_paid: string;
  focus_area: string;
}

interface MonthBlock {
  label: string;
  payments: PaymentRow[];
  total: string;
}

interface PaymentsData {
  current_month: MonthBlock;
  last_month: MonthBlock;
  older: { payments: PaymentRow[]; total: string };
}

function fmt(date: string | null) {
  if (!date) return "—";
  return new Date(date).toLocaleDateString("en-AU", { day: "numeric", month: "short", year: "numeric" });
}

function currency(val: string) {
  return `$${parseFloat(val).toFixed(2)}`;
}

function PaymentTable({ payments }: { payments: PaymentRow[] }) {
  if (payments.length === 0) {
    return <p className="text-muted" style={{ fontSize: 13 }}>No payments this period.</p>;
  }
  return (
    <table className="table table-sm table-hover" style={{ fontSize: 13 }}>
      <thead className="table-light">
        <tr>
          <th>Date</th>
          <th>Student</th>
          <th>Tutor</th>
          <th>Focus Area</th>
          <th className="text-end">Amount</th>
        </tr>
      </thead>
      <tbody>
        {payments.map(p => (
          <tr key={p.id}>
            <td>{fmt(p.date_tuition)}</td>
            <td>{p.student_name}</td>
            <td>{p.tutor_name}</td>
            <td className="text-muted">{p.focus_area || "—"}</td>
            <td className="text-end">{currency(p.amount_paid)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function MonthSection({ title, label, block }: { title: string; label?: string; block: { payments: PaymentRow[]; total: string } }) {
  return (
    <div className="mb-4">
      <div className="d-flex justify-content-between align-items-baseline mb-2">
        <h5 className="mb-0">{title}{label ? ` — ${label}` : ""}</h5>
        <span className="fw-semibold text-success fs-6">{currency(block.total)}</span>
      </div>
      <PaymentTable payments={block.payments} />
    </div>
  );
}

export function ParentPaymentsPage() {
  const [data, setData] = useState<PaymentsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [showOlder, setShowOlder] = useState(false);

  useEffect(() => {
    apiFetch("/api/auth/parent_payments/")
      .then(r => r.json())
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, []);

  return (
    <Layout>
      <div className="container mt-4" style={{ maxWidth: 800 }}>
        <h3 className="mb-4">Payments</h3>

        {loading && <p className="text-muted">Loading…</p>}

        {!loading && !data && (
          <p className="text-danger">Failed to load payments.</p>
        )}

        {data && (
          <>
            <MonthSection title="This Month" label={data.current_month.label} block={data.current_month} />
            <MonthSection title="Last Month" label={data.last_month.label} block={data.last_month} />

            {data.older.payments.length > 0 && (
              <div className="mb-4">
                <button
                  className="btn btn-sm btn-outline-secondary mb-2"
                  onClick={() => setShowOlder(v => !v)}
                >
                  {showOlder ? "Hide older payments" : `Show older payments (${data.older.payments.length})`}
                </button>
                {showOlder && (
                  <MonthSection title="Older" block={data.older} />
                )}
              </div>
            )}
          </>
        )}
      </div>
    </Layout>
  );
}
