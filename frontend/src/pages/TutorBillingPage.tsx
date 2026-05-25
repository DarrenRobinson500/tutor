import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { apiFetch } from "../utils/apiFetch";
import { dashboardPath } from "../utils/dashboardPath";
import "./TutorBillingPage.css";

interface PaymentRow {
  id: number;
  session_date: string | null;
  child_name: string;
  total_amount: string;
  tutor_amount: string;
  status: string;
  paid_at: string | null;
  expected_settlement_date: string | null;
}

interface BillingData {
  pending: PaymentRow[];
  confirmed: PaymentRow[];
  failed: PaymentRow[];
  total_pending: string;
  total_confirmed_this_month: string;
  total_confirmed_all_time: string;
}

function currency(v: string | number) {
  return `$${parseFloat(String(v)).toFixed(2)}`;
}

function fmtShort(iso: string | null) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-AU", { day: "numeric", month: "short", year: "numeric" });
}

function fmtSettlement(iso: string | null) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-AU", { weekday: "short", day: "numeric", month: "short" });
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, React.CSSProperties> = {
    paid:       { background: "var(--sm-success-bg, #E8F5E9)",   color: "var(--sm-success, #2E7D32)" },
    pending:    { background: "#FFF8E1",                          color: "var(--sm-amber, #FFCA3A)" },
    overdue_7:  { background: "#FFF3E0",                          color: "#E65100" },
    overdue_14: { background: "var(--sm-error-bg, #FFEBEE)",     color: "var(--sm-error, #C0392B)" },
    failed:     { background: "var(--sm-error-bg, #FFEBEE)",     color: "var(--sm-error, #C0392B)" },
  };
  const label: Record<string, string> = {
    paid: "Paid", pending: "Pending", overdue_7: "Overdue", overdue_14: "Overdue", failed: "Failed",
  };
  const s = styles[status] || {};
  return (
    <span style={{
      ...s,
      borderRadius: "var(--radius-full, 9999px)",
      padding: "2px 10px",
      fontSize: "var(--text-xs, 0.75rem)",
      fontWeight: 600,
      whiteSpace: "nowrap",
    }}>
      {label[status] || status}
    </span>
  );
}

function SummaryCard({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div className="tb-summary-card">
      <div className="tb-summary-amount" style={{ color }}>{currency(value)}</div>
      <div className="tb-summary-label">{label}</div>
    </div>
  );
}

function PaymentTable({ rows, columns }: { rows: PaymentRow[]; columns: string[] }) {
  if (rows.length === 0) {
    return <p style={{ color: "var(--sm-text-muted, #8A7F74)", fontSize: 13, marginTop: "0.5rem" }}>None.</p>;
  }

  return (
    <div className="tb-table-wrap">
      <table className="tb-table">
        <thead>
          <tr>
            {columns.map((c) => <th key={c}>{c}</th>)}
          </tr>
        </thead>
        <tbody>
          {rows.map((p, i) => (
            <tr key={p.id} style={{ background: i % 2 === 0 ? "var(--sm-bg, #FFFBF5)" : "var(--sm-surface, #fff)" }}>
              <td>{fmtShort(p.session_date)}</td>
              <td>{p.child_name}</td>
              <td><strong>{currency(p.tutor_amount)}</strong></td>
              <td><StatusBadge status={p.status} /></td>
              {columns.includes("Expected by") && (
                <td style={{ color: p.expected_settlement_date ? "var(--sm-text-muted, #8A7F74)" : "var(--sm-text-muted, #8A7F74)" }}>
                  {fmtSettlement(p.expected_settlement_date)}
                </td>
              )}
              {columns.includes("Settled by") && (
                <td>{fmtSettlement(p.expected_settlement_date)}</td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function TutorBillingPage() {
  const { id } = useParams<{ id: string }>();
  const [data, setData] = useState<BillingData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    apiFetch("/api/payments/tutor-billing/")
      .then((r) => {
        if (!r.ok) throw new Error("Could not load billing data");
        return r.json();
      })
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <div className="tb-loading"><img src="/subjectmatter_logo.svg" alt="" style={{ height: 48 }} /></div>;

  if (error || !data) {
    return (
      <div className="tb-error">
        <p>{error || "Could not load billing."}</p>
        <Link to="/" style={{ color: "var(--sm-orange)" }}>Go home</Link>
      </div>
    );
  }

  return (
    <div className="tb-page">
      <nav className="tb-nav">
        <Link to={dashboardPath()} className="tb-nav-logo">
          <img src="/subjectmatter_wordmark.svg" alt="SubjectMatter" />
        </Link>
        <span className="tb-nav-title">Billing</span>
      </nav>

      <main className="tb-main">

        {/* Summary strip */}
        <div className="tb-summary-strip">
          <SummaryCard label="Awaiting payment" value={data.total_pending} color="var(--sm-amber, #FFCA3A)" />
          <SummaryCard label="Confirmed this month" value={data.total_confirmed_this_month} color="var(--sm-success, #2E7D32)" />
          <SummaryCard label="All time" value={data.total_confirmed_all_time} color="var(--sm-text, #2D2D2D)" />
        </div>

        {/* Pending */}
        <section className="tb-section">
          <h2 className="tb-section-title">Pending payments</h2>
          <PaymentTable
            rows={data.pending}
            columns={["Session date", "Child", "Your payment", "Status", "Expected by"]}
          />
        </section>

        {/* Confirmed */}
        <section className="tb-section">
          <h2 className="tb-section-title">Confirmed payments</h2>
          <PaymentTable
            rows={data.confirmed}
            columns={["Session date", "Child", "Your payment", "Status", "Settled by"]}
          />
        </section>

        {/* Failed */}
        {data.failed.length > 0 && (
          <section className="tb-section">
            <h2 className="tb-section-title">Failed payments</h2>
            <PaymentTable
              rows={data.failed}
              columns={["Session date", "Child", "Your payment", "Status", "Expected by"]}
            />
          </section>
        )}
      </main>
    </div>
  );
}
