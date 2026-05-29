import { useEffect, useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { apiFetch } from "../utils/apiFetch";
import { ParentNav } from "./components/ParentNav";
import "./ParentHomePage.css";

interface PaymentRow {
  id: number;
  session_date: string | null;
  child_name: string;
  tutor_name: string;
  total_amount: string;
  tutor_amount: string;
  platform_amount: string;
  distributor_amount: string;
  status: string;
  paid_at: string | null;
  expected_settlement_date: string | null;
}

interface PaymentsData {
  pending: PaymentRow[];
  paid: PaymentRow[];
  failed: PaymentRow[];
}

function currency(v: string | number) {
  return `$${parseFloat(String(v)).toFixed(2)}`;
}

function fmtDate(iso: string | null) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-AU", { day: "numeric", month: "short", year: "numeric" });
}

function StatusBadge({ status }: { status: string }) {
  const cfg: Record<string, { bg: string; color: string; label: string }> = {
    pending:    { bg: "#FFF8E1", color: "var(--sm-amber, #FFCA3A)",              label: "Pending" },
    paid:       { bg: "var(--sm-success-bg, #E8F5E9)", color: "var(--sm-success, #2E7D32)", label: "Paid" },
    failed:     { bg: "var(--sm-error-bg, #FFEBEE)",   color: "var(--sm-error, #C0392B)",   label: "Failed" },
    overdue_7:  { bg: "#FFF3E0", color: "#E65100",                               label: "Overdue" },
    overdue_14: { bg: "var(--sm-error-bg, #FFEBEE)",   color: "var(--sm-error, #C0392B)",   label: "Overdue" },
  };
  const c = cfg[status] || { bg: "#eee", color: "#333", label: status };
  return (
    <span style={{
      background: c.bg, color: c.color,
      borderRadius: "9999px", padding: "2px 10px",
      fontSize: "0.75rem", fontWeight: 600,
    }}>
      {c.label}
    </span>
  );
}

function PaymentTable({
  rows,
  showPayBtn,
  showRetryBtn,
  onAction,
}: {
  rows: PaymentRow[];
  showPayBtn?: boolean;
  showRetryBtn?: boolean;
  onAction?: (id: number) => void;
}) {
  if (rows.length === 0) {
    return <p style={{ color: "var(--sm-text-muted, #8A7F74)", fontSize: 13 }}>None.</p>;
  }
  return (
    <div style={{ overflowX: "auto", borderRadius: 12, border: "1px solid var(--sm-border, #E8E0D6)", boxShadow: "0 2px 8px rgba(0,0,0,.06)", marginBottom: "1rem" }}>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.875rem" }}>
        <thead>
          <tr style={{ background: "#fff", borderBottom: "1px solid var(--sm-border, #E8E0D6)" }}>
            {["Date", "Child", "Tutor", "Amount", "Status", ""].map((h) => (
              <th key={h} style={{ padding: "0.6rem 1rem", textAlign: "left", fontWeight: 600, fontSize: "0.75rem", textTransform: "uppercase", letterSpacing: "0.04em", color: "var(--sm-text-muted, #8A7F74)" }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((p, i) => (
            <tr key={p.id} style={{ background: i % 2 === 0 ? "var(--sm-bg, #FFFBF5)" : "#fff", borderBottom: "1px solid var(--sm-border, #E8E0D6)" }}>
              <td style={{ padding: "0.65rem 1rem" }}>{fmtDate(p.session_date)}</td>
              <td style={{ padding: "0.65rem 1rem" }}>{p.child_name}</td>
              <td style={{ padding: "0.65rem 1rem" }}>{p.tutor_name}</td>
              <td style={{ padding: "0.65rem 1rem", fontWeight: 600 }}>{currency(p.total_amount)}</td>
              <td style={{ padding: "0.65rem 1rem" }}><StatusBadge status={p.status} /></td>
              <td style={{ padding: "0.65rem 1rem" }}>
                {showPayBtn && onAction && (
                  <button className="sm-btn-primary" style={{ fontSize: 13, padding: "4px 14px" }} onClick={() => onAction(p.id)}>
                    Pay now
                  </button>
                )}
                {showRetryBtn && onAction && (
                  <button className="sm-btn-secondary" style={{ fontSize: 13, padding: "4px 14px" }} onClick={() => onAction(p.id)}>
                    Retry
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function ParentPaymentsPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [data, setData] = useState<PaymentsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");


  useEffect(() => {
    apiFetch(`/api/parents/${id}/payments/`)
      .then((r) => {
        if (!r.ok) throw new Error("Could not load payment history");
        return r.json();
      })
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) {
    return (
      <div style={{ minHeight: "60vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <img src="/subjectmatter_logo.svg" alt="" style={{ height: 48 }} />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div style={{ padding: "3rem", textAlign: "center", fontFamily: "Inter, system-ui, sans-serif" }}>
        <p style={{ color: "var(--sm-error, #C0392B)" }}>{error || "Something went wrong."}</p>
        <Link to="/" style={{ color: "var(--sm-orange, #FF8C42)" }}>Go home</Link>
      </div>
    );
  }

  return (
    <div className="ph-page">

      <ParentNav parentId={id!} />

      <header className="ph-header">
        <div className="ph-header-inner">
          <h1 className="ph-greeting">Payments</h1>
        </div>
      </header>

      <main className="ph-body" style={{ maxWidth: 900 }}>

        {/* Pending */}
        <section style={{ marginBottom: "2.5rem" }}>
          <h2 style={{ fontFamily: "var(--font-display, Lora, serif)", fontSize: "1.1rem", fontWeight: 600, marginBottom: "0.75rem" }}>
            Awaiting payment
          </h2>
          <PaymentTable
            rows={data.pending}
            showPayBtn
            onAction={(id) => navigate(`/payments/${id}/authorise`)}
          />
        </section>

        {/* Paid */}
        <section style={{ marginBottom: "2.5rem" }}>
          <h2 style={{ fontFamily: "var(--font-display, Lora, serif)", fontSize: "1.1rem", fontWeight: 600, marginBottom: "0.75rem" }}>
            Payment history
          </h2>
          <PaymentTable rows={data.paid} />
        </section>

        {/* Failed */}
        {data.failed.length > 0 && (
          <section style={{ marginBottom: "2.5rem" }}>
            <h2 style={{ fontFamily: "var(--font-display, Lora, serif)", fontSize: "1.1rem", fontWeight: 600, marginBottom: "0.75rem" }}>
              Failed payments
            </h2>
            <PaymentTable
              rows={data.failed}
              showRetryBtn
              onAction={(id) => navigate(`/payments/${id}/retry`)}
            />
          </section>
        )}
      </main>
    </div>
  );
}
