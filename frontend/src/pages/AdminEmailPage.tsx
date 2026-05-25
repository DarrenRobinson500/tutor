import { useEffect, useState } from "react";
import { Layout } from "./components/Layout";
import { apiFetch } from "../utils/apiFetch";

interface EmailRecord {
  id: number;
  to_email: string;
  to_name: string;
  subject: string;
  body: string;
  sent_at: string;
  sent_by: string;
  status: string;
  error: string;
}

type RecipientType = "custom" | "all_parents" | "all_tutors" | "all_students";

const RECIPIENT_LABELS: Record<RecipientType, string> = {
  custom: "Custom email address",
  all_parents: "All parents",
  all_tutors: "All tutors",
  all_students: "All students",
};

export function AdminEmailPage() {
  const [records, setRecords] = useState<EmailRecord[]>([]);
  const [loading, setLoading] = useState(true);

  const [recipientType, setRecipientType] = useState<RecipientType>("custom");
  const [toEmail, setToEmail] = useState("");
  const [toName, setToName] = useState("");
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [sending, setSending] = useState(false);
  const [sendResult, setSendResult] = useState<{ sent: number; failed: number } | null>(null);
  const [sendError, setSendError] = useState<string | null>(null);

  function loadEmails() {
    apiFetch("/api/admin-emails/list_emails/")
      .then(r => r.json())
      .then(data => { setRecords(data); setLoading(false); })
      .catch(() => setLoading(false));
  }

  useEffect(() => { loadEmails(); }, []);

  async function handleSend() {
    setSendError(null);
    setSendResult(null);
    setSending(true);
    try {
      const payload: Record<string, string> = { recipient_type: recipientType, subject, body };
      if (recipientType === "custom") {
        payload.to_email = toEmail;
        payload.to_name = toName;
      }
      const res = await apiFetch("/api/admin-emails/send/", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) { setSendError(data.error || "Failed to send."); }
      else {
        setSendResult(data);
        setToEmail(""); setToName(""); setSubject(""); setBody("");
        loadEmails();
      }
    } catch (e: any) {
      setSendError(e.message || "Unexpected error");
    } finally {
      setSending(false);
    }
  }

  return (
    <Layout>
      <div className="container mt-4" style={{ maxWidth: 860 }}>
        <h4 className="mb-4">Emails</h4>

        {/* ── Compose ─────────────────────────────────────────────────────── */}
        <div className="card mb-4">
          <div className="card-header fw-semibold">Compose</div>
          <div className="card-body">
            <div className="mb-3">
              <label className="form-label">Recipients</label>
              <select
                className="form-select"
                value={recipientType}
                onChange={e => setRecipientType(e.target.value as RecipientType)}
              >
                {(Object.keys(RECIPIENT_LABELS) as RecipientType[]).map(k => (
                  <option key={k} value={k}>{RECIPIENT_LABELS[k]}</option>
                ))}
              </select>
            </div>

            {recipientType === "custom" && (
              <div className="row g-2 mb-3">
                <div className="col-sm-6">
                  <input
                    type="email"
                    className="form-control"
                    placeholder="Email address"
                    value={toEmail}
                    onChange={e => setToEmail(e.target.value)}
                  />
                </div>
                <div className="col-sm-6">
                  <input
                    type="text"
                    className="form-control"
                    placeholder="Name (optional)"
                    value={toName}
                    onChange={e => setToName(e.target.value)}
                  />
                </div>
              </div>
            )}

            <div className="mb-3">
              <input
                type="text"
                className="form-control"
                placeholder="Subject"
                value={subject}
                onChange={e => setSubject(e.target.value)}
              />
            </div>

            <div className="mb-3">
              <textarea
                className="form-control"
                rows={6}
                placeholder="Message body"
                value={body}
                onChange={e => setBody(e.target.value)}
              />
            </div>

            {sendError && (
              <div className="alert alert-danger py-2 mb-3" style={{ fontSize: 13 }}>{sendError}</div>
            )}
            {sendResult && (
              <div className="alert alert-success py-2 mb-3" style={{ fontSize: 13 }}>
                Sent {sendResult.sent} email{sendResult.sent !== 1 ? "s" : ""}
                {sendResult.failed > 0 && ` · ${sendResult.failed} failed`}.
              </div>
            )}

            <button
              className="btn btn-primary btn-sm"
              onClick={handleSend}
              disabled={sending}
            >
              {sending ? "Sending…" : "Send"}
            </button>
          </div>
        </div>

        {/* ── History ─────────────────────────────────────────────────────── */}
        <h6 className="text-muted mb-2">Sent</h6>
        {loading ? (
          <div className="d-flex justify-content-center py-4">
            <div className="spinner-border text-primary" role="status" />
          </div>
        ) : records.length === 0 ? (
          <p className="text-muted">No emails sent yet.</p>
        ) : (
          <table className="table table-sm table-bordered" style={{ fontSize: 13 }}>
            <thead className="table-light">
              <tr>
                <th>To</th>
                <th>Subject</th>
                <th>Sent</th>
                <th>By</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {records.map(r => (
                <tr key={r.id}>
                  <td>
                    {r.to_name ? <><strong>{r.to_name}</strong><br /></> : null}
                    <span className="text-muted">{r.to_email}</span>
                  </td>
                  <td>
                    <div>{r.subject}</div>
                    <div className="text-muted" style={{ fontSize: 12, whiteSpace: "pre-wrap", maxHeight: 60, overflow: "hidden" }}>
                      {r.body.slice(0, 120)}{r.body.length > 120 ? "…" : ""}
                    </div>
                  </td>
                  <td style={{ whiteSpace: "nowrap" }}>{new Date(r.sent_at).toLocaleString()}</td>
                  <td>{r.sent_by}</td>
                  <td>
                    {r.status === "failed" ? (
                      <>
                        <span className="text-danger">Failed</span>
                        {r.error && (
                          <div className="text-danger" style={{ fontSize: 11, marginTop: 2 }}>{r.error}</div>
                        )}
                      </>
                    ) : (
                      <span className="text-success">Sent</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </Layout>
  );
}
