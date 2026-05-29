import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { apiFetch } from "../utils/apiFetch";
import { ParentNav } from "./components/ParentNav";
import "./ParentHomePage.css";

interface FeedbackItem {
  id: number;
  body: string;
  created_at: string;
  admin_response: string | null;
  responded_at: string | null;
  responded_by_name: string | null;
}

function fmtDate(iso: string) {
  return new Date(iso).toLocaleDateString("en-AU", { day: "numeric", month: "long", year: "numeric" });
}

export default function ParentFeedbackPage() {
  const { id } = useParams();

  const [items, setItems] = useState<FeedbackItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [body, setBody] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState("");

  useEffect(() => {
    apiFetch("/api/parent-feedback/")
      .then(r => r.json())
      .then(d => setItems(Array.isArray(d) ? d : []))
      .catch(() => setItems([]))
      .finally(() => setLoading(false));
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!body.trim()) return;
    setSubmitting(true);
    setSubmitError("");
    try {
      const res = await apiFetch("/api/parent-feedback/", {
        method: "POST",
        body: JSON.stringify({ body: body.trim() }),
      });
      const data = await res.json();
      if (!res.ok) { setSubmitError(data.error || "Failed to submit."); return; }
      setItems(prev => [data, ...prev]);
      setBody("");
    } catch {
      setSubmitError("Something went wrong.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="ph-page">
      <ParentNav parentId={id!} />

      <div className="ph-body" style={{ maxWidth: 700, margin: "0 auto" }}>
        <h2 style={{ fontFamily: "Lora, Georgia, serif", fontWeight: 700, marginBottom: "0.25rem" }}>Feedback</h2>
        <p className="text-muted mb-4" style={{ fontSize: 15 }}>
          Share anything on your mind — questions, suggestions, or concerns. We read everything and aim to respond within a few days.
        </p>

        {/* Submit form */}
        <div className="card mb-5 border-0" style={{ background: "#FFFBF5", border: "1px solid #F0EAE0 !important" }}>
          <div className="card-body p-4">
            <h5 className="fw-semibold mb-3" style={{ fontSize: 16 }}>Send us a message</h5>
            <form onSubmit={handleSubmit}>
              <textarea
                className="form-control mb-3"
                rows={4}
                placeholder="What's on your mind?"
                value={body}
                onChange={e => setBody(e.target.value)}
                required
                style={{ resize: "vertical" }}
              />
              {submitError && <p className="text-danger mb-2" style={{ fontSize: 14 }}>{submitError}</p>}
              <button className="btn btn-primary" disabled={submitting || !body.trim()}>
                {submitting ? "Sending…" : "Send feedback"}
              </button>
            </form>
          </div>
        </div>

        {/* History */}
        <h5 className="fw-semibold mb-3">Previous feedback</h5>
        {loading ? (
          <p className="text-muted">Loading…</p>
        ) : items.length === 0 ? (
          <p className="text-muted">No feedback yet.</p>
        ) : (
          <div className="d-flex flex-column gap-3">
            {items.map(item => (
              <div key={item.id} className="card border-0" style={{ border: "1px solid #E8E0D6 !important", boxShadow: "0 1px 4px rgba(0,0,0,.05)" }}>
                <div className="card-body p-4">
                  <div className="d-flex justify-content-between align-items-start mb-2">
                    <span className="text-muted" style={{ fontSize: 13 }}>{fmtDate(item.created_at)}</span>
                    {item.admin_response ? (
                      <span className="badge" style={{ background: "#d1e7dd", color: "#0a3622", fontSize: 11 }}>Responded</span>
                    ) : (
                      <span className="badge" style={{ background: "#fff3cd", color: "#664d03", fontSize: 11 }}>Awaiting response</span>
                    )}
                  </div>

                  <p style={{ fontSize: 15, color: "#333", lineHeight: 1.65, marginBottom: item.admin_response ? 16 : 0 }}>
                    {item.body}
                  </p>

                  {item.admin_response && (
                    <div style={{ borderLeft: "3px solid #E87722", paddingLeft: 14, marginTop: 8 }}>
                      <p style={{ fontSize: 12, fontWeight: 600, color: "#E87722", marginBottom: 4, textTransform: "uppercase", letterSpacing: "0.04em" }}>
                        Subject Matter replied
                        {item.responded_at && <span style={{ fontWeight: 400, color: "#888", marginLeft: 8 }}>{fmtDate(item.responded_at)}</span>}
                      </p>
                      <p style={{ fontSize: 15, color: "#333", lineHeight: 1.65, marginBottom: 0 }}>
                        {item.admin_response}
                      </p>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
