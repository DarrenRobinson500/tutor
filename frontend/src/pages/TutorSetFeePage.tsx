import { useState, useEffect } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { apiFetch } from "../utils/apiFetch";

export default function TutorSetFeePage() {
  const { id: tutorId } = useParams<{ id: string }>();
  const [searchParams] = useSearchParams();
  const jobId = searchParams.get("job_id");
  const navigate = useNavigate();

  const [rate, setRate] = useState("70");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [platformFee, setPlatformFee] = useState<number | null>(null);

  useEffect(() => {
    apiFetch('/api/settings/')
      .then(r => r.json())
      .then((d: { platform_fee: number }) => { if (d.platform_fee != null) setPlatformFee(d.platform_fee); })
      .catch(() => {});
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    const parsed = parseFloat(rate);
    if (isNaN(parsed) || parsed < 1) {
      setError("Please enter a valid hourly rate.");
      return;
    }
    setSaving(true);
    try {
      const res = await apiFetch(`/api/jobs/${jobId}/complete/`, {
        method: "POST",
        body: JSON.stringify({ hourly_rate: parsed }),
      });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        setError(d.error || "Could not save. Please try again.");
        return;
      }
      navigate(`/tutors/${tutorId}`);
    } catch {
      setError("Something went wrong. Please try again.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div style={{ minHeight: "100vh", background: "#FFFBF5", display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "Inter, system-ui, sans-serif" }}>
      <div style={{ background: "#fff", borderRadius: 16, boxShadow: "0 2px 16px rgba(0,0,0,.08)", padding: "2.5rem", width: "100%", maxWidth: 420 }}>
        <h1 style={{ fontSize: "1.5rem", fontWeight: 700, marginBottom: "0.5rem", color: "#1e293b" }}>
          Set your tutoring fee
        </h1>
        <p style={{ fontSize: "0.9rem", color: "#64748b", marginBottom: "1.75rem", lineHeight: 1.6 }}>
          This is the hourly rate parents will see when choosing a tutor. You can update it any time from your profile settings.
        </p>

        <form onSubmit={handleSubmit} noValidate>
          <label style={{ display: "block", fontWeight: 600, fontSize: "0.875rem", marginBottom: "0.4rem", color: "#1e293b" }}>
            Hourly rate (AUD)
          </label>
          <div style={{ display: "flex", alignItems: "center", border: "1.5px solid #e2e8f0", borderRadius: 8, overflow: "hidden", marginBottom: "1.25rem" }}>
            <span style={{ padding: "0.6rem 0.75rem", background: "#f8fafc", color: "#64748b", fontWeight: 600, borderRight: "1.5px solid #e2e8f0" }}>$</span>
            <input
              type="number"
              min="1"
              step="0.01"
              value={rate}
              onChange={(e) => setRate(e.target.value)}
              style={{ flex: 1, border: "none", outline: "none", padding: "0.6rem 0.75rem", fontSize: "1.1rem", fontWeight: 600, color: "#1e293b", background: "transparent" }}
              placeholder="70"
              required
            />
            <span style={{ padding: "0.6rem 0.75rem", color: "#94a3b8", fontSize: "0.85rem" }}>/ hr</span>
          </div>

          <div style={{ background: "#fff8f0", border: "1px solid #fed7aa", borderRadius: 8, padding: "0.75rem 1rem", marginBottom: "1.5rem", fontSize: "0.82rem", color: "#92400e", lineHeight: 1.5 }}>
            Parents pay your rate plus a ${platformFee != null ? platformFee.toFixed(2) : '…'} platform fee per session.
          </div>

          {error && (
            <p style={{ color: "#dc2626", fontSize: "0.85rem", marginBottom: "1rem" }}>{error}</p>
          )}

          <div style={{ display: "flex", gap: "0.75rem" }}>
            <button
              type="submit"
              disabled={saving}
              className="sm-btn-primary"
              style={{ flex: 1 }}
            >
              {saving ? "Saving…" : "Save fee"}
            </button>
            <button
              type="button"
              className="sm-btn-ghost"
              onClick={() => navigate(`/tutors/${tutorId}`)}
            >
              Later
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
