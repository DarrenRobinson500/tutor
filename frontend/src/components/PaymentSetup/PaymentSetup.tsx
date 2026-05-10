import { useState, useEffect } from "react";
import { loadStripe } from "@stripe/stripe-js";
import {
  Elements,
  CardElement,
  useStripe,
  useElements,
} from "@stripe/react-stripe-js";
import { apiFetch } from "../../utils/apiFetch";
import "./PaymentSetup.css";

const stripePromise = loadStripe(
  process.env.REACT_APP_STRIPE_PUBLISHABLE_KEY || ""
);

const CARD_STYLE = {
  base: {
    fontFamily: "Inter, system-ui, sans-serif",
    fontSize: "16px",
    color: "#2D2D2D",
    "::placeholder": { color: "#B8B0A8" },
  },
  invalid: { color: "#C0392B" },
};

interface PaymentSetupProps {
  onComplete: () => void;
  onCancel: () => void;
  mode?: "setup" | "update";
}

function CardForm({ onComplete, onCancel, clientSecret, mode }: {
  onComplete: () => void;
  onCancel: () => void;
  clientSecret: string;
  mode: "setup" | "update";
}) {
  const stripe = useStripe();
  const elements = useElements();
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!stripe || !elements) return;

    setSaving(true);
    setError("");

    const card = elements.getElement(CardElement);
    if (!card) { setSaving(false); return; }

    const { error: stripeErr, setupIntent } = await stripe.confirmCardSetup(clientSecret, {
      payment_method: { card },
    });

    if (stripeErr) {
      setError(stripeErr.message || "Card setup failed. Please try again.");
      setSaving(false);
      return;
    }

    const pmId = setupIntent?.payment_method as string;
    const res = await apiFetch("/api/payments/save-payment-method/", {
      method: "POST",
      body: JSON.stringify({ payment_method_id: pmId }),
    });

    if (!res.ok) {
      setError("Failed to save your card. Please try again.");
      setSaving(false);
      return;
    }

    setDone(true);
    setTimeout(onComplete, 1200);
  }

  if (done) {
    return (
      <div className="psetup-success">
        <div className="psetup-success-icon">✓</div>
        <p>Your card has been saved. You'll only need to do this once.</p>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="psetup-form">
      <div className="psetup-card-wrap">
        <CardElement options={{ style: CARD_STYLE, hidePostalCode: true }} />
      </div>

      {error && (
        <div className="sm-alert sm-alert-error" style={{ marginBottom: "1rem" }}>
          {error}
        </div>
      )}

      <div className="psetup-actions">
        <button
          type="submit"
          className="sm-btn-primary"
          disabled={saving || !stripe}
        >
          {saving ? "Saving…" : mode === "update" ? "Update Card" : "Save Card"}
        </button>
        <button type="button" className="sm-btn-secondary" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </form>
  );
}

export function PaymentSetup({ onComplete, onCancel, mode = "setup" }: PaymentSetupProps) {
  const [clientSecret, setClientSecret] = useState<string | null>(null);
  const [loadError, setLoadError] = useState("");

  useEffect(() => {
    apiFetch("/api/payments/setup-intent/", { method: "POST" })
      .then((r) => {
        if (!r.ok) throw new Error("Failed to initialise payment setup");
        return r.json();
      })
      .then((d) => setClientSecret(d.client_secret))
      .catch((e) => setLoadError(e.message));
  }, []);

  if (loadError) {
    return (
      <div className="sm-alert sm-alert-error">{loadError}</div>
    );
  }

  if (!clientSecret) {
    return <p style={{ color: "var(--sm-text-muted)", fontSize: 14 }}>Loading payment form…</p>;
  }

  return (
    <Elements stripe={stripePromise} options={{ clientSecret }}>
      <CardForm
        onComplete={onComplete}
        onCancel={onCancel}
        clientSecret={clientSecret}
        mode={mode}
      />
    </Elements>
  );
}
