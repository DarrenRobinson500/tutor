import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { apiFetch } from "../utils/apiFetch";

interface PaymentDetail {
  id: number;
  tutor_name: string;
  child_name: string;
  session_date: string;
  focus_areas: string[];
  tutor_amount: string;
  platform_amount: string;
  distributor_amount: string;
  total_amount: string;
  paid_at: string | null;
  expected_settlement_date: string | null;
}

function currency(v: string | number) {
  return `$${parseFloat(String(v)).toFixed(2)}`;
}

function fmtDate(iso: string) {
  return new Date(iso).toLocaleDateString("en-AU", {
    weekday: "long", day: "numeric", month: "long", year: "numeric",
  });
}

function fmtSettlement(iso: string | null) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-AU", {
    weekday: "long", day: "numeric", month: "long",
  });
}

export function PaymentReceiptPage() {
  const { id } = useParams<{ id: string }>();
  const [payment, setPayment] = useState<PaymentDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    apiFetch(`/api/payments/${id}/`)
      .then((r) => {
        if (!r.ok) throw new Error("Could not load receipt");
        return r.json();
      })
      .then(setPayment)
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

  if (error || !payment) {
    return (
      <div style={{ padding: "3rem", textAlign: "center" }}>
        <p style={{ color: "var(--sm-error, #C0392B)" }}>{error || "Receipt not found."}</p>
        <Link to="/" style={{ color: "var(--sm-orange, #FF8C42)" }}>Go home</Link>
      </div>
    );
  }

  const distAmount = parseFloat(payment.distributor_amount);
  const showDist = distAmount > 0;

  return (
    <div style={{ minHeight: "100vh", background: "var(--sm-bg, #FFFBF5)", fontFamily: "Inter, system-ui, sans-serif" }}>
      <nav style={{ display: "flex", alignItems: "center", padding: "0 2rem", height: 60, background: "#fff", borderBottom: "1px solid var(--sm-border, #E8E0D6)" }}>
        <Link to="/">
          <img src="/subjectmatter_wordmark.svg" alt="SubjectMatter" style={{ height: 28 }} />
        </Link>
      </nav>

      <main style={{ maxWidth: 520, margin: "2rem auto", padding: "0 1rem" }}>
        <div className="sm-card" style={{ padding: "2rem" }}>

          {/* Success heading */}
          <div style={{ textAlign: "center", marginBottom: "2rem" }}>
            <div style={{ fontSize: "3rem", color: "var(--sm-success, #2E7D32)", lineHeight: 1, marginBottom: "0.5rem" }}>✓</div>
            <h1 style={{ fontFamily: "var(--font-display, Lora, serif)", fontSize: "1.5rem", fontWeight: 600, color: "var(--sm-success, #2E7D32)", margin: 0 }}>
              Payment confirmed
            </h1>
          </div>

          {/* Session summary */}
          <div style={{ marginBottom: "1.5rem", paddingBottom: "1.5rem", borderBottom: "1px solid var(--sm-border, #E8E0D6)" }}>
            <p style={{ margin: "0 0 0.25rem", fontWeight: 600 }}>Session with {payment.tutor_name}</p>
            <p style={{ margin: "0 0 0.75rem", fontSize: "0.875rem", color: "var(--sm-text-muted, #8A7F74)" }}>
              {payment.child_name} · {fmtDate(payment.session_date)}
            </p>
            {payment.focus_areas.length > 0 && (
              <ul style={{ margin: "0.25rem 0 0 1.25rem", padding: 0, fontSize: "0.875rem" }}>
                {payment.focus_areas.map((f, i) => <li key={i}>{f}</li>)}
              </ul>
            )}
          </div>

          {/* Fee breakdown */}
          <div style={{ marginBottom: "1.5rem", paddingBottom: "1.5rem", borderBottom: "1px solid var(--sm-border, #E8E0D6)" }}>
            <div style={{ border: "1px solid var(--sm-border, #E8E0D6)", borderRadius: 8, overflow: "hidden" }}>
              {[
                ["Tutor fee", payment.tutor_amount],
                ["Platform fee", payment.platform_amount],
                ...(showDist ? [["Distributor fee", payment.distributor_amount]] : []),
              ].map(([label, val]) => (
                <div key={label} style={{ display: "flex", justifyContent: "space-between", padding: "0.6rem 1rem", fontSize: "0.875rem", borderBottom: "1px solid var(--sm-border, #E8E0D6)" }}>
                  <span>{label}</span><span>{currency(val)}</span>
                </div>
              ))}
              <div style={{ display: "flex", justifyContent: "space-between", padding: "0.6rem 1rem", fontWeight: 700, background: "var(--sm-bg-warm, #FFF8F0)" }}>
                <span>Total</span><span>{currency(payment.total_amount)}</span>
              </div>
            </div>
          </div>

          {/* Settlement note */}
          <div style={{ background: "var(--sm-success-bg, #E8F5E9)", border: "1px solid #A5D6A7", borderRadius: 8, padding: "1rem 1.25rem", marginBottom: "1.5rem" }}>
            <p style={{ margin: 0, fontSize: "0.875rem", color: "var(--sm-success, #2E7D32)" }}>
              Your tutor will receive their payment by{" "}
              <strong>{fmtSettlement(payment.expected_settlement_date)}</strong>.
            </p>
          </div>

          <Link to="/" className="sm-btn-primary" style={{ display: "block", textAlign: "center", textDecoration: "none" }}>
            Back to dashboard
          </Link>
        </div>
      </main>
    </div>
  );
}
