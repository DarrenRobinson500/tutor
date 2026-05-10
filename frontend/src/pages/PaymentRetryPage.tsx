import { useParams, useNavigate, Link } from "react-router-dom";
import { PaymentSetup } from "../components/PaymentSetup/PaymentSetup";
import { apiFetch } from "../utils/apiFetch";

export function PaymentRetryPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  async function handleSetupComplete() {
    // After card update, trigger the retry charge immediately
    const res = await apiFetch(`/api/payments/${id}/retry/`, { method: "POST" });
    const data = await res.json();

    if (res.ok && data.success) {
      navigate(`/payments/${id}/receipt`);
    } else {
      // Stay on page — PaymentSetup's onComplete already showed success state;
      // show a brief error by navigating back to authorise
      navigate(`/payments/${id}/authorise`);
    }
  }

  return (
    <div style={{ minHeight: "100vh", background: "var(--sm-bg, #FFFBF5)", fontFamily: "Inter, system-ui, sans-serif" }}>
      <nav style={{ display: "flex", alignItems: "center", padding: "0 2rem", height: 60, background: "#fff", borderBottom: "1px solid var(--sm-border, #E8E0D6)" }}>
        <Link to="/">
          <img src="/subjectmatter_wordmark.svg" alt="SubjectMatter" style={{ height: 28 }} />
        </Link>
      </nav>

      <main style={{ maxWidth: 480, margin: "2rem auto", padding: "0 1rem" }}>
        <div className="sm-card" style={{ padding: "2rem" }}>
          <h1 style={{ fontFamily: "var(--font-display, Lora, serif)", fontSize: "1.4rem", fontWeight: 600, marginBottom: "0.5rem" }}>
            Update your payment details
          </h1>
          <p style={{ color: "var(--sm-text-muted, #8A7F74)", fontSize: "0.9rem", marginBottom: "1.5rem" }}>
            Your previous card was declined. Please add a new card to complete payment.
          </p>

          <PaymentSetup
            mode="update"
            onComplete={handleSetupComplete}
            onCancel={() => navigate(-1)}
          />
        </div>
      </main>
    </div>
  );
}
