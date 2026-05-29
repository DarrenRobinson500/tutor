import { useEffect, useState } from "react";
import { Layout } from "./components/Layout";
import { apiFetch } from "../utils/apiFetch";

interface ParentFeedbackItem {
  id: number;
  parent_name: string;
  parent_email: string;
  body: string;
  created_at: string;
  admin_response: string | null;
  responded_at: string | null;
  responded_by_name: string | null;
}

function fmtDate(iso: string) {
  return new Date(iso).toLocaleDateString("en-AU", { day: "numeric", month: "short", year: "numeric" });
}

export default function AdminParentFeedbackPage() {
  const [items, setItems] = useState<ParentFeedbackItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [responding, setResponding] = useState<number | null>(null);
  const [responseText, setResponseText] = useState<Record<number, string>>({});

  useEffect(() => {
    apiFetch("/api/parent-feedback/?days=180")
      .then(r => r.json())
      .then(d => setItems(Array.isArray(d) ? d : []))
      .catch(() => setItems([]))
      .finally(() => setLoading(false));
  }, []);

  async function handleRespond(id: number) {
    const text = (responseText[id] || "").trim();
    if (!text) return;
    setResponding(id);
    try {
      const res = await apiFetch(`/api/parent-feedback/${id}/respond/`, {
        method: "POST",
        body: JSON.stringify({ response: text }),
      });
      const data = await res.json();
      if (res.ok) {
        setItems(prev => prev.map(item => item.id === id ? data : item));
        setResponseText(prev => { const n = { ...prev }; delete n[id]; return n; });
      }
    } finally {
      setResponding(null);
    }
  }

  return (
    <Layout>
      <div className="container py-4" style={{ maxWidth: 860 }}>
        <h1 style={{ fontFamily: "Lora, Georgia, serif", fontSize: "1.875rem", fontWeight: 700, color: "#2D2D2D", marginBottom: "0.25rem" }}>Parent Feedback</h1>
        <p className="text-muted mb-4" style={{ fontSize: 14 }}>Last 180 days</p>
        {loading ? (
          <p className="text-muted">Loading…</p>
        ) : items.length === 0 ? (
          <div className="rounded p-4 text-center" style={{ background: "#f8f9fa", border: "1px solid #dee2e6", color: "#6c757d" }}>
            No parent feedback in the last 180 days.
          </div>
        ) : (
          <div className="d-flex flex-column gap-3">
            {items.map(item => (
              <div key={item.id} className="rounded p-3" style={{ background: "#fff", border: "1px solid #e8e0d6" }}>
                <div className="d-flex justify-content-between align-items-start flex-wrap gap-2 mb-2">
                  <div>
                    <span className="fw-semibold" style={{ fontSize: "0.9rem" }}>{item.parent_name}</span>
                    <span className="text-muted ms-2" style={{ fontSize: "0.82rem" }}>{item.parent_email}</span>
                  </div>
                  <div className="d-flex align-items-center gap-2">
                    {item.admin_response
                      ? <span className="badge" style={{ background: "#d1e7dd", color: "#0a3622", fontSize: 11 }}>Responded</span>
                      : <span className="badge" style={{ background: "#fff3cd", color: "#664d03", fontSize: 11 }}>Needs response</span>}
                    <span className="text-muted" style={{ fontSize: "0.78rem" }}>{fmtDate(item.created_at)}</span>
                  </div>
                </div>

                <p style={{ fontSize: 14, color: "#333", lineHeight: 1.65, marginBottom: item.admin_response ? 12 : 16 }}>
                  {item.body}
                </p>

                {item.admin_response && (
                  <div style={{ borderLeft: "3px solid #E87722", paddingLeft: 12, marginBottom: 16 }}>
                    <p style={{ fontSize: 11, fontWeight: 600, color: "#E87722", marginBottom: 3, textTransform: "uppercase", letterSpacing: "0.04em" }}>
                      Your response · {item.responded_at ? fmtDate(item.responded_at) : ""}
                    </p>
                    <p style={{ fontSize: 14, color: "#333", lineHeight: 1.65, marginBottom: 0 }}>{item.admin_response}</p>
                  </div>
                )}

                <div className="d-flex gap-2 align-items-start">
                  <textarea
                    className="form-control form-control-sm"
                    rows={2}
                    placeholder={item.admin_response ? "Update response…" : "Write a response…"}
                    value={responseText[item.id] ?? ""}
                    onChange={e => setResponseText(prev => ({ ...prev, [item.id]: e.target.value }))}
                    style={{ resize: "vertical", fontSize: "0.85rem" }}
                  />
                  <button
                    className="btn btn-sm btn-primary"
                    style={{ whiteSpace: "nowrap" }}
                    disabled={responding === item.id || !(responseText[item.id] || "").trim()}
                    onClick={() => handleRespond(item.id)}
                  >
                    {responding === item.id ? "Sending…" : item.admin_response ? "Update" : "Send"}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </Layout>
  );
}
