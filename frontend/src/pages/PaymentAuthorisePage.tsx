import { useEffect, useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { apiFetch } from "../utils/apiFetch";
import { dashboardPath } from "../utils/dashboardPath";
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
  bank_bsb: string;
  bank_account: string;
  bank_name: string;
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

function paymentRef(childName: string) {
  const parts = childName.trim().split(/\s+/);
  return `TUT_${(parts[0] + (parts[1]?.[0] ?? "")).toUpperCase()}`;
}

function CopyIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
      <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
    </svg>
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
  const [copiedField, setCopiedField] = useState<string | null>(null);

  function copyField(key: string, value: string) {
    navigator.clipboard.writeText(value).then(() => {
      setCopiedField(key);
      setTimeout(() => setCopiedField((cur) => cur === key ? null : cur), 1500);
    });
  }

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
        <Link to={dashboardPath()} className="pa-nav-logo">
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
                className="pa-comment"
                placeholder={`Let us know if you have any feedback on ${payment.tutor_name.split(" ")[0]}…`}
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
          </div>

          {/* Bank transfer instructions */}
          <div className="pa-section">
            <div className="pa-label">Bank transfer details</div>
            <p style={{ marginBottom: "0.75rem", fontSize: 14, color: "var(--sm-text-muted)" }}>
              Please transfer {currency(payment.total_amount)} to the account below, then click
              "I've paid" to confirm.
            </p>
            <div className="pa-breakdown">
              <div className="pa-breakdown-row pa-copy-row">
                <span className="pa-copy-label">Account name</span>
                <span className="pa-copy-value">
                  <span style={{ fontWeight: 600 }}>{payment.bank_name || "SubjectMatter"}</span>
                  <button className="pa-copy-btn" onClick={() => copyField("name", payment.bank_name || "SubjectMatter")} aria-label="Copy account name">
                    {copiedField === "name" ? <span className="pa-copied">Copied!</span> : <CopyIcon />}
                  </button>
                </span>
              </div>
              {payment.bank_bsb && (
                <div className="pa-breakdown-row pa-copy-row">
                  <span className="pa-copy-label">BSB</span>
                  <span className="pa-copy-value">
                    <span style={{ fontWeight: 600, fontFamily: "monospace" }}>{payment.bank_bsb}</span>
                    <button className="pa-copy-btn" onClick={() => copyField("bsb", payment.bank_bsb)} aria-label="Copy BSB">
                      {copiedField === "bsb" ? <span className="pa-copied">Copied!</span> : <CopyIcon />}
                    </button>
                  </span>
                </div>
              )}
              {payment.bank_account && (
                <div className="pa-breakdown-row pa-copy-row">
                  <span className="pa-copy-label">Account number</span>
                  <span className="pa-copy-value">
                    <span style={{ fontWeight: 600, fontFamily: "monospace" }}>{payment.bank_account}</span>
                    <button className="pa-copy-btn" onClick={() => copyField("account", payment.bank_account)} aria-label="Copy account number">
                      {copiedField === "account" ? <span className="pa-copied">Copied!</span> : <CopyIcon />}
                    </button>
                  </span>
                </div>
              )}
              <div className="pa-breakdown-row pa-copy-row">
                <span className="pa-copy-label">Reference</span>
                <span className="pa-copy-value">
                  <span style={{ fontWeight: 600, fontFamily: "monospace" }}>{paymentRef(payment.child_name)}</span>
                  <button className="pa-copy-btn" onClick={() => copyField("ref", paymentRef(payment.child_name))} aria-label="Copy reference">
                    {copiedField === "ref" ? <span className="pa-copied">Copied!</span> : <CopyIcon />}
                  </button>
                </span>
              </div>
            </div>
          </div>

          {/* Errors */}
          {payError && (
            <div className="sm-alert sm-alert-error" style={{ marginBottom: "1rem" }}>
              {payError}
            </div>
          )}

          {/* Actions */}
          <div className="pa-actions">
            <button
              className="sm-btn-primary pa-pay-btn"
              onClick={handlePay}
              disabled={paying}
            >
              {paying ? "Confirming…" : "I've paid"}
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
