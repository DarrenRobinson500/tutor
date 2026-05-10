import { useEffect, useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { apiFetch } from "../utils/apiFetch";
import "./PaymentAuthorisePage.css";

interface PaymentDetail {
  id: number;
  status: string;
  tutor_name: string;
  tutor_id: number;
  child_name: string;
  session_date: string;
  focus_areas: string[];
  parent_message: string;
  tutor_amount: string;
  platform_amount: string;
  distributor_amount: string;
  total_amount: string;
  rating: number | null;
  card_info: { brand: string; last4: string } | null;
}

function fmtDate(iso: string) {
  return new Date(iso).toLocaleDateString("en-AU", {
    weekday: "long", day: "numeric", month: "long", year: "numeric",
  });
}

function currency(v: string | number) {
  return `$${parseFloat(String(v)).toFixed(2)}`;
}

function StarRating({ value, onChange }: { value: number; onChange: (n: number) => void }) {
  const [hover, setHover] = useState(0);
  return (
    <div className="pa-stars">
      {[1, 2, 3, 4, 5].map((n) => (
        <button
          key={n}
          type="button"
          className={`pa-star ${n <= (hover || value) ? "active" : ""}`}
          onMouseEnter={() => setHover(n)}
          onMouseLeave={() => setHover(0)}
          onClick={() => onChange(n)}
          aria-label={`${n} star${n !== 1 ? "s" : ""}`}
        >
          ★
        </button>
      ))}
    </div>
  );
}

export function PaymentAuthorisePage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [payment, setPayment] = useState<PaymentDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [rating, setRating] = useState(0);
  const [comment, setComment] = useState("");
  const [paying, setPaying] = useState(false);
  const [payError, setPayError] = useState("");

  useEffect(() => {
    apiFetch(`/api/payments/${id}/`)
      .then((r) => {
        if (!r.ok) throw new Error("Could not load payment details");
        return r.json();
      })
      .then(setPayment)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [id]);

  async function handlePay() {
    if (!payment) return;
    setPaying(true);
    setPayError("");

    const res = await apiFetch(`/api/payments/${id}/authorise/`, {
      method: "POST",
      body: JSON.stringify({
        rating: rating || undefined,
        rating_comment: comment || undefined,
      }),
    });

    const data = await res.json();

    if (res.ok && data.success) {
      navigate(`/payments/${id}/receipt`);
    } else if (res.status === 402) {
      setPayError("Your card was declined. Please update your payment details.");
    } else {
      setPayError(data.message || data.error || "Something went wrong.");
    }
    setPaying(false);
  }

  if (loading) {
    return (
      <div className="pa-loading">
        <img src="/subjectmatter_logo.svg" alt="" style={{ height: 48 }} />
      </div>
    );
  }

  if (error || !payment) {
    return (
      <div className="pa-error">
        <p>{error || "Payment not found."}</p>
        <Link to="/parent-home" style={{ color: "var(--sm-orange)" }}>Back to dashboard</Link>
      </div>
    );
  }

  const distAmount = parseFloat(payment.distributor_amount);
  const showDist = distAmount > 0;

  return (
    <div className="pa-page">
      <nav className="pa-nav">
        <Link to="/" className="pa-nav-logo">
          <img src="/subjectmatter_wordmark.svg" alt="SubjectMatter" />
        </Link>
      </nav>

      <main className="pa-main">
        <div className="sm-card pa-card">

          {/* Session summary */}
          <div className="pa-section">
            <h1 className="pa-heading">Session with {payment.tutor_name}</h1>
            <div className="pa-meta">
              <span>{payment.child_name}</span>
              <span className="pa-dot">·</span>
              <span>{fmtDate(payment.session_date)}</span>
            </div>

            {payment.focus_areas.length > 0 && (
              <div className="pa-focus">
                <div className="pa-label">Focus areas covered</div>
                <ul className="pa-focus-list">
                  {payment.focus_areas.map((f, i) => <li key={i}>{f}</li>)}
                </ul>
              </div>
            )}

            {payment.parent_message && (
              <div className="pa-message">
                <div className="pa-label">Message from {payment.tutor_name}</div>
                <p className="pa-message-text">{payment.parent_message}</p>
              </div>
            )}
          </div>

          {/* Rating */}
          <div className="pa-section">
            <div className="pa-label">How did the session go?</div>
            <StarRating value={rating} onChange={setRating} />
            {rating > 0 && (
              <textarea
                className="sm-input pa-comment"
                placeholder="Optional comment…"
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                rows={3}
              />
            )}
            {rating > 0 && rating <= 2 && (
              <p className="pa-low-rating-note">
                Thanks for letting us know — we'll follow up.
              </p>
            )}
          </div>

          {/* Fee breakdown */}
          <div className="pa-section">
            <div className="pa-label">Payment summary</div>
            <div className="pa-breakdown">
              <div className="pa-breakdown-row">
                <span>Tutor fee</span>
                <span>{currency(payment.tutor_amount)}</span>
              </div>
              <div className="pa-breakdown-row">
                <span>Platform fee</span>
                <span>{currency(payment.platform_amount)}</span>
              </div>
              {showDist && (
                <div className="pa-breakdown-row">
                  <span>Distributor fee</span>
                  <span>{currency(payment.distributor_amount)}</span>
                </div>
              )}
              <div className="pa-breakdown-row pa-breakdown-total">
                <span>Total</span>
                <span>{currency(payment.total_amount)}</span>
              </div>
            </div>

            {payment.card_info && (
              <p className="pa-card-note">
                Charged to {payment.card_info.brand.charAt(0).toUpperCase() + payment.card_info.brand.slice(1)} ···· {payment.card_info.last4}
              </p>
            )}
          </div>

          {/* Errors */}
          {payError && (
            <div className="sm-alert sm-alert-error" style={{ marginBottom: "1rem" }}>
              {payError}
              {payError.includes("declined") && (
                <div style={{ marginTop: 8 }}>
                  <button
                    className="sm-btn-secondary"
                    style={{ fontSize: 13 }}
                    onClick={() => navigate(`/payments/${id}/retry`)}
                  >
                    Update card
                  </button>
                </div>
              )}
            </div>
          )}

          {/* Actions */}
          <div className="pa-actions">
            <button
              className="sm-btn-primary pa-pay-btn"
              onClick={handlePay}
              disabled={paying}
            >
              {paying ? "Processing…" : `Pay ${currency(payment.total_amount)}`}
            </button>
            <button
              className="sm-btn-ghost"
              onClick={() => navigate(-1)}
              disabled={paying}
            >
              Pay later
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}
