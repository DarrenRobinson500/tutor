import { useEffect, useState } from "react";
import { Layout } from "./components/Layout";
import { apiFetch } from "../utils/apiFetch";

interface PaymentRow {
  id: number;
  status: string;
  session_date: string | null;
  student_name: string;
  child_name: string;
  focus_areas: string[];
  tutor_amount: string;
  total_amount: string;
  paid_at: string | null;
  confirmed_at: string | null;
}

interface BillingData {
  pending: PaymentRow[];
  paid: PaymentRow[];
  confirmed: PaymentRow[];
  failed: PaymentRow[];
  total_pending: string;
  total_paid: string;
  total_confirmed_this_month: string;
  total_confirmed_all_time: string;
}

function fmt(date: string | null) {
  if (!date) return "—";
  return new Date(date).toLocaleDateString("en-AU", { day: "numeric", month: "short", year: "numeric" });
}

function currency(val: string) {
  return `$${parseFloat(val).toFixed(2)}`;
}

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, { label: string; color: string }> = {
    pending:   { label: "Pending",   color: "#f59e0b" },
    paid:      { label: "Paid",      color: "#3b82f6" },
    confirmed: { label: "Confirmed", color: "#16a34a" },
    failed:    { label: "Failed",    color: "#ef4444" },
  };
  const s = map[status] ?? { label: status, color: "#8A7F74" };
  return (
    <span style={{
      display: "inline-block",
      padding: "2px 8px",
      borderRadius: 12,
      fontSize: 12,
      fontWeight: 600,
      background: s.color + "20",
      color: s.color,
    }}>
      {s.label}
    </span>
  );
}

function PaymentTable({
  payments,
  onConfirm,
  confirming,
}: {
  payments: PaymentRow[];
  onConfirm?: (id: number) => void;
  confirming?: number | null;
}) {
  if (payments.length === 0) {
    return <p className="text-muted" style={{ fontSize: 13 }}>None.</p>;
  }
  return (
    <table className="table table-sm table-hover" style={{ fontSize: 13 }}>
      <thead className="table-light">
        <tr>
          <th>Date</th>
          <th>Student</th>
          <th>Focus Area</th>
          <th>Status</th>
          <th className="text-end">Your Payment</th>
          {onConfirm && <th />}
        </tr>
      </thead>
      <tbody>
        {payments.map(p => (
          <tr key={p.id}>
            <td>{fmt(p.session_date)}</td>
            <td>{p.student_name || p.child_name || "—"}</td>
            <td className="text-muted">{p.focus_areas?.[0] || "—"}</td>
            <td><StatusBadge status={p.status} /></td>
            <td className="text-end">{currency(p.tutor_amount)}</td>
            {onConfirm && (
              <td className="text-end">
                <button
                  className="btn btn-sm btn-success"
                  style={{ fontSize: 12, padding: "2px 10px" }}
                  disabled={confirming === p.id}
                  onClick={() => onConfirm(p.id)}
                >
                  {confirming === p.id ? "Confirming…" : "Confirm receipt"}
                </button>
              </td>
            )}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function TutorPaymentsPage() {
  const [data, setData] = useState<BillingData | null>(null);
  const [loading, setLoading] = useState(true);
  const [confirming, setConfirming] = useState<number | null>(null);
  const [confirmError, setConfirmError] = useState("");

  function load() {
    return apiFetch("/api/payments/tutor-billing/")
      .then(r => r.json())
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }

  useEffect(() => { load(); }, []);

  async function handleConfirm(id: number) {
    setConfirming(id);
    setConfirmError("");
    const res = await apiFetch(`/api/payments/${id}/confirm/`, { method: "POST" });
    const json = await res.json();
    if (res.ok && json.success) {
      setLoading(true);
      load();
    } else {
      setConfirmError(json.error || "Something went wrong.");
    }
    setConfirming(null);
  }

  return (
    <Layout>
      <div className="container mt-4" style={{ maxWidth: 860 }}>
        <h3 className="mb-4">Payments</h3>

        {loading && <p className="text-muted">Loading…</p>}

        {!loading && !data && (
          <p className="text-danger">Failed to load payments.</p>
        )}

        {confirmError && (
          <div className="alert alert-danger py-2">{confirmError}</div>
        )}

        {data && (
          <>
            {/* Summary stats */}
            <div className="row g-3 mb-4">
              <div className="col-sm-4">
                <div className="border rounded p-3 text-center">
                  <div className="text-muted" style={{ fontSize: 12, textTransform: "uppercase", letterSpacing: "0.05em" }}>Awaiting Payment</div>
                  <div className="fw-bold fs-5 mt-1" style={{ color: "#f59e0b" }}>{currency(data.total_pending)}</div>
                </div>
              </div>
              <div className="col-sm-4">
                <div className="border rounded p-3 text-center">
                  <div className="text-muted" style={{ fontSize: 12, textTransform: "uppercase", letterSpacing: "0.05em" }}>Confirmed This Month</div>
                  <div className="fw-bold fs-5 mt-1" style={{ color: "#16a34a" }}>{currency(data.total_confirmed_this_month)}</div>
                </div>
              </div>
              <div className="col-sm-4">
                <div className="border rounded p-3 text-center">
                  <div className="text-muted" style={{ fontSize: 12, textTransform: "uppercase", letterSpacing: "0.05em" }}>All Time</div>
                  <div className="fw-bold fs-5 mt-1">{currency(data.total_confirmed_all_time)}</div>
                </div>
              </div>
            </div>

            {/* Paid by parent — awaiting tutor confirmation */}
            {data.paid.length > 0 && (
              <div className="mb-4">
                <h5 className="mb-2" style={{ color: "#3b82f6" }}>
                  Parent has paid — confirm receipt
                  <span className="badge ms-2" style={{ background: "#3b82f620", color: "#3b82f6", fontSize: 12 }}>
                    {data.paid.length}
                  </span>
                </h5>
                <PaymentTable payments={data.paid} onConfirm={handleConfirm} confirming={confirming} />
              </div>
            )}

            {/* Pending — waiting for parent to pay */}
            <div className="mb-4">
              <div className="d-flex justify-content-between align-items-baseline mb-2">
                <h5 className="mb-0">Awaiting parent payment</h5>
                <span className="fw-semibold" style={{ color: "#f59e0b" }}>{currency(data.total_pending)}</span>
              </div>
              <PaymentTable payments={data.pending} />
            </div>

            {/* Confirmed */}
            <div className="mb-4">
              <div className="d-flex justify-content-between align-items-baseline mb-2">
                <h5 className="mb-0">Confirmed</h5>
                <span className="fw-semibold text-success">{currency(data.total_confirmed_all_time)}</span>
              </div>
              <PaymentTable payments={data.confirmed} />
            </div>
          </>
        )}
      </div>
    </Layout>
  );
}
